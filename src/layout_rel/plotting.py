"""Figures: field layout maps (and later: NPV breakdowns, MC histograms, tornados)."""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")  # file output only; no display needed
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

from .layout import Field


def layout_text(field: Field, assignment: dict[str, str], sizes: dict[str, int]) -> str:
    """Short figure label of a layout, e.g. "$M_1$ (4 slots) + $M_3$ (2 slots)"."""
    return " + ".join(f"{field.label(s)} ({sizes[s]} slots)" for s in sorted(sizes))

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


INSET_RATIO = 0.3   # draw a zoomed inset when the well cluster spans < 30 % of the map


def _cluster_box(field: Field, pad_km: float = 0.8) -> tuple[float, float, float, float]:
    """Box around wells and sites [km]; extra room left and right for labels."""
    pts = [_km(field.pos(n)) for n in field.wells + field.sites]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return (min(xs) - 1.5 * pad_km, max(xs) + 1.5 * pad_km,
            min(ys) - pad_km, max(ys) + pad_km)


_COMPASS = {"E": (1.0, 0.0), "NE": (0.7071, 0.7071), "N": (0.0, 1.0), "NW": (-0.7071, 0.7071),
            "W": (-1.0, 0.0), "SW": (-0.7071, -0.7071), "S": (0.0, -1.0), "SE": (0.7071, -0.7071)}
_DIRS = [(1.0, 0.0), (0.7071, 0.7071), (0.0, 1.0), (-0.7071, 0.7071),
         (-1.0, 0.0), (-0.7071, -0.7071), (0.0, -1.0), (0.7071, -0.7071)]


class _Placer:
    """Picks a label direction per node: the one whose label point is farthest from
    the nodes, the lines' end points and the labels already placed (greedy)."""

    def __init__(self, points: list[tuple[float, float]], r_km: float):
        self.occupied = list(points)
        self.r = r_km

    def __call__(self, p: tuple[float, float], avoid=(), fixed: str = "") -> tuple[float, float]:
        import math
        if fixed:                              # direction set in the field file
            u = _COMPASS[fixed.upper()]
            self.occupied.append((p[0] + u[0] * self.r, p[1] + u[1] * self.r))
            return u
        best, best_d = _DIRS[1], -1.0
        for u in _DIRS:
            if u in avoid:
                continue
            q = (p[0] + u[0] * self.r, p[1] + u[1] * self.r)
            d = min((math.hypot(q[0] - o[0], q[1] - o[1]) for o in self.occupied), default=1e9)
            d += 0.05 * self.r * u[0]          # small preference for labels to the right
            if d > best_d:
                best, best_d = u, d
        self.occupied.append((p[0] + best[0] * self.r, p[1] + best[1] * self.r))
        return best


def _label(ax, text: str, xy, u: tuple[float, float], color: str, fs: float) -> None:
    """Annotate ``xy`` with text placed 12 pt away in direction ``u``."""
    ux, uy = u
    ax.annotate(text, xy, xytext=(12 * ux, 12 * uy), textcoords="offset points",
                ha="left" if ux > 0.3 else "right" if ux < -0.3 else "center",
                va="bottom" if uy > 0.3 else "top" if uy < -0.3 else "center",
                color=color, fontsize=fs)


def _draw(ax, field: Field, assignment: dict[str, str], sizes, show_candidates: bool,
          labels: bool, fs: float = 9, r_km: float = 1.0, frame=None) -> None:
    """Lines and markers of one layout; node labels only if ``labels``.

    ``r_km``: label distance from its node in data units, used to keep labels apart.
    ``frame``: (x0, x1, y0, y1) of the view; labels keep clear of its edges.
    """
    open_sites = sorted(set(assignment.values()))
    pts = [_km(field.pos(n)) for n in field.wells + field.sites]
    for s in open_sites:                       # points along the tie-backs, so labels avoid them
        (x0, y0), (x1, y1) = _km(field.pos(s)), _km(field.pos(field.host))
        pts += [(x0 + (x1 - x0) * t / 200, y0 + (y1 - y0) * t / 200) for t in range(1, 200)]
    for w, s in assignment.items():
        (x0, y0), (x1, y1) = _km(field.pos(w)), _km(field.pos(s))
        pts += [(x0 + (x1 - x0) * t / 4, y0 + (y1 - y0) * t / 4) for t in range(1, 4)]
    if frame:
        fx0, fx1, fy0, fy1 = frame
        pts += [(fx0 + (fx1 - fx0) * t / 40, fy) for t in range(41) for fy in (fy0, fy1)]
        pts += [(fx, fy0 + (fy1 - fy0) * t / 40) for t in range(41) for fx in (fx0, fx1)]
    place = _Placer(pts, r_km)
    for s in open_sites:                       # connections first, so markers sit on top
        (x0, y0), (x1, y1) = _km(field.pos(s)), _km(field.pos(field.host))
        ax.plot([x0, x1], [y0, y1], color=C_INK, lw=2.0, zorder=1, solid_capstyle="round")
    for w, s in assignment.items():
        (x0, y0), (x1, y1) = _km(field.pos(w)), _km(field.pos(s))
        ax.plot([x0, x1], [y0, y1], color=C_INK_2, lw=1.2, zorder=1, solid_capstyle="round")

    ring = dict(markeredgecolor="white", markeredgewidth=1.5)
    placed: dict[tuple[float, float], tuple[float, float]] = {}
    at_pos: dict[tuple[float, float], list[str]] = {}       # wells on one template share a label
    fixed: dict[tuple[float, float], str] = {}
    for w in field.wells:
        at_pos.setdefault(field.pos(w), []).append(field.label(w))
        if field.graph.nodes[w].get("label_dir"):
            fixed[field.pos(w)] = field.graph.nodes[w]["label_dir"]
    for p, names in at_pos.items():
        x, y = _km(p)
        ax.plot(x, y, "^", ms=11, color=C_WELL, zorder=3, **ring)
        if labels:
            u = place((x, y), fixed=fixed.get(p, ""))
            _label(ax, ", ".join(names), (x, y), u, C_INK, fs)
            placed[p] = u
    for s in field.sites:
        x, y = _km(field.pos(s))
        if s in open_sites:
            ax.plot(x, y, "s", ms=12, color=C_MANIFOLD, zorder=3, **ring)
        elif show_candidates:
            ax.plot(x, y, "s", ms=11, mfc="none", mec=C_MUTED, mew=1.5, zorder=2)
        if labels:
            label = (f"{field.label(s)}, {sizes[s]} slots" if sizes and s in sizes
                     else field.label(s))
            u = place((x, y), avoid=[placed.get(field.pos(s))],
                      fixed=field.graph.nodes[s].get("label_dir", ""))
            _label(ax, label, (x, y), u, C_INK if s in open_sites else C_INK_2, fs)
    hx, hy = _km(field.pos(field.host))
    ax.plot(hx, hy, "*", ms=18, color=C_HOST, zorder=3, **ring)


def _style(ax) -> None:
    ax.tick_params(colors=C_INK_2)
    ax.grid(True, color=C_GRID, lw=0.8)
    ax.set_axisbelow(True)
    for sp in ax.spines.values():
        sp.set_color(C_GRID)


def plot_layout(field: Field, assignment: dict[str, str] | None = None,
                title: str = "", ax=None, show_candidates: bool = True,
                sizes: dict[str, int] | None = None, inset: bool | None = None):
    """Plot wells, manifold sites, host and (optionally) the chosen connections.

    ``inset``: draw a zoomed inset of the wells and manifold sites, with their labels
    there instead of on the main map. None = automatic (when the cluster is small
    compared with the distance to the host, as for a long tie-back).
    """
    if ax is None:
        _, ax = plt.subplots(figsize=(7, 7))
    assignment = assignment or {}
    open_sites = sorted(set(assignment.values()))
    x0, x1, y0, y1 = _cluster_box(field)
    hx, hy = _km(field.pos(field.host))
    bx0, bx1, by0, by1 = _cluster_box(field, pad_km=0.0)
    span = max(bx1 - bx0, by1 - by0)
    total = max(abs(hx - (x0 + x1) / 2), abs(hy - (y0 + y1) / 2)) + span / 2
    if inset is None:
        inset = span < INSET_RATIO * total

    _draw(ax, field, assignment, sizes, show_candidates, labels=not inset, r_km=0.07 * total)
    htype = field.graph.nodes[field.host].get("host_type", "")
    hname = field.label(field.host)
    ax.annotate(f"{hname} ({htype})" if htype else hname, (hx, hy),
                xytext=(10, -3), textcoords="offset points", color=C_INK, fontsize=9)
    if inset:
        # put the inset on the side of the map away from the tie-backs
        # the tie-back runs from the wells to the host; the lower corner on the far side
        # from the host's direction stays empty
        right = hx <= (x0 + x1) / 2 + 2 * (x1 - x0)
        axin = ax.inset_axes([0.64, 0.06, 0.35, 0.56] if right else [0.01, 0.06, 0.35, 0.56])
        axin.set_facecolor("white")
        _draw(axin, field, assignment, sizes, show_candidates, labels=True, fs=8,
              r_km=0.09 * span, frame=(x0, x1, y0, y1))
        axin.set_xlim(x0, x1)
        axin.set_ylim(y0, y1)
        axin.set_aspect("equal", adjustable="box")
        axin.tick_params(labelsize=7)
        _style(axin)
        for sp in axin.spines.values():
            sp.set_color(C_INK_2)
        axin.set_title("Well area (zoom)", loc="left", fontsize=8, color=C_INK_2)
        ax.indicate_inset_zoom(axin, edgecolor=C_INK_2)

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
    _style(ax)
    if title:
        ax.set_title(title, loc="left", color=C_INK, fontsize=11)
    return ax
