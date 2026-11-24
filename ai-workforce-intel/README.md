# AI Workforce Investment Intelligence — data download and preprocessing

CS3216 Time Series Analysis and Forecasting · team project

This folder downloads the seven project datasets and turns each into clean,
modelling-ready time series. Modelling, the cost engine and the dashboard come
later and read only from `data/processed/`.

## 1. Setup (once)

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## 2. Download

```bash
python src/download.py --only burstgpt metr fred      # small, ~1–2 minutes
python src/download.py --only wildchat --wildchat-shards 5   # start small (see below)
```

| Dataset | How it is fetched | Size |
| --- | --- | --- |
| BurstGPT | GitHub raw file (month 1–2); release asset for months 3–4 | ~50 MB + ~140 MB |
| METR RCT | GitHub raw file | <100 KB |
| FRED / BLS (ECI, PPI, GenAI tracker) | `fredgraph.csv`, no API key | <1 MB |
| WildChat-4.8M | Hugging Face shards | ~12 GB in total |
| Epoch AI prices | **Manual** — see below | <1 MB |

**WildChat size.** Start with `--wildchat-shards 5` to check everything works,
then download the rest overnight. For the smaller 2023–24 version use
`--wildchat-repo allenai/WildChat-1M`. If Hugging Face asks you to log in,
run `huggingface-cli login` and accept the dataset terms on its page first.

**BurstGPT months 3–4.** If `BurstGPT_2.csv` fails to download, get it from
the repository's Releases page and save it as `data/raw/burstgpt/BurstGPT_2.csv`.
The pipeline detects and stitches it automatically.

**Epoch AI (manual).** Open Epoch AI's data hub (epoch.ai, "Data" section),
download the LLM pricing / benchmarking CSV, and save it in `data/raw/epoch/`.
The script finds the release-date and input/output price columns by name; if
it can't, it tells you which columns exist and you pass them with
`--date-col`, `--input-col`, `--output-col`.

## 3. Preprocess

```bash
python src/run_all.py
```

Datasets whose raw files are missing are skipped, so you can run this while
WildChat is still downloading. Results go to `data/processed/` (Parquet for
code, CSV for a quick look), `reports/data_quality.md` and `reports/figures/`.

## 4. What each output is for

| File | Grain | Used for |
| --- | --- | --- |
| `burstgpt_hourly_total` | hour | Request rate, peak requests/min (capacity), failures |
| `burstgpt_daily_wide` | day | Tokens and requests by model × API/chat — main SARIMA/XGBoost target |
| `burstgpt_hourly`, `burstgpt_daily` | hour/day × segment | Same, long format |
| `wildchat_daily` | day × model family | Usage trend, active and new users |
| `wildchat_weekly` | week | Enablement proxies: new users, returning share, turns, prompt length |
| `wildchat_monthly` | month | Monthly expenditure view (flag `partial_month`) |
| `eci_quarterly` | quarter | Wage-cost SARIMA (s=4; NSA column for decomposition) |
| `eci_monthly` | month | Interpolated wages — **cost engine only**, never for model fitting |
| `ppi_hosting_monthly` | month | Cloud price ARIMA |
| `epoch_prices_monthly` | month | Price-per-token frontier → log-linear trend |
| `genai_tracker`, `genai_timesaved_panel` | quarter | Business-outcome projection (time saved) |
| `metr_tasks`, `metr_effect_summary` | task | Downside case for time saved |

## 5. Preprocessing decisions (defend these in the review)

**BurstGPT**
- `Timestamp` is **seconds since the trace started**, not a date. Time is
  indexed as hour/day since start; `day_of_cycle` (0–6) gives the weekly
  position. Day-of-cycle 4–5 carry ~63% of other days' volume, so they are
  probably the weekend — reported as an inference, not assumed.
- Exact duplicate rows are **kept**: identical requests in the same second are
  real traffic (batched API calls), so deleting them would undercount demand.
- Failed requests (0 response tokens) are kept and flagged; failure rate is
  its own series.
- Quiet hours/days are filled with 0 so every series has a complete time grid.
- The last day is partial and flagged (`partial_day`).

**WildChat**
- Streams one Parquet row group at a time and stores no conversation text.
- Fields are read wherever they exist (top-level or per-turn); the report
  lists which source was used. If token counts are missing in any shard, a
  character-based estimate (`user_tokens_charest`, chars ÷ 4) is the
  consistent fallback.
- A user is a hashed IP — an imperfect ID (shared or changing IPs).
- Partial first/last weeks and months are flagged.

**FRED / BLS**
- FRED's `.` gap markers become missing values and are dropped (counts reported).
- ECI is modelled quarterly; the monthly version is linear interpolation for
  the cost engine only.
- The GenAI tracker has ~7 quarterly points: use trend models or pooled
  regression, not ARIMA.

## 6. Folder layout

```
src/            download.py, prep_*.py (one per dataset), run_all.py, common.py
data/raw/       downloaded files (git-ignored)
data/processed/ clean outputs
reports/        data_quality.md, figures/
```
