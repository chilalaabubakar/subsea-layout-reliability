"""Publication figure style, after the `scientific-figure-making` skill of figures4papers
(https://github.com/ChenLiu-1996/figures4papers, scientific-figure-making/references/api.md).

Conventions (from that skill's design theory):
- sans-serif type (Arial/Helvetica, Liberation Sans as metric-compatible fallback);
- top and right spines off, thick remaining spines, frameless legends;
- semantic palette: blue = key result / reliability-aware design, red = baseline
  (CAPEX-only), green = improvement, neutral grey = background or reference;
- tight_layout(pad=2), export PNG at 300 dpi plus PDF with editable text.
Plot styling only: no model numbers live here.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

PALETTE = {
    "blue_main": "#0F4D92", "blue_secondary": "#3775BA",
    "green_1": "#DDF3DE", "green_2": "#AADCA9", "green_3": "#8BCF8B",
    "red_1": "#F6CFCB", "red_2": "#E9A6A1", "red_strong": "#B64342",
    "neutral": "#CFCECE", "highlight": "#FFD700",
    "teal": "#42949E", "violet": "#9A4D8E",
    "grey_dark": "#4D4D4D", "grey_mid": "#767676", "ink": "#272727",
}
DEFAULT_COLORS = [PALETTE[k] for k in ("blue_main", "green_3", "red_strong", "teal", "violet", "neutral")]


@dataclass(frozen=True)
class FigureStyle:
    font_size: int = 15
    axes_linewidth: float = 2.0
    use_tex: bool = False
    font_family: tuple[str, ...] = ("Arial", "Helvetica", "Liberation Sans", "DejaVu Sans", "sans-serif")


def apply_publication_style(style: FigureStyle | None = None) -> None:
    s = style or FigureStyle()
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": list(s.font_family),
        "font.size": s.font_size,
        "axes.spines.right": False,
        "axes.spines.top": False,
        "axes.linewidth": s.axes_linewidth,
        "xtick.major.width": s.axes_linewidth,
        "ytick.major.width": s.axes_linewidth,
        "legend.frameon": False,
        "svg.fonttype": "none",
        "pdf.fonttype": 42,          # TrueType in PDF: text stays editable
        "text.usetex": s.use_tex,
        "mathtext.fontset": "dejavusans",
    })


def finalize_figure(fig, out_path: str | Path, formats=("png", "pdf"), dpi: int = 300,
                    close: bool = True, pad: float = 2.0) -> list[Path]:
    """tight_layout(pad) and save to every format; returns the saved paths."""
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout(pad=pad)
    saved = []
    for fmt in formats:
        p = out.with_suffix("." + fmt)
        fig.savefig(p, dpi=dpi, facecolor="white")
        saved.append(p)
    if close:
        plt.close(fig)
    return saved
