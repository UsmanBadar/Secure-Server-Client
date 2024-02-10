import sys
import tkinter as tk
# Using RegEx for input validation
import re 
from client import Client

"""
This ClientGUI class for handling the client gui.
This uses tkinter for creating the gui. 
This also manages the input validation as well.

"""


class ClientGUI:
    # Constructor
    def __init__(self, host, port):
        # Creating a client instance
        self.client = Client(host, port)
        # Creating a tk instance class
        self.root = tk.Tk()
        self.root.title("Client App")
        self.root.geometry("800x500")

        # Creating Client ID input field, connect and disconnect buttons
        self.create_label(0, 0, "Enter Your Client ID:")
        self.entry_client_id = self.create_entry(0, 1)
        self.connect_button = self.create_button(0, 2, "Connect", self.connect_client)
        self.disconnect_button = self.create_button(0, 3, "Disconnect", self.disconnect, tk.DISABLED)

        # Creating value label and input field for PUT method
        self.label_value = self.create_label(5, 0, "Value:")
        self.entry_value = self.create_entry(5, 1)
        # Hiding these for now, will display when command is PUT in dropdown menu
        self.label_value.grid_remove()
        self.entry_value.grid_remove()

        # Creating an output text box for server responses
        self.create_label(7, 0, "Output:")
        self.output = self.create_text(7, 1, padx=30, pady=30)


    # Class method for creating label
    def create_label(self, row, column, text):
        label = tk.Label(self.root, text=text)
        label.grid(row=row, column=column)
        return label


    # Class method for creating input field
    def create_entry(self, row, column):
        entry = tk.Entry(self.root)
        entry.grid(row=row, column=column)
        return entry


    # Class method for creating a button
    def create_button(self, row, column, text, command, state = tk.NORMAL):
        button = tk.Button(self.root, text=text, command=command, state = state)
        button.grid(row=row, column=column)
        return button


    # Class method for creating a text box
    def create_text(self, row, column, padx, pady):
        text = tk.Text(self.root, wrap=tk.WORD, height=15, width=50)
        text.grid(row=row, column=column, padx=padx, pady=pady)
        return text


    # This method will display PUT command Value field when dropdown option is PUT
    def update_gui(self, *args):
        command = self.command_var.get()
        if command == "PUT":
            # Show the Value label and entry when the command is PUT in dropdown menu
            self.label_value.grid()
            self.entry_value.grid()
        else:
            # Hide the Value label and entry for other commands
            self.label_value.grid_remove()
            self.entry_value.grid_remove()


    # For user input validation, any input must contain letters or numbers. 
    def validate_input(self, input_str, input_name):
        if not input_str:
            return f"Error: {input_name} must be provided", False
        elif not re.match(r'^[a-zA-Z0-9\s]+$', input_str.strip()):
            return f"Error: {input_name} must contain letters and numbers only", False
        else:
            return input_str, True


    # Handling connect button click
    def connect_client(self):
        client_id, is_valid = self.validate_input(self.entry_client_id.get().strip(), "Client ID")
        if not is_valid:
            self.output.insert(tk.END, f"{client_id}\n")
            return 
        
        # Displaying server response
        response = self.client.connect(client_id)
        self.output.insert(tk.END, f"{response}\n")

        # If response is OK, then displaying dropdown for client commands
        if response == "CONNECT: OK":
            self.connect_button.config(state=tk.DISABLED)
            self.disconnect_button.config(state=tk.NORMAL)
            
            # Creating dropdown for PUT, GET and DELETE
            self.create_label(3, 0, "Select a Method:")
            self.command_var = tk.StringVar()
            self.command_var.set("SELECT")
            self.command_var.trace('w', self.update_gui)
            self.dropdown = tk.OptionMenu(self.root, self.command_var, "PUT", "GET", "DELETE")
            self.dropdown.grid(row=3, column=1)

            # Creating input field and label for key
            self.create_label(4, 0, "Key:")
            self.entry_key = self.create_entry(4, 1)

            # Creating send button to send the command to server
            self.send_button = self.create_button(6, 1, "Send", self.send_command, state=tk.NORMAL)
        else:
            self.client.close()
            

    # Send command method to send the command to server
    def send_command(self):
        command = self.command_var.get()
        response = ""

        # A command must be valid validation
        if command == "SELECT":
            self.output.insert(tk.END, "Error: A method must be selected\n")
            return
        
        # Key must be valid validation
        key, valid_key = self.validate_input(self.entry_key.get().strip(), "Key")
        if not valid_key:
            self.output.insert(tk.END, f"{key}\n")
            return
        
        # Sending commands to server 
        if command == "PUT":
            # PUT value validation
            value, valid_value = self.validate_input(self.entry_value.get().strip(), "Value")
            if not valid_value:
                self.output.insert(tk.END, f"{value}\n")
                return
            else:
                response = self.client.put(key, value)
        elif command == "GET":
            response = self.client.get(key)
        elif command == "DELETE":
            response = self.client.delete(key)
        else:
            self.output.insert(tk.END, "An error occurred, try again.\n")
            self.client.close()
            return 
        # Displaying server response
        self.output.insert(tk.END, f"{response}\n") 


    # Method for handling disconnect button    
    def disconnect(self):
        response = self.client.disconnect()
        self.disconnect_button.config(state=tk.DISABLED)
        self.send_button.config(state=tk.DISABLED)
        self.output.insert(tk.END, f"Server: {response}\n")


    # Method to start tkInter event loop 
    def run(self):
        self.root.mainloop()





if __name__ == "__main__":
    # Checking command line arguments
    if len(sys.argv) < 3:
        print("Provide Host and port number values.")
        sys.exit(1)
    try:
        host = sys.argv[1]
        port = int(sys.argv[2])
        app = ClientGUI(host, port)
        app.run()
    except (tk.TclError, IndexError, ValueError, OSError) as e:
        print(f"An error occurred: {str(e)}")
