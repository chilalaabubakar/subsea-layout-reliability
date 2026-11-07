# Subsea layout optimization with reliability and maintenance costs

MSc research code. It asks: **does the optimal subsea field layout change when
failure, repair and lost-production costs are included, and by how much?**

The key idea: a manifold failure stops *all* wells tied in to that manifold, but a tree
failure stops only *one* well. So the way wells are grouped on manifolds changes the
expected cost of failures. See `CLAUDE.md` for the full project brief and work plan.

## Status

| Step | What | Status |
|---|---|---|
| 1 | Repo, environment, config, README | done |
| 2 | `layout.py`: toy field (6 wells, 3 sites, 1 host) | done |
| 3 | `economics.py`: CAPEX model | done |
| 4 | `optimizer.py`: CAPEX-only MILP (case 1) | done |
| 5 | `reliability.py` + `maintenance.py`: expected failure cost per component | done |
| 6 | Failure cost in the MILP, NPV objective (cases 2-3) | done |
| 7 | Monte Carlo check + risk-averse (CVaR) layouts | done |
| 8 | Sensitivity analysis | next |
| 9-10 | Realistic North Sea case, figures | to do |

> Cost data: lines from Kaiser (2016); trees, manifolds and vessel rates from Bai & Bai (2010) Ch. 6.
> Details, page numbers and ranges are in `docs/sources.md`. Costs are not yet escalated to one year.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -e .                 # makes `import layout_rel` work everywhere
```

## Run

```bash
python scripts/run_case1.py         # case 1: CAPEX-only optimal layout
python scripts/run_failure_cost.py  # step 5: expected yearly failure cost of candidate layouts
python scripts/run_case2.py         # cases 2-3: NPV-optimal layout incl. failures vs case 1
python scripts/run_step7.py         # step 7: Monte Carlo check of the EV model, CVaR layouts (~1 min)
pytest                           # run the tests
```

Outputs go to `results/` (`case1_layout.png`, `case1_capex.csv`).

## Model (case 1)

Decision variables: `size[s,k]` (install a *k*-slot manifold at candidate site *s*,
k in 2/4/6/8) and `assign[w,s]` (tie in well *w* to site *s*), both binary.

Constraints: at most one manifold per site, each well goes to exactly one manifold,
a manifold holds at most *k* wells, and wells can only go to open sites.

Objective: minimise CAPEX = trees + manifolds (cost depends on slot count) + infield
lines (well to manifold, cost per m times length) + tie-back lines (manifold to host).
Solved with HiGHS through Pyomo.

## Layout of the repo

```
config/          parameters (value, unit, source) and field geometry
src/layout_rel/  model code (config, layout, economics, optimizer, plotting)
scripts/         runnable case studies
tests/           pytest tests (MILP is checked against brute-force enumeration)
results/         figures and tables
```

## Failure cost model (step 5)

Each component of a layout is a failure mode with a constant rate (OREDA / DNV GL data, see
`docs/sources.md`): X-mas tree (incl. SCM) and infield flowline stop one well; manifold,
tie-back flowline and tie-back umbilical stop every well on that manifold. Per failure:
downtime = vessel mobilisation + repair days x (1 + weather allowance); repair cost =
day rate x downtime + spare part; lost production = downtime x rate of the stopped wells x oil
price. Expected yearly cost = sum of rate x (repair cost + lost production).
`maintenance.failure_cost_coefficients` gives the same cost in linear form for the MILP.

## NPV model (case 2)

NPV = PV(revenue) - CAPEX - PV(OPEX) - PV(expected failure cost), CAPEX at t = 0, production
years 1..N with a plateau then exponential decline, discount rate r. Lost production is treated
as lost (not deferred). The manifold failure rate grows with slot count k:
rate(k) = rate_ref x ((1 - f) + f x k / 4), with f = 0.493 (share of slot-related valves and
couplers in Liu et al. 2024). Without this, expected lost production would not depend on how
wells are grouped. The product assign x size is linearised with z >= assign + size - 1.

## Monte Carlo and risk (step 7)

`montecarlo.simulate_layout` draws Poisson failure times over field life for a fixed layout,
merges overlapping outages of the same well and cuts them at end of life, then applies the same
discounting as the EV model. `montecarlo.sample_scenarios` writes sampled scenarios in the
linear MILP form; `optimize_npv(..., risk_weight=rho)` then minimises
(1 - rho) E[failure cost] + rho CVaR_alpha[failure cost] (Rockafellar-Uryasev LP form).
Seeds are fixed in the config.

## Conventions

- Every parameter is in YAML with `value`, `unit` and `source`. No numbers hard-coded in the code.
- Values in YAML are written in the source's units; the first word of `unit` (e.g. `days`, `1/h`,
  `bbl/day`) is converted to SI (m, s, Sm3, USD) by `config.param` (see `units.py`).
