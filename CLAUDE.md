# Project: Reliability and Maintenance in Subsea Field Layout Optimization (Python)

## Goal
Build a subsea field layout optimization model that includes reliability and
maintenance costs, not just CAPEX, and apply it to a case study.

Core research question: does the optimal subsea layout change when failure,
repair and lost-production costs are included, and by how much?

Key idea: a manifold failure stops ALL wells connected to it; a tree failure
stops ONE well. So the way wells are grouped on manifolds changes the cost of
failures. This links reliability to layout decisions.

Working title: "Integrating Reliability and Maintenance Costs into Subsea Field
Layout Optimization"

Alternative titles:
- "Reliability-Aware Optimization of Subsea Production System Layouts"
- "Effect of Failure and Intervention Costs on Optimal Subsea Field Layout: A MILP Approach"

## Novelty angles (choose one as main focus, decide during literature review)
1. Fast expected-value reliability model inside a MILP, validated by Monte Carlo
   (shows it is both fast and accurate enough).
2. Vessel mobilization and waiting time as the main driver of downtime cost.
3. (Dropped, decision 2026-11: Tanzania vs North Sea comparison removed because too
   little is known about Tanzanian conditions. The case study is North Sea only.)

## Scope
- One field case: 6-12 wells, one host (platform or FPSO), North Sea conditions
  (vessel availability, mobilisation, weather, costs).
- Components: X-mas trees, manifolds, flowlines, umbilicals (subsea pumps optional).
- Reliability: constant failure rate (exponential model), MTTF = 1/lambda.
- Field life economics with discounting (NPV).
- Model must be computationally fast (usable inside an optimizer).

## Cases
1. CAPEX-only optimization (baseline)
2. CAPEX + expected maintenance + lost production optimization
3. Compare layouts from cases 1 and 2
4. Monte Carlo simulation of random failures to check the expected-value model
5. Sensitivity: oil/gas price, vessel day rate, failure rates (x0.5, x2),
   water depth, mobilization time

## Outputs
- Optimal layouts (plots of wells, manifolds, host, connections)
- NPV breakdown: revenue, CAPEX, OPEX, repair cost, lost production
- Expected downtime and production loss per layout
- Monte Carlo distribution vs expected-value estimate
- Sensitivity / tornado plots

## Cost model
- Expected failures per year per component = lambda
- Repair cost per failure = vessel day rate x (mobilization days + repair days)
  + spare part cost
- Downtime per failure = mobilization + waiting + repair time
- Lost production per failure = downtime x production rate of affected wells x price
- Expected yearly failure cost = sum over components of
  lambda x (repair cost + lost production)
- NPV = sum over years of discounted (revenue - OPEX - expected failure cost) - CAPEX

## Optimization model (MILP, Pyomo + HiGHS)
Decisions:
- Which candidate manifold sites to open (binary)
- Which well connects to which manifold (binary)
- Optional: redundancy choices (e.g. dual flowline) (binary)
Constraints:
- Each well connected to exactly one manifold
- Manifold slot capacity (max wells per manifold)
- Only open manifolds can receive wells
Objective:
- Case 1: minimize CAPEX
- Case 2: maximize NPV including expected failure costs
Keep the model linear where possible so it solves fast.

## Data (all public, every value must have a source)
- Failure rates: OREDA is standard but paid; use values quoted in published
  papers and theses. Record source for each value.
- Vessel day rates: light intervention vessel vs heavy-lift vessel, from
  papers and industry reports.
- Mobilization and waiting times: from literature.
- CAPEX unit costs (per manifold, per tree, per km flowline/umbilical): literature.
- Oil/gas price, discount rate, field life: own assumptions, tested in sensitivity.

## Tools
Python 3.11+, pyomo, highspy, networkx, numpy, pandas, matplotlib, pyyaml, pytest.

## Repo structure
```
subsea-layout-reliability/
├── CLAUDE.md
├── README.md
├── requirements.txt
├── config/
│   └── base_case.yaml        # all parameters with units and source
├── data/
│   ├── raw/
│   └── processed/
├── src/layout_rel/
│   ├── layout.py             # wells, manifold sites, host, distances (NetworkX)
│   ├── reliability.py        # failure rates, expected failures
│   ├── maintenance.py        # repair cost, downtime, lost production
│   ├── economics.py          # CAPEX, OPEX, NPV
│   ├── optimizer.py          # Pyomo MILP
│   ├── montecarlo.py         # random failure simulation
│   └── plotting.py           # layout and results figures
├── notebooks/
├── results/
└── tests/
```

## Work plan
1. Repo setup, environment, config file, README
2. layout.py: small made-up field (6 wells, 3 candidate manifold sites, 1 host),
   coordinates, distances, plot
3. economics.py: CAPEX model
4. optimizer.py: CAPEX-only MILP, solve and plot layout (case 1)
5. reliability.py + maintenance.py: expected failure cost per component
6. Add failure cost to optimizer, NPV objective (case 2), compare with case 1
7. montecarlo.py: random failure simulation, compare to expected-value model
8. Sensitivity analysis
9. Replace made-up field with a realistic North Sea case (published field)
10. Figures and tables for the report/paper

## Conventions
- All parameters in config YAML with value, unit and source fields.
  No hard-coded numbers in code.
- SI units internally (m, s, kg, Sm3, USD); convert only for plots and tables.
- Each module has a small pytest test.
- Fix random seeds in Monte Carlo for reproducibility.
- Commit after each working step with a clear message.
- Explain choices in plain English. I am a petroleum engineering MSc student,
  comfortable with engineering but still learning Python tooling.
- Keep explanations brief and give numbered steps when I need to do something.

## First task
Set up the repo and environment, then build layout.py and a CAPEX-only MILP
for a small made-up field (6 wells, 3 candidate manifold sites, 1 host).
Plot the optimal layout.
