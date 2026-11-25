"""Build ai-workforce-intel_colab.zip: code, needed data and finished outputs for the Colab notebooks.

Usage:  python src/make_colab_bundle.py [--out ai-workforce-intel_colab.zip] [--no-verify]

The processed files are found by reading the driver tables (config.DRIVERS, the Phase 1
handoff, the cross-correlation file and the Phase 2 extra series), not guessed. Only .parquet
copies go in; data/raw and the large request-level files are never included. After building,
the zip is unpacked into a fresh temporary folder and `run_phase1.py --fast` is run there.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import config  # noqa: E402
import config_phase2 as P2  # noqa: E402
import config_phase3 as P3  # noqa: E402

ROOT = config.ROOT
TOP = "ai-workforce-intel"
LIMIT_MB = 60
NEVER = {"burstgpt_requests_clean", "wildchat_conversations"}  # large request-level tables
SKIP_PARTS = {"__pycache__", ".pytest_cache"}


def needed_data_files() -> list[str]:
    """Processed file stems used by Phase 1 and Phase 2 drivers (that exist on disk)."""
    stems = {c["file"] for c in config.DRIVERS} | {config.CCF_FILE}
    stems |= {e["file"] for e in P2.EXTRA_SERIES.values()}
    stems.add("burstgpt_daily_wide")  # the hourly loader borrows the anomaly flags from it
    stems |= set(P3.DATA_FILES)  # Phase 3: token shares and scenario inputs
    handoff = ROOT / "outputs" / "phase1" / "handoff.json"
    if handoff.exists():
        stems |= {d["file"] for d in json.loads(handoff.read_text(encoding="utf-8"))["drivers"]}
    return sorted(s for s in stems - NEVER if (config.DATA_DIR / f"{s}.parquet").exists())


def _tree(folder: Path, pattern: str = "*") -> list[Path]:
    return [p for p in sorted(folder.rglob(pattern))
            if p.is_file() and not SKIP_PARTS & set(p.parts) and p.suffix != ".pyc"]


def collect() -> dict[str, list[Path]]:
    """Files per bundle folder (keys are display names)."""
    groups = {
        "requirements.txt": [ROOT / "requirements.txt"],
        "src": [p for p in _tree(ROOT / "src", "*.py")],
        "tests": _tree(ROOT / "tests", "*.py"),
        "data/processed": [config.DATA_DIR / f"{s}.parquet" for s in needed_data_files()],
        "reports": _tree(ROOT / "reports" / "figures", "*.png") + [p for p in [P3.QUALITY_LOG] if p.exists()],
        "outputs/phase1": _tree(ROOT / "outputs" / "phase1"),
        "outputs/phase2": _tree(ROOT / "outputs" / "phase2"),
        "outputs/phase3": _tree(ROOT / "outputs" / "phase3"),
        "outputs/phase4": _tree(ROOT / "outputs" / "phase4"),
        "outputs/phase5": _tree(ROOT / "outputs" / "phase5"),
        "dashboard extras": [p for p in [ROOT / "src" / "dashboard" / "ui" / "styles.css", ROOT / ".streamlit" / "config.toml",
                                         ROOT / "requirements-dashboard.txt", *_tree(ROOT / "src" / "dashboard" / "ui" / "assets")]
                             if p.exists()],
        "config": _tree(ROOT / "config", "*.json"),
    }
    return {k: v for k, v in groups.items() if v}


def write_zip(groups: dict[str, list[Path]], out: Path) -> None:
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for files in groups.values():
            for f in files:
                zf.write(f, f"{TOP}/{f.relative_to(ROOT).as_posix()}")


def report_sizes(groups: dict[str, list[Path]], out: Path) -> float:
    for name, files in groups.items():
        print(f"  {name:20s} {len(files):4d} files {sum(f.stat().st_size for f in files) / 1e6:7.2f} MB")
    total = out.stat().st_size / 1e6
    print(f"  zip total (compressed) {total:.2f} MB (limit {LIMIT_MB} MB)")
    return total


def shrink(groups: dict[str, list[Path]], out: Path) -> None:
    """Drop the largest data files (least necessary first) until the zip fits the limit."""
    data = sorted(groups["data/processed"], key=lambda p: p.stat().st_size, reverse=True)
    while out.stat().st_size / 1e6 > LIMIT_MB and data:
        dropped = data.pop(0)
        groups["data/processed"] = data
        print(f"  over the limit: dropped {dropped.name}")
        write_zip(groups, out)


def verify(out: Path) -> bool:
    """Unzip into a fresh folder (no data/raw) and run Phase 1 --fast there."""
    with tempfile.TemporaryDirectory() as tmp:
        with zipfile.ZipFile(out) as zf:
            bad = [n for n in zf.namelist() if n.startswith("/") or ":" in n or "\\" in n]
            if bad:
                print("  absolute or Windows paths in zip:", bad[:3])
                return False
            zf.extractall(tmp)
        proj = Path(tmp) / TOP
        assert not (proj / "data" / "raw").exists()
        res = subprocess.run([sys.executable, "src/run_phase1.py", "--fast", "--out-dir",
                              str(Path(tmp) / "verify_phase1")], cwd=proj, capture_output=True, text=True)
        tail = (res.stdout + res.stderr).strip().splitlines()[-1:]
        print(f"  verify: run_phase1.py --fast in a fresh unzip -> exit {res.returncode}; {tail}")
        res3 = subprocess.run([sys.executable, "src/run_phase3.py", "--fast", "--out-dir",
                               str(Path(tmp) / "verify_phase3")], cwd=proj, capture_output=True, text=True)
        tail3 = (res3.stdout + res3.stderr).strip().splitlines()[-1:]
        print(f"  verify: run_phase3.py --fast in a fresh unzip -> exit {res3.returncode}; {tail3}")
        return res.returncode == 0 and res3.returncode == 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--out", type=Path, default=ROOT / "ai-workforce-intel_colab.zip")
    p.add_argument("--no-verify", action="store_true")
    args = p.parse_args(argv)
    groups = collect()
    print("data files used by the drivers:", ", ".join(f.name for f in groups["data/processed"]))
    write_zip(groups, args.out)
    shrink(groups, args.out)
    report_sizes(groups, args.out)
    ok = True if args.no_verify else verify(args.out)
    print(f"bundle written: {args.out.name}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
