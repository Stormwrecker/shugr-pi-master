"""Utilities for emulator.py"""
import time

import pygame
from socket import gethostbyname, gethostname
from time import sleep

pygame.init()

# colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)

# text handling
font_cache = {}
all_fonts = []
default_font = pygame.font.match_font("calibri.ttf", False, False)
def get_font(font, size):
    actual_font = str(font) + str(size)
    if actual_font not in font_cache:
        font_cache[actual_font] = pygame.font.Font(font, size)

    return font_cache[actual_font]


def draw_text(display, text, x, y, color, size, font=default_font, centered=False):
    font = get_font(font, size)
    text_surface = font.render(str(text), True, color)
    text_rect = text_surface.get_rect()
    if centered:
        text_rect.center = (x, y)
    else:
        text_rect.topleft = (x, y)
    display.blit(text_surface, text_rect)


# check for internet
internet_connection = False
def check_internet_status():
    global internet_connection
    my_ip = gethostbyname(gethostname())
    internet_connection = False
    if my_ip != "127.0.0.1":
        internet_connection = True
    return internet_connection
