# Decisions

Each ambiguity in the MVP brief, the option chosen, and why. Newest last.

| # | Topic | Decision | Why |
|---|---|---|---|
| 1 | "Seven monthly series" | Treat each series at its real frequency (quarterly, monthly, daily, hourly). Date-range buttons go on the dated series; the undated BurstGPT series get count-based ranges. | The data is not monthly; resampling would invent numbers. |
| 2 | Folder structure | Pages move to `app_pages/`, shared UI to `ui/`, logic to `core/`; file names (and so URLs) stay the same. | Matches the brief; URLs and behaviour unchanged. |
| 3 | Where heavy statistics run | Diagnostics, cross-validation and calibrated intervals are computed offline by `src/build_artifacts.py` into `artifacts/`, then only read by the app. | Render's free tier has about 0.1 CPU and sleeps; nothing slow may run on a page load. |
