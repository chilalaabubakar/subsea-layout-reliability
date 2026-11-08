"""Figures 1-3 of the paper (workflow, failure scope, downtime schematic) in the
figures4papers house style (src/layout_rel/pubstyle.py). Diagrams only: no model data.

Usage:  python scripts/make_schematic_figures.py
Writes: figures/fig1_workflow, fig2_failure_scope, fig3_downtime  (.png at 300 dpi and .pdf)
"""
import numpy as np

from layout_rel.config import REPO_ROOT
from layout_rel.pubstyle import PALETTE, FigureStyle, apply_publication_style, finalize_figure

import matplotlib.pyplot as plt  # noqa: E402  (backend set in pubstyle)
from matplotlib.patches import Circle, FancyArrowPatch, FancyBboxPatch, Polygon, Rectangle  # noqa: E402

P = PALETTE
OUT = REPO_ROOT / "figures"
LIGHT_BLUE = "#E4EDF7"


def _blank(ax, w, h):
    ax.set_xlim(0, w)
    ax.set_ylim(0, h)
    ax.set_aspect("equal")
    ax.axis("off")


def fig1_workflow(out):
    steps = [
        ("Gather public data", "Well and host positions, equipment costs, failure rates, 10 years of wave data", "Sec. 3.1, 4"),
        ("Put a price on each failure", "Downtime = mobilization + waiting on weather + repair; cost = vessel hire + lost oil", "Sec. 3.4–3.7"),
        ("Optimize the layout twice", "Case 1: cheapest to build.  Case 2: highest NPV once failure costs are included", "Sec. 3.8"),
        ("Check the answer", "Simulate random failures over the field life; add a risk-averse version of Case 2", "Sec. 3.9"),
        ("Test the assumptions", "Change one input at a time; map where the best layout switches", "Sec. 3.10"),
    ]
    W, H = 10.0, 8.2
    fig, ax = plt.subplots(figsize=(W, H))
    _blank(ax, W, H)
    bx, bw, bh, gap = 1.1, 8.7, 1.05, 0.38
    ytop = H - 0.2
    for k, (title, desc, sec) in enumerate(steps):
        y = ytop - (k + 1) * bh - k * gap
        key = k == 2
        ax.add_patch(FancyBboxPatch((bx, y), bw, bh, boxstyle="round,pad=0,rounding_size=0.12",
                                    fc=LIGHT_BLUE if key else "white",
                                    ec=P["blue_main"] if key else P["grey_dark"], lw=2.5 if key else 1.5))
        cy = y + bh / 2
        ax.add_patch(Circle((0.5, cy), 0.3, fc=P["blue_main"], ec="none"))
        ax.text(0.5, cy, str(k + 1), ha="center", va="center", color="white", fontsize=15, fontweight="bold")
        ax.text(bx + 0.25, y + bh - 0.33, title, ha="left", va="center", fontsize=15, fontweight="bold", color=P["ink"])
        ax.text(bx + 0.25, y + 0.32, desc, ha="left", va="center", fontsize=11.5, color=P["grey_dark"])
        ax.text(bx + bw - 0.2, y + bh - 0.33, sec, ha="right", va="center", fontsize=11, color=P["grey_mid"])
        if k < len(steps) - 1:
            ax.add_patch(FancyArrowPatch((0.5, cy - 0.32), (0.5, cy - bh - gap + 0.32),
                                         arrowstyle="-|>", mutation_scale=16, color=P["grey_mid"], lw=1.5))
    ylast = ytop - 5 * bh - 4 * gap
    ya = ylast - gap - 0.85
    ax.add_patch(FancyArrowPatch((0.5, ylast + bh / 2 - 0.32), (0.5, ya + 0.85),
                                 arrowstyle="-|>", mutation_scale=16, color=P["grey_mid"], lw=1.5))
    ax.add_patch(FancyBboxPatch((0.15, ya), W - 0.35, 0.85, boxstyle="round,pad=0,rounding_size=0.12",
                                fc="#F2F2F0", ec=P["grey_dark"], lw=1.5))
    ax.text(W / 2, ya + 0.425, "Answer: does the optimal layout change when failures are costed, and by how much?",
            ha="center", va="center", fontsize=13.5, fontweight="bold", color=P["ink"])
    finalize_figure(fig, out, pad=0.5)


def _tree(ax, x, y, state):
    """Well symbol: triangle. state = failed / stopped / ok."""
    s = 0.32
    fc = {"failed": P["red_strong"], "stopped": P["red_1"], "ok": "white"}[state]
    ec = P["red_strong"] if state != "ok" else P["grey_mid"]
    ax.add_patch(Polygon([(x - s, y - s * 0.8), (x + s, y - s * 0.8), (x, y + s)], closed=True,
                         fc=fc, ec=ec, lw=2.5 if state == "failed" else 1.8, zorder=3))


def fig2_scope(out):
    W, H = 12.0, 5.6
    fig, ax = plt.subplots(figsize=(W, H))
    _blank(ax, W, H)
    panels = [("X-mas tree fails", "1 of 3 wells stops", "tree"),
              ("Manifold fails", "3 of 3 wells stop", "manifold"),
              ("Tie-back line or umbilical fails", "3 of 3 wells stop", "tieback")]
    for k, (title, sub, failed) in enumerate(panels):
        cx = 2.0 + k * 4.0
        # host
        ax.add_patch(FancyBboxPatch((cx - 0.8, 4.55), 1.6, 0.6, boxstyle="round,pad=0,rounding_size=0.08",
                                    fc="white", ec=P["grey_dark"], lw=1.5))
        ax.text(cx, 4.85, "Host", ha="center", va="center", fontsize=12, color=P["grey_dark"])
        # tie-back
        tb = failed == "tieback"
        ax.plot([cx, cx], [4.55, 3.35], color=P["red_strong"] if tb else P["ink"], lw=4 if tb else 2, zorder=1)
        if tb:
            for sx in (-1, 1):                               # an X across the failed line
                ax.plot([cx - 0.22, cx + 0.22], [3.95 - 0.22 * sx, 3.95 + 0.22 * sx],
                        color=P["red_strong"], lw=3, zorder=4)
        # manifold
        mf = failed == "manifold"
        ax.add_patch(Rectangle((cx - 0.3, 2.75), 0.6, 0.6, fc=P["red_strong"] if mf else P["blue_main"],
                               ec=P["red_strong"] if mf else P["blue_main"], lw=2, zorder=3))
        # wells
        for j, dx in enumerate((-1.1, 0.0, 1.1)):
            ax.plot([cx, cx + dx], [2.75, 1.75], color=P["grey_dark"], lw=1.5, zorder=1)
            state = ("failed" if j == 0 else "ok") if failed == "tree" else "stopped"
            _tree(ax, cx + dx, 1.45, state)
        ax.text(cx, 0.75, title, ha="center", va="center", fontsize=14, fontweight="bold", color=P["ink"])
        ax.text(cx, 0.3, sub, ha="center", va="center", fontsize=12, color=P["grey_dark"])
    # legend row
    ly = -0.45
    items = [("failed", "failed component"), ("stopped", "well stopped until repair"), ("ok", "well producing")]
    x = 1.0
    for state, lab in items:
        _tree(ax, x, ly, state)
        ax.text(x + 0.5, ly, lab, va="center", fontsize=12, color=P["ink"])
        x += 3.4
    ax.add_patch(Rectangle((x - 0.25, ly - 0.25), 0.5, 0.5, fc=P["blue_main"], ec=P["blue_main"]))
    ax.text(x + 0.5, ly, "manifold", va="center", fontsize=12, color=P["ink"])
    ax.set_ylim(-0.9, H)
    finalize_figure(fig, out, pad=0.5)


def fig3_downtime(out):
    fig, ax = plt.subplots(figsize=(12, 6.6))
    ax.set_xlim(0, 12)
    ax.set_ylim(-1.3, 7.2)
    ax.axis("off")
    xf, xm, xw, xr = 2.6, 4.4, 7.4, 9.2          # failure, end mobilization, window start, restored
    xs = np.linspace(1.8, 12, 400)
    # wave height row
    hs = 5.6 + 0.35 * np.sin(1.7 * xs) + 0.25 * np.sin(3.1 * xs + 1)
    mid, half = (xw + xr) / 2, (xr - xw) / 2
    wgt = np.exp(-((xs - mid) / (0.75 * half)) ** 4)       # smooth dip below the limit in the window
    hs = hs * (1 - wgt) + 4.95 * wgt
    ax.add_patch(Rectangle((xw, 4.7), xr - xw, 1.7, fc=P["green_1"], ec="none"))
    ax.plot(xs, hs, color=P["blue_main"], lw=2.5)
    ax.plot([1.8, 12], [5.25, 5.25], color=P["red_strong"], lw=1.8, ls="--")
    ax.text((xw + xr) / 2, 6.6, r"window of length $T_R$", ha="center", fontsize=12, color=P["ink"])
    ax.text(xf + 0.15, 4.85, r"limit $OP_{WF} = \alpha \times OP_{LIM}$", fontsize=12, color=P["grey_dark"])
    ax.text(0, 5.75, "Wave height $H_s$", fontsize=14, fontweight="bold", color=P["ink"])
    ax.text(0, 5.3, "hourly hindcast", fontsize=12, color=P["grey_dark"])
    # production row
    ax.add_patch(Rectangle((xf, 2.7), xr - xf, 1.1, fc=P["red_1"], ec="none"))
    ax.plot([1.8, xf, xf, xr, xr, 12], [3.8, 3.8, 2.7, 2.7, 3.8, 3.8], color=P["ink"], lw=2.2)
    ax.text((xf + xr) / 2, 3.38, "Lost production", ha="center", fontsize=14, fontweight="bold", color=P["ink"])
    ax.text((xf + xr) / 2, 2.95, "downtime × stopped wells × well rate", ha="center", fontsize=12,
            color=P["ink"])
    ax.text(0, 3.4, "Production", fontsize=14, fontweight="bold", color=P["ink"])
    ax.text(0, 2.95, "of the stopped wells", fontsize=12, color=P["grey_dark"])
    ax.text(xr + 0.12, 3.95, "restored", fontsize=12, color=P["grey_dark"])
    ax.add_patch(FancyArrowPatch((1.8, 2.3), (12, 2.3), arrowstyle="-|>", mutation_scale=16,
                                 color=P["grey_mid"], lw=1.5))
    ax.text(12, 2.0, "time", ha="right", fontsize=12, color=P["grey_dark"])
    # intervention row
    segs = [(xf, xm, P["neutral"], "Mobilization", r"$T^{mob}$"),
            (xm, xw, P["red_2"], "Waiting on weather", r"$T^{wait}$"),
            (xw, xr, P["blue_secondary"], "Repair (lifts)", r"$T^{rep}$")]
    for a, b, col, lab, sym in segs:
        ax.add_patch(FancyBboxPatch((a + 0.03, 0.85), b - a - 0.06, 0.75, boxstyle="round,pad=0,rounding_size=0.1",
                                    fc=col, ec="black", lw=1.2, alpha=0.9))
        ax.text((a + b) / 2, 1.22, lab, ha="center", va="center", fontsize=12.5,
                color="white" if col == P["blue_secondary"] else P["ink"])
        ax.text((a + b) / 2, 0.45, sym, ha="center", va="center", fontsize=13, color=P["grey_dark"])
    ax.text(0, 1.35, "Intervention", fontsize=14, fontweight="bold", color=P["ink"])
    ax.text(0, 0.9, "vessel on hire", fontsize=12, color=P["grey_dark"])
    # event lines and downtime bracket
    for x in (xf, xr):
        ax.plot([x, x], [0.05, 6.9 if x == xf else 4.7], color=P["grey_mid"], lw=1, ls=":")
    ax.text(xf, 6.95, "Failure", ha="center", fontsize=12.5, fontweight="bold", color=P["ink"])
    ax.plot([xf, xf, xr, xr], [0.0, -0.15, -0.15, 0.0], color=P["ink"], lw=1.5)
    ax.text((xf + xr) / 2, -0.6, r"Downtime $D = T^{mob} + T^{wait} + T^{rep}$", ha="center", fontsize=14,
            fontweight="bold", color=P["ink"])
    ax.text((xf + xr) / 2, -1.05, r"repair cost = vessel day rate $\times\ D$ + spare part", ha="center",
            fontsize=12, color=P["grey_dark"])
    finalize_figure(fig, out, pad=0.5)


def main():
    apply_publication_style(FigureStyle(font_size=15, axes_linewidth=2))
    fig1_workflow(OUT / "fig1_workflow")
    fig2_scope(OUT / "fig2_failure_scope")
    fig3_downtime(OUT / "fig3_downtime")
    print(f"Saved figures 1-3 to {OUT}")


if __name__ == "__main__":
    main()
