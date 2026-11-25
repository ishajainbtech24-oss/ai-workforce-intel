# Decisions

Each ambiguity in the MVP brief, the option chosen, and why. Newest last.

| # | Topic | Decision | Why |
|---|---|---|---|
| 1 | "Seven monthly series" | Treat each series at its real frequency (quarterly, monthly, daily, hourly). Date-range buttons go on the dated series; the undated BurstGPT series get count-based ranges. | The data is not monthly; resampling would invent numbers. |
| 2 | Folder structure | Pages move to `app_pages/`, shared UI to `ui/`, logic to `core/`; file names (and so URLs) stay the same. | Matches the brief; URLs and behaviour unchanged. |
| 3 | Where heavy statistics run | Diagnostics, cross-validation and calibrated intervals are computed offline by `src/build_artifacts.py` into `artifacts/`, then only read by the app. | Render's free tier has about 0.1 CPU and sleeps; nothing slow may run on a page load. |
| 4 | Download label | The chart download button says "Download these numbers" (file is .csv). | The plain-language check bans "CSV" on screen. |
| 5 | Range controls on undated series | BurstGPT charts get "Last 7 days / Last 30 days / All" (hours: "Last day / Last week / All") instead of 6M/1Y/5Y. | Their x axis counts days or hours, not dates. |
| 6 | Shock markers | COVID-19 (Mar 2020) and ChatGPT launch (Nov 2022) are marked on dated charts that span them (pay levels, hosting prices). | Only these two are documented shocks relevant to the series. |
| 7 | 3D | The cost donut opens flat; 3D is one click away. The year-end 3D columns stay inside a closed panel. | "Flat charts by default (3D optional)". |
| 8 | Theme | `.streamlit/config.toml` has `[theme.light]` and `[theme.dark]`; the app's own switch still drives the page styles and follows the visitor's setting on the first visit. | Native theme first, custom styles kept for the look. |
