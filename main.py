from typing import Any
import pygame
from collections import deque
from functools import cached_property
import numpy as np
from pathlib import Path
import time
from PIL import Image


def load_image_compat(path: str | Path) -> pygame.Surface:
    """Load images even when pygame lacks SDL_image extended format support."""
    image_path = Path(path)
    try:
        return pygame.image.load(image_path.as_posix())
    except pygame.error:
        # Fallback for environments where pygame can only load BMP natively.
        with Image.open(image_path) as pil_img:
            rgba_img = pil_img.convert("RGBA")
            return pygame.image.fromstring(rgba_img.tobytes(), rgba_img.size, "RGBA")


def get_path():
    """
    path generator
    """
    points = [
        (-0, 275),
        (165, 324),
        (400, 390),
        (620, 230),
        (775, 175),
        (880, 220),
        (935, 325),
        (907, 405),
        (1100, 520),
        (1200, 450),
        (1250, 400),
        (1160, 310),
        (1240, 220),
        (1350, 250),
        (1435, 230),
        (1540, 250),
        (1620, 220),
        (1690, 340),
        (1790, 290),
        (1840, 300),
    ]
    for point in points:
        yield point


class General(pygame.sprite.Sprite):
    # Default render layer; subclasses override (enemies=10, towers=20, effects=30, UI=40).
    _layer = 0

    def __init__(
        self, *args, source=None, parent=None, width=80, height=80, pos=None, **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.source = Path(source) if source else getattr(self, "source", None)
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
            frame_path = self.source.rglob("*_[0-9][0-9].png")
            return sorted(frame_path)

    @property
    def fps(self):
        if self.Dt:
            denominator = self.time - self.Dt[0]
            if denominator == 0:
                return 1
            else:
                return max(1, int(len(self.Dt) / (self.time - self.Dt[0])))

    def distance(self, other):
        return (
            (self.rect.center[0] - other[0]) ** 2
            + (self.rect.center[1] - other[1]) ** 2
        ) ** 0.5

    def get_image_n(self, n):
        cache = self.__dict__.setdefault("_image_cache", {})
        if n not in cache:
            image = load_image_compat(self.frame_path[n])
            if "level" not in self.source.as_posix():  # FIXME
                image = image.convert_alpha()
            width, height = image.get_width(), image.get_height()
            self.scale = (
                min(self.width / width, self.height / height)
                if self.scale is None
                else self.scale
            )
            img = pygame.transform.scale(
                image,
                (
                    int(image.get_width() * self.scale),
                    int(image.get_height() * self.scale),
                ),
            )
            cache[n] = img
        return cache[n]

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
    """
    text stats in top right corner
    """

    FONTSIZE = 20
    _layer = 40  # UI sits on top of everything

    def __init__(self, *args, width=480, height=120, **kwargs):
        kwargs = kwargs | {"width": width, "height": height}
        super().__init__(*args, **kwargs)
        # self.image = pygame.Surface((width, height), pygame.SRCALPHA)
        self.game = self.parent
        self.rect.x = self.parent.screen.get_width() - self.rect.width - 10
        self.rect.y = 10
        self.log = deque(maxlen=6)

    def get_image_n(self, n):
        cache = self.__dict__.setdefault("_image_cache", {})
        if n not in cache:
            cache[n] = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        return cache[n]

    @cached_property
    def pngs(self):
        return [
            load_image_compat(f"assets/effects/heart/heart_{n:02d}.png")
            for n in range(4)
        ]

    @property
    def life(self):
        hearts = [self.pngs[3]] * (self.game.health // 3)
        hearts += [self.pngs[self.game.health % 3]] if self.game.health % 3 else []
        hearts += [self.pngs[0]] * (10 - len(hearts))

        for x, heart in zip(range(11, 0, -1), hearts):
            scale = 0.2
            heart = pygame.transform.scale(
                heart, (int(heart.get_width() * scale), int(heart.get_height() * scale))
            )
            self.image.blit(heart, (x * heart.get_width(), 0))

    @cached_property
    def font(self):
        return pygame.font.Font(None, self.FONTSIZE)

    @cached_property
    def Font(self):
        return pygame.font.Font(None, int(self.FONTSIZE * 1.5))

    def update(self, *args, **kwargs):
        super().update(*args, **kwargs)
        self.image.fill((0, 0, 0, 0))
        stats = (
            [self.Font.render(f"Money: {self.game.money}", True, (219, 172, 52))]
            + [
                self.Font.render(
                    f"Wave: {self.game.wave_number} / {self.game.WAVE_COUNT}",
                    True,
                    (255, 220, 120),
                )
            ]
            + [self.font.render(f"Time: {self.game.time:.2f}", True, (255, 255, 255))]
            + [
                self.font.render(
                    f"FPS: {self.game.fps}/{self.game.FPS}", True, (255, 255, 255)
                )
            ]
        )
        texts = stats + [
            self.font.render(f"{log}", True, (255, 255, 255)) for log in self.log
        ]

        for i, text in enumerate(texts):
            text_rect = text.get_rect()
            text_rect.x = self.image.get_width() - text_rect.width
            text_rect.y += self.FONTSIZE * i
            self.image.blit(text, text_rect)
        self.life


class Character(General):
    # Default HP. Concrete enemy subclasses override (Viking=60, Golem=100).
    # Used as max_hp at construction; if None, this Character is not damageable
    # (Effect / decorative followers fall through this path).
    MAX_HP: int | None = 50
    # Gold awarded to the player when this character dies. 0 = no reward.
    GOLD_REWARD: int = 0
    # Set to True the first time this character drops below half HP and we've
    # spawned a fire Effect. Class-level default keeps hand-built / __new__'d
    # instances safe without a custom __init__.
    _on_fire: bool = False

    def __init__(self, *args, route=get_path, speed=45, left=True, **kwargs):
        if "pos" in kwargs:
            self.pos = kwargs.pop("pos")
        super().__init__(*args, **kwargs)
        if hasattr(self, "pos"):
            self.rect.x, self.rect.y = self.pos
        self.speed = speed
        self.move_offset = [0, 0]
        self.route = route()
        self.left = left

        self.destination = next(self.route)
        self.max_hp = self.MAX_HP if self.MAX_HP is not None else 0
        self.hp = self.max_hp

    def take_damage(self, amount: int) -> None:
        """Reduce hp by ``amount``; on death, award gold and remove the sprite.

        Safe to call on Characters whose MAX_HP is None — they simply have 0 hp
        and die instantly, which is acceptable since we never aim bullets at them.
        """
        if amount <= 0:
            return
        self.hp -= amount
        if self.hp <= 0:
            self.hp = 0
            if self.parent is not None and self.GOLD_REWARD:
                self.parent.money += self.GOLD_REWARD
                self.parent.stats.log.append(
                    f"{type(self).__name__} died (+{self.GOLD_REWARD}g)"
                )
            self.kill()
            return
        # Light up at half HP. One-shot: the Effect is owned by the sprite
        # group and cleaned up when the enemy dies (Effect self-kills when its
        # follow is no longer alive).
        if not self._on_fire and self.max_hp > 0 and self.hp < self.max_hp / 2:
            self._on_fire = True
            self.put_on_fire()

    def move(self, dx, dy):
        self.rect.x += dx
        self.rect.y += dy

    def navigate(self):
        # Removed dead debug hook (was: per-instance position print gated by id(self)).
        left = -66 if self.left else 22
        direction_vector = np.array(self.destination) - np.array(
            [self.rect.center[0], self.rect.bottom + left]
        )
        vector_length = (direction_vector[0] ** 2 + direction_vector[1] ** 2) ** 0.5
        if vector_length == 0:
            norm = [0, 0]
        else:
            norm = direction_vector / vector_length
        if vector_length <= self.speed:
            try:
                self.destination = next(self.route)
            except StopIteration:
                self.kill()
                self.parent.stats.log.append(
                    f"enemy reached goal at {self.rect.center}"
                )
                self.parent.health -= 1
                if self.parent.health <= 0:
                    self.parent.stats.log.append("game over")
                return
        move_x = self.speed / self.fps * norm[0] + self.move_offset[0]
        self.move_offset[0] = move_x - int(move_x)
        move_y = self.speed / self.fps * norm[1] + self.move_offset[1]
        self.move_offset[1] = move_y - int(move_y)
        self.rect.x += int(move_x)
        self.rect.y += int(move_y)

    def put_on_fire(self):
        fire = Effect(
            width=80,
            height=80,
            follow=self,
            source="assets/effects/fire",
            parent=self.parent,
        )


class Effect(Character):
    """
    animated effect which
    can be attached to a sprite
    """

    _layer = 30  # effects on top of towers and enemies

    def __init__(
        self, *args, source="assets/effects/fire", follow: Character = None, **kwargs
    ):
        kwargs = kwargs | {"source": source}
        super().__init__(*args, **kwargs)
        self.follow = follow
        self.parent.all_sprites.add(self)
        self.counter = 0

    def update(self, *args, **kwargs):
        # If the thing we're attached to is gone, we go too. Without this the
        # fire would be stuck floating wherever the enemy died.
        if self.follow is None or not self.follow.alive():
            self.kill()
            return
        super().update(*args, **kwargs)
        # Cycle through frames at ~12 fps regardless of game FPS.
        ticks_per_frame = max(1, self.parent.FPS // 12)
        n_frame = (self.counter // ticks_per_frame) % self.n_frames
        self.image = self.get_image_n(n_frame)
        self._rect.x = self.follow.rect.center[0] - self.image.get_width() / 2
        self._rect.y = self.follow.rect.center[1] - self.image.get_height()

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
    source = Path("assets/sprites/golem")
    _layer = 10  # enemies render above background, below towers
    MAX_HP = 100
    GOLD_REWARD = 25

    # animate sprite
    def update(self, *args: Any, **kwargs: Any) -> None:
        super().update(*args, **kwargs)
        # cycle sprite images
        n_frame = self.WALK[
            self.counter // (max(1, self.parent.FPS // 8)) % len(self.WALK)
        ]
        self.image = self.get_image_n(n_frame)

        self.navigate()


class Viking(Golem):
    WALK = [0, 1, 2, 3, 4, 5, 6, 7]
    source = Path("assets/sprites/viking")
    MAX_HP = 60
    GOLD_REWARD = 10


def closest_enemy(pos, enemies, max_range):
    """Return the enemy in ``enemies`` closest to ``pos`` within ``max_range``, or None.

    Pure helper — no pygame state mutation, easy to unit-test.
    """
    best = None
    best_d2 = max_range * max_range
    for e in enemies:
        ex, ey = e.rect.center
        dx = ex - pos[0]
        dy = ey - pos[1]
        d2 = dx * dx + dy * dy
        if d2 <= best_d2:
            best_d2 = d2
            best = e
    return best


def _make_arrow_surface() -> pygame.Surface:
    """Build a horizontal arrow sprite once. Tip points to +x.

    Brown wooden shaft, grey triangular tip. Module-level so we don't rebuild
    it per arrow instance — rotation reuses this baked surface.
    """
    width, height = 28, 8
    surf = pygame.Surface((width, height), pygame.SRCALPHA)
    # Shaft: ~22 px brown rect, vertically centered, 3 px thick.
    pygame.draw.rect(surf, (102, 60, 22), pygame.Rect(0, 3, 22, 3))
    # Highlight stripe for contrast.
    pygame.draw.rect(surf, (140, 90, 40), pygame.Rect(0, 4, 22, 1))
    # Tip: grey triangle pointing right, ~6 px long.
    tip = [(22, 1), (28, 4), (22, 7)]
    pygame.draw.polygon(surf, (180, 180, 190), tip)
    pygame.draw.polygon(surf, (90, 90, 100), tip, width=1)
    return surf


_ARROW_SURFACE: pygame.Surface | None = None


def _arrow_surface() -> pygame.Surface:
    """Lazy accessor — pygame.display must be initialised before SRCALPHA surfaces."""
    global _ARROW_SURFACE
    if _ARROW_SURFACE is None:
        _ARROW_SURFACE = _make_arrow_surface()
    return _ARROW_SURFACE


class Bullet(pygame.sprite.Sprite):
    """Ballistic projectile base. Subclasses provide visuals via ``self.image``.

    Movement model: at spawn, an initial velocity is computed toward the target
    (with an optional upward "launch" kick for a lobbed arc). Each frame:
    - gravity adds to vertical velocity (parabolic trajectory)
    - drag scales velocity down (the bullet slows with age)
    - position is integrated and the visuals are rotated to current direction.

    Class-level config knobs let variants (Arrow, future Fireball, etc.) tune
    behaviour without touching logic.
    """

    _layer = 25  # between towers (20) and effects (30)
    damage: int = 10
    speed: float = 600.0  # initial speed, px / sec
    impact_radius: int = 0  # 0 = single-target hit; > 0 = AoE
    max_hits: int = 1  # pierce count
    enemy_modifiers: dict[type, float] = {}
    gravity: float = 250.0  # px / sec^2 (positive = pulls down). Low because
    # towers are tall and enemies are close, so we just want a gentle dip.
    drag: float = 0.4  # fraction of speed lost per second
    launch_elevation: float = 0.0  # archer is already elevated; aim straight

    def __init__(self, *, pos, target, parent, direction=None):
        super().__init__()
        self.parent = parent
        self.target = target
        self.pos = [float(pos[0]), float(pos[1])]
        self._hits_left = self.max_hits
        self._hit: set[int] = set()  # ids of enemies already damaged (for pierce)
        self._last_update = time.time()
        # Velocity replaces the old "direction + speed" pair so we can apply
        # gravity and drag to it independently each frame.
        self._velocity = self._initial_velocity(direction)
        self.image = pygame.Surface((4, 4), pygame.SRCALPHA)
        pygame.draw.circle(self.image, (255, 255, 255), (2, 2), 2)
        self.rect = self.image.get_rect(center=(int(self.pos[0]), int(self.pos[1])))

    # --- direction / movement -------------------------------------------------

    def _initial_velocity(self, direction):
        """Velocity vector at spawn: toward target plus an upward launch kick."""
        if direction is not None:
            dx, dy = self._normalise(direction)
        elif self.target is not None and self.target.alive():
            dx, dy = self._direction_to(self.target.rect.center)
        else:
            dx, dy = (1.0, 0.0)
        return [dx * self.speed, dy * self.speed - self.launch_elevation]

    def _direction_to(self, point):
        dx = point[0] - self.pos[0]
        dy = point[1] - self.pos[1]
        return self._normalise((dx, dy))

    @staticmethod
    def _normalise(v):
        length = (v[0] ** 2 + v[1] ** 2) ** 0.5
        if length == 0:
            return (1.0, 0.0)
        return (v[0] / length, v[1] / length)

    @property
    def _direction(self):
        """Current unit direction (used by subclasses for rotation)."""
        return self._normalise(self._velocity)

    # --- damage ---------------------------------------------------------------

    def damage_for(self, enemy) -> int:
        """Final integer damage this bullet deals to ``enemy`` (modifier applied)."""
        mult = self.enemy_modifiers.get(type(enemy), 1.0)
        return int(self.damage * mult)

    def apply_damage(self, enemy) -> None:
        if hasattr(enemy, "take_damage"):
            enemy.take_damage(self.damage_for(enemy))

    # --- main loop ------------------------------------------------------------

    def update(self, *_args, **_kwargs) -> None:
        now = time.time()
        dt = now - self._last_update
        self._last_update = now

        # Drag: scale velocity down by a fraction proportional to dt.
        # (1 - drag * dt) is a simple linear approximation; clamp at 0 to be safe.
        decay = max(0.0, 1.0 - self.drag * dt)
        self._velocity[0] *= decay
        self._velocity[1] *= decay
        # Gravity: pulls velocity downward (positive y in screen coords).
        self._velocity[1] += self.gravity * dt

        self.pos[0] += self._velocity[0] * dt
        self.pos[1] += self._velocity[1] * dt
        self._render()
        self.rect = self.image.get_rect(center=(int(self.pos[0]), int(self.pos[1])))

        if self._out_of_bounds():
            self.kill()
            return

        self._check_hits()

    def _out_of_bounds(self) -> bool:
        screen = self.parent.screen
        x, y = self.pos
        return (
            x < -50
            or y < -50
            or x > screen.get_width() + 50
            or y > screen.get_height() + 50
        )

    def _check_hits(self) -> None:
        for enemy in list(self.parent.all_enemies):
            if id(enemy) in self._hit:
                continue
            if not enemy.rect.collidepoint(int(self.pos[0]), int(self.pos[1])):
                continue
            self._hit.add(id(enemy))
            self.apply_damage(enemy)
            if self.impact_radius > 0:
                self._apply_aoe(enemy)
            self._hits_left -= 1
            if self._hits_left <= 0:
                self.kill()
                return

    def _apply_aoe(self, primary) -> None:
        cx, cy = primary.rect.center
        r2 = self.impact_radius * self.impact_radius
        for enemy in list(self.parent.all_enemies):
            if enemy is primary or id(enemy) in self._hit:
                continue
            ex, ey = enemy.rect.center
            if (ex - cx) ** 2 + (ey - cy) ** 2 <= r2:
                self._hit.add(id(enemy))
                self.apply_damage(enemy)

    # --- visuals (subclasses override) ---------------------------------------

    def _render(self) -> None:
        """Update ``self.image``. Base draws nothing fancy; Arrow rotates its sprite."""


class Arrow(Bullet):
    """Wooden arrow with a grey tip. Rotates to face its flight direction."""

    _layer = 25
    speed = 650.0
    damage = 15
    enemy_modifiers = {}  # populated below once Viking/Golem are defined

    def _render(self) -> None:
        # pygame.transform.rotate uses degrees, CCW positive. Our sprite points
        # to +x at angle 0, so the rotation angle is -atan2(dy, dx) in degrees.
        import math

        angle = -math.degrees(math.atan2(self._direction[1], self._direction[0]))
        self.image = pygame.transform.rotate(_arrow_surface(), angle)


# Per-enemy damage multipliers for arrows. Defined after enemy classes exist.
Arrow.enemy_modifiers = {Viking: 1.3, Golem: 0.8}


class Tower(General):
    PRICE = 50
    UPGRADE_PRICES = [50, 100]
    TOWERS = {
        "brown": [(2, 0, 18), (2, 41, 0, 43), (2, 41, 0, 41, 24)],
        "grey": [(37, 2, 2, 36)],
        "red": [(52, 40, 40, 40, 24)],
    }
    # Effective range in pixels by rank (index = self.rank).
    RANGE_BY_RANK = (140, 190, 240)
    DAMAGE_BY_RANK = (10, 20, 35)
    COOLDOWN_BY_RANK = (0.8, 0.6, 0.4)  # seconds between shots
    ARCHER_HEIGHT = 160  # px above tower base where arrows spawn
    _layer = 20  # towers above enemies

    def __init__(
        self,
        *args,
        source="assets/Towers (brown)",
        pos=None,
        color="brown",
        rank=0,
        **kwargs,
    ):
        kwargs = kwargs | {"source": source}
        super().__init__(*args, **kwargs)
        self.color = color
        self.rank = rank
        self.pos = pos
        self._last_fire_time = 0.0

    @property
    def range(self) -> int:
        """Effective range in pixels for the current rank."""
        idx = min(self.rank, len(self.RANGE_BY_RANK) - 1)
        return self.RANGE_BY_RANK[idx]

    def upgrade(self):
        if self.rank >= len(self.UPGRADE_PRICES):
            self.parent.stats.log.append(
                f"tower at {self.pos} is already max rank ({self.rank})"
            )
            return
        if self.parent.money < self.UPGRADE_PRICES[min(self.rank, 1)]:
            self.parent.stats.log.append(
                f"not enough money to upgrade tower at {self.pos}"
            )
            return
        self.parent.money -= self.UPGRADE_PRICES[self.rank]
        self.rank += 1
        self.__dict__.pop("_image_cache", None)
        self.update()

    def stack_images(self, ns):
        imgs = []
        for n in ns:
            img = self.get_image_n(n)

            imgs.append(img)
            max_width = max([img.get_width() for img in imgs])
        self.image = pygame.Surface(
            (max_width, sum([img.get_height() for img in imgs])), pygame.SRCALPHA
        )
        y = self.image.get_height() - imgs[0].get_height()
        for i, img in enumerate(imgs):
            self.image.blit(img, (0 + (max_width - img.get_width()) / 2, y))
            y -= img.get_height() - 43

        self._rect = self.image.get_rect()
        self.rect.x = self.pos[0] - self.rect.width / 2
        self.rect.y = self.pos[1] - self.rect.height + imgs[0].get_height() / 2

    def update(self):
        tower = self.TOWERS[self.color][self.rank]
        self.stack_images(tower)
        self._maybe_fire()

    def _maybe_fire(self) -> None:
        """Find closest enemy in range and spawn an Arrow if cooldown elapsed."""
        if self.parent is None or self.pos is None:
            return
        idx = min(self.rank, len(self.COOLDOWN_BY_RANK) - 1)
        cooldown = self.COOLDOWN_BY_RANK[idx]
        now = time.time()
        if now - self._last_fire_time < cooldown:
            return
        target = closest_enemy(self.pos, self.parent.all_enemies, self.range)
        if target is None:
            return
        # Spawn from where the archer stands. The tower's `pos` is at the
        # tower's base (ground anchor); the archer sits ~160 px above the base
        # on all ranks. Keeping this fixed (not tied to `rect.top`) means
        # arrows still appear on-screen even when a tall rank-2 sprite extends
        # above the play area.
        spawn = (self.pos[0], self.pos[1] - self.ARCHER_HEIGHT)
        arrow = Arrow(pos=spawn, target=target, parent=self.parent)
        arrow.damage = self.DAMAGE_BY_RANK[idx]
        self.parent.all_sprites.add(arrow)
        self.parent.all_bullets.add(arrow)
        self._last_fire_time = now


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
        ready = (time.time() - self.start_time) * 1000 > self.delay
        # print(ready)
        return ready

    def __call__(self):
        if self.is_ready:
            rv = self.callable(*self.args, **self.kwargs)
            self.parent.all_enemies.add(rv)
            self.parent.all_sprites.add(rv)
            # Tell the game one pending spawn has been delivered so it can
            # decide when the wave is fully out and the next one may start.
            on_spawned = getattr(self.parent, "_on_schedule_spawned", None)
            if on_spawned is not None:
                on_spawned()
        else:
            pygame.event.post(self.event)


class Game(General):
    def __init__(
        self, money=200, width=1800, height=600, level=0, fps=180, *args, **kwargs
    ):
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
        self.setup()

    # Wave system constants. Tuneable in one place.
    WAVE_COUNT = 4
    WAVE_INTER_DELAY_MS = 4000  # pause between waves once the field is clear
    WAVE_FIRST_DELAY_MS = 1500  # short grace period before wave 1

    def create_wave(self, n_enemies=22, offset=0):
        """Schedule a wave's enemies. Returns the number of pending spawns so
        the caller can track when the wave has fully emerged."""
        enemy_class = Viking if self.wave_number % 2 == 1 else Golem
        for i in range(n_enemies):
            s = Schedule(
                enemy_class, delay=i * 1200 + offset, left=bool(i % 2), parent=self
            )
            e = pygame.event.Event(42000, func=s)
            pygame.event.post(e)
        self._wave_pending_spawns += n_enemies
        return n_enemies

    def _on_schedule_spawned(self):
        """Schedule callback: one queued enemy has actually spawned."""
        self._wave_pending_spawns = max(0, self._wave_pending_spawns - 1)

    def _start_next_wave(self):
        """Spawn the next wave if there is one. Idempotent if all waves done."""
        if self.wave_number >= self.WAVE_COUNT:
            return
        self.wave_number += 1
        self.create_wave()
        self._wave_clear_time = None
        self.stats.log.append(f"wave {self.wave_number}/{self.WAVE_COUNT} incoming")

    def _update_waves(self):
        """Per-frame: advance to the next wave once the field is clear and
        the grace delay has elapsed."""
        if self.wave_number >= self.WAVE_COUNT:
            return
        field_clear = self._wave_pending_spawns == 0 and len(self.all_enemies) == 0
        if not field_clear:
            self._wave_clear_time = None
            return
        # Field just cleared this frame: stamp the time.
        if self._wave_clear_time is None:
            self._wave_clear_time = time.time()
            return
        if (time.time() - self._wave_clear_time) * 1000 >= self.WAVE_INTER_DELAY_MS:
            self._start_next_wave()

    def setup(self):
        # LayeredUpdates respects each sprite's _layer attr, giving us deterministic
        # z-order: enemies (10) → towers (20) → bullets (25) → effects (30) → UI (40).
        self.all_enemies = pygame.sprite.Group()
        self.all_bullets = pygame.sprite.Group()
        self.all_sprites = pygame.sprite.LayeredUpdates()

        self.character = Character(source="assets/effects/fire", width=40, height=40)
        self.stats = GameStats(parent=self)
        # Wave state: counts incoming spawns + alive enemies to know when the
        # field is clear and we can advance to the next wave.
        self.wave_number = 0
        self._wave_pending_spawns = 0
        self._wave_clear_time: float | None = None
        # Kick off wave 1 after a short grace period.
        self.create_wave(offset=self.WAVE_FIRST_DELAY_MS)
        self.wave_number = 1
        self.all_sprites.add(self.character)
        self.all_sprites.add(self.stats)
        # Touch the cached background once so the path dots are baked in before the first frame.
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
        enemies = self.all_enemies.sprites()
        if enemies:
            enemies[0].put_on_fire()
        self.stats.log.append(f"tower spawned at {pos}")

    def mouse_hover(self, event):
        self._hovered_tower = None
        for tower in self.all_sprites:
            if isinstance(tower, Tower) and tower.rect.collidepoint(event.pos):
                self._hovered_tower = tower
                break

    def _draw_range_overlay(self) -> None:
        """Draw the hover range ring on top of all sprites. Called every frame.

        The ring is a narrow whitish-blue gradient: bright/white at the core,
        fading out to a soft blue at the inner and outer edges.
        """
        tower = getattr(self, "_hovered_tower", None)
        if tower is None or not tower.alive():
            return

        r = tower.range
        # 5 concentric strokes, offsets in pixels from the nominal radius.
        # Each entry: (offset, (r, g, b, a)).
        strokes = [
            (-2, (160, 200, 255, 60)),
            (-1, (210, 230, 255, 140)),
            (0, (255, 255, 255, 230)),
            (1, (210, 230, 255, 140)),
            (2, (160, 200, 255, 60)),
        ]
        size = 2 * (r + 3)
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        center = (size // 2, size // 2)
        for offset, color in strokes:
            pygame.draw.circle(surf, color, center, r + offset, width=1)
        self.screen.blit(surf, surf.get_rect(center=tower.pos))

    def _draw_health_bars(self) -> None:
        """Tiny HP bar above each enemy. Drawn each frame in a post-pass.

        Lives outside the sprite ``image`` so we don't re-rasterize the enemy
        sprite on every tick — same approach as the range overlay.
        """
        bar_w, bar_h = 30, 4
        for enemy in self.all_enemies:
            if enemy.max_hp <= 0:
                continue
            ratio = max(0.0, min(1.0, enemy.hp / enemy.max_hp))
            x = enemy.rect.centerx - bar_w // 2
            y = enemy.rect.top - bar_h - 2
            # Background (dark) + foreground (red→green by ratio).
            pygame.draw.rect(self.screen, (40, 40, 40), (x, y, bar_w, bar_h))
            fg_w = int(bar_w * ratio)
            color = (int(255 * (1 - ratio)), int(200 * ratio), 40)
            if fg_w > 0:
                pygame.draw.rect(self.screen, color, (x, y, fg_w, bar_h))
            pygame.draw.rect(self.screen, (0, 0, 0), (x, y, bar_w, bar_h), width=1)

    def update(self, *args: Any, **kwargs: Any) -> None:
        super().update(*args, **kwargs)
        self.all_sprites.update()
        self._update_waves()

    @cached_property
    def background(self) -> pygame.Surface:
        """Level background with path waypoints baked in. Computed once."""
        bgd = self.get_image_n(self.level).copy()
        for point in get_path():
            pygame.draw.circle(bgd, (255, 0, 0), point, 5)
        return bgd

    def cleanup(self):
        self.all_sprites.empty()
        # Invalidate cached background so a new level rebuilds it.
        self.__dict__.pop("background", None)
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
                    if event.type == pygame.QUIT:
                        self.pause = False
                        run = False
                        break
                    if event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_ESCAPE:
                            self.pause = False
                            run = False
                            break
                        if event.key == pygame.K_p:
                            # unpause
                            self.pause = not self.pause
                            time_offset = time.time() - time_paused
                            self.time0 += time_offset
                self.clock.tick(self.FPS)
            if not run:
                break

            self.time = time.time() - self.time0
            for event in pygame.event.get():  # Retrieve all pending events
                if event.type == pygame.QUIT:
                    run = False
                    continue
                if event.type == 42000 and hasattr(event, "func"):
                    event.func()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
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
                    if event.key == pygame.K_r and (
                        pygame.key.get_mods() & pygame.KMOD_CTRL
                    ):
                        self.cleanup()
                        # game = Game()
                # mouse click
                if event.type == pygame.MOUSEBUTTONDOWN:
                    self.mouse_click(event)
                if event.type == pygame.MOUSEMOTION:
                    self.mouse_hover(event)

            self.update()
            self.clock.tick(self.FPS)

            # Single, obvious render pipeline: background → sprites (z-ordered by
            # _layer) → range overlay → flip. No dirty-rect bookkeeping.
            self.screen.blit(self.background, (0, 0))
            self.all_sprites.draw(self.screen)
            self._draw_range_overlay()
            self._draw_health_bars()
            pygame.display.flip()

        pygame.quit()


if __name__ == "__main__":
    pygame.init()
    pygame.font.init()
    game = Game(source="assets/level", level=0)

    game.run()

    # import cProfile as profile
    # with profile.Profile() as pr:
    #     game.run()
    #     pr.dump_stats('main.prof')
    #     # gprof2dot -f pstats main.pstats | dot -Tsvg -o main.svg
