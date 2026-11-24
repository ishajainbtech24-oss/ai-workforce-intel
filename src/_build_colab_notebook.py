"""Build the Colab notebooks TSAF_Phase1.ipynb .. TSAF_Phase5.ipynb (one per phase).

Usage:  python src/_build_colab_notebook.py [--out-dir .]

Shared cells (settings, helpers, bundle upload, packages, run cell, summary, next) come from
`_nb_common.py`; the Phase 1 and 2 sections from `_nb_parts_12.py` (the sections of the earlier
combined notebook, TSAF_Phases_1_2.ipynb, which is kept as it was); Phase 3 from `_nb_parts_3.py`.
The notebooks only CALL the project (subprocess for the runners, imports, inspect.getsource);
no model code is copied into them. Each needs only the shared zip, never another notebook.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _nb_common import NB, closing, drivers_cell, setup, title  # noqa: E402
from _nb_parts_3 import phase3_sections  # noqa: E402
from _nb_parts_4 import phase4_sections  # noqa: E402
from _nb_parts_5 import phase5_sections  # noqa: E402
from _nb_parts_12 import part_a, part_b, part_c  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def phase1() -> NB:
    nb = NB()
    title(nb, 1, "Phase 1 explores seven demand and cost series (BurstGPT LLM traffic, WildChat usage, wages and "
                 "hosting prices) and sets simple benchmark forecasts that every later model must beat.",
          "the processed data in `data/processed` (inside the zip).",
          "`outputs/phase1/handoff.json` (seasonal periods, differencing, decomposition, backtest settings) "
          "and the baseline scores, used by Phase 2.")
    setup(nb, 1)
    drivers_cell(nb, "handoff")
    part_a(nb)
    part_b(nb)
    closing(nb, 1)
    return nb


def phase2() -> NB:
    nb = NB()
    title(nb, 2, "Phase 2 fits smoothing, ARIMA, machine-learning and ensemble models to each series and compares "
                 "them all with the same rolling-origin backtest, then picks one model per series.",
          "`outputs/phase1/handoff.json` from Phase 1 (inside the zip).",
          "`outputs/phase2/chosen_models.json` and the backtest errors `cv_residuals.parquet`, used by Phase 3.")
    setup(nb, 2)
    drivers_cell(nb, "handoff")
    part_c(nb)
    closing(nb, 2)
    return nb


def phase3() -> NB:
    nb = NB()
    title(nb, 3, "Phase 3 refits each chosen model, draws 200 simulated future paths per series from the model's "
                 "own backtest errors, checks those ranges on the holdout, and writes everything in one standard table.",
          "`outputs/phase2/chosen_models.json` and `outputs/phase2/tables/cv_residuals.parquet` from Phase 2 "
          "(inside the zip).",
          "`outputs/phase3/forecasts/<series>.parquet` (the standard table), the scenario table and "
          "`inputs_for_phase4.json`, used by the Phase 4 cost and value engine.")
    setup(nb, 3)
    drivers_cell(nb, "manifest")
    phase3_sections(nb)
    closing(nb, 3)
    return nb


def phase4() -> NB:
    nb = NB()
    title(nb, 4, "Phase 4 turns the Phase 3 forecast paths and a company's own inputs into monthly cost, value and a "
                 "break-even range, with honest labels for what is forecast, estimated or assumed.",
          "the Phase 3 forecast tables, `inputs_for_phase4.json` and the scenario table (inside the zip), plus "
          "company inputs (`config/example_company.json`, an illustrative example).",
          "`outputs/phase4/`: break-even and cost tables, figures, `assumptions.json`, used by the Phase 5 dashboard.")
    setup(nb, 4)
    phase4_sections(nb)
    closing(nb, 4)
    return nb


def phase5() -> NB:
    nb = NB()
    title(nb, 5, "Phase 5 is a plain-language dashboard that shows the project's real results and lets anyone try their "
                 "own numbers through the Phase 4 engine. Streamlit does not run inside Colab, so this notebook shows "
                 "the pages as screenshots and the numbers behind them.",
          "the saved Phase 4 results and the engine (inside the zip).",
          "`src/dashboard/` (run with `streamlit run src/dashboard/app.py`) and `outputs/phase5/` (screenshots, notes).")
    setup(nb, 5)
    phase5_sections(nb)
    closing(nb, 5)
    return nb


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--out-dir", type=Path, default=ROOT)
    p.add_argument("--phases", type=int, nargs="+", default=[1, 2, 3, 4, 5], help="which notebooks to write")
    args = p.parse_args(argv)
    for k, build in ((1, phase1), (2, phase2), (3, phase3), (4, phase4), (5, phase5)):
        if k not in args.phases:
            continue
        nb = build()
        path = args.out_dir / f"TSAF_Phase{k}.ipynb"
        nb.write(path)
        print(f"notebook written: {path.name} ({len(nb.cells)} cells)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
