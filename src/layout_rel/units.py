"""Unit conversion to SI (m, s, Sm3, USD).

Config values are written in the units the sources use (hours, days, years,
bbl, km). The first word of a parameter's ``unit`` field says which unit it is;
``config.param`` multiplies by the factor below, so model code only sees SI.
"""
from __future__ import annotations

HOUR = 3600.0                   # s
DAY = 86400.0                   # s
YEAR = 365.25 * DAY             # s (Julian year)
KM = 1000.0                     # m
BBL = 0.158987294928            # m3 (oil barrel)

# first word of `unit` -> factor to SI
TO_SI: dict[str, float] = {
    # dimensionless / already SI / labels
    "-": 1.0, "USD": 1.0, "USD/m": 1.0, "m": 1.0, "s": 1.0, "slots": 1.0, "key": 1.0,
    # time
    "h": HOUR, "days": DAY, "yr": YEAR,
    # rates (failures per time)
    "1/h": 1.0 / HOUR, "1/yr": 1.0 / YEAR, "1/(km*yr)": 1.0 / (KM * YEAR),
    # money per time / per volume
    "USD/day": 1.0 / DAY, "USD/bbl": 1.0 / BBL,
    # flow
    "bbl/day": BBL / DAY, "Sm3/day": 1.0 / DAY,
    # fraction
    "fraction": 1.0,
}


def unit_token(unit: str) -> str:
    return str(unit).split()[0] if str(unit).strip() else ""


def si_factor(unit: str) -> float:
    tok = unit_token(unit)
    if tok not in TO_SI:
        raise KeyError(f"Unknown unit '{tok}' (from '{unit}'); add it to units.TO_SI")
    return TO_SI[tok]
