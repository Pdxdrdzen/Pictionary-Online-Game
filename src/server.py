import socket
import threading
from http import client

SERVER_HOST='127.0.0.1'
SERVER_PORT=12345

server=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1) #restart bugfix
server.bind((SERVER_HOST,SERVER_PORT))
server.listen()

clients=[]
print(f"TCP server listening on {SERVER_HOST}:{SERVER_PORT}")

def handle_client(client_socket,client_addr): #client handling/connections
    print(f"Client {client_socket} connected")
    clients.append(client_socket)
    while True:
        try:
            message = client_socket.recv(1024) #packet size 1024
            if not message:
                break
            print(f"From {client_addr}:{message}")
            for client in clients:
                try:
                    client.send(f"echo: {message}".encode('utf-8')) #echo the received message through all clients
                except:
                    clients.remove(client)
        except:
            break
    print(f"Client {client_addr} disconnected") # when clients socket isnt available - the client has probably disconnected
    if client_socket in clients:
        clients.remove(client_socket)
    client_socket.close()
try:
    while True:
        client_socket, client_addr = server.accept()
        client_thread = threading.Thread(target=handle_client, args=(client_socket,client_addr))
        client_thread.daemon=True #Automatically killing background threads when the main thread has ended
        client_thread.start()
except KeyboardInterrupt: #Graceful shutdown handling #ctrl+c closes the server#
    print("\nClosing server...")
finally:
    for client in clients:
        client.close()
    server.close()
    print("Server closed")
