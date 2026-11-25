"""Make `src/` importable (config, tsaf, run_phase1) for every test."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

os.environ.setdefault("AIWI_STRICT", "1")  # page errors fail the tests instead of showing the error card
os.environ.setdefault("AIWI_TOUR", "off")  # no first-visit dialog in tests
