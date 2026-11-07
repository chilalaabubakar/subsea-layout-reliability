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
