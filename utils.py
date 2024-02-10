def send_message(socket, message):
    message = message.encode('ascii').strip()
    # Allowing message length up to 4 bytes, most significant byte at the start
    message_length = len(message).to_bytes(4, 'big')
    # Sending the length of message as well
    socket.sendall(message_length + message)

def receive_message(socket):
    data = bytearray()
    message_length = int.from_bytes(socket.recv(4), 'big')
    while len(data) < message_length:
        chunk = socket.recv(1024)
        if not chunk:
            break
        data.extend(chunk)
    return data.decode('ascii').strip()


def sanitize(value):
    if not value or value.isspace():
        return False
    for char in value:
        if not char.isalnum() and not char.isspace():
            return False
    return True