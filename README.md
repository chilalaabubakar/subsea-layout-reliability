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

> **CAPEX values in `config/base_case.yaml` are placeholders** (rough orders of
> magnitude, no source yet). Replace them with cited literature values before
> reporting any result. List the parameters that still need a source with:
> `python -m layout_rel.config`

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

Decision variables: `open[s]` (install a manifold at candidate site *s*) and
`assign[w,s]` (tie in well *w* to site *s*), both binary.

Constraints: each well goes to exactly one manifold, a manifold holds at most
`manifold.slots` wells, and wells can only go to open sites.

Objective: minimise CAPEX = trees + manifolds + infield lines (well to manifold,
cost per m times length) + tie-back lines (manifold to host, cost per m times length).
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
