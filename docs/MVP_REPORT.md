# MVP upgrade: final report (25 Nov 2026)

Live site: https://ai-workforce-intel.onrender.com · Decisions: `docs/DECISIONS.md` (28 rows) · Number changes:
`docs/CHANGELOG.md` · Screenshots: `docs/screenshots/`

## What changed, by workstream

| Step | Commit | Summary |
|---|---|---|
| 0 Audit | 3fa8e5c | `docs/AUDIT.md`, decision log, changelog, 36 "before" screenshots (9 pages × light/dark × 1280/375 px). |
| A Structure | d8854a9 | `app_pages/`, `ui/`, `core/`; shared components used on every page (headers, insight rows, notes, KPI cards, empty/loading states, one chart wrapper with *View as table*, *Download these numbers* and PNG); time controls and shock markers on dated charts; native light/dark theme sections. |
| B State | 7338232 | One view state mirrored to the address (company, outlook, caution, trend); scenario bar on every Money page; small-team and enterprise presets; grouped trend picker; first-visit tour; warm-up note; error boundary (strict in tests); partial reruns for chart switches. |
| C Forecast rigour | f39459a | Precomputed diagnostics in `artifacts/`; Analyst mode (STL, ADF/KPSS, ACF/PACF, subseries, CUSUM, outliers, model cards, CV table with DM tests, error by step, residuals with Ljung–Box and Q–Q, coverage plot); split-conformal 50%/80% ranges on every forecast. |
| D Money | 3a3c205 | PERT input uncertainty inside the Monte Carlo; NPV, return on cost, cost per person; goal-seek; explanation where payback is structurally 0%; PDF decision memo; Excel summary; save/load scenario file. |
| E Trust | ef7415f | Provenance panel for all seven trends (licences checked at source); *How we forecast* page with steps, limits, sources and how to repeat it. |
| F Hardening | 6ade752 | GitHub Actions CI (passes); accessibility tests at 375/768/1280 px; README rewritten; `.env.example`; measured load times. |

## Acceptance criteria

| Criterion | Status |
|---|---|
| Shared components everywhere | Met: no raw `unsafe_allow_html` or `st.plotly_chart` left in the page files. |
| Scenario bar on every Money page; URL reproduces the view | Met (Overview, Costs, Timing, Levers; `?preset=&outlook=&caution=&trend=`). |
| Analyst mode: diagnostics, model cards, CV table, residual checks | Met (Data and Reliability pages, all seven trends tested). |
| 80% CV coverage between 70% and 90%, shown on Reliability | Met: 71.4–85.7% for all seven (pay 78.6%, hosting 75.7%, AI total 71.4%, apps 71.4%, chat 85.7%, hourly 79.2%, conversations 78.6%); test enforces the bounds. |
| Payback not flat 0%/100%, or explained | Met: expected 1.8%, optimistic 74.2%; cautious 0% with an on-page explanation (benefit below zero in every future). |
| Goal-seek, scenario compare, PDF memo | Met. |
| Provenance for all 7 series; methodology page; README | Met. |
| Loading, empty, error states | Met (warm-up note and spinners; empty state on missing data; error card with traceback in the server log). |
| Chart table view and downloads | Met (every chart). |
| Contrast and keyboard checks | Met (browser tests, both themes; focus visible). |
| Tests and CI pass; no page raises | Met: 376 passed locally (4 min); CI green on GitHub. |

## Number changes (details and before/after values in `docs/CHANGELOG.md`)

- Forecast ranges: bootstrap → conformal. E.g. hosting at 12 months 127.0–131.3 → 127.5–130.0; AI usage per day
  0–28.4 crore → 0–7.3 crore units (old range held only 29% of real values in the rolling check). Expected lines
  unchanged.
- Money (example, standard caution): payback chance expected 0% → 1.8%, optimistic 100% → 74.2%; typical
  12-month balance expected −$96,641 → −$101,603, optimistic $60,928 → $53,443; 1-in-10 ranges now realistic.

## Remaining gaps, most important first

1. **Time saved is the weakest input.** The outlooks rest on three studies that disagree, and the PERT spreads
   (×0.5–1.6 and others) are judgement calls. The result is most sensitive to exactly these. A company-specific
   pilot measurement would matter more than any modelling change.
2. **Short AI-usage records.** The three BurstGPT token series have only 4 cross-validation folds (7 scored values),
   so their coverage figures are rough (the page says so).
3. **Hourly requests range is very wide** at 168 hours (0 to about 30,000), because cross-validation only checks 24
   hours ahead and the range is held flat beyond that. Honest, but of little practical use.
4. **Two "inside the range" figures on Reliability.** The past-check chart still describes the original hold-out
   range (e.g. "0 of 6") next to the calibrated coverage (76%). Each is explained, but a reader could be confused.
5. **Free hosting.** 29 s for the first page after a deploy, up to a minute more after sleep, about 3 s per page
   after that.
6. **Accessibility is checked automatically only** (contrast, layout, names, focus). It has not been tested by a
   person with a screen reader.
7. **Downloads cover the standard caution level only** (PDF memo and Excel); the page itself shows all three levels.
8. **Screenshots after C–E cover the changed pages only** (B has the full 36-image set).
