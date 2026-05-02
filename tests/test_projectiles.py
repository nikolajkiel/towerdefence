"""Unit tests for the projectile + HP system.

These tests deliberately avoid constructing a real Game — they exercise the
pure helpers (closest_enemy, Bullet.damage_for, Character.take_damage) on
small stand-ins. That keeps them fast and asset-free, per
``pytest-conventions.md``.
"""
from __future__ import annotations

import os

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402


@pytest.fixture(scope="module", autouse=True)
def _pygame_init():
    pygame.init()
    pygame.font.init()
    pygame.display.set_mode((100, 100))
    yield
    pygame.quit()


class _StubEnemy:
    """Stand-in for an enemy sprite — exposes only what helpers need."""

    def __init__(self, center, hp_type=None):
        self.rect = pygame.Rect(0, 0, 20, 20)
        self.rect.center = center
        # Allow tests to stamp on a "type" for modifier lookups.
        if hp_type is not None:
            self.__class__ = hp_type


def test_closest_enemy_picks_nearest_in_range():
    from main import closest_enemy

    near = _StubEnemy(center=(110, 100))
    far = _StubEnemy(center=(300, 100))

    chosen = closest_enemy((100, 100), [far, near], max_range=200)

    assert chosen is near


def test_closest_enemy_returns_none_when_all_out_of_range():
    from main import closest_enemy

    e = _StubEnemy(center=(500, 500))

    chosen = closest_enemy((0, 0), [e], max_range=100)

    assert chosen is None


def test_bullet_damage_for_respects_modifiers():
    from main import Bullet, Golem, Viking

    class StubBullet(Bullet):
        damage = 20
        enemy_modifiers = {Viking: 1.5, Golem: 0.5}

    # Construct without going through __init__ (no parent/screen needed for
    # this pure helper).
    b = StubBullet.__new__(StubBullet)
    b.damage = 20
    b.enemy_modifiers = StubBullet.enemy_modifiers

    viking = _StubEnemy(center=(0, 0))
    viking.__class__ = Viking
    golem = _StubEnemy(center=(0, 0))
    golem.__class__ = Golem

    assert b.damage_for(viking) == 30
    assert b.damage_for(golem) == 10


def test_bullet_damage_for_defaults_to_one_when_no_modifier():
    from main import Bullet

    b = Bullet.__new__(Bullet)
    b.damage = 7
    b.enemy_modifiers = {}

    plain = _StubEnemy(center=(0, 0))

    assert b.damage_for(plain) == 7


def test_character_take_damage_kills_at_zero_and_awards_gold():
    """Drive Character.take_damage on a hand-built instance to avoid asset I/O."""
    from main import Character

    # Fake parent with the bits take_damage touches.
    class _FakeStats:
        def __init__(self):
            from collections import deque
            self.log = deque(maxlen=10)

    class _FakeGame:
        def __init__(self):
            self.money = 0
            self.stats = _FakeStats()

    parent = _FakeGame()

    # Bypass General.__init__ (no asset loading) — we only need the take_damage path.
    c = Character.__new__(Character)
    c.parent = parent
    c.max_hp = 50
    c.hp = 50
    c.GOLD_REWARD = 7
    # kill() requires sprite group state; stub it out — we just check it was called.
    killed = []
    c.kill = lambda: killed.append(True)

    c.take_damage(20)
    assert c.hp == 30
    assert killed == []
    assert parent.money == 0

    c.take_damage(50)  # overshoot
    assert c.hp == 0
    assert killed == [True]
    assert parent.money == 7
    assert any("died" in line for line in parent.stats.log)
