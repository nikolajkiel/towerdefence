from typing import Any
import pygame
from collections import deque
from functools import cached_property, lru_cache
import numpy as np
from pathlib import Path
import time

def get_path():
    '''
    path generator
    '''
    points = [(-0, 275), (165, 324), (400, 390), (620,230), (775, 175), (880, 220), (935, 325), (907, 405), (1100, 520), (1200, 450), (1250, 400), (1160, 310), (1240, 220), (1350, 250), (1435, 230), (1540, 250), (1620, 220), (1690, 340), (1790, 290), (1840, 300)]
    for point in points:
        yield point


class General(pygame.sprite.DirtySprite):
    def __init__(self, *args, source=None, parent=None, width=80, height=80, pos=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.source = Path(source) if source is not None else None
        self.parent = parent
        self.width = width
        self.height = height
        self.scale = None
        self.image = self.get_image_n(0)
        self._rect = self.image.get_rect()
        (self.rect.x, self.rect.y) = pos if pos is not None else (0, 0)
        self.time0, self.time = time.time(), 1
        
        self.counter = 0
        self.Dt = deque(maxlen=60)
        self.Pt = deque(maxlen=60)

    def __repr__(self):
        return super().__repr__() + f' ("{self.source}")'

    @property
    def frame_path(self):
        if self.source:
            frame_path = self.source.rglob('*_[0-9][0-9].png')
            return sorted(frame_path)
    
    @property
    def fps(self):
        if self.Dt:
            denominator = (self.time-self.Dt[0])
            return int(len(self.Dt)/(self.time-self.Dt[0])) if denominator != 0 else 1
    
    def distance(self, other):
        return ((self.rect.center[0]-other[0])**2 + (self.rect.center[1]-other[1])**2)**0.5

    @lru_cache
    def get_image_n(self, n):
        image = pygame.image.load(self.frame_path[n])
        if not 'level' in self.source.as_posix():  # FIXME
            image = image.convert_alpha()
        width, height = image.get_width(), image.get_height()
        self.scale = min(self.width/width, self.height/height) if self.scale is None else self.scale
        img = pygame.transform.scale(image, (image.get_width()*self.scale, image.get_height()*self.scale))
        return img

    @property
    def rect(self):
        return self._rect

    def update(self, *args: Any, **kwargs: Any) -> None:
        super().update(*args, **kwargs)
        self.counter += 1
        self.time = time.time() - self.time0
        self.Dt.append(self.time)
        self.Pt.append(self.rect.center)


    @property
    def n_frames(self):
        # two digits combined with '*.png'
        return len(self.frame_path)

class GameStats(General):
    '''
    text stats in top right corner
    '''
    FONTSIZE = 20
    def __init__(self, *args, width=480, height=120, **kwargs):
        kwargs = kwargs | {"width": width, "height": height}
        super().__init__(*args, **kwargs)
        # self.image = pygame.Surface((width, height), pygame.SRCALPHA)
        self.game = self.parent
        self.rect.x = self.parent.screen.get_width() - self.rect.width - 10
        self.rect.y = 10
        self.log = deque(maxlen=6)

    @lru_cache
    def get_image_n(self, n):
        image = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        return image

    @cached_property
    def pngs(self):
        return [pygame.image.load(f'assets/effects/heart/heart_{n:02d}.png') for n in range(4)]

    @property
    def life(self):
        from itertools import takewhile
        hearts = [self.pngs[3]] * (self.game.health//3)
        hearts += [self.pngs[self.game.health%3]] if self.game.health%3 else []
        hearts += [self.pngs[0]] * (10-len(hearts))


        for x, heart in zip(range(11,0,-1), hearts):
            scale = 0.2
            heart = pygame.transform.scale(heart, (int(heart.get_width()*scale), int(heart.get_height()*scale)))
            self.image.blit(heart, (x*heart.get_width(), 0))
    
    @cached_property
    def font(self):
        return pygame.font.Font(None, self.FONTSIZE)
    
    @cached_property
    def Font(self):
        return pygame.font.Font(None, int(self.FONTSIZE*1.5))

    def update(self, *args, **kwargs):
        self.dirty = 1
        super().update(*args, **kwargs)
        self.image.fill((0,0,0,0))
        self.parent.blit_rects[-1].append(self.rect)
        stats = [self.Font.render(f"Money: {game.money}", True, (219, 172, 52))] + \
            [self.font.render(f"Time: {game.time:.2f}", True, (255, 255, 255))] + \
            [self.font.render(f"FPS: {game.fps}/{game.FPS}", True, (255, 255, 255))]
        texts = stats + [self.font.render(f"{log}", True, (255, 255, 255)) for log in self.log]

        for i, text in enumerate(texts):
            text_rect = text.get_rect()
            text_rect.x = self.image.get_width() - text_rect.width
            text_rect.y += self.FONTSIZE * i
            self.image.blit(text, text_rect)
        self.life


class Character(General):
    def __init__(self,*args, route=get_path, speed=45, **kwargs):
        if 'pos' in kwargs:
            self.pos = kwargs.pop('pos')
        super().__init__(*args, **kwargs)
        if hasattr(self, 'pos'):
            self.rect.x, self.rect.y = self.pos
        self.speed = speed
        self.move_offset = [0, 0]
        self.route = route()
        
        self.destination = next(self.route)

    def move(self, dx, dy):
        self.rect.x += dx
        self.rect.y += dy

    def navigate(self, debug=[]):
        self.dirty = 1
        if not debug:
            debug.append(id(self))
        if id(self) in debug:
            ...
            # print(self.rect.x, self.rect.y, self.rect.center)
        direction_vector = np.array(self.destination) - np.array(self.rect.center)
        vector_length = (direction_vector[0]**2 + direction_vector[1]**2) ** 0.5
        if vector_length == 0:
            norm = [0, 0]
        else:
            norm = direction_vector / vector_length
        if vector_length <= self.speed:
            try:
                self.destination = next(self.route)
            except StopIteration:
                self.kill()
                game.stats.log.append(f"enemy reached goal at {self.rect.center}")
                if game.health > 0:
                    game.health -= 1
                else:
                    game.stats.log.append(f"game over")
                return
        move_x = self.speed/self.fps * norm[0] + self.move_offset[0]
        self.move_offset[0] = move_x - int(move_x)
        move_y = self.speed/self.fps * norm[1] + self.move_offset[1]
        self.move_offset[1] = move_y - int(move_y)
        self.rect.x += int(move_x)
        self.rect.y += int(move_y)

    def put_on_fire(self):
        fire = Effect(width=80, height=80, follow=self, source='assets/effects/fire')


class Effect(Character):
    '''
    animated effect which
    can be attached to a sprite
    '''
    def __init__(self, *args, source = 'assets/effects/fire', follow: Character = None, **kwargs):
        kwargs = kwargs | {"source": source}
        super().__init__(*args, **kwargs)
        self.follow = follow
        game.all_sprites.add(self)
        self.counter = 0

    def update(self, *args, **kwargs):
        super().update(*args, **kwargs)
        self._rect.x = self.follow.rect.center[0]-self.image.get_width()/2
        self._rect.y = self.follow.rect.center[1]-self.image.get_height()
    
    # def update(self, *args: Any, **kwargs: Any) -> None:
    #     super().update(*args, **kwargs)
    #     if self.time > 19:
    #         self.kill()
    #         return
    #     # cycle sprite images
    #     # self.image = pygame.Surface
    #     # n_frame = self.counter//min(self.fps, 20)%min(self.n_frames, max(1, int(self.time)))
    #     n_frame = self.counter//4%min(self.n_frames, max(1, int(self.time)))
    #     self.image = self.get_image_n(n_frame).convert_alpha() # pygame.image.load(f'{self.source}/{self.source.parts[-1]}_{n_frame:02d}.png').convert_alpha()

    #     self.rect.x = self.follow.rect.center[0]-self.image.get_width()/2
    #     self.rect.y = self.follow.rect.center[1]-self.image.get_height()
        
    

class Golem(Character):
    WALK = [24, 25, 26, 27, 28, 29, 30, 31, 15]
    source = Path('assets/sprites/golem')

    # animate sprite
    def update(self, *args: Any, **kwargs: Any) -> None:
        super().update(*args, **kwargs)
        # cycle sprite images
        n_frame = self.WALK[self.counter//(max(1, self.parent.FPS//8))%len(self.WALK)]
        self.image = self.get_image_n(n_frame)

        self.navigate()


class Tower(General):
    PRICE = 50
    UPGRADE_PRICES = [50, 100]
    TOWERS = {'brown': [(2,0,18), (2, 41, 0, 43), (2, 41, 0, 41, 24)], 'grey': [(37,2,2,36)], 'red': [(52,40,40,40,24)]}
    def __init__(self, *args, source='assets/Towers (brown)', pos=None, color='brown', rank=0, **kwargs):
        kwargs = kwargs | {"source": source}
        super().__init__(*args, **kwargs)
        self.color = color
        self.rank = rank
        self.pos = pos

    def upgrade(self):
        self.dirty = 1
        if self.rank >= len(self.UPGRADE_PRICES):
            game.stats.log.append(f"tower at {self.pos} is already max rank ({self.rank})")
            return
        if game.money < self.UPGRADE_PRICES[min(self.rank,1)]:
            game.stats.log.append(f"not enough money to upgrade tower at {self.pos}")
            return
        game.money -= self.UPGRADE_PRICES[self.rank]
        self.rank += 1
        self.get_image_n.cache_clear()
        self.update()

    @lru_cache
    def stack_images(self, ns):
        print(42, self._rect, dir(self._rect))
        self.parent.blit_rects[-1].append(self.rect.inflate(2,2))

        imgs = []
        for n in ns:
            img = self.get_image_n(n)
            
            imgs.append(img)
            max_width = max([img.get_width() for img in imgs])
        self.image = pygame.Surface((max_width, sum([img.get_height() for img in imgs])), pygame.SRCALPHA)
        y = self.image.get_height() - imgs[0].get_height()
        for img in imgs:
            self.image.blit(img, (0 + (max_width-img.get_width())/2, y))
            y -= img.get_height() - 0

        self._rect = self.image.get_rect()
        self.rect.x = self.pos[0]-self.rect.width/2
        self.rect.y = self.pos[1]-self.rect.height+imgs[0].get_height()/2

    def update(self):
        tower = self.TOWERS[self.color][self.rank]
        self.stack_images(tower)

class Schedule:
    type = 42000
    def __init__(self, func, *args, delay=500, parent=None, **kwargs):
        self.start_time = time.time()
        self.delay = delay
        self.callable = func
        self.args = args
        self.kwargs = kwargs | {"parent": parent}
        self.parent = parent
    
    @property
    def event(self):
        return pygame.event.Event(self.type, func=self)

    @property
    def is_ready(self):
        ready = (time.time() - self.start_time)*1000 > self.delay
        # print(ready)
        return ready

    def __call__(self):
        if self.is_ready:
            rv = self.callable(*self.args, **self.kwargs)
            self.parent.all_enemies.add(rv)
            self.parent.all_sprites.add(rv)
        else:
            pygame.event.post(self.event)


class Game(General):
    def __init__(self, money=200, width=1800, height=600, level=0, fps=180, *args, **kwargs):
        kwargs = kwargs | {"width": width, "height": height}
        super().__init__(*args, **kwargs)
        self.level = level
        self.screen = pygame.display.set_mode((self.width, self.height))
        self.money = money
        self.health = 30
        self.FPS = fps
        self.time0 = time.time()
        self.time = time.time()
        self.clock = pygame.time.Clock()
        self.pause = False
        self.blit_rects = deque(maxlen=2) # store dirty rects from current and previous frame for clearing
        [self.blit_rects.append([]) for _ in range(self.blit_rects.maxlen)]
        self.setup()

    def create_wave(self, n_enemies=2, offset=0):
        '''spawn enemies with a delay'''
        for i in range(n_enemies):
            s = Schedule(Golem, delay=i*1200 + offset, parent=self, source='assets/sprites/golem')
            e = pygame.event.Event(42000, func=s)
            pygame.event.post(e)

    def setup(self):
        # self.image = self.get_image_n(self.level)
        self.all_enemies = pygame.sprite.LayeredDirty() # pygame.sprite.Group()
        self.all_sprites = pygame.sprite.LayeredDirty() # pygame.sprite.Group()

        self.character = Character(source='assets/effects/fire', width=40, height=40)
        self.stats = GameStats(parent=self)
        [self.create_wave(offset=15000*i) for i in range(4)]
        # for offset in range(0,-11,-1):
        #     enemy = Enemy(source='assets/sprites/golem')
        #     self.all_enemies.add(enemy)
        self.all_sprites.add(self.character)
        self.all_sprites.add(self.stats)
        self.all_sprites.add(self.all_enemies)
        self.background

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
        tower = Tower(pos=pos, parent=self)
        self.all_sprites.add(tower)
        self.all_enemies.sprites()[0].put_on_fire()
        self.stats.log.append(f"tower spawned at {pos}")

    def mouse_hover(self, event):
        return
        for tower in self.all_sprites:
            if isinstance(tower, Tower) and tower.rect.collidepoint(event.pos):
                self.screen.blit(pygame.image.load('assets/range.png'), (tower.pos[0]-tower.rect.width/2, tower.pos[1]-tower.rect.height/2))
                break

    def update(self, *args: Any, **kwargs: Any) -> None:
        self.all_sprites.clear(self.background, self.get_image_n(self.level))
        super().update(*args, **kwargs)
        # sort all sprites by y position
        # self.all_sprites = pygame.sprite.LayeredUpdates(sorted(self.all_sprites.sprites(), key=lambda sprite: sprite.rect.y+sprite.rect.height))
        
        self.all_sprites.update()

    @property
    def background(self):
        # Load and blit the background image
        bgd = self.get_image_n(self.level)
        for point in get_path():
            pygame.draw.circle(bgd, (255, 0, 0), point, 5)
        
        return bgd

    def cleanup(self):
        self.all_sprites.empty()
        self.__init__()

    def run(self):
        run = True


        while run:
        #     if self.time > 2 and not any([isinstance(inst, Effect) for inst in self.all_sprites.__iter__()]) and self.time< 3:
        #         for enemy in self.all_enemies:
        #             fire = Effect(width=80, height=80, follow=enemy, source='assets/effects/fire')
        #             self.all_sprites.add(fire)

            while self.pause:
                for event in pygame.event.get():
                    if event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_p:
                            # unpause
                            self.pause = not self.pause
                            time_offset = time.time() - time_paused
                            self.time0 += time_offset
                            
            self.time = time.time() - self.time0
            for event in pygame.event.get():  # Retrieve all pending events
                if event.type == 42000 and hasattr(event, 'func'):
                    event.func()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE or event.type == pygame.QUIT:
                        run = False
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
                    if event.key == pygame.K_h:
                        self.health += 1 if self.health < 30 else 0
                    if event.key == pygame.K_p:
                        time_paused = time.time()
                        self.pause = not self.pause
                    if event.key == pygame.K_r and pygame.K_LCTRL:
                        self.cleanup()
                        # game = Game()
                # mouse click
                if event.type == pygame.MOUSEBUTTONDOWN:
                    self.mouse_click(event)
                if event.type == pygame.MOUSEMOTION:
                    self.mouse_hover(event)
            
            
            
            self.update()
            # self.all_sprites = pygame.sprite.LayeredUpdates(sorted(self.all_sprites.sprites(), key=lambda sprite: sprite.rect.y+sprite.rect.height))
            self.clock.tick(self.FPS)

            rects = self.all_sprites.draw(self.screen)
            pygame.display.update(rects)
            # pygame.display.flip()

        pygame.quit()


if __name__ == "__main__":
    pygame.init()
    game = Game(source='assets/level', level=0)

    game.run()

    # import cProfile as profile
    # with profile.Profile() as pr:
    #     game.run()
    #     pr.dump_stats('main.prof')
    #     # gprof2dot -f pstats main.pstats | dot -Tsvg -o main.svg