"""Make `src/` importable (config, tsaf, run_phase1) for every test."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
