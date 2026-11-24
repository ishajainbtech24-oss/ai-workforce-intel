"""Phase 4 notebook sections (Monte Carlo cost and value engine)."""
from __future__ import annotations

from _nb_common import NB

ENGINE_SETUP = r'''
ENGINE = {}
with step("load the engine"):
    import logging
    logging.getLogger("engine").setLevel(logging.ERROR)  # the fallback is reported below in plain words
    import config, config_phase4 as P4
    from engine.inputs import load_inputs
    from engine.drivers import load_drivers
    from engine.simulate import run_engine, summarise
    INPUTS, RAW = load_inputs(P4.EXAMPLE_INPUTS)
    SC_TABLE = pd.read_csv(P4.PHASE3_DIR / "forecasts" / "scenario_tables.csv")
    DRIVERS_T = load_drivers(int(INPUTS["horizon_months"]), P4.PHASE3_DIR, config.DATA_DIR)
    ENGINE.update(inputs=INPUTS, drivers=DRIVERS_T, scenarios=SC_TABLE)
    print("Engine ready: horizon", INPUTS["horizon_months"], "months;", len(DRIVERS_T.drivers), "drivers loaded")
    for role, d in DRIVERS_T.drivers.items():
        if d.used_fallback:
            print(f"Note: {role} uses a fallback: {d.note}")
'''


def part_question(nb: NB) -> None:
    nb.md("""
    ## 1. The question
    **What will an AI programme cost, what does it return, and when does it break even?** The engine combines the
    Phase 3 forecast paths (wages, hosting prices, token demand) with a company's own numbers (people, training,
    engineering hours) and a time-saved scenario, and runs thousands of possible futures.
    """)
    nb.code(ENGINE_SETUP)


def part_labels(nb: NB) -> None:
    nb.md("""
    ## 2. The four outputs and their labels
    Every cost or value line says what kind of evidence it rests on. *Forecast-driven* lines move with the Phase 3
    forecasts; *estimates* come from the company's own inputs; *projections* rest on scenario assumptions.
    The labels matter because a reader must not mistake an assumption for a forecast.
    """)
    nb.code(r'''
    with step("labels"):
        rows = [{"output": P4.LINE_LABEL[k], "type": P4.LINE_TYPE[k]} for k in P4.LINE_LABEL]
        show_table(pd.DataFrame(rows))
    ''')


def part_company(nb: NB) -> None:
    nb.md("""
    ## 3. The example company
    **Every value below is illustrative**: an invented example company used to demonstrate the engine. Replace
    them with real numbers (edit `config/example_company.json` or pass `--inputs your_file.json`).
    """)
    nb.code(r'''
    with step("inputs"):
        a = json.loads(Path("outputs/phase4/assumptions.json").read_text(encoding="utf-8"))
        t = pd.DataFrame([{"input": k, "value": v["value"], "unit": v["unit"], "type": v["evidence_type"],
                           "note": v["note"]} for k, v in a["inputs"].items()])
        show_table(t, n=30)
    ''')


def part_paths(nb: NB) -> None:
    nb.md("""
    ## 4. From forecast paths to monthly numbers
    Each Phase 3 path becomes a month-by-month series. Hosting costs follow the PPI hosting index, wages the ECI
    wage index (interpolated from quarters to months). Beyond a driver's forecast horizon the last forecast value is
    carried forward **flat**, and the engine counts how much cost falls in those extrapolated months.
    """)
    nb.code(r'''
    with step("path diagram"):
        import matplotlib.pyplot as plt
        long = load_drivers(18, P4.PHASE3_DIR, config.DATA_DIR)["hosting"]
        m = range(1, 19)
        fig, ax = plt.subplots(figsize=(9, 3.4))
        for row in long.paths[:20]:
            ax.plot(m, row, color="#8C8C8C", lw=0.6, alpha=0.6)
        ax.plot(m, long.point, color="#0072B2", lw=2, label="point forecast")
        ax.axvspan(long.covered_months + 0.5, 18.5, color="#E69F00", alpha=0.15, label="flat extrapolation")
        ax.set(xlabel="engine month", ylabel="PPI hosting index / last observed value",
               title="Hosting driver: 20 of the 200 paths, monthly, with flat extrapolation after month 12")
        ax.legend(fontsize=8)
        plt.tight_layout()
        plt.show()
        show_table(read_table("phase4", "extrapolation"), n=10)
    ''')


def part_one_draw(nb: NB) -> None:
    nb.md("""
    ## 5. One draw, step by step
    One possible future for the expected scenario: the adoption ramp gives the active and new users, which drive
    tokens, training and the value of saved time; each line is shown so the arithmetic can be followed.
    """)
    nb.code(r'''
    with step("one draw"):
        r = run_engine(INPUTS, "expected", 1.0, 1, 42, DRIVERS_T, SC_TABLE)
        T = r.meta["T"]
        one = pd.DataFrame({"month": range(1, T + 1), "active users": r.meta["U"], "new users": r.meta["N"],
                            "ramped users (value)": r.meta["E"],
                            "tokens (M)": r.meta["U"] * INPUTS["tokens_per_active_user_per_month"] / 1e6,
                            "token cost": r.lines["token_expenditure"][0], "hosting": r.lines["hosting"][0],
                            "enablement": r.lines["enablement"][0], "integration": r.lines["integration"][0],
                            "value": r.value[0], "net": r.net[0], "cumulative net": r.cum_net[0]})
        print(f"time saved: {r.meta['scenario_info']['conversion']}")
        show_table(one, n=T, digits=0)
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(9, 3.4))
        ax.bar(one["month"], -one[["token cost", "hosting", "enablement", "integration"]].sum(axis=1),
               color="#E69F00", label="total cost (negative)")
        ax.bar(one["month"], one["value"], color="#009E73", label="value")
        ax.plot(one["month"], one["cumulative net"], color="#0072B2", lw=2, marker="o", label="cumulative net")
        ax.axhline(0, color="#222222", lw=1)
        ax.set(xlabel="month", ylabel="USD", title="One draw, expected scenario (illustrative example company)")
        ax.legend(fontsize=8)
        plt.tight_layout()
        plt.show()
    ''')


def part_futures(nb: NB) -> None:
    nb.md("""
    ## 6. Running 5,000 futures
    Each draw picks one Phase 3 path per driver at random (independently between drivers) and computes every month.
    The table gives, per scenario and uncertainty multiplier k, the probability of breaking even within the horizon
    and the P10, P50 and P90 break-even month among the draws that do. The fan charts show the cumulative net.
    """)
    nb.code(r'''
    with step("break-even"):
        be = read_table("phase4", "break_even_summary")
        show_table(be, n=12, cols=["scenario", "multiplier", "prob_break_even_within_T", "p10_month", "p50_month",
                                   "p90_month", "share_no_break_even"])
        for sc in ("downside", "expected", "optimistic"):
            show_img(f"outputs/phase4/figures/cumulative_net_{sc}.png", width=800)
    ''')


def part_breakdown(nb: NB) -> None:
    nb.md("""
    ## 7. Cost breakdown
    Which line costs most, and how much of the cost rests on forecasts versus the company's own estimates.
    """)
    nb.code(r'''
    with step("breakdown"):
        show_img("outputs/phase4/figures/cost_stack_expected.png", width=800)
        show_img("outputs/phase4/figures/cost_share_by_type.png", width=600)
        text = md_section("outputs/phase4/PHASE4_SUMMARY.md", "Cost breakdown")
        if text:
            display(Markdown("\n".join(l for l in text.splitlines() if not l.startswith("|"))))
    ''')


def part_compare(nb: NB) -> None:
    nb.md("""
    ## 8. Scenarios and the uncertainty multiplier
    The scenario chart compares downside, expected and optimistic time saved. The multiplier chart widens the forecast
    uncertainty by k = 1.5 and 2.0 (Phase 3 found its intervals too narrow) and shows what changes.
    """)
    nb.code(r'''
    with step("compare"):
        show_img("outputs/phase4/figures/scenario_compare.png", width=800)
        show_img("outputs/phase4/figures/multiplier_effect.png", width=850)
        text = md_section("outputs/phase4/PHASE4_SUMMARY.md", "uncertainty multiplier")
        if text:
            display(Markdown(text))
    ''')


def part_tornado(nb: NB) -> None:
    nb.md("""
    ## 9. Which inputs matter
    Each main input is moved by -20% and +20% (an illustrative stress range, not a measured uncertainty) and the change
    in median cumulative net at the horizon is shown. Long bars mark the inputs worth measuring carefully.
    """)
    nb.code(r'''
    with step("tornado"):
        show_img("outputs/phase4/figures/tornado.png", width=750)
    ''')


def part_widget(nb: NB) -> None:
    nb.md("""
    ## 10. Try your own numbers (interactive, optional)
    Move the sliders and press the button: the engine reruns with 2,000 draws and redraws the cumulative net.
    Nothing else in the notebook depends on this cell.
    """)
    nb.code(r'''
    with step("try your own numbers"):
        try:
            import ipywidgets as widgets
        except ImportError:
            widgets = None
            print("ipywidgets is not available; edit config/example_company.json and use MODE = 'run' instead.")
        if widgets is not None and ENGINE:
            import matplotlib.pyplot as plt
            import numpy as np
            w = {"employees": widgets.IntSlider(value=INPUTS["employees"], min=10, max=5000, step=10, description="employees"),
                 "adoption_target": widgets.FloatSlider(value=INPUTS["adoption_target"], min=0.0, max=1.0, step=0.05, description="adoption"),
                 "training_hours_per_new_user": widgets.FloatSlider(value=INPUTS["training_hours_per_new_user"], min=0, max=40, step=1, description="training h"),
                 "engineering_hours_build": widgets.FloatSlider(value=INPUTS["engineering_hours_build"], min=0, max=5000, step=50, description="eng. hours"),
                 "realisation_rate": widgets.FloatSlider(value=INPUTS["realisation_rate"], min=0.0, max=1.0, step=0.05, description="realisation")}
            scen = widgets.Dropdown(options=["expected", "optimistic", "downside"], value="expected", description="scenario")
            mult = widgets.Dropdown(options=[1.0, 1.5, 2.0], value=1.0, description="k")
            out = widgets.Output()
            def _redraw(_=None):
                out.clear_output()
                with out:
                    inp = dict(INPUTS, **{k: v.value for k, v in w.items()})
                    inp["adoption_target"] = max(inp["adoption_target"], inp["adoption_start"])
                    res = run_engine(inp, scen.value, mult.value, 2000, 42, DRIVERS_T, SC_TABLE)
                    s = summarise(res)["break_even"]
                    p10, p50, p90 = np.percentile(res.cum_net, [10, 50, 90], axis=0)
                    m = np.arange(1, res.cum_net.shape[1] + 1)
                    fig, ax = plt.subplots(figsize=(8, 3.2))
                    ax.fill_between(m, p10, p90, color="#0072B2", alpha=0.2, label="P10-P90")
                    ax.plot(m, p50, color="#0072B2", lw=2, label="median")
                    ax.axhline(0, color="#222222", lw=1)
                    ax.set(xlabel="month", ylabel="cumulative net (USD)", title="Your inputs (illustrative)")
                    ax.legend(fontsize=8)
                    plt.show()
                    print(f"P(break-even within {res.meta['T']} months) = {s['prob_within_T']:.0%}")
            btn = widgets.Button(description="Run 2,000 draws")
            btn.on_click(_redraw)
            display(widgets.VBox([*w.values(), scen, mult, btn]), out)
            _redraw()
    ''')


def part_code(nb: NB) -> None:
    nb.md("""
    ## 11. Look at the code
    Break-even is the first month whose cumulative net is at or above zero; the value of saved time ramps up for each
    adoption cohort, computed for all months at once with a convolution.
    """)
    nb.code(r'''
    with step("code"):
        show_source("engine.model", "break_even")
        show_source("engine.model", "effective_users")
    ''')


def phase4_sections(nb: NB) -> None:
    for part in (part_question, part_labels, part_company, part_paths, part_one_draw, part_futures,
                 part_breakdown, part_compare, part_tornado, part_widget, part_code):
        part(nb)
