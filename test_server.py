import unittest
from unittest.mock import patch, MagicMock, call
from collections import defaultdict
import threading
from server import Server

class TestServer(unittest.TestCase):
    def setUp(self):
        """Set up test environment"""
        self.port = 12345
        
        # Create and start patches
        self.ssl_context_patcher = patch('server.SSLContext')
        self.socket_patcher = patch('server.socket')
        self.logger_patcher = patch('server.configure_logger')
        
        # Get mocks from patches
        self.mock_ssl_context = self.ssl_context_patcher.start()
        self.mock_socket = self.socket_patcher.start()
        self.mock_logger = self.logger_patcher.start()
        
        # Set up mock returns
        mock_logger = MagicMock()
        self.mock_logger.return_value = mock_logger
        
        # Set up mock socket
        mock_raw_socket = MagicMock()
        self.mock_socket.return_value = mock_raw_socket
        
        # Set up mock SSL context
        mock_ssl_socket = MagicMock()
        self.mock_ssl_context.return_value.wrap_socket.return_value = mock_ssl_socket
        
        # Initialize server with mocked components
        self.server = Server(self.port)
        
        # Set up test client socket
        self.client_socket = MagicMock()
        
        # Reset rate limiting
        self.server.request_timestamps = defaultdict(list)

    def tearDown(self):
        """Clean up test environment"""
        # Stop all patches
        self.ssl_context_patcher.stop()
        self.socket_patcher.stop()
        self.logger_patcher.stop()

        # Clear all server data structures
        if hasattr(self, 'server'):
            # Clear dictionaries and sets
            self.server.kv_store.clear()
            self.server.request_timestamps.clear()
            self.server.active_ids.clear()
            
            # Close any open sockets
            if hasattr(self.server, 'secure_socket'):
                self.server.secure_socket.close()
                self.server.secure_socket = None
            if hasattr(self.server, 'server_socket'):
                self.server.server_socket.close()
                self.server.server_socket = None

            # Clear any client threads
            for thread in self.server.client_threads:
                if thread.is_alive():
                    # Give threads 1 second to finish
                    thread.join(timeout=1.0)  
            self.server.client_threads.clear()

            # Release locks if they're acquired
            try:
                self.server.kv_store_lock.release()
            except RuntimeError:
                # Lock wasn't acquired
                pass  
            try:
                self.server.request_timestamps_lock.release()
            except RuntimeError:
                # Lock wasn't acquired
                pass  

        # Clear mock objects
        if hasattr(self, 'client_socket'):
            self.client_socket = None

        # Clear server instance
        self.server = None

        # Clear mock references
        self.mock_ssl_context = None
        self.mock_socket = None
        self.mock_logger = None


    def test_initialization(self):
        """Test server initialization"""
        self.assertEqual(self.server.port, self.port)
        self.assertEqual(self.server.kv_store, {})
        self.assertIsInstance(self.server.request_timestamps, defaultdict)
        self.assertIsInstance(self.server.kv_store_lock, type(threading.Lock()))
        self.assertIsInstance(self.server.request_timestamps_lock, type(threading.Lock()))

    @patch('server.receive_message')
    @patch('server.send_message')
    def test_handle_client_connection_valid(self, mock_send, mock_receive):
        """Test handling valid client connection"""
        mock_receive.side_effect = ["CONNECT client1", None]
        addr = ('127.0.0.1', 54321)
        
        # Reset rate limiting for this specific test
        self.server.request_timestamps.clear()
        
        # Mock the rate_limit method to always return False
        with patch.object(self.server, 'rate_limit', return_value=False):
            self.server.handle_client_connection(self.client_socket, addr)
            
            expected_calls = [
                call(self.client_socket, "CONNECT: OK")
            ]
            self.assertEqual(mock_send.call_args_list, expected_calls)
            self.assertNotIn("client1", self.server.active_ids)
    

    @patch('server.receive_message')
    @patch('server.send_message')
    def test_handle_client_requests_rate_limit(self, mock_send, mock_receive):
        """Test rate limiting response"""
        client_id = "test_client"
        
        # Mock rate_limit to return True (limit exceeded)
        with patch.object(self.server, 'rate_limit', return_value=True):
            self.server.handle_client_requests(self.client_socket, client_id)
        
        # Should send rate limit message and break
        mock_send.assert_called_once_with(
            self.client_socket, 
            "ERROR: TOO MANY REQUESTS, CONNECTION DROPPED"
        )

    @patch('server.receive_message')
    @patch('server.send_message')
    def test_handle_client_requests_empty_message(self, mock_send, mock_receive):
        """Test handling of empty message"""
        client_id = "test_client"
        
        # Mock receive_message to return None (empty message)
        mock_receive.return_value = None
        
        with patch.object(self.server, 'rate_limit', return_value=False):
            self.server.handle_client_requests(self.client_socket, client_id)
        
        # Should break without sending any message
        mock_send.assert_not_called()


    @patch('server.receive_message')
    @patch('server.send_message')
    def test_handle_client_requests_put(self, mock_send, mock_receive):
        """Test PUT request handling sequence"""
        client_id = "test_client"
        
        # Let's test a single PUT request followed by termination
        mock_receive.side_effect = [
            "PUT test_key",    # First receive: Command and key
            None              # Second receive: End the handling loop
        ]
        
        # Test just the PUT handler directly
        key = "test_key"
        value = "test_value"
        hashed_value = "hash_value"
        
        with patch.object(self.server, 'rate_limit', return_value=False):
            self.server.handle_put_request(self.client_socket, key, value, hashed_value)
        
        # Verify the results
        self.assertEqual(self.server.kv_store[key], (value, hashed_value))
        mock_send.assert_called_once_with(self.client_socket, "PUT: OK")


    @patch('server.receive_message')
    @patch('server.send_message')
    def test_handle_get_request_existing_key(self, mock_send, mock_receive):
        """Test GET request for existing key"""
        # Set up test data
        key = "test_key"
        value = "test_value"
        hashed_value = "hash_value"
        self.server.kv_store[key] = (value, hashed_value)
        
        # Call the method directly
        self.server.handle_get_request(self.client_socket, key)
        
        # Verify the calls
        expected_calls = [
            call(self.client_socket, "test_value"),
            call(self.client_socket, "hash_value")
        ]
        self.assertEqual(mock_send.call_args_list, expected_calls)

    @patch('server.receive_message')
    @patch('server.send_message')
    def test_handle_get_request_nonexistent_key(self, mock_send, mock_receive):
        """Test GET request for non-existent key"""
        # Try to get a key that doesn't exist
        key = "nonexistent_key"
        
        # Call the method directly
        self.server.handle_get_request(self.client_socket, key)
        
        # Verify the error message
        mock_send.assert_called_once_with(self.client_socket, "GET: KEY DOES NOT EXIST")


    @patch('server.receive_message')
    @patch('server.send_message')
    def test_handle_delete_request_existing_key(self, mock_send, mock_receive):
        """Test DELETE request for existing key"""
        # Set up test data
        key = "test_key"
        value = "test_value"
        hashed_value = "hash_value"
        self.server.kv_store[key] = (value, hashed_value)
        
        # Call the method directly
        self.server.handle_delete_request(self.client_socket, key)
        
        # Verify the delete operation
        self.assertNotIn(key, self.server.kv_store)
        mock_send.assert_called_once_with(self.client_socket, "DELETE: OK")

    @patch('server.receive_message')
    @patch('server.send_message')
    def test_handle_delete_request_nonexistent_key(self, mock_send, mock_receive):
        """Test DELETE request for non-existent key"""
        # Try to delete a key that doesn't exist
        key = "nonexistent_key"
        
        # Call the method directly
        self.server.handle_delete_request(self.client_socket, key)
        
        # Verify the error message
        mock_send.assert_called_with(self.client_socket, "DELETE: Key does not exist")




if __name__ == '__main__':
    unittest.main()


