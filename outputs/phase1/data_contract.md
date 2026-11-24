# Data contract (Phase 1 pre-flight)

Source folder: `C:\Users\Isha Jain\Downloads\ai-workforce-intel\data\processed`. Each table is also saved as CSV with the same content.

## burstgpt_daily

- rows: 484; columns: 9; range `day_index`: 0 to 120

| column | dtype | nulls |
|---|---|---|
| day_index | int64 | 0 |
| model | str | 0 |
| log_type | str | 0 |
| requests | float64 | 20 |
| request_tokens | float64 | 20 |
| response_tokens | float64 | 20 |
| total_tokens | float64 | 20 |
| failures | float64 | 20 |
| segment | str | 0 |

## burstgpt_daily_wide

- rows: 121; columns: 18; range `day_index`: 0 to 120

| column | dtype | nulls |
|---|---|---|
| day_index | int64 | 0 |
| ChatGPT_api_requests | float64 | 5 |
| ChatGPT_conversation_requests | float64 | 5 |
| GPT-4_api_requests | float64 | 5 |
| GPT-4_conversation_requests | float64 | 5 |
| ChatGPT_api_total_tokens | float64 | 5 |
| ChatGPT_conversation_total_tokens | float64 | 5 |
| GPT-4_api_total_tokens | float64 | 5 |
| GPT-4_conversation_total_tokens | float64 | 5 |
| total_tokens | float64 | 5 |
| requests | float64 | 5 |
| failures | float64 | 5 |
| day_of_cycle | int64 | 0 |
| partial_day | bool | 0 |
| copied_day | bool | 0 |
| low_activity | bool | 0 |
| anomaly_low_day | bool | 0 |
| in_model_window | bool | 0 |

## burstgpt_hourly

- rows: 11,616; columns: 9; range `hour_index`: 0 to 2903

| column | dtype | nulls |
|---|---|---|
| hour_index | int64 | 0 |
| model | str | 0 |
| log_type | str | 0 |
| requests | float64 | 480 |
| request_tokens | float64 | 480 |
| response_tokens | float64 | 480 |
| total_tokens | float64 | 480 |
| failures | float64 | 480 |
| segment | str | 0 |

## burstgpt_hourly_total

- rows: 2,904; columns: 12; range `day_index`: 0 to 120

| column | dtype | nulls |
|---|---|---|
| hour_index | int64 | 0 |
| requests | float64 | 120 |
| total_tokens | float64 | 120 |
| failures | float64 | 120 |
| peak_requests_per_min | float64 | 120 |
| hour_of_day | int64 | 0 |
| day_index | int64 | 0 |
| day_of_cycle | int64 | 0 |
| failure_rate | float64 | 120 |
| low_activity | bool | 0 |
| in_model_window | bool | 0 |
| copied_day | bool | 0 |

## burstgpt_requests_clean

- rows: 4,804,926; columns: 10; range `day_index`: 0 to 120

| column | dtype | nulls |
|---|---|---|
| t_sec | float64 | 0 |
| model | category | 0 |
| request_tokens | int64 | 0 |
| response_tokens | int64 | 0 |
| total_tokens | int64 | 0 |
| log_type | category | 0 |
| failed | int8 | 0 |
| minute_index | int64 | 0 |
| hour_index | int64 | 0 |
| day_index | int64 | 0 |

## eci_monthly

- rows: 307; columns: 3; range `date`: 2001-02-01 00:00:00 to 2026-08-01 00:00:00

| column | dtype | nulls |
|---|---|---|
| date | datetime64[us] | 0 |
| eci_wages_sa | float64 | 0 |
| note | str | 0 |

## eci_quarterly

- rows: 103; columns: 4; range `date`: 2001-01-01 00:00:00 to 2026-07-01 00:00:00

| column | dtype | nulls |
|---|---|---|
| date | datetime64[us] | 0 |
| eci_wages_sa | float64 | 0 |
| eci_wages_nsa | float64 | 0 |
| quarter | int32 | 0 |

## fred_long

- rows: 836; columns: 4; range `date`: 2000-12-01 00:00:00 to 2026-10-01 00:00:00

| column | dtype | nulls |
|---|---|---|
| date | datetime64[us] | 0 |
| value | float64 | 0 |
| series_id | str | 0 |
| description | str | 0 |

## genai_timesaved_panel

- rows: 64; columns: 5; range `date`: 2024-10-01 00:00:00 to 2026-07-01 00:00:00

| column | dtype | nulls |
|---|---|---|
| date | datetime64[us] | 0 |
| series_id | str | 0 |
| description | str | 0 |
| time_saved_pct_hours | float64 | 0 |
| group_type | str | 0 |

## genai_tracker

- rows: 8; columns: 3; range `date`: 2024-10-01 00:00:00 to 2026-07-01 00:00:00

| column | dtype | nulls |
|---|---|---|
| date | datetime64[us] | 0 |
| hours_assisted_pct | float64 | 0 |
| time_saved_pct_hours | float64 | 0 |

## metr_effect_summary

- rows: 2; columns: 5; range no time column

| column | dtype | nulls |
|---|---|---|
| ai_treatment | int64 | 0 |
| tasks | int64 | 0 |
| mean_minutes | float64 | 0 |
| median_minutes | float64 | 0 |
| arm | str | 0 |

## metr_tasks

- rows: 246; columns: 12; range no time column

| column | dtype | nulls |
|---|---|---|
| dev_id | int64 | 0 |
| issue_id | int64 | 0 |
| predicted_time_no_ai | float64 | 0 |
| predicted_time_ai_allowed | float64 | 0 |
| prior_task_exposure_1_to_5 | float64 | 87 |
| external_resource_needs_1_to_3 | float64 | 87 |
| ai_treatment | int64 | 0 |
| initial_implementation_time | float64 | 0 |
| post_review_implementation_time | float64 | 16 |
| log_time | float64 | 0 |
| log_pred_no_ai | float64 | 0 |
| forecast_speedup_expected | float64 | 0 |

## ppi_hosting_monthly

- rows: 311; columns: 3; range `date`: 2000-12-01 00:00:00 to 2026-10-01 00:00:00

| column | dtype | nulls |
|---|---|---|
| date | datetime64[us] | 0 |
| ppi_hosting | float64 | 0 |
| ppi_hosting_infra | float64 | 72 |

## wildchat_conversations

- rows: 930,200; columns: 15; range `date`: 2023-04-09 00:00:00 to 2024-07-03 00:00:00

| column | dtype | nulls |
|---|---|---|
| timestamp | datetime64[us, UTC] | 0 |
| date | datetime64[us] | 0 |
| model | str | 0 |
| model_family | str | 0 |
| user_hash | str | 0 |
| country | str | 4,399 |
| language | str | 0 |
| n_turns_raw | int32 | 0 |
| user_turns | int64 | 0 |
| user_tokens | float64 | 0 |
| assistant_tokens | float64 | 0 |
| total_tokens | float64 | 0 |
| user_tokens_charest | float64 | 0 |
| first_prompt_tokens | float64 | 0 |
| is_first_conversation_day | bool | 0 |

## wildchat_daily

- rows: 904; columns: 9; range `date`: 2023-04-09 00:00:00 to 2024-07-03 00:00:00

| column | dtype | nulls |
|---|---|---|
| date | datetime64[us] | 0 |
| model_family | str | 0 |
| conversations | float64 | 0 |
| total_tokens | float64 | 0 |
| user_tokens | float64 | 0 |
| assistant_tokens | float64 | 0 |
| active_users | float64 | 0 |
| new_users | float64 | 0 |
| missing_day | bool | 0 |

## wildchat_monthly

- rows: 28; columns: 8; range `month`: 2023-04-01 00:00:00 to 2024-07-01 00:00:00

| column | dtype | nulls |
|---|---|---|
| month | datetime64[us] | 0 |
| model_family | str | 0 |
| conversations | int64 | 0 |
| total_tokens | float64 | 0 |
| active_users | int64 | 0 |
| days_observed | int64 | 0 |
| days_in_month | int32 | 0 |
| partial_month | bool | 0 |

## wildchat_weekly

- rows: 66; columns: 11; range `week`: 2023-04-03 00:00:00 to 2024-07-01 00:00:00

| column | dtype | nulls |
|---|---|---|
| week | datetime64[us] | 0 |
| conversations | int64 | 0 |
| total_tokens | float64 | 0 |
| active_users | int64 | 0 |
| avg_user_turns | float64 | 0 |
| median_first_prompt_tokens | float64 | 0 |
| new_users | int64 | 0 |
| returning_users | int64 | 0 |
| returning_share | float64 | 0 |
| tokens_per_active_user | float64 | 0 |
| partial_week | bool | 0 |
