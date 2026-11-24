# Phase 4 data contract

## Phase 3 forecast files

| driver | unit | grain | horizon | paths | model | file |
|---|---|---|---|---|---|---|
| burst_tokens_total_daily | tokens | daily | 14 | 200 | ensemble | forecasts/burst_tokens_total_daily.parquet |
| burst_tokens_api_daily | tokens | daily | 14 | 200 | ensemble | forecasts/burst_tokens_api_daily.parquet |
| burst_tokens_chat_daily | tokens | daily | 14 | 200 | ensemble | forecasts/burst_tokens_chat_daily.parquet |
| burst_requests_hourly | requests | hourly | 168 | 200 | ensemble | forecasts/burst_requests_hourly.parquet |
| wildchat_conversations_daily | conversations | daily | 14 | 200 | seasonal_ma3 | forecasts/wildchat_conversations_daily.parquet |
| eci_wages_quarterly | index_points | quarterly | 8 | 200 | arima | forecasts/eci_wages_quarterly.parquet |
| ppi_hosting_monthly | index_points | monthly | 12 | 200 | ensemble | forecasts/ppi_hosting_monthly.parquet |

## Engine roles (src/config.py ENGINE_DRIVERS)

| role | driver | file | required | status |
|---|---|---|---|---|
| token_demand | burst_tokens_total_daily | forecasts/burstgpt_monthly_run_rate.csv | yes | found |
| wages | eci_wages_quarterly | forecasts/eci_wages_quarterly.parquet | yes | found |
| hosting | ppi_hosting_monthly | forecasts/ppi_hosting_monthly.parquet | yes | found |
| token_price | epoch_cheapest_price_monthly | forecasts/epoch_cheapest_price_monthly.parquet | no (optional) | MISSING |

## scenario_tables.csv (every row)

- **downside** / `task_time_change_with_ai` = 18.8 pct_change_in_task_time (status from_quality_log); source: METR RCT (paper estimate, recorded in reports/data_quality.md); derivation: Read from the quality log line 'paper_estimate: +18.8% time with AI (95% CI ~+1% to +39%), per repo README': AI-allowed tasks took this much LONGER, so no time is saved.
- **downside** / `task_time_change_with_ai_naive` = 31.508 pct_change_in_task_time (status measured); source: METR RCT (metr_effect_summary); derivation: Mean minutes per task with AI allowed (119.54, 136 tasks) divided by without AI (90.90, 110 tasks), minus 1; a ratio of means, not the paper's regression.
- **expected** / `time_saved_share_of_work_hours` = 2.084485382 pct_of_work_hours (status measured); source: FRED GenAI tracker RPSGENAITSALL (genai_tracker); derivation: Latest quarter (2026-07-01) of time_saved_pct_hours, GenAI time savings as % of work hours, all employed adults.
- **optimistic** / `time_saved_share_of_work_hours` = 3.9078089975 pct_of_work_hours (status measured); source: FRED GenAI tracker panel RPSGENAITSIND5 (genai_timesaved_panel); derivation: Highest value in the 8-series occupation/industry panel: 'GenAI time savings: wholesale trade' (industry) in 2024-10-01.

## inputs_for_phase4.json

```json
{
  "phase": 3,
  "note": "Measured inputs for Phase 4; no cost calculations here.",
  "window": "BurstGPT days 0-86",
  "input_token_share": 0.8608563439193945,
  "output_token_share": 0.13914365608060553,
  "input_token_note": "request_tokens / total_tokens summed over the window (burstgpt_daily)",
  "api_token_share": 0.8956953691582766,
  "chat_token_share": 0.10430463084172334,
  "forecast_files": [
    {
      "driver": "burst_tokens_total_daily",
      "file": "forecasts/burst_tokens_total_daily.parquet",
      "unit": "tokens",
      "grain": "day",
      "horizon": 14
    },
    {
      "driver": "burst_tokens_api_daily",
      "file": "forecasts/burst_tokens_api_daily.parquet",
      "unit": "tokens",
      "grain": "day",
      "horizon": 14
    },
    {
      "driver": "burst_tokens_chat_daily",
      "file": "forecasts/burst_tokens_chat_daily.parquet",
      "unit": "tokens",
      "grain": "day",
      "horizon": 14
    },
    {
      "driver": "burst_requests_hourly",
      "file": "forecasts/burst_requests_hourly.parquet",
      "unit": "requests",
      "grain": "hour",
      "horizon": 168
    },
    {
      "driver": "wildchat_conversations_daily",
      "file": "forecasts/wildchat_conversations_daily.parquet",
      "unit": "conversations",
      "grain": "day",
      "horizon": 14
    },
    {
      "driver": "eci_wages_quarterly",
      "file": "forecasts/eci_wages_quarterly.parquet",
      "unit": "index_points",
      "grain": "quarter",
      "horizon": 8
    },
    {
      "driver": "ppi_hosting_monthly",
      "file": "forecasts/ppi_hosting_monthly.parquet",
      "unit": "index_points",
      "grain": "month",
      "horizon": 12
    }
  ],
  "scenario_file": "forecasts/scenario_tables.csv",
  "uncertainty_multiplier": 1.0,
  "uncertainty_sensitivity": {
    "multipliers": [
      1.0,
      1.5,
      2.0
    ],
    "how": "path_m = point + m x (path - point), then clip at 0; sample_id -1 is the point. The saved forecast files are NOT scaled (m = 1.0).",
    "why": "the holdout check shows bands that are still too narrow for several drivers"
  }
}
```
