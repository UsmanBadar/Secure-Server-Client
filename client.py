# Import socket library
from socket import socket, AF_INET, SOCK_STREAM
import ssl
import hashlib
from utils import send_message, receive_message

"""
This is Client Class and here each client action is 
written as a separate method for better readability and modular structure.

"""

class Client:
    # Constructor
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.client_socket = None

        # Create a SSL context
        self.context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        # Disabling it for checking host name
        self.context.check_hostname = False
        # Loading the server certificate
        self.context.load_verify_locations('cert.pem')

    # Handling connection with server
    def connect(self, client_id):
        try:
            raw_socket = socket(AF_INET, SOCK_STREAM)
            self.client_socket = self.context.wrap_socket(raw_socket, server_hostname=self.host)
            self.client_socket.connect((self.host, self.port))
            send_message(self.client_socket, f"CONNECT {client_id}")
            response = receive_message(self.client_socket)

            if response == "CONNECT: ERROR" or response == "CONNECT: ID already taken":
                self.close()       
                return response
            
            return response
        except Exception as e:
            return f"Failed to connect: {str(e)}. Try again"

    # PUT method    
    def put(self, key, value):
        try:
            # Compute the hash value
            sha = hashlib.sha256(value.encode()).hexdigest()

            # Send the key, value and hash value
            send_message(self.client_socket, f"PUT {key}")
            send_message(self.client_socket, f"{value}")
            send_message(self.client_socket, f"{sha}")

            response = receive_message(self.client_socket)
            if response == "PUT: OK" or response == "PUT: ERROR":
                return response
            else:
                self.disconnect()
                return "An error occurred"
        except OSError as e:
            return f"Failed to process command: {str(e)}"
 
    # GET method     
    def get(self, key):
        try: 
            send_message(self.client_socket, f"GET {key}")
            value = receive_message(self.client_socket)
            if value == "GET: ERROR":
                return value
            if value ==  "GET: KEY DOES NOT EXIST":
                return value
            if value == "ERROR: TOO MANY REQUESTS, CONNECTION DROPPED":
                return value
            if value:
                hashed_value = receive_message(self.client_socket)
                computed_hash = hashlib.sha256(value.encode()).hexdigest()
    
                if computed_hash == hashed_value:
                    return value
                else:
                    return "Error: Data has been modified"
            else:
                self.disconnect()
                return "An error occurred"
        except OSError as e:
            return f"Failed to process command: {str(e)}"
 
    # DELETE method 
    def delete(self, key):
        try: 
            send_message(self.client_socket, f"DELETE {key}")
            response = receive_message(self.client_socket)
            if response == "DELETE: OK" or response == "DELETE: ERROR" or response == "DELETE: Key does not exist":
                return response
            else:
                self.disconnect()
                return "An error occurred"
        except OSError as e:
            return f"Failed to process command: {str(e)}"

    # DISCONNECT method 
    def disconnect(self):
        if self.client_socket:
            try:
                send_message(self.client_socket, "DISCONNECT")
                response = receive_message(self.client_socket)
                self.close()
                return response
            except OSError as e:
                return f"Failed to process command: {str(e)}"
        else:
            return "Connection not established"

    # For closing the socket
    def close(self):
        if self.client_socket:   
            self.client_socket.close()
            self.client_socket = None
    
        