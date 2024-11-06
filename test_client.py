import unittest
from unittest.mock import patch, MagicMock, call
import hashlib
from socket import AF_INET, SOCK_STREAM
from client import Client

class TestClient(unittest.TestCase):
    def setUp(self):
        self.host = 'localhost'
        self.port = 12345
        
        # Start SSL context patch for setUp
        self.ssl_patcher = patch('client.ssl.create_default_context')
        self.mock_ssl = self.ssl_patcher.start()
        
        # Start verify locations patch
        self.verify_patcher = patch('client.ssl.SSLContext.load_verify_locations')
        self.mock_verify = self.verify_patcher.start()
        
        # Create client with mocked SSL
        self.client = Client(self.host, self.port)

    def tearDown(self):
        """Clean up all resources after each test"""
        # Stop SSL-related patches
        self.ssl_patcher.stop()
        self.verify_patcher.stop()
    
        # Close any open socket
        if hasattr(self, 'client') and self.client.client_socket:
            self.client.client_socket.close()
            self.client.client_socket = None
    
        # Clear any mocks created during tests
        self.client = None

    @patch('client.socket')
    @patch('client.receive_message')
    @patch('client.send_message')
    def test_connect_success(self, mock_send, mock_receive, mock_socket):
        """Test successful connection"""
        # Set up mocks
        mock_raw_socket = MagicMock()
        mock_wrapped_socket = MagicMock()
        
        # Set up the chain of returns
        mock_socket.return_value = mock_raw_socket
        self.mock_ssl.return_value.wrap_socket.return_value = mock_wrapped_socket
        mock_receive.return_value = "CONNECT: OK"
        
        # Call connect
        result = self.client.connect("client1")
        
        # Verify connection sequence
        mock_socket.assert_called_once_with(AF_INET, SOCK_STREAM)
        mock_wrapped_socket.connect.assert_called_once_with((self.host, self.port))
        mock_send.assert_called_once_with(mock_wrapped_socket, "CONNECT client1")
        self.assertEqual(result, "CONNECT: OK")
        self.assertEqual(self.client.client_socket, mock_wrapped_socket)

    @patch('client.socket')
    @patch('client.receive_message')
    @patch('client.send_message')
    def test_connect_id_taken(self, mock_send, mock_receive, mock_socket):
        """Test connection with taken ID"""
        # Set up mocks
        mock_raw_socket = MagicMock()
        mock_wrapped_socket = MagicMock()
        
        # Set up the chain of returns
        mock_socket.return_value = mock_raw_socket
        self.mock_ssl.return_value.wrap_socket.return_value = mock_wrapped_socket
        mock_receive.return_value = "CONNECT: ID already taken"
        
        # Call connect
        result = self.client.connect("client1")
        
        # Verify behavior
        mock_socket.assert_called_once_with(AF_INET, SOCK_STREAM)
        mock_send.assert_called_once_with(mock_wrapped_socket, "CONNECT client1")
        mock_wrapped_socket.close.assert_called_once()
        self.assertEqual(result, "CONNECT: ID already taken")
        self.assertIsNone(self.client.client_socket)
  

    @patch('client.receive_message')
    @patch('client.send_message')
    def test_put_success(self, mock_send, mock_receive):
        """Test successful PUT operation"""
        mock_receive.return_value = "PUT: OK"
        key = "test_key"
        value = "test_value"
        hashed_value = hashlib.sha256(value.encode()).hexdigest()
        
        response = self.client.put(key, value)
        
        expected_calls = [
            call(self.client.client_socket, f"PUT {key}"),
            call(self.client.client_socket, value),
            call(self.client.client_socket, hashed_value)
        ]
        mock_send.assert_has_calls(expected_calls)
        self.assertEqual(response, "PUT: OK")

    
    @patch('client.receive_message')
    @patch('client.send_message')
    def test_get_success(self, mock_send, mock_receive):
        """Test successful GET operation"""
        value = "test_value"
        hashed_value = hashlib.sha256(value.encode()).hexdigest()
        mock_receive.side_effect = [value, hashed_value]
        
        response = self.client.get("test_key")
        
        mock_send.assert_called_with(self.client.client_socket, "GET test_key")
        self.assertEqual(response, value)

    @patch('client.receive_message')
    @patch('client.send_message')
    def test_get_nonexistent_key(self, mock_send, mock_receive):
        """Test GET with non-existent key"""
        mock_receive.return_value = "GET: KEY DOES NOT EXIST"
        
        response = self.client.get("nonexistent_key")
        
        self.assertEqual(response, "GET: KEY DOES NOT EXIST")

    @patch('client.receive_message')
    @patch('client.send_message')
    def test_delete_success(self, mock_send, mock_receive):
        """Test successful DELETE operation"""
        mock_receive.return_value = "DELETE: OK"
        
        response = self.client.delete("test_key")
        
        mock_send.assert_called_with(self.client.client_socket, "DELETE test_key")
        self.assertEqual(response, "DELETE: OK")

    
    @patch('client.receive_message')
    @patch('client.send_message')
    def test_disconnect(self, mock_send, mock_receive):
        """Test disconnect operation"""
        # Set up mocks
        mock_socket = MagicMock()
        self.client.client_socket = mock_socket
        mock_receive.return_value = "DISCONNECT: OK"
        
        # Perform disconnect
        response = self.client.disconnect()
        
        # Verify correct message was sent
        mock_send.assert_called_once_with(mock_socket, "DISCONNECT")
        
        # Verify response and socket cleanup
        self.assertEqual(response, "DISCONNECT: OK")
        self.assertIsNone(self.client.client_socket)
        mock_socket.close.assert_called_once()

    @patch('client.receive_message')
    @patch('client.send_message')
    def test_disconnect_not_connected(self, mock_send, mock_receive):
        """Test disconnect when not connected"""
        # Ensure client is not connected
        self.client.client_socket = None
        
        # Perform disconnect
        response = self.client.disconnect()
        
        # Verify no messages were sent
        mock_send.assert_not_called()
        mock_receive.assert_not_called()
        
        # Verify correct response
        self.assertEqual(response, "Connection not established")


if __name__ == '__main__':
    unittest.main()
