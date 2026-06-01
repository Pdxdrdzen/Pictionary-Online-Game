import pygame
import sys
import socket
import threading
import json
import math
import random
from PIL import Image

WIDTH, HEIGHT = 900, 660
CANVAS_X = 10
CANVAS_Y = 60
CANVAS_W = 880
CANVAS_H = 480
FPS = 144

BG_TOP       = (15, 10, 35)
BG_BOT       = (35, 10, 60)
WHITE        = (255, 255, 255)
BLACK        = (10, 10, 10)
ACCENT1      = (255, 60, 180)
ACCENT2      = (60, 220, 255)
ACCENT3      = (255, 200, 0)
ACCENT4      = (100, 255, 120)
RED_HOT      = (255, 60, 60)
PANEL_BG     = (25, 18, 50)
PANEL_BORDER = (80, 50, 140)
INPUT_BG     = (35, 25, 65)

BRUSH_COLORS = [
    (10,10,10),(255,255,255),(255,60,60),(255,140,0),
    (255,220,0),(60,200,60),(0,180,255),(180,60,255),
    (255,60,180),(100,60,20),(0,120,80),(60,60,180),
]

my_role        = None
in_lobby       = True
current_scores = {}
current_word   = None
notifications  = []
time_left      = None
timer_start    = None
messages       = []
particles      = []

active_gif = {
    "name": None,       # GIF key
    "frame": 0,         # current frame
    "expire": 0,        # when it expires
    "next_frame": 0     # when to change
}


def load_gif(path):
    gif = Image.open(path)
    frames = []
    durations = []
    try:
        while True:
            frame = gif.copy().convert("RGBA")
            px = pygame.image.fromstring(frame.tobytes(), frame.size, "RGBA")
            frames.append(px)
            durations.append(gif.info.get("duration", 100))  # ms na klatke
            gif.seek(gif.tell() + 1)
    except EOFError:
        pass
    return frames, durations

GIFS = {}
gif_files = {
    "wrong":     "assets/wrong.gif",
    "correct":   "assets/correct.gif",
    "win":       "assets/win.gif",
    "timeup":    "assets/timeup.gif",
    "quickshot": "assets/quickshot.gif",
}
for name, path in gif_files.items():
    try:
        GIFS[name] = load_gif(path)
    except FileNotFoundError:
        print(f"Brak pliku: {path}")

def spawn_particles(x, y, color, count=18):
    for _ in range(count):
        angle = random.uniform(0, 2*math.pi)
        speed = random.uniform(2, 8)
        lifetime = random.randint(30, 70)
        particles.append({
            "x": x, "y": y,
            "vx": math.cos(angle)*speed,
            "vy": math.sin(angle)*speed - 3,
            "color": color,
            "life": lifetime,
            "max_life": lifetime,
            "size": random.randint(3, 8)
        })

def update_draw_particles(surf):
    for p in particles[:]:
        p["x"] += p["vx"]
        p["y"] += p["vy"]
        p["vy"] += 0.3
        p["life"] -= 1
        size = max(1, int(p["size"] * p["life"] / p["max_life"]))
        pygame.draw.circle(surf, p["color"], (int(p["x"]), int(p["y"])), size)
        if p["life"] <= 0:
            particles.remove(p)

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Pictionary TCP Online")
clock = pygame.time.Clock()

font_big   = pygame.font.SysFont("Arial", 32, bold=True)
font_med   = pygame.font.SysFont("Arial", 22, bold=True)
font_small = pygame.font.SysFont("Arial", 17)
font_tiny  = pygame.font.SysFont("Arial", 14)

def draw_gradient_bg():
    for y in range(HEIGHT):
        t = y / HEIGHT
        r = int(BG_TOP[0]*(1-t) + BG_BOT[0]*t)
        g = int(BG_TOP[1]*(1-t) + BG_BOT[1]*t)
        b = int(BG_TOP[2]*(1-t) + BG_BOT[2]*t)
        pygame.draw.line(screen, (r,g,b), (0,y), (WIDTH,y))

def draw_glow_rect(surf, color, rect, radius=10, glow_size=8):
    for i in range(glow_size, 0, -1):
        alpha_surf = pygame.Surface((rect[2]+i*2, rect[3]+i*2), pygame.SRCALPHA)
        a = int(60 * (i / glow_size))
        pygame.draw.rect(alpha_surf, (*color, a),
                         (0, 0, rect[2]+i*2, rect[3]+i*2), border_radius=radius+i)
        surf.blit(alpha_surf, (rect[0]-i, rect[1]-i))
    pygame.draw.rect(surf, color, rect, border_radius=radius, width=2)

def draw_panel(surf, rect, radius=12):
    s = pygame.Surface((rect[2], rect[3]), pygame.SRCALPHA)
    pygame.draw.rect(s, (*PANEL_BG, 220), (0,0,rect[2],rect[3]), border_radius=radius)
    surf.blit(s, (rect[0], rect[1]))
    pygame.draw.rect(surf, PANEL_BORDER, rect, width=2, border_radius=radius)

def add_notification(text, color=ACCENT2):
    expire = pygame.time.get_ticks() + 3000
    notifications.append({"text": text, "color": color,
                           "expire": expire, "born": pygame.time.get_ticks()})
    spawn_particles(WIDTH//2, 200, color, 25)

# nick view
client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect(("127.0.0.1", 12345))
prompt = client.recv(1024).decode("utf-8")
nick = ""
waiting_for_nick = True
nick_cursor_timer = 0

while waiting_for_nick:
    clock.tick(FPS)
    nick_cursor_timer += 1
    draw_gradient_bg()
    t = pygame.time.get_ticks() / 1000
    for i in range(6):
        angle = t * 0.7 + i * math.pi / 3
        x = WIDTH//2 + int(math.cos(angle) * 160)
        y = HEIGHT//2 + int(math.sin(angle) * 60)
        r = 18 + int(math.sin(t*2+i)*6)
        colors = [ACCENT1, ACCENT2, ACCENT3, ACCENT4, RED_HOT, ACCENT1]
        s2 = pygame.Surface((r*2+20, r*2+20), pygame.SRCALPHA)
        pygame.draw.circle(s2, (*colors[i], 60), (r+10, r+10), r+8)
        screen.blit(s2, (x-r-10, y-r-10))
        pygame.draw.circle(screen, colors[i], (x, y), r)
    title = font_big.render("PICTIONARY TCP ONLINE", True, ACCENT3)
    screen.blit(title, (WIDTH//2 - title.get_width()//2, HEIGHT//2 - 130))
    draw_panel(screen, (WIDTH//2-200, HEIGHT//2-55, 400, 110), radius=16)
    label = font_med.render("Podaj nick:", True, ACCENT2)
    screen.blit(label, (WIDTH//2 - label.get_width()//2, HEIGHT//2 - 45))
    cursor = "|" if (nick_cursor_timer // 20) % 2 == 0 else ""
    nick_surf = font_med.render(nick + cursor, True, WHITE)
    screen.blit(nick_surf, (WIDTH//2 - nick_surf.get_width()//2, HEIGHT//2 - 10))
    hint = font_tiny.render("Wcisnij Enter aby dolaczyc", True, ACCENT1)
    screen.blit(hint, (WIDTH//2 - hint.get_width()//2, HEIGHT//2 + 35))
    pygame.display.flip()
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit(); sys.exit()
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN and nick.strip():
                client.send(nick.encode("utf-8"))
                waiting_for_nick = False
            elif event.key == pygame.K_BACKSPACE:
                nick = nick[:-1]
            else:
                nick += event.unicode

canvas = pygame.Surface((CANVAS_W, CANVAS_H))
canvas.fill(WHITE)
drawing = False
last_pos = None
brush_color = BLACK
brush_size = 5
selected_color_idx = 0
input_text = ""

def play_gif(name, duration_ms=2500):
    if name in GIFS:
        active_gif["name"] = name
        active_gif["frame"] = 0
        active_gif["expire"] = pygame.time.get_ticks() + duration_ms
        active_gif["next_frame"] = pygame.time.get_ticks()

def draw_active_gif():
            now = pygame.time.get_ticks()
            name = active_gif["name"]
            if not name or now > active_gif["expire"]:
                active_gif["name"] = None
                return

            frames, durations = GIFS[name]

            # change of frame
            if now >= active_gif["next_frame"]:
                active_gif["frame"] = (active_gif["frame"] + 1) % len(frames)
                active_gif["next_frame"] = now + durations[active_gif["frame"]]

            frame_surf = frames[active_gif["frame"]]

            # center the gif
            fw, fh = frame_surf.get_size()
            gx = WIDTH // 2 - fw // 2
            gy = HEIGHT // 2 - fh // 2

            # black background under the gif
            bg = pygame.Surface((fw + 20, fh + 20), pygame.SRCALPHA)
            pygame.draw.rect(bg, (0, 0, 0, 160), (0, 0, fw + 20, fh + 20), border_radius=12)
            screen.blit(bg, (gx - 10, gy - 10))
            screen.blit(frame_surf, (gx, gy))

def draw_ui():
    now = pygame.time.get_ticks()
    draw_panel(screen, (0, 0, WIDTH, 58), radius=0)

    if time_left is not None:
        elapsed = (now - timer_start) // 1000
        remaining = max(0, time_left - elapsed)
        pulse = 1.0 + 0.15*math.sin(now/120) if remaining <= 10 else 1.0
        tc = RED_HOT if remaining <= 10 else ACCENT2
        t_surf = font_med.render(f"CZAS: {remaining}s", True, tc)
        tw = int(t_surf.get_width() * pulse)
        th = int(t_surf.get_height() * pulse)
        t_surf = pygame.transform.scale(t_surf, (max(1,tw), max(1,th)))
        screen.blit(t_surf, (WIDTH//2 - tw//2, 8))
        bar_w = 300
        bar_x = WIDTH//2 - bar_w//2
        total = time_left if time_left is not None else 1
        frac = remaining / total if total > 0 else 0
        pygame.draw.rect(screen, PANEL_BORDER, (bar_x, 46, bar_w, 8), border_radius=4)
        fill_c = RED_HOT if frac < 0.25 else (ACCENT3 if frac < 0.5 else ACCENT4)
        if frac > 0:
            pygame.draw.rect(screen, fill_c, (bar_x, 46, int(bar_w*frac), 8), border_radius=4)

    score_x = WIDTH - 10
    for player, score in current_scores.items():
        s = font_small.render(f"{player}: {score}pt", True, ACCENT3)
        score_x -= s.get_width() + 20
        screen.blit(s, (score_x, 18))

    role_color = ACCENT1 if my_role == "drawer" else ACCENT4
    role_text = "RYSUJESZ" if my_role == "drawer" else "ZGADUJESZ"
    rs = font_small.render(role_text, True, role_color)
    screen.blit(rs, (10, 18))

    draw_panel(screen, (0, CANVAS_Y + CANVAS_H + 3, WIDTH, HEIGHT - CANVAS_Y - CANVAS_H - 3), radius=0)

    if my_role == "drawer":
        for i, c in enumerate(BRUSH_COLORS):
            cx2 = CANVAS_X + 5 + i * 30
            cy2 = CANVAS_Y + CANVAS_H + 42
            pygame.draw.circle(screen, c, (cx2+10, cy2+10), 11)
            if i == selected_color_idx:
                draw_glow_rect(screen, ACCENT2, (cx2-3, cy2-3, 26, 26), radius=13, glow_size=5)
                pygame.draw.circle(screen, WHITE, (cx2+10, cy2+10), 13, 2)
        for idx, sz in enumerate([3, 5, 9, 15]):
            bx = CANVAS_X + 5 + len(BRUSH_COLORS)*30 + idx*36
            by = CANVAS_Y + CANVAS_H + 42
            pygame.draw.circle(screen, brush_color, (bx+15, by+10), sz//2+2)
            if brush_size == sz:
                pygame.draw.circle(screen, ACCENT2, (bx+15, by+10), sz//2+5, 2)

    if my_role == "drawer" and current_word:
        ws = font_med.render(f"Rysujesz: {current_word}", True, ACCENT3)
        screen.blit(ws, (WIDTH//2 - ws.get_width()//2, CANVAS_Y + CANVAS_H + 10))

    input_y = CANVAS_Y + CANVAS_H + 78
    draw_glow_rect(screen, ACCENT1 if my_role=="guesser" else PANEL_BORDER,
                   (CANVAS_X, input_y, CANVAS_W, 34), radius=8, glow_size=4)
    s2 = pygame.Surface((CANVAS_W, 34), pygame.SRCALPHA)
    pygame.draw.rect(s2, (*INPUT_BG, 200), (0,0,CANVAS_W,34), border_radius=8)
    screen.blit(s2, (CANVAS_X, input_y))
    placeholder = "Wpisz odpowiedz i wcisnij Enter..." if my_role=="guesser" else "Jestes drawerem - rysuj!"
    display_text = input_text + ("|" if (now//400)%2==0 else " ")
    txt_c = WHITE if input_text else (80, 70, 120)
    ts = font_small.render(display_text if input_text else placeholder, True, txt_c)
    screen.blit(ts, (CANVAS_X+10, input_y+8))

    for i, m in enumerate(messages[-2:]):
        ms = font_tiny.render(f"> {m}", True, (150,130,200))
        screen.blit(ms, (CANVAS_X+10, input_y - 20*(i+1)))

    notifications[:] = [n for n in notifications if n["expire"] > now]
    for i, notif in enumerate(notifications):
        age = now - notif["born"]
        total_dur = 3000
        if age < 200:
            scale = 0.5 + 0.5*(age/200)
        elif age > total_dur - 400:
            scale = max(0.05, (total_dur - age) / 400)
        else:
            scale = 1.0
        ns = font_big.render(notif["text"], True, notif["color"])
        w2 = int(ns.get_width() * scale)
        h2 = int(ns.get_height() * scale)
        if w2 > 0 and h2 > 0:
            ns = pygame.transform.scale(ns, (w2, h2))
            shadow = font_big.render(notif["text"], True, (0,0,0))
            shadow = pygame.transform.scale(shadow, (w2, h2))
            screen.blit(shadow, (WIDTH//2 - w2//2 + 3, 85 + i*55 + 3))
            screen.blit(ns, (WIDTH//2 - w2//2, 85 + i*55))

def receive_loop():
    global my_role, in_lobby, current_scores, current_word, time_left, timer_start
    buffer = ""
    while True:
        try:
            data = client.recv(4096).decode("utf-8")
            if data:
                buffer += data
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    if line.strip():
                        msg = json.loads(line)
                        print(f"RECEIVED: {msg}")
                        t = msg.get("type")
                        if t == "lobby":
                            in_lobby = True
                        elif t == "role":
                            in_lobby = False
                            my_role = msg["role"]
                            label = "RYSUJESZ!" if my_role=="drawer" else "ZGADUJESZ!"
                            add_notification(label, ACCENT1 if my_role=="drawer" else ACCENT4)
                        elif t == "word":
                            current_word = msg["word"]
                        elif t == "draw" and my_role == "guesser":
                            pygame.draw.line(canvas, tuple(msg["color"]),
                                             (msg["x1"], msg["y1"]),
                                             (msg["x2"], msg["y2"]), msg["size"])
                        elif t == "clear_canvas":
                            canvas.fill(WHITE)
                            add_notification("Nowa runda!", ACCENT2)
                        elif t == "scores":
                            current_scores = msg["scores"]
                        elif t == "correct":
                            add_notification(f"{msg['player']} zgadl haslo!", ACCENT4)
                            spawn_particles(WIDTH//2, 300, ACCENT4, 40)
                            play_gif("correct")
                        elif t=="wrong":
                            play_gif("wrong")
                        elif t == "timer":
                            time_left = msg["seconds"]
                            timer_start = pygame.time.get_ticks()
                        elif t == "time_up":
                            add_notification(f"Czas! Haslo: {msg['word']}", RED_HOT)
                            play_gif("time_up")
                            time_left = None
                        elif t == "game_over":
                            play_gif("win",duration_ms=4000)
                            sc = ", ".join([f"{p}:{s}" for p,s in msg["scores"].items()])
                            add_notification(f"WYGRYWA {msg['winner']}! ({sc})", ACCENT3)
                            spawn_particles(WIDTH//2, HEIGHT//2, ACCENT3, 60)
                            time_left = None
                        elif t == "quick_shot":
                            add_notification("REMIS! QUICK SHOT - 10 SEKUND!", RED_HOT)
                            play_gif("quick_shot")
                            spawn_particles(WIDTH//2, HEIGHT//2, RED_HOT, 50)
            if not data:
                pygame.quit(); sys.exit()
        except Exception as e:
            print(f"ERROR: {e}")
            pygame.quit(); sys.exit()

thread = threading.Thread(target=receive_loop, daemon=True)
thread.start()

while True:
    clock.tick(FPS)
    now = pygame.time.get_ticks()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit(); sys.exit()

        if event.type == pygame.MOUSEBUTTONDOWN:
            mx, my2 = event.pos
            if my_role == "drawer":
                for i, c in enumerate(BRUSH_COLORS):
                    cx2 = CANVAS_X + 5 + i*30
                    cy2 = CANVAS_Y + CANVAS_H + 42
                    if math.hypot(mx-(cx2+10), my2-(cy2+10)) <= 13:
                        brush_color = c
                        selected_color_idx = i
                for idx, sz in enumerate([3,5,9,15]):
                    bx = CANVAS_X + 5 + len(BRUSH_COLORS)*30 + idx*36
                    by = CANVAS_Y + CANVAS_H + 42
                    if math.hypot(mx-(bx+15), my2-(by+10)) <= sz//2+6:
                        brush_size = sz
            if CANVAS_X <= mx <= CANVAS_X+CANVAS_W and CANVAS_Y <= my2 <= CANVAS_Y+CANVAS_H:
                drawing = True
                last_pos = (mx - CANVAS_X, my2 - CANVAS_Y)

        if event.type == pygame.MOUSEBUTTONUP:
            drawing = False
            last_pos = None

        if event.type == pygame.MOUSEMOTION and drawing:
            mx, my2 = event.pos
            cur = (mx - CANVAS_X, my2 - CANVAS_Y)
            if last_pos and my_role == "drawer":
                pygame.draw.line(canvas, brush_color, last_pos, cur, brush_size)
                dx = cur[0]-last_pos[0]; dy = cur[1]-last_pos[1]
                if dx*dx+dy*dy > 9:
                    msg_out = json.dumps({
                        "type":"draw","x1":last_pos[0],"y1":last_pos[1],
                        "x2":cur[0],"y2":cur[1],
                        "color":list(brush_color),"size":brush_size
                    })
                    client.send(msg_out.encode("utf-8"))
                last_pos = cur

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                if input_text.strip() and my_role == "guesser":
                    client.send(json.dumps({"type":"guess","payload":input_text}).encode("utf-8"))
                    messages.append(input_text)
                    input_text = ""
            elif event.key == pygame.K_BACKSPACE:
                input_text = input_text[:-1]
            else:
                input_text += event.unicode

    if in_lobby:
        draw_gradient_bg()
        t2 = now / 1000
        for i in range(8):
            angle = t2*0.5 + i*math.pi/4
            x = WIDTH//2 + int(math.cos(angle)*200)
            y = HEIGHT//2 + int(math.sin(angle)*80)
            r = 14+int(math.sin(t2*3+i)*5)
            cols = [ACCENT1,ACCENT2,ACCENT3,ACCENT4,RED_HOT,ACCENT1,ACCENT2,ACCENT3]
            gs = pygame.Surface((r*3, r*3), pygame.SRCALPHA)
            pygame.draw.circle(gs, (*cols[i],80), (r+r//2,r+r//2), r+r//2)
            screen.blit(gs, (x-r-r//2, y-r-r//2))
            pygame.draw.circle(screen, cols[i], (x,y), r)
        dots = "." * ((now//500)%4)
        ls = font_big.render(f"Czekam na gracza{dots}", True, WHITE)
        screen.blit(ls, (WIDTH//2 - ls.get_width()//2, HEIGHT//2 - 20))
        hint = font_small.render("Gra zacznie sie gdy dolazy drugi gracz", True, (150,130,200))
        screen.blit(hint, (WIDTH//2 - hint.get_width()//2, HEIGHT//2+30))
        pygame.display.flip()
        continue

    draw_gradient_bg()
    glow_color = ACCENT1 if my_role=="drawer" else ACCENT2
    draw_glow_rect(screen, glow_color, (CANVAS_X, CANVAS_Y, CANVAS_W, CANVAS_H), radius=6, glow_size=10)
    screen.blit(canvas, (CANVAS_X, CANVAS_Y))
    pygame.draw.rect(screen, glow_color, (CANVAS_X, CANVAS_Y, CANVAS_W, CANVAS_H), width=2, border_radius=6)
    update_draw_particles(screen)
    draw_ui()
    draw_active_gif()
    pygame.display.flip()