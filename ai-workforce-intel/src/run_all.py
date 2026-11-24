"""Run every preprocessing step that has raw data, then write the quality report.

    python src/run_all.py              # process whatever is in data/raw/
    python src/run_all.py --download   # download first, then process

A dataset whose raw files are missing is skipped with a message, so the
pipeline still runs while you wait on a large download (e.g. WildChat).
"""
from __future__ import annotations

import argparse
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402

STEPS = ["prep_burstgpt", "prep_wildchat", "prep_fred", "prep_epoch", "prep_metr"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--download", action="store_true")
    ap.add_argument("--wildchat-shards", type=int, default=None)
    a = ap.parse_args()
    if a.download:
        import download
        sys.argv = ["download.py"] + (["--wildchat-shards", str(a.wildchat_shards)] if a.wildchat_shards else [])
        download.main()

    status = {}
    for name in STEPS:
        try:
            __import__(name).run()
            status[name] = "ok"
        except FileNotFoundError as e:
            status[name] = f"skipped: {e}"
            print(f"  {name} skipped: {e}")
        except Exception as e:  # keep going, report at the end
            status[name] = f"FAILED: {e}"
            traceback.print_exc()
    common.log_quality("Pipeline status", **status)
    common.write_quality_report()
    print("\n".join(f"{k:15s} {v}" for k, v in status.items()))


if __name__ == "__main__":
    main()
