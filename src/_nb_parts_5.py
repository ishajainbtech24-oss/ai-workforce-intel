"""Phase 5 notebook sections: the dashboard shown through screenshots and the numbers behind it."""
from __future__ import annotations

from _nb_common import NB

PAGES = [("overview", "The big picture",
          "The headline: what the programme costs over a year, the estimated benefit, the running balance and when it "
          "pays for itself, for the expected outlook, plus the running balance of all three outlooks and three findings."),
         ("costs", "Where the money goes",
          "Monthly cost by type, each tagged Based on trends or Our estimate, the share of each type and the estimated "
          "benefit against the cost, with selectors for the outlook and how cautious to be about the future."),
         ("timing", "When it pays for itself",
          "A one-sentence verdict, the month the programme pays for itself across many possible futures (with a separate "
          "bar for not within 12 months) and the three outlooks side by side."),
         ("levers", "What matters most",
          "Which choices change the year-end balance most when they are 20% lower or higher, and what could make the "
          "expected outlook pay for itself."),
         ("your_company", "Try your own numbers",
          "A control panel: change the figures, press Update results, and the real engine reruns on them in a couple "
          "of seconds; the results can be downloaded.")]


def part_launch(nb: NB) -> None:
    nb.md("""
    ## 1. The dashboard and how to open it
    The dashboard is a small website that runs on your own computer. From the project folder:

    ```bash
    pip install -r requirements.txt -r requirements-dashboard.txt
    streamlit run src/dashboard/app.py
    ```

    It opens at `http://localhost:8501`. It is written for readers with no technical background: plain words, the
    example company is labelled on every page, and the benefit is always called an estimate.
    """)


SHOTS = "outputs/phase5/ui_v3/after"  # UI v3: side navigation, warm palette, amounts in Indian rupees


def part_tour(nb: NB) -> None:
    nb.md("## 2. A tour of the five pages\nScreenshots taken from the running dashboard at desktop width "
          "(UI v3: pages listed in a side panel on the left, amounts in Indian rupees).")
    for key, title_, text in PAGES:
        nb.md(f"### {title_}\n{text}")
        nb.code(f'''
        with step("{key}"):
            show_img("{SHOTS}/{key}_1440_light.png", width=900)
        ''')
    nb.md("### On a phone\nThe same first page at phone width: cards stack and the charts resize.")
    nb.code(f'''
    with step("phone"):
        show_img("{SHOTS}/overview_390_light.png", width=320)
    ''')


def part_polish(nb: NB) -> None:
    nb.md("""
    ## 2b. The look: light and dark, depth and motion
    The pages are listed in a side panel on the left; at its foot are the **Word guide**, a **Dark mode** switch and
    **Reduce motion** (or the computer's own reduced-motion setting), which swaps every animation and 3D piece for a
    still version. Three 3D pieces remain: a slowly turning shape in the Welcome banner, 3D columns of the year-end
    running balance (the same figures are plain bars beside them) and a tilted cost donut (a flat view is one click
    away). They show the same saved numbers as the rest of the page. Before and after, and the dark version:
    """)
    nb.code(f'''
    with step("before and after"):
        show_img("outputs/phase5/ui_v3/before/overview_1440_light.png", width=440)
        show_img("{SHOTS}/overview_1440_light.png", width=440)
        show_img("{SHOTS}/overview_1440_dark.png", width=900)
    ''')


def part_numbers(nb: NB) -> None:
    nb.md("""
    ## 3. The numbers behind the main cards
    The four cards on the first page are read straight from the saved Phase 4 tables and formatted the same way as
    in the dashboard: converted to Indian rupees at the one rate in `src/dashboard/currency.py`. Nothing is typed in by hand.
    """)
    nb.code(r'''
    with step("card numbers"):
        from dashboard.ui import theme as T
        tot = read_table("phase4", "totals_summary")
        be = read_table("phase4", "break_even_summary")
        t = tot[(tot["scenario"] == "expected") & (tot["multiplier"] == 1.0)].iloc[0]
        b = be[(be["scenario"] == "expected") & (be["multiplier"] == 1.0)].iloc[0]
        pays = b["p50_month"] if b["prob_break_even_within_T"] >= 0.5 else float("nan")
        rows = [("Total cost over the year", T.money(t["total_cost_p50"]), "totals_summary.csv", "total_cost_p50"),
                ("Estimated benefit over the year", T.money(t["total_value_p50"]), "totals_summary.csv", "total_value_p50"),
                ("Running balance at year end", T.money(t["cum_net_T_p50"]), "totals_summary.csv", "cum_net_T_p50"),
                ("Pays for itself", T.month(pays, int(b["T"])), "break_even_summary.csv", "p50_month, prob_break_even_within_T")]
        show_table(pd.DataFrame(rows, columns=["card", "shown as", "file", "column"]))
    ''')


def part_engine(nb: NB) -> None:
    nb.md("""
    ## 4. The "Try your own numbers" idea
    The last page sends the viewer's figures to the same engine as Phase 4. Here it runs once with the example
    company and once with twice as many employees (2,000 possible futures each).
    """)
    nb.code(r'''
    with step("your company"):
        import logging
        import numpy as np
        logging.getLogger("engine").setLevel(logging.ERROR)
        import config, config_phase4 as P4
        from dashboard.ui import theme as T
        from engine.inputs import load_inputs
        from engine.drivers import load_drivers
        from engine.simulate import run_engine
        base, _ = load_inputs(P4.EXAMPLE_INPUTS)
        drv = load_drivers(int(base["horizon_months"]), P4.PHASE3_DIR, config.DATA_DIR)
        sc = pd.read_csv(P4.PHASE3_DIR / "forecasts" / "scenario_tables.csv")
        rows = []
        for label, inp in (("Example company", base), ("Twice as many employees", dict(base, employees=2 * base["employees"]))):
            r = run_engine(inp, "expected", 1.0, 2000, 42, drv, sc)
            rows.append({"case": label, "total cost": T.money(np.median(r.total_cost.sum(axis=1))),
                         "estimated benefit": T.money(np.median(r.value.sum(axis=1))),
                         "running balance at the end": T.money(np.median(r.cum_net_T))})
        show_table(pd.DataFrame(rows))
    ''')


def phase5_sections(nb: NB) -> None:
    for part in (part_launch, part_tour, part_polish, part_numbers, part_engine):
        part(nb)
