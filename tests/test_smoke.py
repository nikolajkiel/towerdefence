"""Smoke tests — verify the module imports and core helpers behave."""
from __future__ import annotations

import pytest


def test_module_imports():
    """main.py should import cleanly under the headless SDL driver."""
    import main  # noqa: F401


def test_get_path_yields_expected_count():
    """get_path() is the level-0 waypoint generator; must yield all 20 points."""
    import main

    points = list(main.get_path())

    assert len(points) == 20
    assert all(isinstance(p, tuple) and len(p) == 2 for p in points)


def test_get_path_first_and_last_waypoints():
    """Pin the entry and exit so balance/level changes are visible in tests."""
    import main

    points = list(main.get_path())

    assert points[0] == (0, 275)  # entry on the left edge
    assert points[-1] == (1840, 300)  # exit on the right edge


def test_get_path_is_a_fresh_generator_each_call():
    """Each call must return a fresh generator — Character relies on this."""
    import main

    g1 = main.get_path()
    g2 = main.get_path()

    assert next(g1) == next(g2)  # both start at the beginning
    next(g1)
    # g2 must not have advanced
    assert next(g2) == (165, 324)
