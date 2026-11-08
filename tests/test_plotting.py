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


def test_pubstyle_finalize(tmp_path):
    import matplotlib.pyplot as plt
    from layout_rel.pubstyle import apply_publication_style, finalize_figure
    apply_publication_style()
    fig, ax = plt.subplots()
    ax.plot([0, 1], [0, 1])
    paths = finalize_figure(fig, tmp_path / "x")
    assert [p.suffix for p in paths] == [".png", ".pdf"] and all(p.exists() for p in paths)
    assert plt.rcParams["axes.spines.top"] is False
