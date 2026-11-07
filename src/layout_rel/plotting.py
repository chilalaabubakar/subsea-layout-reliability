"""Figures: field layout maps (and later: NPV breakdowns, MC histograms, tornados)."""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")  # file output only; no display needed
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

from .layout import Field

# Palette (validated categorical slots 1-3 + neutral ink). Plot styling only.
C_WELL = "#2a78d6"
C_MANIFOLD = "#eb6834"
C_HOST = "#1baf7a"
C_INK = "#0b0b0b"
C_INK_2 = "#52514e"
C_MUTED = "#a3a29c"
C_GRID = "#e6e5e1"
M_PER_KM = 1000.0


def _km(p):
    return p[0] / M_PER_KM, p[1] / M_PER_KM


def plot_layout(field: Field, assignment: dict[str, str] | None = None,
                title: str = "", ax=None, show_candidates: bool = True):
    """Plot wells, manifold sites, host and (optionally) the chosen connections."""
    if ax is None:
        _, ax = plt.subplots(figsize=(7, 7))
    assignment = assignment or {}
    open_sites = sorted(set(assignment.values()))

    # connections first, so markers sit on top
    for s in open_sites:
        (x0, y0), (x1, y1) = _km(field.pos(s)), _km(field.pos(field.host))
        ax.plot([x0, x1], [y0, y1], color=C_INK, lw=2.0, zorder=1,
                solid_capstyle="round")
    for w, s in assignment.items():
        (x0, y0), (x1, y1) = _km(field.pos(w)), _km(field.pos(s))
        ax.plot([x0, x1], [y0, y1], color=C_INK_2, lw=1.2, zorder=1,
                solid_capstyle="round")

    ring = dict(markeredgecolor="white", markeredgewidth=1.5)
    for w in field.wells:
        x, y = _km(field.pos(w))
        ax.plot(x, y, "^", ms=11, color=C_WELL, zorder=3, **ring)
        ax.annotate(w, (x, y), xytext=(7, -13), textcoords="offset points",
                    color=C_INK, fontsize=9)
    for s in field.sites:
        x, y = _km(field.pos(s))
        if s in open_sites:
            ax.plot(x, y, "s", ms=12, color=C_MANIFOLD, zorder=3, **ring)
        elif show_candidates:
            ax.plot(x, y, "s", ms=11, mfc="none", mec=C_MUTED, mew=1.5, zorder=2)
        ax.annotate(s, (x, y), xytext=(8, 7), textcoords="offset points",
                    color=C_INK if s in open_sites else C_INK_2, fontsize=9)
    hx, hy = _km(field.pos(field.host))
    ax.plot(hx, hy, "*", ms=18, color=C_HOST, zorder=3, **ring)
    htype = field.graph.nodes[field.host].get("host_type", "")
    ax.annotate(f"{field.host} ({htype})" if htype else field.host, (hx, hy),
                xytext=(10, -3), textcoords="offset points", color=C_INK, fontsize=9)

    handles = [
        Line2D([], [], marker="^", ls="", color=C_WELL, ms=9, label="Well (X-mas tree)"),
        Line2D([], [], marker="s", ls="", color=C_MANIFOLD, ms=9, label="Manifold (open)"),
        Line2D([], [], marker="*", ls="", color=C_HOST, ms=13, label="Host"),
        Line2D([], [], color=C_INK_2, lw=1.2, label="Infield flowline + umbilical"),
        Line2D([], [], color=C_INK, lw=2.0, label="Tie-back flowline + umbilical"),
    ]
    if show_candidates and len(open_sites) < len(field.sites):
        handles.insert(2, Line2D([], [], marker="s", ls="", mfc="none", mec=C_MUTED,
                                 mew=1.5, ms=9, label="Candidate site (not used)"))
    ax.legend(handles=handles, loc="upper left", bbox_to_anchor=(1.02, 1.0),
              frameon=False, fontsize=9, labelcolor=C_INK_2)

    ax.set_aspect("equal", adjustable="datalim")
    ax.set_xlabel("Easting [km]", color=C_INK_2)
    ax.set_ylabel("Northing [km]", color=C_INK_2)
    ax.tick_params(colors=C_INK_2)
    ax.grid(True, color=C_GRID, lw=0.8)
    ax.set_axisbelow(True)
    for sp in ax.spines.values():
        sp.set_color(C_GRID)
    if title:
        ax.set_title(title, loc="left", color=C_INK, fontsize=11)
    return ax
