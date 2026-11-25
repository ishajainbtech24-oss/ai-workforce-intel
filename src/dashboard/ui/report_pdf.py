"""PDF report of a 'Try your own numbers' result: the summary cards, every chart of the results pages and the
month-by-month table, on A4 pages in the light theme (made for printing).

Built with matplotlib's object interface only (no pyplot): the download button calls `build` on its own thread
when it is clicked, so nothing here may touch shared plotting state or Streamlit. Money arrives in dollars from
the engine and is shown in rupees through `theme.money` / `theme.money_tick`, as on screen.
"""
from __future__ import annotations

import datetime as _dt
import io

import numpy as np
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.figure import Figure
from matplotlib.patches import FancyBboxPatch
from matplotlib.ticker import FuncFormatter, MaxNLocator

from dashboard.ui import copy as C
from dashboard.core import currency as CUR
from dashboard.core import logic
from dashboard.ui import theme as T

A4 = (8.27, 11.69)
LIGHT = T.TOKENS["light"]
INK, MUTED, FAINT, RULE = LIGHT["text"], LIGHT["muted"], LIGHT["faint"], "#E4DCCF"
ACCENT, MARIGOLD, MARIGOLD_SOFT, WARM = LIGHT["accent"], LIGHT["marigold"], LIGHT["marigold-soft"], LIGHT["warm-text"]
OUTLOOK = T.OUTLOOK_COLORS["light"]
LINES = T.LINE_COLORS["light"]
HATCH = {"token_expenditure": "xx", "hosting": "//", "enablement": "", "integration": ".."}
DASH = {"downside": (0, (5, 3)), "expected": "solid", "optimistic": (0, (1.5, 2))}
FONT = "DejaVu Sans"  # ships with matplotlib and has the rupee sign


def _inr(usd) -> np.ndarray:
    """Engine dollars -> rupees for plotting, so the axis steps are round rupee amounts (₹10 L, ₹20 L...)."""
    return np.asarray(CUR.to_inr(np.asarray(usd, dtype=float)), dtype=float)


def _money_axis(ax, axis: str = "y") -> None:
    """Axis in rupees (the plotted values are already rupees): round steps, labels like '₹20 L' or '-₹1 Cr'."""
    a = ax.yaxis if axis == "y" else ax.xaxis
    a.set_major_locator(MaxNLocator(6, steps=[1, 2, 2.5, 5, 10]))
    a.set_major_formatter(FuncFormatter(lambda x, _: CUR.tick(x)))


def _style(ax, title: str | None = None) -> None:
    ax.set_facecolor("white")
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(RULE)
    ax.tick_params(colors=MUTED, labelsize=8, length=0)
    ax.grid(axis="y", color=RULE, linewidth=0.6)
    ax.set_axisbelow(True)
    if title:
        ax.set_title(title, loc="left", fontsize=11, fontweight="bold", color=INK, pad=10)


def _page(pdf: PdfPages, n: int, who: str) -> Figure:
    fig = Figure(figsize=A4, facecolor="white")
    fig.text(0.07, 0.03, f"{C.PRODUCT}  ·  {who}", fontsize=7.5, color=FAINT)
    fig.text(0.93, 0.03, str(n), fontsize=7.5, color=FAINT, ha="right")
    return fig


def _heading(fig: Figure, y: float, text: str) -> None:
    fig.text(0.07, y, text, fontsize=15, fontweight="bold", color=INK)
    fig.add_artist(FancyBboxPatch((0.07, y - 0.012), 0.06, 0.002, boxstyle="square,pad=0", color=MARIGOLD,
                                  transform=fig.transFigure))


def _wrap(text: str, width: int) -> str:
    out, line = [], ""
    for word in text.split():
        if len(line) + len(word) + 1 > width:
            out.append(line)
            line = word
        else:
            line = f"{line} {word}".strip()
    return "\n".join(out + [line])


def _guide(fig: Figure, y: float, lines: tuple[str, str, str], width: int = 100) -> None:
    """The three plain lines under a chart: what you see, what it means, why it matters."""
    for label, text in zip(C.GUIDE_LABELS, lines):
        fig.text(0.07, y, label.upper(), fontsize=6.5, color=FAINT, fontweight="bold")
        body = _wrap(text, width)
        fig.text(0.22, y, body, fontsize=8, color=INK, va="top", linespacing=1.35)
        y -= 0.016 * (body.count("\n") + 1) + 0.008


def _kpis(fig: Figure, cards: dict, y: float, balance_negative: bool) -> None:
    keys = ("cost", "benefit", "balance", "payback")
    w, gap = 0.2, 0.0167
    for i, k in enumerate(keys):
        x = 0.07 + i * (w + gap)
        lead = k == "balance"
        fig.add_artist(FancyBboxPatch((x, y), w, 0.095, boxstyle="round,pad=0,rounding_size=0.008",
                                      transform=fig.transFigure, facecolor=MARIGOLD_SOFT if lead else "white",
                                      edgecolor=MARIGOLD if lead else RULE, linewidth=0.9))
        fig.text(x + 0.012, y + 0.07, _wrap(C.KPI_YOURS[k].upper(), 22), fontsize=6.5, color=MUTED,
                 fontweight="bold", va="top")
        colour = WARM if (k == "balance" and balance_negative) or (k == "payback" and "Not" in cards[k]) else INK
        fig.text(x + 0.012, y + 0.018, _wrap(cards[k], 16), fontsize=12.5 if len(cards[k]) < 14 else 10,
                 fontweight="bold", color=colour)


def _table(ax, header: list[str], rows: list[list[str]], widths: list[float] | None = None, size: float = 8) -> None:
    ax.axis("off")
    tab = ax.table(cellText=rows, colLabels=header, loc="upper left", cellLoc="left", colLoc="left",
                   colWidths=widths)
    tab.auto_set_font_size(False)
    tab.set_fontsize(size)
    tab.scale(1, 1.35)
    lines = max(h.count(chr(10)) + 1 for h in header)  # one height for the whole header row
    for (r, _), cell in tab.get_celld().items():
        cell.set_edgecolor(RULE)
        cell.set_linewidth(0.5)
        if r == 0:
            cell.set_height(cell.get_height() * (1 + 0.55 * (lines - 1)))
            cell.set_facecolor("#F3ECE0")
            cell.get_text().set_fontweight("bold")
            cell.get_text().set_color(INK)
        else:
            cell.get_text().set_color(INK)


# ---------------------------------------------------------------- pages
def _page_summary(pdf, res, scenario, who, made) -> None:
    fig = _page(pdf, 1, who)
    fig.text(0.07, 0.94, C.PRODUCT, fontsize=9, color=MUTED, fontweight="bold")
    fig.text(0.07, 0.905, C.PDF_TITLE, fontsize=24, fontweight="bold", color=INK)
    fig.text(0.07, 0.878, who, fontsize=11, color=ACCENT)
    fig.text(0.07, 0.858, _wrap(made, 110), fontsize=7.5, color=MUTED, va="top")
    cards = logic.live_cards(res)
    bal = np.median(res.cum_net, axis=0)
    _kpis(fig, cards, 0.725, bal[-1] < 0)
    T_ = res.meta["T"]
    fig.text(0.07, 0.69, _wrap(logic.verdict(cards["prob"], cards["p50"], T_), 78), fontsize=11, color=INK,
             va="top", fontweight="bold", linespacing=1.3)
    fig.text(0.07, 0.635, C.PDF_OUTLOOK_NOTE.format(outlook=C.OUTLOOK[scenario].lower()), fontsize=8, color=MUTED)
    ax = fig.add_axes((0.11, 0.33, 0.82, 0.27))
    _style(ax, C.PDF_SECTIONS["balance"])
    m = np.arange(1, T_ + 1)
    lo, mid, hi = np.percentile(res.cum_net, [10, 50, 90], axis=0)
    colour = OUTLOOK[scenario]
    ax.fill_between(m, _inr(lo), _inr(hi), color=colour, alpha=0.22, linewidth=0, label=C.PDF_LEGEND["range"])
    ax.plot(m, _inr(mid), color=colour, linewidth=2.2, label=C.PDF_LEGEND["typical"])
    ax.axhline(0, color=MUTED, linewidth=0.8, linestyle=(0, (3, 3)))
    i = int(np.argmin(mid))
    ax.annotate(T.money(mid[i]), (m[i], _inr(mid[i])), xytext=(0, -14), textcoords="offset points", ha="center",
                fontsize=7.5, color=INK)
    ax.annotate(T.money(mid[-1]), (m[-1], _inr(mid[-1])), xytext=(-4, 8), textcoords="offset points", ha="right",
                fontsize=7.5, color=INK, fontweight="bold")
    ax.set_xticks(m)
    ax.set_xlabel(C.PDF_AXIS["month"], fontsize=8, color=MUTED)
    _money_axis(ax)
    ax.legend(frameon=False, fontsize=7.5, loc="lower right")
    from dashboard.core import explain as EX
    _guide(fig, 0.27, EX.company_balance(cards, T_, float(bal[-1])))
    pdf.savefig(fig)


def _page_money(pdf, res, who) -> None:
    from dashboard.core import explain as EX
    fig = _page(pdf, 2, who)
    _heading(fig, 0.94, C.PDF_SECTIONS["split"])
    shares = logic.live_shares(res)
    total = float(shares["p50_total"].sum())
    ax = fig.add_axes((0.04, 0.66, 0.36, 0.25))
    ax.pie(shares["p50_total"], colors=[LINES[ln] for ln in shares["line"]], startangle=90, counterclock=False,
           wedgeprops={"width": 0.38, "edgecolor": "white", "linewidth": 1.5},
           hatch=[HATCH[ln] for ln in shares["line"]])
    ax.set_aspect("equal")
    y = 0.86
    for r in shares.sort_values("p50_total", ascending=False).itertuples():
        fig.add_artist(FancyBboxPatch((0.45, y - 0.002), 0.012, 0.009, boxstyle="square,pad=0", color=LINES[r.line],
                                      transform=fig.transFigure))
        fig.text(0.47, y, C.LINE[r.line], fontsize=9, color=INK)
        fig.text(0.47, y - 0.014, C.LINE_TAG[r.line], fontsize=7, color=MUTED)
        fig.text(0.93, y, T.money(r.p50_total), fontsize=9, color=INK, ha="right", fontweight="bold")
        fig.text(0.93, y - 0.014, T.share(r.p50_total / total if total else 0.0), fontsize=7, color=MUTED, ha="right")
        y -= 0.045
    _guide(fig, 0.635, EX.donut(shares, "company_donut"))

    T_ = res.meta["T"]
    m = np.arange(1, T_ + 1)
    ax = fig.add_axes((0.11, 0.33, 0.82, 0.19))
    _style(ax, C.PDF_SECTIONS["monthly"])
    bottom = np.zeros(T_)
    for ln in ("enablement", "integration", "hosting", "token_expenditure"):
        v = _inr(np.median(res.lines[ln], axis=0))
        ax.bar(m, v, bottom=bottom, color=LINES[ln], hatch=HATCH[ln], edgecolor="white", linewidth=0.4,
               width=0.65, label=C.LINE[ln])
        bottom += v
    ax.set_xticks(m)
    _money_axis(ax)
    ax.legend(frameon=False, fontsize=7, ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.12))

    ax = fig.add_axes((0.11, 0.1, 0.82, 0.15))
    _style(ax, C.PDF_SECTIONS["benefit"])
    cost, value = _inr(np.median(res.total_cost, axis=0)), _inr(np.median(res.value, axis=0))
    ax.bar(m, cost, color="#D4CCBF", width=0.65, label=C.PDF_LEGEND["cost"])
    ax.plot(m, value, color=ACCENT, linewidth=2, marker="o", markersize=3, label=C.PDF_LEGEND["benefit"])
    ax.set_xticks(m)
    _money_axis(ax)
    ax.legend(frameon=False, fontsize=7, ncol=2, loc="upper center", bbox_to_anchor=(0.5, -0.12))
    pdf.savefig(fig)


def _page_outlooks(pdf, bundle, scenario, who) -> None:
    fig = _page(pdf, 3, who)
    _heading(fig, 0.94, C.PDF_SECTIONS["outlooks"])
    tables = bundle["tables"]
    ms, tot, be = tables["monthly_summary"], tables["totals_summary"], tables["break_even_summary"]
    k1 = np.isclose(ms["multiplier"], 1.0)
    T_ = int(be["T"].iloc[0])
    ax = fig.add_axes((0.11, 0.62, 0.82, 0.26))
    _style(ax)
    order = [s for s in ("downside", "expected", "optimistic") if s in set(ms["scenario"])]
    for s in order:
        d = ms[k1 & (ms["scenario"] == s) & (ms["line"] == "cumulative_net")].sort_values("month")
        ax.plot(d["month"], _inr(d["p50"]), color=OUTLOOK[s], linestyle=DASH[s],
                linewidth=2.4 if s == scenario else 1.6, label=C.OUTLOOK[s])
        ax.annotate(T.money(float(d["p50"].iloc[-1])), (d["month"].iloc[-1], _inr(d["p50"].iloc[-1])), xytext=(4, 0),
                    textcoords="offset points", fontsize=7, color=OUTLOOK[s], va="center")
    ax.axhline(0, color=MUTED, linewidth=0.8, linestyle=(0, (3, 3)))
    ax.set_xticks(range(1, T_ + 1))
    ax.set_xlim(0.6, T_ + 1.8)
    ax.set_xlabel(C.PDF_AXIS["month"], fontsize=8, color=MUTED)
    ax.set_ylabel(C.PDF_AXIS["balance"], fontsize=8, color=MUTED)
    _money_axis(ax)
    ax.legend(frameon=False, fontsize=7.5, loc="lower left")

    rows = []
    for s in order:
        b = be[(be["scenario"] == s) & np.isclose(be["multiplier"], 1.0)].iloc[0]
        t = tot[(tot["scenario"] == s) & np.isclose(tot["multiplier"], 1.0)].iloc[0]
        pays = b["p50_month"] if b["prob_break_even_within_T"] >= 0.5 else float("nan")
        rows.append([C.OUTLOOK[s], T.share(float(b["prob_break_even_within_T"])), T.month(pays, T_),
                     T.money(float(t["cum_net_T_p50"])), T.money(float(t["peak_investment_p50"]))])
    ax = fig.add_axes((0.07, 0.43, 0.86, 0.13))
    _table(ax, [_wrap(h, 16) for h in C.COMPARE_COLS], rows, [0.22, 0.17, 0.21, 0.2, 0.2], size=7.5)

    counts, none, total = bundle["payback"][(scenario, 1.0)]
    ax = fig.add_axes((0.11, 0.1, 0.82, 0.24))
    _style(ax, C.PDF_SECTIONS["payback"])
    x = list(range(1, T_ + 1)) + [T_ + 1.5]
    shares = [c / total for c in counts] + [none / total]
    ax.bar(x, shares, color=[OUTLOOK[scenario]] * T_ + [MARIGOLD], width=0.65)
    ax.set_xticks(x)
    ax.set_xticklabels([str(i) for i in range(1, T_ + 1)] + [C.NOT_WITHIN.format(months=T_).replace(" ", "\n", 2)],
                       fontsize=7)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0%}"))
    ax.set_ylim(0, 1.08)
    for xi, sh in zip(x, shares):
        if sh >= 0.005:
            ax.text(xi, sh + 0.02, T.share(sh), ha="center", fontsize=7, color=INK)
    ax.set_xlabel(f"{C.PDF_AXIS['month']} ({C.OUTLOOK[scenario].lower()})", fontsize=8, color=MUTED)
    ax.set_ylabel(C.PDF_AXIS["share"], fontsize=8, color=MUTED)
    pdf.savefig(fig)


def _input_rows(inputs: dict) -> list[list[str]]:
    rows = []
    for f, (label, unit, _) in C.FIELDS.items():
        if f not in inputs:
            continue
        v = inputs[f]
        if f in logic.PCT_FIELDS:
            text = f"{100 * float(v):.0f}%"
        elif f in logic.MONEY_FIELDS:
            text = CUR.fmt(CUR.to_inr(float(v)))
        else:
            text = f"{float(v):,.0f}" if float(v).is_integer() else f"{float(v):,.2f}"
        rows.append([label, unit, text])
    return rows


def _page_levers(pdf, bundle, who) -> None:
    fig = _page(pdf, 4, who)
    _heading(fig, 0.94, C.PDF_SECTIONS["levers"])
    fig.text(0.07, 0.915, _wrap(C.PDF_LEVERS_NOTE, 110), fontsize=8, color=MUTED, va="top")
    s = bundle["tables"]["sensitivity"].sort_values("swing_cum_net_T", ascending=True)
    base = float(s["base_median_cum_net_T"].iloc[0])
    ax = fig.add_axes((0.36, 0.56, 0.57, 0.32))
    _style(ax)
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", color=RULE, linewidth=0.6)
    y = np.arange(len(s))
    ax.barh(y, _inr(s["median_cum_net_T_low"] - base), color=OUTLOOK["downside"], height=0.55,
            label=C.PDF_LEGEND["lower"])
    ax.barh(y, _inr(s["median_cum_net_T_high"] - base), color=ACCENT, height=0.55, label=C.PDF_LEGEND["higher"])
    ax.axvline(0, color=MUTED, linewidth=0.8)
    ax.set_yticks(y)
    ax.set_yticklabels([C.LEVER.get(i, i) for i in s["input"]], fontsize=8, color=INK)
    _money_axis(ax, "x")
    ax.set_xlabel(C.PDF_AXIS["change"], fontsize=8, color=MUTED)
    ax.legend(frameon=False, fontsize=7.5, loc="lower right")
    top = s.sort_values("swing_cum_net_T", ascending=False).head(3)
    lines = [f"{C.LEVER.get(r.input, r.input)}: {T.money(float(r.swing_cum_net_T))}" for r in top.itertuples()]
    fig.text(0.07, 0.505, "\n".join(lines), fontsize=8.5, color=INK, va="top", linespacing=1.5)

    _heading(fig, 0.42, C.PDF_SECTIONS["inputs"])
    ax = fig.add_axes((0.07, 0.06, 0.86, 0.33))
    _table(ax, C.PDF_INPUT_COLS, _input_rows(bundle["inputs"]), [0.55, 0.2, 0.25], size=8)
    pdf.savefig(fig)


def _page_table(pdf, res, who) -> None:
    from dashboard.core import data as D
    fig = _page(pdf, 5, who)
    _heading(fig, 0.94, C.PDF_SECTIONS["table"])
    tab = D.monthly_result_table(res)
    rows = [[str(int(r[0]))] + [CUR.fmt(float(v)) for v in r[1:]] for r in tab.itertuples(index=False)]
    n = len(rows)
    ax = fig.add_axes((0.07, 0.9 - 0.022 * (n + 1), 0.86, 0.022 * (n + 1)))
    _table(ax, list(tab.columns), rows, [0.13, 0.29, 0.29, 0.29], size=8)
    y = 0.86 - 0.022 * (n + 1)
    _heading(fig, y, C.PDF_SECTIONS["notes"])
    y -= 0.035
    for note in C.PDF_NOTES:
        body = _wrap(note, 105)
        fig.text(0.07, y, "•", fontsize=8.5, color=MARIGOLD, va="top")
        fig.text(0.09, y, body, fontsize=8.5, color=INK, va="top", linespacing=1.4)
        y -= 0.018 * (body.count("\n") + 1) + 0.01
    pdf.savefig(fig)


def build(res, scenario: str, bundle: dict, yours: bool, today: _dt.date | None = None) -> bytes:
    """The report as PDF bytes. `res` = the run shown on the page (its outlook, standard caution); `bundle` = the
    tables, payback counts and inputs of the same figures (data.run_all); `yours` picks the wording."""
    import matplotlib
    matplotlib.rcParams["font.family"] = FONT
    matplotlib.rcParams["hatch.color"] = "white"
    matplotlib.rcParams["hatch.linewidth"] = 0.8
    who = C.PDF_FOR["yours" if yours else "example"]
    day = today or _dt.date.today()
    rate = C.RATE_NOTE.format(rate=CUR.rate_text(), source=CUR.RATE_SOURCE, date=CUR.date_text())
    made = C.PDF_MADE.format(date=f"{day.day} {day.strftime('%B %Y')}", rate=rate)
    buf = io.BytesIO()
    meta = {"Title": f"{C.PRODUCT}: {C.PDF_TITLE}", "Author": C.PRODUCT, "Subject": who,
            "CreationDate": _dt.datetime(day.year, day.month, day.day)}
    with PdfPages(buf, metadata=meta) as pdf:
        _page_summary(pdf, res, scenario, who, made)
        _page_money(pdf, res, who)
        _page_outlooks(pdf, bundle, scenario, who)
        _page_levers(pdf, bundle, who)
        _page_table(pdf, res, who)
    return buf.getvalue()


PAGES = 5  # summary, money, outlooks, what matters most + figures used, month by month
