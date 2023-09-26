from typing import Any
import pygame
from collections import deque
from functools import cached_property
import numpy as np
from random import randint
from pathlib import Path
import time

def get_path():
    '''
    path generator
    '''
    points = [(-30, 275), (165, 324), (400, 390), (620,230), (775, 175), (880, 220), (935, 325), (907, 405), (1100, 520), (1200, 450), (1250, 400), (1160, 310), (1240, 220), (1350, 250), (1435, 230), (1540, 250), (1620, 220), (1690, 340), (1790, 290), (1840, 300)]
    while True:
        for point in points:
            yield point
            if 'game' in globals():
                game.stats.log.append(f"point reached at {point}")



class GameStats(pygame.sprite.Sprite):
    '''
    text stats in top right corner
    '''
    def __init__(self, screen, *args, width=320, height=120, **kwargs):
        super().__init__(*args, **kwargs)
        self.image = pygame.Surface((width, height), pygame.SRCALPHA)
        self.parent_screen = screen
        self.rect = self.image.get_rect()
        self.rect.x = self.parent_screen.get_width() - self.rect.width - 10
        self.rect.y = 10
        self.log = deque(maxlen=6)
    
    def update(self, *args, **kwargs):
        font_size = 20
        self.image.fill((0,0,0,0))
        font = pygame.font.Font(None, font_size)
        stats = [font.render(f"Money: {game.money}", True, (219, 172, 52))] + \
            [font.render(f"Time: {game.time:.2f}", True, (255, 255, 255))]
        texts = stats + [font.render(f"{log}", True, (255, 255, 255)) for log in self.log]

        for i, text in enumerate(texts):
            text_rect = text.get_rect()
            text_rect.y += font_size * i
            self.image.blit(text, text_rect)


class Character(pygame.sprite.Sprite):
    def __init__(self,*args, color=(0, 0, 0), width=80, height=80, pos=(0,0), route=get_path, speed=2, **kwargs):
        super().__init__(*args, **kwargs)
        self.route = route()
        self.speed = speed
        self.width = width
        self.height = height
        self.image = pygame.Surface((width, height))
        self.image.fill(color)
        self.rect = self.image.get_rect()
        (self.rect.x, self.rect.y) = pos if pos is not None else next(self.route)
        self.destination = next(self.route)
        self.time0, self.time = time.time(), 1

    def update(self, *args: Any, **kwargs: Any) -> None:
        return super().update(*args, **kwargs)


    def move(self, dx, dy):
        self.rect.x += dx
        self.rect.y += dy

    @property
    def n_frames(self):
        # two digits combined with '*.png'
        frames = self.source.rglob('*_[0-9][0-9].png')
        return len(list(frames))
    
    def navigate(self):
        direction_vector = np.array(self.destination) - np.array(self.rect.center)
        norm = np.linalg.norm(direction_vector)

        vector_length = (direction_vector[0]**2 + direction_vector[1]**2) ** 0.5
        if vector_length < 10:
            try:
                self.destination = next(self.route)
            except StopIteration:
                self.kill()
                game.stats.log.append(f"enemy reached goal at {self.rect.center}")
                game.money -= 10
                return
        self.rect.x += self.speed * direction_vector[0] / norm
        self.rect.y += self.speed * direction_vector[1] / norm


class Effect(Character):
    '''
    animated effect which
    can be attached to a sprite
    '''
    def __init__(self, *args, source = 'assets/effects/fire', follow: Character = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.source = Path(source)
        self.follow = follow
        self.counter = 0
    
    def update(self):
        if self.time > 9:
            self.kill()
            return
        self.time = time.time() - self.time0
        # cycle sprite images
        self.counter += 1
        # self.image = pygame.Surface
        n_frame = self.counter//4%min(self.n_frames, max(1, int(self.time)))
        self.image = pygame.image.load(f'{self.source}/{self.source.parts[-1]}_{n_frame:02d}.png').convert_alpha()
        width, height = self.image.get_width(), self.image.get_height()
        scale = self.width/width
        self.image = pygame.transform.scale(self.image, (self.image.get_width()*scale, self.image.get_height()*scale))
        self.rect.x = self.follow.rect.center[0]-self.image.get_width()/2
        self.rect.y = self.follow.rect.center[1]-self.image.get_height()
        
    

class Enemy(Character):
    WALK = [24, 25, 26, 27, 28, 29, 30, 31]
    def __init__(self, *args, source = 'assets/sprites/golem', **kwargs):
        super().__init__(*args, **kwargs)
        self.source = Path(source)
        self.counter = 0

    
    
    # animate sprite
    def update(self):
        # cycle sprite images
        self.counter += 1
        # self.image = pygame.Surface
        n_frame = self.counter//4%len(self.WALK) + self.WALK[0]
        self.image = pygame.image.load(f'{self.source}/{self.source.parts[-1]}_{n_frame:02d}.png').convert_alpha()
        width, height = self.image.get_width(), self.image.get_height()
        scale = self.width/width
        self.image = pygame.transform.scale(self.image, (self.image.get_width()*scale, self.image.get_height()*scale))
        # if self.counter % 4 == 0:
        self.navigate()



class Tower(pygame.sprite.Sprite):
    PRICE = 50
    UPGRADE_PRICES = [50, 100]
    TOWERS = {'brown': [(2,0,18)], 'grey': [(37,2,2,36)], 'red': [(52,40,40,40,24)]}
    def __init__(self, *args, color=(0, 0, 0), width=30, height=30, pos=(0,0), rank=0, **kwargs):
        super().__init__(*args, **kwargs)
        self.image = pygame.Surface((width, height), pygame.SRCALPHA)
        self.image.fill(color)
        self.pos = (pos[0]-pos[0]%20, pos[1]-pos[1]%10 )
        self.rank = rank

    def upgrade(self):
        if game.money < self.UPGRADE_PRICES[min(self.rank,1)]:
            game.stats.log.append(f"not enough money to upgrade tower at {self.pos}")
            return
        game.money -= self.UPGRADE_PRICES[min(self.rank,2)]
        game.money -= self.UPGRADE_PRICES[self.rank]
        self.rank += 1

    def update(self):
        color = ['brown', 'grey', 'red'][min(self.rank,2)]
        imgs = []
        for n in self.TOWERS[color][0]:
            img = pygame.image.load(f'assets/Towers ({color})/tower_{n:02d}.png').convert_alpha()
            imgs.append(img)
        max_width = max([img.get_width() for img in imgs])
        self.image = pygame.Surface((max_width, sum([img.get_height() for img in imgs])), pygame.SRCALPHA)
        
        y = self.image.get_height() - imgs[0].get_height()
        for img in imgs:
            self.image.blit(img, (0 + (max_width-img.get_width())/2, y))
            y -= img.get_height()-42

        self.rect = self.image.get_rect()
        self.rect.x = self.pos[0]-self.rect.width/2
        self.rect.y = self.pos[1]-self.rect.height+imgs[0].get_height()/2



class Game:
    def __init__(self, money=200, width=1800, height=600, level=1, *args, **kwargs):
        self.level = level
        self.width = width
        self.height = height
        self.screen = pygame.display.set_mode((self.width, self.height))
        self.money = money
        self.setup()
        self.time0 = time.time()
        self.time = time.time()

    def setup(self):
        self.all_enemies = pygame.sprite.Group()
        self.all_sprites = pygame.sprite.Group()

        self.character = Character(color=(255, 0, 0), width=40, height=40)
        self.stats = GameStats(self.screen)
        for offset in range(0,-11,-1):
            enemy = Enemy(width=200, pos=(offset*100-30, 275))
            self.all_enemies.add(enemy)
        self.all_sprites.add(self.character)
        self.all_sprites.add(self.stats)
        self.all_sprites.add(self.all_enemies)

    def draw_background(self):
        # Load and blit the background image
        self.screen.blit(pygame.image.load(f'assets/levels/level_{self.level:02d}.png'), (0, 0))

    def move(self, dx, dy):
        self.character.move(dx, dy)

    def mouse_click(self, event):
        # self.stats.log.append(f"mouse click at {event.pos}")
        if event.button == 1:
            self.spawn_tower(event.pos)
        elif event.button == 3:
            self.upgrade_tower(event.pos)

    def upgrade_tower(self, pos):
        for tower in self.all_sprites:
            if isinstance(tower, Tower) and tower.rect.collidepoint(pos):
                tower.upgrade()
                self.stats.log.append(f"tower upgraded at {pos} (rank: {tower.rank})")
                break
    
    def spawn_tower(self, pos):
        if self.money < Tower.PRICE:
            self.stats.log.append(f"not enough money to spawn tower at {pos}")
            return
        self.money -= Tower.PRICE
        tower = Tower(pos=pos)
        self.all_sprites.add(tower)
        self.stats.log.append(f"tower spawned at {pos}")

    def mouse_hover(self, event):
        return
        for tower in self.all_sprites:
            if isinstance(tower, Tower) and tower.rect.collidepoint(event.pos):
                self.screen.blit(pygame.image.load('assets/range.png'), (tower.pos[0]-tower.rect.width/2, tower.pos[1]-tower.rect.height/2))
                break
    def cleanup(self):
        self.all_sprites.empty()
        self.__init__()

    def run(self):
        run = True


        while run:
            if self.time > 2 and not any([isinstance(inst, Effect) for inst in self.all_sprites.__iter__()]) and self.time< 3:
                for enemy in self.all_enemies:
                    fire = Effect(width=80, height=80, follow=enemy, source='assets/effects/fire')
                    self.all_sprites.add(fire)

            
            self.time = time.time() - self.time0
            for event in pygame.event.get():  # Retrieve all pending events
                if event.type == pygame.QUIT:
                    run = False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_LEFT:
                        self.move(-10, 0)
                    if event.key == pygame.K_RIGHT:
                        self.move(10, 0)
                    if event.key == pygame.K_UP:
                        self.move(0, -10)
                    if event.key == pygame.K_DOWN:
                        self.move(0, 10)
                    if event.key == pygame.K_m:
                        self.money += 100
                    if event.key == pygame.K_r and pygame.K_LCTRL:
                        self.cleanup()
                        # game = Game()
                # mouse click
                if event.type == pygame.MOUSEBUTTONDOWN:
                    self.mouse_click(event)
                if event.type == pygame.MOUSEMOTION:
                    self.mouse_hover(event)

            self.draw_background()  # Draw the background in each frame
            self.all_sprites.update()
            # sort all sprites by y position
            self.all_sprites = pygame.sprite.LayeredUpdates(sorted(self.all_sprites.sprites(), key=lambda sprite: sprite.rect.y+sprite.rect.height))
            self.all_sprites.draw(self.screen)
            pygame.display.flip()

        pygame.quit()


if __name__ == "__main__":
    pygame.init()
    game = Game()
    game.run()