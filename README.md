# Secure Server - Client 

This app is built with vanilla Python. This has a server and client architecture with encrypted communication using SSL. It supports basic CRUD operations for a key value vault. It also uses hashing to check data integrity in storage. Basic rate limiting is also implemented avoid Denial of Service scenario. It also uses multi-threading to handle several clients concurrently. Client gui is built with Tkinter. 

## Features

- Secure communication between client and server using SSL.
- Key-value store operations: PUT, GET, DELETE
- GUI for client interactions.

## Prerequisites

- Python 3.x installed on your system.
- OpenSSL for generating SSL certificates.

## Installation

Clone the repository: 

```
git clone <repository-url>
cd <application-directory>
```

## Setup

### Generating SSL Certificates

Before running the server or client, generate SSL certificates:

```bash
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes
```

Place the `cert.pem` and `key.pem` in the directory. The client needs access to the `cert.pem` for verifying the server's identity.

### Starting the Server

Use the `startServer.sh` script to launch the server. Provide the port number as an argument:

```bash
chmod +x startServer.sh
./startServer.sh <port>
```

Replace `<port>` with the desired port number for the server to listen on.

### Starting the Client

To start the client, use the `startClient.sh` script with the host and port as arguments:

```bash
chmod +x startClient.sh
./startClient.sh <host> <port>
```

Replace `<host>` with the server's hostname or IP address and `<port>` with the port number the server is listening on.

## Usage

After starting the server and client, use the client GUI to connect to the server and perform operations such as PUT, GET, and DELETE.
