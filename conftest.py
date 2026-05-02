"""
Pytest config for the towerdefence project.

Forces SDL into a headless 'dummy' driver so importing main.py and
constructing Game() does not require a display server. This lets us
unit-test pure logic and small wiring without launching a real window.
"""
import os
import sys
from pathlib import Path

# Headless SDL — must be set BEFORE pygame is imported anywhere.
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

# Make the project root importable so `import main` works from tests/.
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
