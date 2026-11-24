# Phase 5D summary: the redesigned dashboard ("Clear Horizon") and the beginner pass

Plan: `FRONTEND_DESIGN_PLAN.md`. Step notes: `phaseA_check/` to `phaseG_check/`, `PHASE_B_NOTES.md`, `beginner_pass/`.
Final checks: `phaseH_check/`.

## What the dashboard is now

Nine pages, in the order a newcomer reads them:

| Menu | Page | What it answers |
|---|---|---|
| | Welcome | What this is, in one sentence, with a real forecast chart and the three headline numbers |
| | The big picture | Cost, benefit, running balance, payback; what needs a decision; what the data shows vs ideas to consider |
| Forecasts | The data we used | The seven real public records, what they hold, their repeating patterns and unusual points |
| Forecasts | What we expect next | Each trend carried forward with its likely range, in words, and in a 3D cone |
| Forecasts | How reliable it is | How close earlier predictions came, and which approach came closest |
| The money | Where the money goes | Monthly cost by type, share of cost, benefit against cost |
| The money | When it pays for itself | Each outlook's payback month, and the month across all futures |
| The money | What matters most | Which choices move the result most |
| | Try your own numbers | The live engine on your own figures |

Every chart carries a short guide (What you see / What it means / Why it matters) filled in from the saved results; a
"What do these words mean?" glossary is in the top bar on every page; every choice has a hint; deeper technical detail
sits in closed "Explore technical details" panels, each term explained.

## Bugs found and fixed along the way (several predate Phase 5D)

1. A first visit straight to a page address showed a bare page (no styles, banner or menu): a folder named `pages/`
   switches Streamlit into an old mode. Fixed by renaming it `views/`.
2. Long chart lines were cut short by the draw-in effect (fixed 3,000 px dash).
3. Short shaded ranges showed stray dots.
4. Two lines on How reliable it is looked alike for red-weak viewers; two cost types for green-weak viewers; pale cost
   colours and white text on a light teal gradient failed contrast.
5. A Phase 1 check note was counted as an unusual point.

## Final quality checklist (plan section 18)

| Check | Result | Evidence |
|---|---|---|
| Plain language: all on-screen words in `copy.py` (technical panel words in `copy_technical.py`) | Pass | 326 tests incl. banned-word and technical-word scans on every page |
| No jargon outside the closed technical panels | Pass | Browser scan of visible text: 0 hits on 52 views; AppTest scans on every page and trend |
| Real numbers | Pass | 26 of 26 on-screen spot checks equal the saved files (recomputed independently); every chart guide sentence recomputed in tests |
| Rupees everywhere, rate note visible | Pass | No "$" on any view; rate note on every view |
| Example-company banner on every page; benefit shown as an estimate | Pass | Banner on all views; "estimate" wording kept |
| Likely ranges only from saved simulations; honest notes where real values fell outside | Pass | Tests against the saved 10th / 90th percentiles; range notes use Phase 3's own counts |
| Accessibility: text 4.5:1, chart marks 3:1, colour-blind separation, never colour alone | Pass | `colour_check.py`, 11 colour tests, patterns on cost types |
| Reduced motion, no WebGL, blocked 3D library: complete still site | Pass | All three runs: no 3D canvas, still versions shown, no page errors (Welcome, The big picture, Where the money goes, What we expect next) |
| 3D pieces each with a still version; one moving scene at a time | Pass | 7 pieces (4 WebGL, 3 CSS); shared runtime |
| Responsive at 1440, 768 and 390 px; no sideways scroll | Pass | 52 views, no sideways scroll |
| Speed: first paint under 2.5 s; frame time 20 ms or less | Pass | First paint 0.85 to 1.56 s; frames 16.7 to 18.8 ms (cone 17.9 ms) on Intel UHD |
| Tests | Pass | 326 passed |
| Phase 1 to 4 outputs, engine, forecasting code, data, notebooks unchanged | Pass | 245 files, SHA-256 identical to the fingerprints recorded at the start of step H |

## Known limits

- Two of 54 views (Where the money goes and When it pays for itself, 768 px dark) timed out once in the final browser
  run with a dropped connection in the server log; ten reloads on a fresh server all loaded in 3.4 to 5.7 s, and the
  previous full run had all 54. Treated as a connection stall, not a page fault.
- The first chart appears 3.9 to 4.7 s after opening a page (Streamlit start-up and Plotly drawing); text appears first.
- A long-running server keeps old code in memory: after any change to the dashboard files, restart
  `streamlit run src/dashboard/app.py` (this caused the `SECTION_FORECASTS` error seen earlier).
- `outputs/phase5/PHASE5_SUMMARY.md`, `DESIGN_NOTES.md`, the Phase 5 screenshots and the Colab notebook describe the
  earlier five-page dashboard; they are left unchanged as the record of that phase.
- Nothing is committed: the project folder is not a git repository.
