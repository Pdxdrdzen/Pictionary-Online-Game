import socket
import sys
import threading
from http import client
from game import GameState

game=GameState()

SERVER_HOST='127.0.0.1'
SERVER_PORT=12345

server=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1) #restart bugfix
server.bind((SERVER_HOST,SERVER_PORT))
server.listen()
server.settimeout(1.0)

clients=[]
print(f"TCP server listening on {SERVER_HOST}:{SERVER_PORT}")

def handle_client(client_socket, client_addr):
    clients.append(client_socket)
    client_socket.send("What your username shall be?".encode('utf-8'))
    nick = client_socket.recv(1024).decode('utf-8').strip()
    game.add_player(nick, client_socket)  # add player
    print(f"{client_addr} connected as: {nick}")

    while True:
        try:
            message = client_socket.recv(1024)
            if not message:
                break
            game.handle_message(nick, message.decode('utf-8'))
        except:
            break
    print(f"Client {client_addr} disconnected") # when clients socket isnt available - the client has probably disconnected
    if client_socket in clients:
        clients.remove(client_socket)
    client_socket.close()
try:

    while True:
        try:
            client_socket, client_addr = server.accept()
            client_thread = threading.Thread(target=handle_client, args=(client_socket,client_addr))
            client_thread.daemon=True #Automatically killing background threads when the main thread has ended
            client_thread.start()
        except socket.timeout:
            continue
except KeyboardInterrupt: #Graceful shutdown handling #ctrl+c closes the server#
    print("\nClosing server...")
    for c in clients:
        try:
            c.close()
        except:
            #TODO resolve in the future
            pass
        server.close()
        print("Server closed")
        sys.exit(0)
finally:
    for client in clients:
        client.close()
    server.close()
    print("Server closed")
