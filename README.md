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
| 5 | `reliability.py` + `maintenance.py` | next |
| 6-10 | NPV objective, Monte Carlo, sensitivity, realistic case, figures | to do |

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
python scripts/run_case1.py      # case 1: CAPEX-only optimal layout
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

## Conventions

- Every parameter is in YAML with `value`, `unit` and `source`. No numbers hard-coded in the code.
- SI units inside the code (m, s, USD). Units are converted only for plots and tables.
