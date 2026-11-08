from layout_rel.config import REPO_ROOT
from layout_rel.layout import load_field
from layout_rel.plotting import plot_layout


def _insets(ax):
    return [c for c in ax.child_axes]


def test_inset_only_for_long_tieback():
    sol = load_field(REPO_ROOT / "config" / "field_solveig.yaml")
    ax = plot_layout(sol, {w: "M_CEN" for w in sol.wells}, sizes={"M_CEN": 6})
    assert len(_insets(ax)) == 1                 # 18 km tie-back, wells within 5 km
    toy = load_field(REPO_ROOT / "config" / "field_toy.yaml")
    ax = plot_layout(toy, {w: "M2" for w in toy.wells}, sizes={"M2": 6})
    assert not _insets(ax)
