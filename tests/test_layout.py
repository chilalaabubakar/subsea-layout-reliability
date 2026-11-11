import math

from layout_rel.layout import build_field


def test_toy_field_size(field):
    assert len(field.wells) == 6
    assert len(field.sites) == 3
    # candidate edges: every well-site pair + every site-host pair + every site-site pair (daisy chain)
    assert field.graph.number_of_edges() == 6 * 3 + 3 + 3
    kinds = [d["kind"] for _, _, d in field.graph.edges(data=True)]
    assert kinds.count("infield") == 18 and kinds.count("tieback") == 3 and kinds.count("link") == 3


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


def _vincenty(lat1, lon1, lat2, lon2, a=6378388.0, f=1 / 297.0):
    """Geodesic distance [m] on an ellipsoid (Vincenty inverse formula)."""
    import math
    b = a * (1 - f)
    L = math.radians(lon2 - lon1)
    U1, U2 = math.atan((1 - f) * math.tan(math.radians(lat1))), math.atan((1 - f) * math.tan(math.radians(lat2)))
    sU1, cU1, sU2, cU2 = math.sin(U1), math.cos(U1), math.sin(U2), math.cos(U2)
    lam = L
    for _ in range(200):
        sl, cl = math.sin(lam), math.cos(lam)
        ss = math.hypot(cU2 * sl, cU1 * sU2 - sU1 * cU2 * cl)
        cs = sU1 * sU2 + cU1 * cU2 * cl
        sig = math.atan2(ss, cs)
        sa = cU1 * cU2 * sl / ss
        c2a = 1 - sa * sa
        c2sm = cs - 2 * sU1 * sU2 / c2a
        C = f / 16 * c2a * (4 + f * (4 - 3 * c2a))
        lam_new = L + (1 - C) * f * sa * (sig + C * ss * (c2sm + C * cs * (-1 + 2 * c2sm ** 2)))
        if abs(lam_new - lam) < 1e-12:
            break
        lam = lam_new
    u2 = c2a * (a * a - b * b) / (b * b)
    A = 1 + u2 / 16384 * (4096 + u2 * (-768 + u2 * (320 - 175 * u2)))
    B = u2 / 1024 * (256 + u2 * (-128 + u2 * (74 - 47 * u2)))
    ds = B * ss * (c2sm + B / 4 * (cs * (-1 + 2 * c2sm ** 2) - B / 6 * c2sm * (-3 + 4 * ss ** 2) * (-3 + 4 * c2sm ** 2)))
    return b * A * (sig - ds)


def test_solveig_projection_matches_geodesic():
    """Local x/y distances agree with the ED50 ellipsoidal geodesic to < 0.01 % (incl. the 18.7 km tie-back)."""
    import importlib.util
    import math
    import pandas as pd
    from layout_rel.config import REPO_ROOT
    spec = importlib.util.spec_from_file_location("ps", REPO_ROOT / "scripts" / "prepare_solveig.py")
    ps = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ps)
    fac = ps.latlon(pd.read_csv(ps.RAW / "facility_fixed.csv", encoding="utf-8-sig", low_memory=False))
    f = fac[(fac.fclBelongsToName.astype(str).str.upper() == "SOLVEIG") | (fac.fclName.str.upper() == "EDVARD GRIEG")]
    ref = f[f.fclName.str.upper().str.contains("MANIFOLD")].iloc[0]
    rx, ry = ps.local_scale(ref.lat)
    for r in f.itertuples():
        if abs(r.lat - ref.lat) + abs(r.lon - ref.lon) < 1e-6:
            continue
        d_geo = _vincenty(ref.lat, ref.lon, r.lat, r.lon)
        d_xy = math.hypot(math.radians(r.lon - ref.lon) * rx, math.radians(r.lat - ref.lat) * ry)
        assert abs(d_xy / d_geo - 1) < 1e-4, (r.fclName, d_xy, d_geo)


def test_synthetic_field_is_reproducible_and_complete():
    from layout_rel.synthetic import synthetic_field
    a = synthetic_field(12, 6, 4000.0, 15000.0, seed=3)
    b = synthetic_field(12, 6, 4000.0, 15000.0, seed=3)
    assert len(a.wells) == 12 and len(a.sites) == 6
    assert all(a.pos(n) == b.pos(n) for n in a.wells + a.sites)
    assert all(0 <= a.pos(s)[0] <= 4000 and 0 <= a.pos(s)[1] <= 4000 for s in a.sites)   # centres of well clusters
    assert a.length(a.sites[0], a.host) > 0
