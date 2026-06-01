import pygame
import sys
import socket
import threading
import json

WIDTH, HEIGHT = 800, 600
CANVAS_HEIGHT = 500
FPS = 144

WHITE = (255, 255, 255)
BLACK = (0,   0,   0)
GRAY  = (40,  40,  40)
LIGHT = (220, 220, 220)

my_role=None
in_lobby=True
current_scores={}
current_word=None
notifications=[]

time_left=None
timer_start=None

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption('Pictionary Tcp Online')
clock = pygame.time.Clock()

#initalize input field for guessers
font=pygame.font.SysFont("Arial", 20)
input_text=""
messages=[]

client=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect(('127.0.0.1',12345))

prompt = client.recv(1024).decode('utf-8')
nick = ""
waiting_for_nick = True

while waiting_for_nick:
    screen.fill(GRAY)
    label = font.render("Podaj nick i wcisnij Enter:", True, WHITE)
    nick_surface = font.render(nick + "|", True, WHITE)
    screen.blit(label, (WIDTH//2 - label.get_width()//2, HEIGHT//2 - 40))
    screen.blit(nick_surface, (WIDTH//2 - nick_surface.get_width()//2, HEIGHT//2))
    pygame.display.flip()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN and nick.strip():
                client.send(nick.encode('utf-8'))
                waiting_for_nick = False
            elif event.key == pygame.K_BACKSPACE:
                nick = nick[:-1]
            else:
                nick += event.unicode

canvas = pygame.Surface((WIDTH, CANVAS_HEIGHT))
canvas.fill(WHITE)

drawing = False
last_pos = None
brush_color = BLACK
brush_size = 4
def add_notification(text,color=(255,255,255)):
    expire_time=pygame.time.get_ticks()+2500
    notifications.append([text,color,expire_time])

def draw_ui():

    #whiteboard
    pygame.draw.rect(screen, GRAY, (0, CANVAS_HEIGHT, WIDTH, HEIGHT - CANVAS_HEIGHT))
    pygame.draw.line(screen, LIGHT, (0, CANVAS_HEIGHT), (WIDTH, CANVAS_HEIGHT), 2)

    #input field
    pygame.draw.rect(screen,WHITE,(10,CANVAS_HEIGHT+15,WIDTH-20,35),border_radius=6)

    #text in field
    txt_surface=font.render(input_text+"|",True,BLACK)
    screen.blit(txt_surface,(18,CANVAS_HEIGHT+22))

    #messages history over the input field
    for i,msg in enumerate(messages[-3:]):
        s=font.render(f">{msg}",True,LIGHT)
        screen.blit(s,(10,CANVAS_HEIGHT-25*(i+1)))

    y=CANVAS_HEIGHT+30
    for player,score in current_scores.items():
        s=font.render(f"{player}:{score}",True,LIGHT)
        screen.blit(s,(WIDTH-150,y))
        y+=22
    if my_role=="drawer" and current_word:
        word_surface=font.render(f"Drawing: {current_word}",True,(255,200,0))
        screen.blit(word_surface,(WIDTH//2-word_surface.get_width()//2,CANVAS_HEIGHT-35))

    if time_left is not None:
        elapsed = (pygame.time.get_ticks() - timer_start) // 1000
        remaining = max(0, time_left - elapsed)
        color = (255, 80, 80) if remaining <= 10 else LIGHT
        t = font.render(f"Czas: {remaining}s", True, color)
        screen.blit(t, (10, 10))

    now = pygame.time.get_ticks()
    notifications[:] = [n for n in notifications if n[2] > now]
    for i, (text, color, _) in enumerate(notifications):
        s = font.render(text, True, color)
        screen.blit(s, (WIDTH // 2 - s.get_width() // 2, 20 + i * 30))
def receive_loop():
    global my_role, in_lobby, current_scores,current_word,time_left,timer_start
    buffer = ""
    while True:
        try:
            data = client.recv(4096).decode('utf-8')
            if data:
                buffer += data
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    if line.strip():
                        msg = json.loads(line)
                        print(f"RECEIVED: {msg}")
                        if msg.get("type") == "correct":
                            add_notification(f"{msg['player']} zgadł hasło!", (100, 220, 100))
                        elif msg.get("type") == "clear_canvas":
                            add_notification("Nowa runda!", (255, 200, 0))
                            canvas.fill(WHITE)
                        elif msg.get("type") == "scores":
                            current_scores = msg["scores"]
                        if msg.get("type")=="lobby":
                            in_lobby = True
                        elif msg.get("type") == "role":
                            in_lobby = False
                            my_role = msg["role"]
                            print(f"Moja rola: {my_role}")
                        elif msg.get("type")=="draw" and my_role=="guesser":
                            pygame.draw.line(
                                canvas,
                                tuple(msg["color"]),
                                (msg["x1"], msg["y1"]),
                                (msg["x2"], msg["y2"]),
                                msg["size"]
                            )
                        elif msg.get("type")=="word":
                            current_word=msg["word"]
                        elif msg.get("type") == "timer":
                            time_left = msg["seconds"]
                            timer_start = pygame.time.get_ticks()
                        elif msg.get("type") == "time_up":
                            add_notification(f"Czas minąl! Hasło to: {msg['word']}", (255, 80, 80))
                            time_left = None
            if not data:
                print("Server disconnected.")
                pygame.quit()
                sys.exit()
        except Exception as e:
            print(f"ERROR: {e}")
            pygame.quit()
            sys.exit()
            break

#starting the thread
thread=threading.Thread(target=receive_loop,daemon=True)
thread.start()

while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.pos[1] < CANVAS_HEIGHT:
                drawing = True
                last_pos = event.pos

        if event.type == pygame.MOUSEBUTTONUP:
            drawing = False
            last_pos = None

        if event.type == pygame.MOUSEMOTION and drawing:
            if last_pos and my_role=="drawer":
                pygame.draw.line(canvas, brush_color, last_pos, event.pos, brush_size)
                dx=event.pos[0]-last_pos[0]
                dy=event.pos[1]-last_pos[1]
                if dx*dx + dy*dy > 9:
                    msg = json.dumps({"type":"draw","x1":last_pos[0],"y1":last_pos[1],"x2":event.pos[0],"y2":event.pos[1],"color":list(brush_color),"size":brush_size})
                    client.send(msg.encode('utf-8'))
                last_pos=event.pos
        if event.type==pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                print(f"Enter wciśnięty, my_role={my_role}")
                if input_text.strip() and my_role=="guesser":
                    #send message to the server
                    msg=json.dumps({"type":"guess","payload":input_text})
                    client.send(msg.encode('utf-8'))
                    messages.append(input_text)
                    input_text = ""
            elif event.key == pygame.K_BACKSPACE:
                input_text = input_text[:-1]
            else:
                input_text += event.unicode
    if in_lobby:
        screen.fill(GRAY)
        lobby_text = font.render("Waiting for other players...", True, WHITE)
        screen.blit(lobby_text, (WIDTH // 2 - lobby_text.get_width() // 2, HEIGHT // 2))
        pygame.display.flip()
        clock.tick(FPS)
        continue

    screen.fill(WHITE)
    screen.blit(canvas, (0, 0))
    draw_ui()
    pygame.display.flip()
    clock.tick(FPS)