from socket import socket, AF_INET, SOCK_STREAM, SOL_SOCKET, SO_REUSEADDR, timeout
from ssl import SSLContext, PROTOCOL_TLS_SERVER
import threading
from collections import defaultdict
import sys, time
from logger_config import configure_logger
from utils import send_message, receive_message, sanitize


"""
Class KeyValueServer is handling server side.
Class methods are defined for each server action 
for better readability and modular code.

"""

class Server:
    # Constructor 
    def __init__(self, port):
        
        # Server port number
        self.port = port
        # Using TCP sockets
        self.server_socket = socket(AF_INET, SOCK_STREAM)
        self.server_socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        self.server_socket.bind(('', self.port))
        # Server is listening for connections
        self.server_socket.listen(5)
        #self.server_socket.settimeout(1.0)
        

        # Creating context for the socket for secure communication with SSL module
        self.context = SSLContext(PROTOCOL_TLS_SERVER)
        # Loading certificate and key from this folder. IN PRODUCTION ENV, THIS SHOULD NOT BE THE CASE
        self.context.load_cert_chain(certfile='cert.pem', keyfile='key.pem')
        # Wrapping the socket for secure communication with TLS PROTOCOL
        self.secure_socket = self.context.wrap_socket(self.server_socket, server_side=True)

        # Initializing the logger
        self.logger = configure_logger()

        # Locks for the thread safe operations
        self.kv_store_lock = threading.Lock()
        self.request_timestamps_lock = threading.Lock()

        # To manage threads
        self.client_threads =[]

        # Shared resources
        self.kv_store = {}
        self.request_timestamps = defaultdict(list)
        self.active_ids = set()


    # This handles client connection
    def handle_client_connection(self, client_socket, addr):
        self.logger.info(f"Handling client {addr} connection")
        client_id = None
        try:
            message = receive_message(client_socket)
            command, client_id = message.split(" ", 1)
            id_validation = sanitize(client_id)

            if command != "CONNECT" or not id_validation:
                send_message(client_socket, "CONNECT: ERROR")
                return
            
            if client_id in self.active_ids:
                send_message(client_socket, "CONNECT: ID already taken")
                return 
            
            self.active_ids.add(client_id)
            send_message(client_socket, "CONNECT: OK")
            self.handle_client_requests(client_socket, client_id)
            
        except Exception as e:
            self.logger.error(f"Error handling client {addr}: {str(e)}")
        finally:
            if client_id and client_id in self.active_ids:
                self.active_ids.discard(client_id)
            client_socket.close()


    def handle_client_requests(self, client_socket, client_id):
        while True:
            if self.rate_limit(client_id):
                send_message(client_socket, "ERROR: TOO MANY REQUESTS, CONNECTION DROPPED")
                break

            message = receive_message(client_socket)
            if not message:
                break

            try:
                command, key = (message.split(" ", 1) + [None])[:2]
                
                if command == "PUT" and key and sanitize(key):
                    value = receive_message(client_socket)
                    hashed_value = receive_message(client_socket)
                    self.handle_put_request(client_socket, key, value, hashed_value)

                elif command == "GET" and key and sanitize(key):
                    self.handle_get_request(client_socket, key)
                
                elif command == "DELETE" and key and sanitize(key):
                    self.handle_delete_request(client_socket, key)

                elif command == "DISCONNECT":
                    send_message(client_socket, "DISCONNECT: OK")
                    break
            except ValueError as e: 
                self.logger.error(f"Error processing request from {client_id}: {str(e)}")
                send_message(client_socket, "Error: Invalid request format")
            except Exception as e:
                self.logger.error(f"Unexpected error from {client_id}: {str(e)}")
                send_message(client_socket, "Error: Server encountered an expected error")


        
    def rate_limit(self, client_id):
        with self.request_timestamps_lock:
            now = time.time()
            timestamps = self.request_timestamps[client_id]
            timestamps = [timestamp for timestamp in timestamps if now - timestamp < 60]
            self.request_timestamps[client_id] = timestamps

            if len(timestamps) >= 10:
                return True
            else:
                timestamps.append(now)
                return False

    def handle_put_request(self, client_socket, key, value, hashed_value):
        with self.kv_store_lock:
            self.kv_store[key] = (value, hashed_value)
            send_message(client_socket, "PUT: OK")
    
    def handle_get_request(self, client_socket, key):
        with self.kv_store_lock:
            if key in self.kv_store:
                value, hashed_value = self.kv_store[key]
                send_message(client_socket, f"{value}")
                send_message(client_socket, f"{hashed_value}")
            elif key not in self.kv_store:
                send_message(client_socket, "GET: KEY DOES NOT EXIST")
            else:
                send_message(client_socket, "GET: ERROR")

    def handle_delete_request(self, client_socket, key):
        with self.kv_store_lock:
            if key not in self.kv_store:
                send_message(client_socket, "DELETE: Key does not exist")

            if key in self.kv_store:
                del self.kv_store[key]
                send_message(client_socket, "DELETE: OK")
            else:
                send_message(client_socket, "DELETE: ERROR")

    def run(self):
        self.logger.info(f"Server is listening at {self.port}")
        # Set a timeout for accept to periodically check for shutdown
        self.secure_socket.settimeout(10)  

        try:
            while True:
                try:
                    client_socket, addr = self.secure_socket.accept()
                    self.logger.info(f"Accepted connection from {addr}")
                    client_thread = threading.Thread(target=self.handle_client_connection, args=(client_socket, addr))
                    client_thread.daemon = True 
                    client_thread.start()
                    self.client_threads.append(client_thread)
                except timeout:
                    continue
                except KeyboardInterrupt:
                    self.logger.info("Keyboard interrupt: Shutting down the server")
                    break  
        finally:
            self.shutdown()




    def shutdown(self):
        for thread in self.client_threads:
            thread.join()
        self.logger.info("Server shutdown completed")


    
        
            
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 server.py <PORT>")
        sys.exit(1)
            
    port = int(sys.argv[1])
    server = Server(port)

    server.run()


    