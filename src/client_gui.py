import pygame
import sys

from pygame.examples.go_over_there import event

WIDTH, HEIGHT = 800, 600
CANVAS_HEIGHT=500
FPS=144

WHITE  = (255, 255, 255)
BLACK  = (0,   0,   0)
GRAY   = (40,  40,  40)
LIGHT  = (220, 220, 220)

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption('Pictionary Tcp Online')
clock = pygame.time.Clock()

canvas=pygame.Surface(WIDTH,CANVAS_HEIGHT)
canvas.fill(WHITE)

drawing=False
last_pos=None
brush_color=BLACK
brush_size=4

def draw_ui():
    """Drawing bottom UI panel"""
    pygame.draw.rect(canvas, GRAY, (0, CANVAS_HEIGHT, WIDTH, HEIGHT-CANVAS_HEIGHT))
    pygame.draw.line(screen, LIGHT, (0, CANVAS_HEIGHT), (WIDTH, CANVAS_HEIGHT),2)

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.pos[1]<CANVAS_HEIGHT:
                    drawing=True
                    last_pos=event.pos

            if event.type == pygame.MOUSEBUTTONUP:
                if last_pos:
                    pygame.draw.line(canvas,brush_color,last_pos,event.pos,brush_size)
                    last_pos=event.pos
        screen.blit(canvas,(0,0))
        draw_ui()

        pygame.display.flip()
        clock.tick(FPS)

