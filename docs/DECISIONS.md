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
| 9 | One view state | `core/state.py` holds company, outlook, caution and trend in the session and mirrors them to the address (`?preset=small&outlook=optimistic&caution=more&trend=pay`). Widgets keep their own keys and write back on change. | Streamlit forgets a widget's value on pages that do not draw it; a separate key survives page changes. |
| 10 | Company presets | Small team (50 people) and Enterprise (5,000) scale the example company's head count, build hours, hosting, enablement and ramp. They are run through the same engine once per server and cached; nothing is saved to disk. | Render's disk is wiped on restart; the free CPU is small, so each preset runs once. |
| 11 | Trend picker | Three groups (Pay, Technology, AI usage), then the trend inside the group. The choice is shared by the three Forecast pages. | Seven flat pills were hard to scan on a phone. |
| 12 | First-visit tour | A three-step dialog on Welcome, once per browser (cookie `aiwi_tour=seen`, no personal data); off with `?tour=off`. | Short and skippable; the cookie avoids showing it on every visit. |
| 13 | Error boundary | A failing page shows a plain warning and logs the traceback to the server log; the rest of the site keeps working. Tests set `AIWI_STRICT=1` so errors still fail them. | Visitors never see a traceback; bugs are not hidden from tests. |
| 14 | Partial reruns | The overview view switch, the reliability "show all" switch and the donut flat/3D switch redraw only their own section (`st.fragment`). | Less waiting on the small server. |
