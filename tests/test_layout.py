import math

from layout_rel.layout import build_field


def test_toy_field_size(field):
    assert len(field.wells) == 6
    assert len(field.sites) == 3
    # candidate edges: every well-site pair + every site-host pair
    assert field.graph.number_of_edges() == 6 * 3 + 3


def test_distances():
    data = {
        "host": {"name": "H", "x": 0.0, "y": 0.0},
        "wells": [{"name": "W", "x": 3000.0, "y": 4000.0}],
        "manifold_sites": [{"name": "M", "x": 0.0, "y": 4000.0}],
    }
    f = build_field(data)
    assert math.isclose(f.length("W", "M"), 3000.0)
    assert math.isclose(f.length("M", "H"), 4000.0)
    f2 = build_field(data, length_factor=1.1)
    assert math.isclose(f2.length("M", "H"), 4400.0)


def test_solveig_field_from_sodir():
    from layout_rel.config import CONFIG_DIR, field_path, load_config
    from layout_rel.layout import load_field
    f = load_field(field_path(load_config(CONFIG_DIR / "solveig_case.yaml")))
    assert len(f.wells) == 6 and len(f.sites) == 4
    assert 18_000 < f.length("M_ACT", f.host) < 19_500        # tie-back to Edvard Grieg ~18.7 km


def test_display_labels():
    from layout_rel.layout import load_field
    from layout_rel.config import REPO_ROOT
    f = load_field(REPO_ROOT / "config" / "field_solveig.yaml")
    assert f.label("M_ACT") == "$M_1$" and f.label("M_CEN") == "$M_4$"
    assert f.label("W_BA1") == "BA-1" and f.label("EDVARD_GRIEG") == "Edvard Grieg"
    toy = load_field(REPO_ROOT / "config" / "field_toy.yaml")
    assert toy.label("M2") == "$M_2$"
