import socket
import threading
import json

HOST='127.0.0.1'
PORT=12345

def send_message(client_socket, message: dict):
    data=json.dumps(message)+'\n' #convert the data string into json
    client_socket.sendall(data.encode('utf-8'))
def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))
        print(f"Connected to {HOST}:{PORT}")

        while True:
            msg=input("Write a message to send: ");
            if msg.lower()=='quit':
                break;
            send_message(s,{"type":"message","payload":msg}) #message format
            data=s.recv(1024).decode('utf-8')
            print(f"Received from {HOST}:{PORT}: {data}")

if __name__ == '__main__':
    main()
