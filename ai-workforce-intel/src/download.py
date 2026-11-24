"""Download every raw dataset into data/raw/.

Usage:
    python src/download.py                    # everything that can be fetched automatically
    python src/download.py --only fred burstgpt
    python src/download.py --wildchat-shards 5   # limit WildChat download size

Already-downloaded files are skipped. Epoch AI is the only manual download
(see README); everything else is fetched here.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import RAW  # noqa: E402

HEADERS = {"User-Agent": "TSAF student project (data download)"}

BURSTGPT_FILES = {
    # In the repo itself (verified): first 2 months, includes failures.
    "BurstGPT_1.csv": "https://raw.githubusercontent.com/HPMLL/BurstGPT/main/data/BurstGPT_1.csv",
    # Release assets (months 3-4). If this 404s, download from
    # https://github.com/HPMLL/BurstGPT/releases manually into data/raw/burstgpt/.
    "BurstGPT_2.csv": "https://github.com/HPMLL/BurstGPT/releases/download/v1.1/BurstGPT_2.csv",
}

METR_FILES = {
    "data_complete.csv": "https://raw.githubusercontent.com/METR/Measuring-Early-2025-AI-on-Exp-OSS-Devs/main/data_complete.csv",
}

# FRED series, downloaded as CSV without an API key.
FRED_SERIES = {
    # Labour cost (quarterly)
    "CIS202540A000000I": "ECI wages, professional & business services, SA",
    "CIU202540A000000I": "ECI wages, professional & business services, NSA",
    # Cloud / hosting prices (monthly)
    "PCU518210518210": "PPI data processing, hosting & related services",
    "PCU5182105182105": "PPI hosting, ASP & IT infrastructure provisioning",
    # Generative AI Adoption Tracker (quarterly) - national
    "RPSGENAITSALL": "GenAI time savings, % of work hours, all employed adults",
    "RPSGENAIASSISTWRKHRSALL": "GenAI work hours assisted, %, all employed adults",
    # Tracker - occupation / industry time-savings panels (pooled outcome model)
    "RPSGENAITSOCC2": "GenAI time savings: business & financial operations occ.",
    "RPSGENAITSOCC4": "GenAI time savings: architecture & engineering occ.",
    "RPSGENAITSOCC6": "GenAI time savings: community & social service occ.",
    "RPSGENAITSOCC11": "GenAI time savings: healthcare support occ.",
    "RPSGENAITSIND5": "GenAI time savings: wholesale trade",
    "RPSGENAITSIND7": "GenAI time savings: transportation & warehousing",
    "RPSGENAITSIND14": "GenAI time savings: admin & support services",
    "RPSGENAITSIND19": "GenAI time savings: other services",
}


def fetch(url: str, dest: Path, chunk: int = 1 << 20) -> bool:
    if dest.exists() and dest.stat().st_size > 0:
        print(f"  skip (exists) {dest.name}")
        return True
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        with requests.get(url, headers=HEADERS, stream=True, timeout=120) as r:
            r.raise_for_status()
            tmp = dest.with_suffix(dest.suffix + ".part")
            with open(tmp, "wb") as f:
                for block in r.iter_content(chunk):
                    f.write(block)
            tmp.rename(dest)
        print(f"  ok   {dest.name} ({dest.stat().st_size / 1e6:.1f} MB)")
        return True
    except Exception as e:  # report and continue with the rest
        print(f"  FAIL {dest.name}: {e}")
        return False


def get_burstgpt():
    print("BurstGPT")
    for name, url in BURSTGPT_FILES.items():
        fetch(url, RAW / "burstgpt" / name)


def get_metr():
    print("METR RCT")
    for name, url in METR_FILES.items():
        fetch(url, RAW / "metr" / name)


def get_fred():
    print("FRED / BLS series")
    for sid in FRED_SERIES:
        fetch(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}", RAW / "fred" / f"{sid}.csv")


def get_wildchat(repo: str, shards: int | None):
    """Download WildChat Parquet shards from Hugging Face.

    The full 4.8M set is ~12 GB. `shards` limits how many files are fetched;
    shards are roughly chronological, so take enough to cover the period you
    need, or all of them for the final run.
    """
    print(f"WildChat ({repo})")
    from huggingface_hub import HfApi, hf_hub_download

    files = sorted(f for f in HfApi().list_repo_files(repo, repo_type="dataset")
                   if f.startswith("data/") and f.endswith(".parquet"))
    if shards:
        files = files[:shards]
    print(f"  {len(files)} shard(s) to fetch")
    out = RAW / "wildchat"
    for f in files:
        if (out / f).exists():
            print(f"  skip (exists) {f}")
            continue
        hf_hub_download(repo, f, repo_type="dataset", local_dir=out)
        print(f"  ok   {f}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*", choices=["burstgpt", "metr", "fred", "wildchat"])
    ap.add_argument("--wildchat-repo", default="allenai/WildChat-4.8M",
                    help="or allenai/WildChat-1M for the smaller 2023-24 version")
    ap.add_argument("--wildchat-shards", type=int, default=None,
                    help="limit number of Parquet shards (default: all)")
    a = ap.parse_args()
    todo = a.only or ["burstgpt", "metr", "fred", "wildchat"]
    if "burstgpt" in todo:
        get_burstgpt()
    if "metr" in todo:
        get_metr()
    if "fred" in todo:
        get_fred()
    if "wildchat" in todo:
        get_wildchat(a.wildchat_repo, a.wildchat_shards)
    print("\nManual step: Epoch AI price data -> see README section 'Epoch AI'.")


if __name__ == "__main__":
    main()
