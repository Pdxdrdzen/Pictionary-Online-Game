import socket
import sys
import threading
from http import client
from game import GameState
import random, string
import json

rooms={}
player_room={}
player_nick={}

SERVER_HOST='127.0.0.1'
SERVER_PORT=12345

server=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1) #restart bugfix
server.bind((SERVER_HOST,SERVER_PORT))
server.listen()
server.settimeout(1.0)

clients=[]
print(f"TCP server listening on {SERVER_HOST}:{SERVER_PORT}")

def generate_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

def send_to(sock, msg):
    sock.send((json.dumps(msg) + '\n').encode('utf-8'))

def broadcast_room(code, msg):
    for sock, c in player_room.items():
        if c == code:
            send_to(sock, msg)

def handle_client(client_socket, client_addr):
    clients.append(client_socket)
    client_socket.send("What your username shall be?".encode('utf-8'))
    nick = client_socket.recv(1024).decode('utf-8').strip()
    player_nick[client_socket] = nick
    print(f"{client_addr} connected as: {nick}")

    while True:
        try:
            message = client_socket.recv(4096)
            if not message:
                break
            msg = json.loads(message.decode('utf-8'))
            t = msg.get("type")

            if t == "create_room":
                code = generate_code()
                rooms[code] = {"owner": nick, "players": [nick],
                               "state": "lobby", "game": None}
                player_room[client_socket] = code
                send_to(client_socket, {"type": "room_created", "code": code})
                broadcast_room(code, {"type": "lobby_update",
                                      "players": [nick], "owner": nick})

            elif t == "join_room":
                code = msg["code"].upper()
                if code not in rooms:
                    send_to(client_socket, {"type": "error", "msg": "Nieprawidłowy kod"})
                elif rooms[code]["state"] == "playing":
                    send_to(client_socket, {"type": "error", "msg": "Gra już trwa"})
                elif len(rooms[code]["players"]) >= 8:
                    send_to(client_socket, {"type": "error", "msg": "Lobby pełne (max 8)"})
                else:
                    rooms[code]["players"].append(nick)
                    player_room[client_socket] = code
                    send_to(client_socket, {"type": "joined_room", "code": code,
                                            "owner": rooms[code]["owner"]})
                    broadcast_room(code, {"type": "lobby_update",
                                          "players": rooms[code]["players"],
                                          "owner": rooms[code]["owner"]})

            elif t == "start_game":
                code = player_room.get(client_socket)
                room = rooms[code]
                if nick != room["owner"]:
                    send_to(client_socket, {"type": "error", "msg": "Tylko właściciel może startować"})
                elif len(room["players"]) < 2:
                    send_to(client_socket, {"type": "error", "msg": "Min. 2 graczy"})
                else:
                    room["state"] = "playing"
                    room["game"] = GameState(room["players"],
                                             {s: player_nick[s] for s in player_room
                                              if player_room.get(s) == code})
                    broadcast_room(code, {"type": "game_start"})
                    room["game"].start()

            else:
                code = player_room.get(client_socket)
                if code and rooms.get(code, {}).get("state") == "playing":
                    rooms[code]["game"].handle_message(nick, message.decode('utf-8'))

        except Exception as e:
            print(f"Error: {e}")
            break

    # rozłączenie
    code = player_room.pop(client_socket, None)
    if code and code in rooms:
        rooms[code]["players"] = [p for p in rooms[code]["players"]
                                  if p != nick]
        if not rooms[code]["players"]:
            del rooms[code]
        else:
            broadcast_room(code, {"type": "lobby_update",
                                   "players": rooms[code]["players"],
                                   "owner": rooms[code]["owner"]})
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
