"""Tests for pure helpers on General that don't need a display."""
from __future__ import annotations

import math
import os

import pytest

# Ensure headless before pygame import (conftest also does this; belt + braces).
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402


@pytest.fixture(scope="module", autouse=True)
def _pygame_init():
    pygame.init()
    pygame.font.init()
    yield
    pygame.quit()


class _StubGeneral:
    """
    Minimal stand-in exposing just the attributes General.distance and
    General.fps need. We test the algorithms on the stub to avoid loading
    sprite assets in unit tests.
    """

    def __init__(self, center, dt_samples=None, current_time=0.0):
        from collections import deque

        rect = pygame.Rect(0, 0, 0, 0)
        rect.center = center
        self.rect = rect
        self.Dt = deque(dt_samples or [], maxlen=60)
        self.time = current_time


def test_distance_zero():
    from main import General

    g = _StubGeneral(center=(100, 100))
    # Bind unbound method to our stub.
    assert General.distance(g, (100, 100)) == 0


def test_distance_pythagorean():
    from main import General

    g = _StubGeneral(center=(0, 0))
    assert math.isclose(General.distance(g, (3, 4)), 5.0)


def test_fps_returns_none_when_no_samples():
    from main import General

    g = _StubGeneral(center=(0, 0), dt_samples=[], current_time=0.0)
    assert General.fps.fget(g) is None


def test_fps_handles_zero_denominator():
    """If only one sample exists, denominator is 0 → must not divide by zero."""
    from main import General

    g = _StubGeneral(center=(0, 0), dt_samples=[1.0], current_time=1.0)
    assert General.fps.fget(g) == 1


def test_fps_normal_case():
    from main import General

    # 60 samples spanning 1 second → 60 fps.
    samples = [i / 60 for i in range(60)]
    g = _StubGeneral(center=(0, 0), dt_samples=samples, current_time=1.0)
    fps = General.fps.fget(g)
    assert fps is not None
    assert fps == 60
