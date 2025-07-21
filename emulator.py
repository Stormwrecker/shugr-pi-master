"""A game-launcher OS designed to run python applications inside of a Raspberry Pi"""

PATH = "games"

import os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"

import sys
import subprocess
import threading
import queue
import time
import pygame
import random
import math
from emulator_utils import *

try:
    import RPi.GPIO as GPIO
except ImportError:
    GPIO = None

class GPIOInputBridge(threading.Thread):
    def __init__(self, gpio_key_map, event_queue):
        super().__init__(daemon=True)
        self.gpio_key_map = gpio_key_map  # {gpio_pin: pygame_key}
        self.event_queue = event_queue
        self.running = True

        if GPIO:
            GPIO.setmode(GPIO.BCM)
            for pin in self.gpio_key_map:
                GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # Buttons active low

        self.pin_states = {pin: True for pin in self.gpio_key_map}

    def run(self):
        while self.running:
            if not GPIO:
                threading.Event().wait(1)
                continue
            for pin, key in self.gpio_key_map.items():
                current_state = GPIO.input(pin)
                if current_state != self.pin_states[pin]:
                    event_type = pygame.KEYDOWN if current_state == False else pygame.KEYUP
                    self.event_queue.put(pygame.event.Event(event_type, {'key': key}))
                    self.pin_states[pin] = current_state
            threading.Event().wait(0.01)

    def stop(self):
        self.running = False
        if GPIO:
            GPIO.cleanup()


class PowerButtonMonitor(threading.Thread):
    def __init__(self, power_button_pin, event_queue, debounce_time=0.2):
        super().__init__(daemon=True)
        self.power_button_pin = power_button_pin
        self.event_queue = event_queue
        self.debounce_time = debounce_time
        self.last_time = 0
        self.running = True

        if GPIO:
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self.power_button_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            GPIO.add_event_detect(self.power_button_pin, GPIO.FALLING, callback=self._handle_button_press, bouncetime=int(debounce_time*1000))

    def _handle_button_press(self, channel):
        current_time = time.time()
        if (current_time - self.last_time) >= self.debounce_time:
            print("Power button pressed! Initiating shutdown...")
            self.event_queue.put(pygame.event.Event(pygame.QUIT))
            self.last_time = current_time

    def run(self):
        # No continuous polling needed with event detect
        while self.running:
            time.sleep(1)

    def stop(self):
        self.running = False
        if GPIO:
            try:
                GPIO.remove_event_detect(self.power_button_pin)
            except Exception as e:
                print("Error removing GPIO event detect:", e)


# initialize pygame
pygame.init()

# Get the screen resolution
display_info = pygame.display.Info()
screen_width, screen_height = (480, 270)
screen = pygame.display.set_mode((screen_width, screen_height))
display = pygame.Surface((480, 270)).convert()
midscreen_x = display.get_width() // 2
midscreen_y = display.get_height() // 2
pygame.display.set_caption("Raspberry Pi Pygame OS")
clock = pygame.time.Clock()


# wheel ui element
class WheelUI:
    def __init__(self, w, h, games_dir, fail_thumb):
        # positioning
        self.centerx = w // 2
        self.centery = h // 2
        self.width = 150
        self.height = 40

        # angles and indices
        self.master_index = 0
        self.target_index = 0
        self.master_angle = 0
        self.target_angle = 0
        self.bottom_angle = math.radians(90)

        # get items (names)
        self.items = [item for item in os.listdir(games_dir) if os.path.exists(f"{games_dir}/{item}/main.py")]
        # for i in range(8):
        #     self.items.append(self.items[random.randint(0, 1)])
        self.thumbnails = []

        # get angles for even spacing
        self.item_angle = 0
        self.num_items = len(self.items)
        self.angle_increment = 360 / self.num_items if self.num_items > 0 else 0

        # add thumbnails and wheel-items
        for index, item in enumerate(self.items):
            if os.path.exists(f"{games_dir}/{item}/thumbnail.png"):
                img = pygame.image.load(os.path.join(games_dir, f"{item}/thumbnail.png")).convert_alpha()
            else:
                img = fail_thumb
            img = pygame.transform.scale_by(img, 1.25)
            self.thumbnails.append(img)
            self.item_angle = math.radians(self.angle_increment * index + 90)
            x = int(math.cos(self.item_angle) * self.width) + self.centerx
            y = int(math.sin(self.item_angle) * self.height) + self.centery
            wheel_item = WheelItem(index, img, x, y, self.item_angle, self.items[index])

    def update(self):
        self.master_index = self.target_index

        # Normalize target_angle to prevent floating-point overflow
        self.target_angle %= 360

        # Smoothly interpolate towards target_angle
        angle_diff = (self.target_angle - self.master_angle) % 360
        if angle_diff > 180:
            angle_diff -= 360

        if abs(angle_diff) > 1:
            self.master_angle += angle_diff * 0.15
        else:
            self.master_angle = self.target_angle

        # Keep master_angle normalized
        self.master_angle %= 360

    def get_bottom_item(self):
        # Find which item is currently closest to bottom position
        closest_item = None
        min_diff = float('inf')

        for item in wheel_item_group:
            # Calculate angle difference from bottom position
            item_angle = (item.angle + math.radians(self.master_angle)) % (2 * math.pi)
            diff = abs(item_angle - self.bottom_angle)

            # Take shortest path around circle
            if diff > math.pi:
                diff = 2 * math.pi - diff

            if diff < min_diff:
                min_diff = diff
                closest_item = item

        return closest_item


# wheel item for placing in wheel ui element
class WheelItem(pygame.sprite.Sprite):
    def __init__(self, index, image, x, y, angle, label):
        pygame.sprite.Sprite.__init__(self, wheel_item_group)
        self.index = index
        self.x = x
        self.y = y
        self.original_image = image
        self.image = image
        self.image.set_colorkey(WHITE)
        self.rect = self.image.get_rect()
        self.rect.center = (x, y)
        self.base_angle = angle
        self.angle = angle
        self.depth = 0
        self.label = str(label).lower().replace("_", " ").title()
        self.original_scale = 1
        self.grow = 0

    def update(self, wheel_ui):
        # get wheel_ui values for positioning
        self.w_width = wheel_ui.width
        self.w_height = wheel_ui.height
        self.w_centerx = wheel_ui.centerx
        self.w_centery = wheel_ui.centery

        current_angle = self.base_angle + math.radians(wheel_ui.master_angle)

        # center rect based on wheel_ui pos
        self.rect.midbottom = (int(math.cos(current_angle) * self.w_width) + self.w_centerx,
                            int(math.sin(current_angle) * self.w_height) + self.w_centery + 40)

        self.z_depth = math.sin(current_angle) + 2

    def zoom_in(self, zoom_factor):
        diff = abs(self.image.get_width() - int(self.original_image.get_width() * zoom_factor))
        if diff != 0:
            orig_x, orig_y = self.original_image.get_size()
            if diff > 1:
                self.grow += diff * 0.2
                size_x = orig_x + round(self.grow)
                size_y = orig_y + round(self.grow)
            else:
                size_x = int(self.original_image.get_width() * zoom_factor)
                size_y = int(self.original_image.get_height() * zoom_factor)
            self.image = pygame.transform.scale(self.original_image, (size_x, size_y))
            self.image.set_colorkey(WHITE)
            self.rect = self.image.get_rect(midbottom=self.rect.midbottom)

    def zoom_out(self):
        diff = abs(self.image.get_width() - self.original_image.get_width())
        if diff != 0:
            orig_x, orig_y = self.original_image.get_size()
            if diff > 1:
                self.grow -= diff * 0.2
                size_x = orig_x + round(self.grow)
                size_y = orig_y + round(self.grow)
            else:
                size_x = self.original_image.get_width()
                size_y = self.original_image.get_height()
            self.image = pygame.transform.scale(self.original_image, (size_x, size_y))
            self.image.set_colorkey(WHITE)
            self.rect = self.image.get_rect(midbottom=self.rect.midbottom)

    def draw(self, display, wheel_ui):
        pygame.draw.line(display, (100, 100, 100), (self.w_centerx, self.w_centery), self.rect.center)

        # pygame.draw.rect(display, (0, 0, 0), (self.rect.x - 3, self.rect.y - 3, self.rect.width + 6, self.rect.height + 6), 3)

        display.blit(self.image, self.rect)

        # Draw selection frame if this is the selected item
        bottom_item = wheel_ui.get_bottom_item()
        if bottom_item and self.index == bottom_item.index:
            if abs(wheel_ui.master_angle - wheel_ui.target_angle) < 6:
                self.zoom_in(2)
            # pygame.draw.rect(display, (255, 0, 0), (self.rect.x - 3, self.rect.y - 3, self.rect.width + 6, self.rect.height + 6), 3)
            draw_text(display, self.label, wheel_ui.centerx, screen_height - 10, (255, 255, 255), 20, centered=True)
        else:
            self.zoom_out()


# group for wheel items
wheel_item_group = pygame.sprite.Group()


# logo for floating in the BG
class BGLogo(pygame.sprite.Sprite):
    def __init__(self, img):
        pygame.sprite.Sprite.__init__(self)
        self.original_image = img
        self.reset()
        self.start_timer = 120

    def reset(self):
        self.image = self.original_image.copy()
        self.image = pygame.transform.rotate(self.image, random.randint(-20, 20))
        self.rect = self.image.get_rect()
        self.rect.center = (random.randint(75, screen_width - 75), random.randint(50, screen_height - 50))
        self.floating_x = self.rect.x
        self.floating_y = self.rect.y
        if self.rect.centerx >= midscreen_x:
            self.dx = -random.randint(1, 3) / 10
        else:
            self.dx = random.randint(1, 3) / 10
        if self.rect.centery >= midscreen_y:
            self.dy = -random.randint(1, 3) / 10
        else:
            self.dy = random.randint(1, 3) / 10
        self.alpha = 0
        self.max_alpha = 30
        self.timer = 240
        self.wait_timer = 180
        self.toggled = False
        self.image.set_alpha(self.alpha)

    def update(self):
        self.image.set_alpha(self.alpha)
        if self.start_timer:
            self.start_timer -= 1
        else:
            if self.alpha < self.max_alpha and not self.toggled:
                self.alpha += 1
            else:
                self.toggled = True

        if self.toggled:
            if self.timer:
                self.timer -= 1
            else:
                if self.alpha > 0:
                    self.alpha -= 1
                else:
                    self.alpha = 0
                    if self.wait_timer:
                        self.wait_timer -= 1
                    else:
                        self.reset()

        self.floating_x += self.dx
        self.floating_y += self.dy
        self.rect.topleft = (self.floating_x, self.floating_y)

    def draw(self, display):
        display.blit(self.image, self.rect)


# emulator
class PygameEmulator:
    def __init__(self):
        # pygame.event.set_grab(True)

        self.games = self.scan_games()
        self.selected_index = 0
        self.original_thumbnail = pygame.transform.scale(pygame.image.load("images/fail_load.png").convert_alpha(), (180, 180))
        self.background = False
        self.wheel = WheelUI(screen_width, screen_height, PATH, pygame.image.load("images/fail_load.png").convert_alpha())

        self.original_logo_img = pygame.image.load("images/logo.png").convert_alpha()
        self.logo_img = pygame.transform.scale(self.original_logo_img, (int(165 * 2), int(165 * 2)))
        self.big_logo_img = pygame.transform.scale(self.original_logo_img, (int(165 * 4), int(165 * 4)))
        self.logo_alpha = 0
        self.logo_img.set_alpha(self.logo_alpha)

        self.wifi_images = {True:pygame.image.load("images/wifi_on.png").convert_alpha(), False:pygame.image.load("images/wifi_off.png").convert_alpha()}
        internet_connection = check_internet_status()
        self.wifi_image = pygame.transform.scale(self.wifi_images[internet_connection], (20, 20))
        self.wifi_thread = threading.Thread(target=self.update_internet_connection, daemon=True)

        self.bg_logo = BGLogo(self.big_logo_img)

        self.startup = True
        self.logo_timer = 180
        self.start_timer = 240

        self.banner_top = pygame.Surface((screen_width, 20)).convert_alpha()
        self.banner_top.fill((70, 70, 70))
        self.banner_top_rect = self.banner_top.get_rect()
        self.banner_top_rect.midtop = (midscreen_x, 0)

        self.banner_bottom = pygame.Surface((screen_width, 20)).convert_alpha()
        self.banner_bottom.fill((70, 70, 70))
        self.banner_bottom_rect = self.banner_bottom.get_rect()
        self.banner_bottom_rect.midbottom = (midscreen_x, screen_height)

        # text handling
        self.font_cache = {}

        # GPIO to Pygame key mapping (adjust pins per your hardware)
        self.gpio_key_map = {
            17: pygame.K_UP,
            18: pygame.K_DOWN,
            27: pygame.K_LEFT,
            22: pygame.K_RIGHT,
            23: pygame.K_RETURN,
            24: pygame.K_ESCAPE,
        }

        self.power_button_pin = 5  # Set this to your actual power button GPIO pin

        self.gpio_event_queue = queue.Queue()
        self.input_bridge = GPIOInputBridge(self.gpio_key_map, self.gpio_event_queue)
        self.power_button_monitor = PowerButtonMonitor(self.power_button_pin, self.gpio_event_queue)

        self.input_bridge.start()
        self.power_button_monitor.start()
        self.wifi_thread.start()

    def scan_games(self):
        if not os.path.exists("games"):
            os.makedirs("games")
        game_dirs = [d for d in os.listdir(PATH) if os.path.isdir(os.path.join(PATH, d))]
        valid_games = []
        for d in game_dirs:
            main_py = os.path.join(PATH, d, "main.py")
            if os.path.exists(main_py):
                valid_games.append(d)
        return valid_games

    def get_thumb(self, game_folder):
        try:
            if game_folder not in self.all_thumbnails:
                game_path = os.path.abspath(os.path.join(PATH, game_folder))
                new_image = os.path.join(game_path, "thumbnail.png")
                thumbnail = pygame.transform.scale(pygame.image.load(new_image).convert_alpha(), (180, 180))
                self.all_thumbnails[game_folder] = thumbnail
            else:
                thumbnail = self.all_thumbnails[game_folder]

        except Exception as e:
            thumbnail = self.original_thumbnail
        return thumbnail

    def draw_start(self):
        screen.fill((30, 30, 30))
        display.fill((30, 30, 30))
        self.logo_img.set_alpha(self.logo_alpha)
        display.blit(self.logo_img, (midscreen_x - self.logo_img.get_width() // 2, midscreen_y - self.logo_img.get_height() // 2))
        if self.start_timer:
            self.start_timer -= 1
            if self.start_timer <= 180:
                if self.logo_alpha < 255:
                    self.logo_alpha += 5
                else:
                    self.logo_alpha = 255
        else:
            if self.logo_timer:
                self.logo_timer -= 1
                if self.logo_timer <= 90:
                    if self.logo_alpha > 0:
                        self.logo_alpha -= 5
                    else:
                        self.logo_alpha = 0
            else:
                self.logo_timer = 0
                if self.logo_alpha == 0:
                    self.startup = False

        screen.blit(pygame.transform.scale(display, (screen.get_width(), screen.get_height())), (0, 0))
        pygame.display.flip()

    def render_wheel(self, display, wheel_ui):
        pygame.draw.ellipse(display, (60, 60, 60), pygame.Rect((wheel_ui.centerx - wheel_ui.width,
                                                        wheel_ui.centery - 20, wheel_ui.width * 2,
                                                        wheel_ui.height * 2)))

        sprites = sorted(wheel_item_group.sprites(), key=lambda x: x.z_depth)
        for sprite in [s for s in sprites if s.z_depth < 2.0]:
            sprite.draw(display, wheel_ui)

        # display.blit(self.original_logo_img, (midscreen_x - self.original_logo_img.get_width() // 2, midscreen_y - self.original_logo_img.get_height() // 2))

        for sprite in [s for s in sprites if s.z_depth >= 2.0]:
            sprite.draw(display, wheel_ui)

    def update_internet_connection(self):
        while True:
            time.sleep(3)
            internet_connection = check_internet_status()
            self.wifi_image = pygame.transform.scale(self.wifi_images[internet_connection], (20, 20))

    def draw_menu(self):
        screen.fill((30, 30, 30))
        display.fill((40, 40, 40))
        self.bg_logo.update()

        self.bg_logo.draw(display)

        display.blit(self.banner_top, self.banner_top_rect)
        display.blit(self.banner_bottom, self.banner_bottom_rect)

        draw_text(display, int(clock.get_fps()), screen_width - 30, 30, (255, 255, 255), 20, default_font)
        draw_text(display, time.strftime("%H:%M"), screen_width - 40, 5, (255, 255, 255), 20, default_font)
        internet_connection = check_internet_status()
        self.wifi_image = pygame.transform.scale(self.wifi_images[internet_connection], (20, 20))
        display.blit(self.wifi_image, (screen_width - 70, 0))

        self.wheel.update()
        wheel_item_group.update(self.wheel)
        self.selected_index = abs(len(self.games) - 1 - self.wheel.master_index) + 1
        self.selected_index %= len(self.games)
        game_folder = self.games[self.selected_index]
        self.render_wheel(display, self.wheel)

        screen.blit(pygame.transform.scale(display, (screen.get_width(), screen.get_height())), (0, 0))
        pygame.display.flip()

    def run_game(self, game_folder):
        game_path = os.path.abspath(os.path.join(PATH, game_folder))
        main_script = os.path.join(game_path, "main.py")
        try:
            self.background = True
            proc = subprocess.Popen(['python', main_script], cwd=game_path)
            proc.communicate()
        except Exception as e:
            print("Error running game process:", e)

    def run(self):
        try:
            while True:
                clock.tick(60)
                if self.startup:
                    self.draw_start()
                else:
                    self.draw_menu()
                    if self.background:
                        self.background = False

                # Process queued GPIO events first
                while not self.gpio_event_queue.empty():
                    event = self.gpio_event_queue.get()
                    pygame.event.post(event)
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        self.cleanup()
                        pygame.quit()
                        sys.exit()
                    elif event.type == pygame.KEYDOWN:
                        if not self.startup:
                            if event.key == pygame.K_LEFT:
                                self.wheel.target_index = (self.wheel.target_index - 1) % self.wheel.num_items
                                self.wheel.target_angle = self.wheel.angle_increment * self.wheel.target_index
                            if event.key == pygame.K_RIGHT:
                                self.wheel.target_index = (self.wheel.target_index + 1) % self.wheel.num_items
                                self.wheel.target_angle = self.wheel.angle_increment * self.wheel.target_index
                            elif event.key == pygame.K_RETURN:
                                game_folder = self.games[self.selected_index]
                                self.run_game(game_folder)
                                self.background = True
                        else:
                            self.start_timer = 0
                            self.logo_timer = 60
                        if event.key == pygame.K_ESCAPE:
                            self.cleanup()
                            pygame.quit()
                            sys.exit()


        except KeyboardInterrupt:
            self.cleanup()
            pygame.quit()
            sys.exit()

    def cleanup(self):
        self.input_bridge.stop()
        self.power_button_monitor.stop()
        self.input_bridge.join()
        self.power_button_monitor.join()
        if GPIO:
            GPIO.cleanup()


if __name__ == "__main__":
    emulator = PygameEmulator()
    emulator.run()
