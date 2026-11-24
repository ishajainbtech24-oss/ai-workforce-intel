# References: what was captured, and from where (18 Nov 2026)

Reference material only. These images belong to their authors; they are kept here as evidence for the
VERIFIED labels in `../FRONTEND_DESIGN_PLAN.md`, not for reuse in the product.

| File | What it shows | Source |
|---|---|---|
| `skforecast_studio_live_landing.jpg` | Studio landing page (hero) | live, https://studio.skforecast.org/ |
| `skforecast_studio_live_explore.jpg` | Explore step: stat tiles + series chart, step sidebar | live, demo set "H2O" |
| `skforecast_studio_live_decomposition.jpg` | Explore > Decomposition tab | live |
| `skforecast_studio_live_fit_predict.jpg` | Fit & Predict results: metric cards, history vs forecast | live |
| `skforecast_studio_repo_screenshot.png` | Load Data step | repo `docs/img/skforecast-studio-screen.png` (BSD-3-Clause repository) |
| `forecasthub_live_dashboard.jpg` | Dashboard: KPI cards, forecast chart, alerts, table | live, https://frontend-eta-sand-86.vercel.app (mock data) |
| `forecasthub_repo_screenshot.png` | Dashboard | repo `docs/dashboard-screenshot.png` (MIT) |
| `visual_data_forecaster_live_after_generate.jpg` | After "Sample: Web Traffic" + Generate Forecast (small, the pane rendered it scaled down) | live, https://garud218.github.io/Visual-Data-Forecaster/ |
| `visual_data_forecaster_repo_screenshot.png` | Dark dashboard with polynomial forecast | repo `Dashboard.png` (no licence) |
| `concept_welcome.html` / `.png` | **Concept, not implemented**: Welcome page drawn with real saved values | made for this plan |
| `concept_reliability.html` / `.png` | **Concept, not implemented**: How reliable it is, hosting prices | made for this plan |

Live captures are low resolution because the in-app browser pane was small; they are evidence, not design assets.
Not captured: Skforecast Studio's Backtesting, Hyperparameters and Explainability steps (not run), phone layouts of all
three references, ForecastHub's Inventory/Alerts/Ask/Upload pages.

Concept mock-ups use only: `data/processed/ppi_hosting_monthly.csv`, `outputs/phase3/forecasts/ppi_hosting_monthly.csv`,
`outputs/phase2/tables/holdout.csv`, `outputs/phase2/tables/leaderboard.csv`, `outputs/phase3/tables/interval_check.csv`,
`outputs/phase4/tables/totals_summary.csv`, `break_even_summary.csv`; rupees through `src/dashboard/currency.py`.
They load Inter / Plus Jakarta Sans from Google Fonts when opened.
