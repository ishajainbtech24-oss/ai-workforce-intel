"""Cells shared by the three Colab notebooks (TSAF_Phase1/2/3.ipynb), so they cannot drift apart.

`NB` collects cells for one notebook. The shared cells are: title with a "where this fits" box,
the settings cell, helper functions (step, show_img, show_table, read_table, md_section,
show_source), getting the project from the bundle zip, the package check, seeds and layout,
the run cell of that phase, the driver list, the phase summary, "what we have" and "next".
Code cells must be plain ASCII.
"""
from __future__ import annotations

from textwrap import dedent

import nbformat
from nbformat.v4 import new_code_cell, new_markdown_cell, new_notebook

PHASES = {
    1: {"title": "Phase 1: exploration and baselines", "script": "src/run_phase1.py",
        "summary": "outputs/phase1/PHASE1_SUMMARY.md", "notebook": "TSAF_Phase1.ipynb",
        "estimate": "about 1 to 5 minutes",
        "built": "loaders, decomposition, trend methods, ADF/KPSS, ACF/PACF, anomaly screen, 5 baselines, backtest",
        "outputs": "outputs/phase1: tables, figures, handoff.json, PHASE1_SUMMARY.md"},
    2: {"title": "Phase 2: forecasting models and rolling backtests", "script": "src/run_phase2.py",
        "summary": "outputs/phase2/PHASE2_SUMMARY.md", "notebook": "TSAF_Phase2.ipynb",
        "estimate": "about 4 minutes with --fast, 20 minutes or more for the full run",
        "built": "smoothing, ARIMA/SARIMA/SARIMAX, Ridge/RF/XGBoost, ensemble, intervals, diagnostics, model choice",
        "outputs": "outputs/phase2: tables, figures, chosen_models.json, cv_residuals.parquet, PHASE2_SUMMARY.md"},
    3: {"title": "Phase 3: simulated paths and the standard forecast table", "script": "src/run_phase3.py",
        "summary": "outputs/phase3/PHASE3_SUMMARY.md", "notebook": "TSAF_Phase3.ipynb",
        "estimate": "under 1 minute (both --fast and full)",
        "built": "refit of the chosen models, 200 bootstrap paths per driver, holdout interval check, standard table, scenarios",
        "outputs": "outputs/phase3: forecasts/*.parquet and .csv, manifest.json, inputs_for_phase4.json, PHASE3_SUMMARY.md"},
    4: {"title": "Phase 4: Monte Carlo cost and value engine", "script": "src/run_phase4.py",
        "summary": "outputs/phase4/PHASE4_SUMMARY.md", "notebook": "TSAF_Phase4.ipynb",
        "estimate": "under 1 minute (both --fast and full)",
        "built": "cost lines (tokens, hosting, enablement, integration), value projection, break-even, multiplier, tornado",
        "outputs": "outputs/phase4: tables (break-even, totals, monthly), figures, assumptions.json, PHASE4_SUMMARY.md"},
    5: {"title": "Phase 5: the dashboard", "script": None,
        "summary": "outputs/phase5/PHASE5_SUMMARY.md", "notebook": "TSAF_Phase5.ipynb",
        "estimate": "nothing to recompute (the dashboard runs locally with Streamlit)",
        "built": "five-page plain-language dashboard on the saved results, with a live try-your-own-numbers page",
        "outputs": "src/dashboard/, outputs/phase5: screenshots, DESIGN_NOTES.md, PHASE5_SUMMARY.md"},
}
NEXT = {1: "**Next: Phase 2** (`TSAF_Phase2.ipynb`) fits smoothing, ARIMA, machine-learning and ensemble models and "
           "compares them with the same backtest; it reads `outputs/phase1/handoff.json` from the bundle.",
        2: "**Next: Phase 3** (`TSAF_Phase3.ipynb`) refits each chosen model and turns it into 200 simulated "
           "future paths in one standard table; it reads `chosen_models.json` and `cv_residuals.parquet` from the bundle.",
        3: "**Next: Phase 4**, the Monte Carlo cost and value engine, will read the standard forecast tables, "
           "`inputs_for_phase4.json` and the scenario table. Then Phase 5 (dashboard) and Phase 6 (report).",
        4: "**Next: Phase 5, the dashboard**, will put `engine.simulate.run_engine` behind sliders so a company can enter "
           "its own numbers, using the same preloaded forecast paths. Then Phase 6, the report.",
        5: "**Next: Phase 6, the report**, which writes up the method, the results and their limits."}


class NB:
    """Cells of one notebook."""

    def __init__(self) -> None:
        self.cells: list = []

    def md(self, text: str) -> None:
        self.cells.append(new_markdown_cell(dedent(text).strip()))

    def code(self, text: str) -> None:
        src = dedent(text).strip()
        if not src.isascii():
            raise ValueError(f"non-ASCII character in code cell: {src[:60]!r}")
        self.cells.append(new_code_cell(src))

    def write(self, path) -> None:
        nb = new_notebook(cells=self.cells, metadata={
            "kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"},
            "language_info": {"name": "python"}, "colab": {"provenance": []}})
        nbformat.validate(nb)
        nbformat.write(nb, str(path))


def title(nb: NB, phase: int, overview: str, needs: str, produces: str) -> None:
    p = PHASES[phase]
    nb.md(f"""
    # AI Workforce Intelligence, {p['title']} (CS3216 Time Series Analysis and Forecasting)

    {overview}

    > **Where this fits.** This is **Phase {phase}** of 6.
    > **Needs:** {needs}
    > **Produces:** {produces}

    > **How to use this notebook**
    > 1. In Colab: *Runtime > Run all*. When asked, upload `ai-workforce-intel_colab.zip` (the same zip for all three notebooks).
    > 2. `MODE = "show"` (default) only displays the finished results inside the zip: under 1 minute.
    > 3. `MODE = "run"` recomputes **this phase only** ({p['estimate']} on Colab), using the earlier phases' results in the zip.
    > 4. Outside Colab, put the unzipped `ai-workforce-intel` folder (or the zip) next to this notebook.
    """)


def settings(nb: NB, phase: int) -> None:
    lstm = ('WITH_LSTM = False   # only for MODE = "run": also train the optional LSTM challenger (needs torch)\n    '
            if phase == 2 else "")
    nb.code(f'''
    # ---- Settings: change these, then Runtime > Run all ----
    MODE = "show"       # "show": display the finished results in the bundle (under 1 minute)
                        # "run":  recompute Phase {phase} first, then display the new results
    RUN_FAST = True     # only for MODE = "run": True = --fast, False = full run
    {lstm}DRIVERS = None      # None = all drivers, or a list such as ["burst_tokens_total_daily"]
    PHASE = {phase}

    import os
    MODE = os.environ.get("TSAF_MODE", MODE)  # used only by the automated test; ignore in Colab
    print("Phase", PHASE, "| MODE =", MODE, "| RUN_FAST =", RUN_FAST, "| DRIVERS =", DRIVERS or "all")
    ''')


HELPERS = r'''
import contextlib, importlib, inspect, json, re, subprocess, sys, time, warnings
from pathlib import Path
import pandas as pd
from IPython.display import Image, Markdown, display

warnings.filterwarnings("ignore")
pd.set_option("display.max_columns", 12)
pd.set_option("display.max_colwidth", 90)

@contextlib.contextmanager
def step(name):
    """Run one notebook step; a problem prints a short message instead of a traceback."""
    try:
        yield
    except FileNotFoundError as exc:
        print(f"[{name}] skipped: a result file is missing ({Path(str(exc.filename or exc)).name}).")
    except Exception as exc:
        print(f"[{name}] skipped: {type(exc).__name__}: {str(exc)[:200]}")

def show_img(path, width=900):
    """Display a saved PNG figure, or a short message if it does not exist."""
    path = Path(path)
    if not path.exists():
        print(f"No figure {path.name}; skipped.")
        return
    display(Image(filename=str(path), width=width))

def show_table(df, n=10, cols=None, digits=3):
    """Display the first n rows of a table, selected columns, rounded numbers."""
    if df is None or len(df) == 0:
        print("No rows to show.")
        return
    df = df[[c for c in cols if c in df.columns]] if cols else df
    display(df.head(n).round(digits).reset_index(drop=True))

def read_table(phase, name):
    """Read outputs/<phase>/tables/<name>.csv."""
    return pd.read_csv(Path("outputs") / phase / "tables" / f"{name}.csv")

def md_section(path, title):
    """Text of the '## ... title ...' section of a generated summary file (None if absent)."""
    text = Path(path).read_text(encoding="utf-8")
    pat = r"^## [^\n]*" + re.escape(title) + r"[^\n]*\n(.*?)(?=^## |\Z)"
    m = re.search(pat, text, flags=re.M | re.S)
    return m.group(1).strip() if m else None

def show_source(module, func, max_lines=25):
    """Print the source of module.func (first max_lines lines), or a short message."""
    try:
        obj = getattr(importlib.import_module(module), func)
        lines = inspect.getsource(obj).splitlines()
    except Exception as exc:
        print(f"Could not find {module}.{func}: {type(exc).__name__}; skipped.")
        return
    more = f"\n# ... {len(lines) - max_lines} more lines" if len(lines) > max_lines else ""
    display(Markdown(f"`{module}.{func}`\n```python\n" + "\n".join(lines[:max_lines]) + more + "\n```"))
'''

GET_PROJECT = r'''
def _is_project(p):
    return (p / "src" / "run_phase2.py").exists()

def _find_project():
    here = Path.cwd()
    for c in (here, here / "ai-workforce-intel", Path("/content/ai-workforce-intel")):
        if _is_project(c):
            return c
    return None

def _get_zip():
    if os.environ.get("TSAF_BUNDLE_PATH"):          # automated test: no upload dialog
        return Path(os.environ["TSAF_BUNDLE_PATH"])
    if Path("ai-workforce-intel_colab.zip").exists():
        return Path("ai-workforce-intel_colab.zip")
    try:
        from google.colab import files               # only exists inside Colab
    except ImportError:
        print("Not in Colab: place ai-workforce-intel_colab.zip or the unzipped folder next to this notebook.")
        return None
    print("Please upload ai-workforce-intel_colab.zip")
    uploaded = files.upload()
    return Path(next(iter(uploaded))) if uploaded else None

# Alternative: unzip from Google Drive instead of uploading (uncomment the two lines):
# from google.colab import drive; drive.mount("/content/drive")
# import zipfile; zipfile.ZipFile("/content/drive/MyDrive/ai-workforce-intel_colab.zip").extractall("/content")

PROJECT = None
with step("get the project"):
    PROJECT = _find_project()
    if PROJECT is None:
        zpath = _get_zip()
        if zpath is not None and zpath.exists():
            import zipfile
            base = Path("/content") if Path("/content").is_dir() else Path.cwd()
            zipfile.ZipFile(zpath).extractall(base)
            PROJECT = base / "ai-workforce-intel"
    if PROJECT is not None and _is_project(PROJECT):
        os.chdir(PROJECT)
        if str(PROJECT / "src") not in sys.path:
            sys.path.insert(0, str(PROJECT / "src"))
        print("Project ready: working folder is", Path.cwd().name)
    else:
        print("Project not found. Upload the zip and run this cell again.")
'''

PACKAGES = r'''
IMPORT_NAME = {"scikit-learn": "sklearn"}
with step("packages"):
    wanted = []
    for line in Path("requirements.txt").read_text().splitlines():
        line = line.split("#")[0].strip()
        if line:
            wanted.append(re.split(r"[<>=!~ ]", line)[0])
    missing = []
    for pkg in wanted + ["xgboost"]:
        try:
            importlib.import_module(IMPORT_NAME.get(pkg, pkg))
        except ImportError:
            missing.append(pkg)
    if missing:
        print("Installing:", ", ".join(missing))
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", "--disable-pip-version-check", *missing], check=False)
    else:
        print("All required packages are already installed.")
    import numpy, statsmodels, sklearn, matplotlib
    print(f"Python {sys.version.split()[0]} | pandas {pd.__version__} | numpy {numpy.__version__} | "
          f"statsmodels {statsmodels.__version__} | scikit-learn {sklearn.__version__} | matplotlib {matplotlib.__version__}")
    import optional
    for name, ok in [("xgboost", optional.has_xgboost()), ("prophet", optional.has_prophet()), ("torch (LSTM)", optional.has_torch())]:
        print(f"  optional {name:13s}: {'available' if ok else 'not installed (model skipped)'}")
'''

SEEDS = r'''
with step("seeds and tree"):
    import random, numpy as np
    random.seed(42)
    np.random.seed(42)
    for top in sorted(p for p in Path(".").iterdir() if p.is_dir() and not p.name.startswith(".")):
        subs = sorted(q.name for q in top.iterdir() if q.is_dir() and q.name != "__pycache__")
        print(f"{top.name}/" + (f"  ->  {', '.join(subs)}" if subs else ""))
'''


def setup(nb: NB, phase: int) -> None:
    """Settings, helpers, project, packages, seeds and the run cell of this phase."""
    settings(nb, phase)
    nb.md("""
    ### Helper functions
    Small helpers used by every step: `step` turns any problem into a one-line message (so *Run all*
    never stops), `show_img` and `show_table` display figures and tables at a readable size, and
    `show_source` prints a real function from the project.
    """)
    nb.code(HELPERS)
    nb.md("""
    ## Setup 1: get the project
    If the project folder is not here yet, the cell asks you to upload `ai-workforce-intel_colab.zip`
    (about 10 MB), unzips it and moves into the folder. Outside Colab it looks for the folder (or the zip)
    next to the notebook. The commented lines show how to unzip it from Google Drive instead.
    """)
    nb.code(GET_PROJECT)
    nb.md("""
    ## Setup 2: packages
    Colab already has pandas, numpy, statsmodels, scikit-learn, matplotlib and pyarrow. This cell installs
    only what is missing from `requirements.txt`, plus `xgboost` if it is missing. Prophet and torch are
    optional and are never installed automatically.
    """)
    nb.code(PACKAGES)
    nb.md("""
    ## Setup 3: seeds and project layout
    All randomness uses seed 42, so a rerun gives the same numbers.
    """)
    nb.code(SEEDS)
    run_cell(nb, phase)


def run_cell(nb: NB, phase: int) -> None:
    p = PHASES[phase]
    if p["script"] is None:
        nb.md("""
        ## Run
        This phase has nothing to recompute in a notebook: the dashboard is a Streamlit app that runs on your own
        computer. `MODE = "run"` behaves like `"show"` here.
        """)
        nb.code('''
        print("MODE =", MODE, "- nothing to recompute in this notebook; showing the saved screenshots and results.")
        ''')
        return
    lstm = ', *(["--with-lstm"] if WITH_LSTM else [])' if phase == 2 else ""
    nb.md(f"""
    ## Run (only when `MODE = "run"`)
    In `show` mode nothing is recomputed. In `run` mode this cell runs `python {p['script']}` exactly as in a
    terminal (this phase only; earlier phases' results come from the zip), then the notebook shows the new results.
    """)
    nb.code(f'''
    def run_script(args):
        """Run one project script and print the last lines of its log."""
        t0 = time.time()
        res = subprocess.run([sys.executable, *args], capture_output=True, text=True)
        for line in (res.stdout + res.stderr).strip().splitlines()[-8:]:
            print("   ", line[:150])
        print(f"  -> exit code {{res.returncode}}, {{time.time() - t0:.0f}} s")
        return res.returncode

    with step("run"):
        if MODE == "run":
            extra = ["--drivers", *DRIVERS] if DRIVERS else []
            fast = ["--fast"] if RUN_FAST else []
            print("Estimated time on Colab's CPU: {p['estimate']}.")
            T0 = time.time()
            run_script(["{p['script']}", *fast{lstm}, *extra])
            print(f"Total elapsed: {{(time.time() - T0) / 60:.1f}} minutes")
        else:
            print("MODE = 'show': displaying the finished results in outputs/ (nothing is recomputed).")
    ''')


def drivers_cell(nb: NB, source: str) -> None:
    """NAMES (and HANDOFF) for the later cells; `source` is 'handoff' or 'manifest'."""
    if source == "manifest":
        nb.code(r'''
        NAMES = []
        with step("drivers"):
            MANIFEST = json.loads(Path("outputs/phase3/manifest.json").read_text(encoding="utf-8"))
            NAMES = [d["driver"] for d in MANIFEST["drivers"] if not DRIVERS or d["driver"] in DRIVERS]
            print(f"{len(NAMES)} drivers:", ", ".join(NAMES))
        ''')
        return
    nb.code(r'''
    NAMES, HANDOFF = [], {"drivers": []}
    with step("drivers"):
        HANDOFF = json.loads(Path("outputs/phase1/handoff.json").read_text(encoding="utf-8"))
        NAMES = [d["name"] for d in HANDOFF["drivers"] if not DRIVERS or d["name"] in DRIVERS]
        print(f"{len(NAMES)} drivers:", ", ".join(NAMES))
    ''')


def closing(nb: NB, phase: int) -> None:
    """This phase's summary sections, the 'what we have so far' table and the 'Next' cell."""
    p = PHASES[phase]
    nb.md(f"""
    # Summary

    The talking points and limitations below are taken directly from `{p['summary'].split('/')[-1]}`,
    so every number comes from the run.
    """)
    nb.code(f'''
    with step("summary"):
        for title in ("What to say in the review", "Limitations"):
            text = md_section("{p['summary']}", title)
            display(Markdown(f"### Phase {phase}: {{title}}\\n\\n" + (text or "_Section not found._")))
    ''')
    rows = ", ".join(f'{{"phase": "{k}. {v["title"].split(": ", 1)[1]}", "built": "{v["built"]}", '
                     f'"outputs": "{v["outputs"]}", "notebook": "{v["notebook"]}"}}'
                     for k, v in PHASES.items() if k <= phase)
    nb.code(f'''
    with step("what we have"):
        display(Markdown("### What we have so far"))
        display(pd.DataFrame([{rows}]))
    ''')
    nb.md(NEXT[phase])
