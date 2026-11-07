# Literature notes: positioning of this project

## Closest prior work: Silva & Guedes Soares (2025), Ocean Engineering 324, 120668

A MILP that chooses wells-to-manifold/platform assignment, manifold slot size, platform size and
rigid vs. flexible pipe, minimising infrastructure cost + "expected loss" from manifold and pipeline
failures. This is the paper the project must be compared against.

How their failure cost is modelled (Eqs. 40-43):

- Manifold: `elm = (manifold flow) x (oil price) x DF x FR_m`, with DF = "number of days until manifold
  failure" and FR_m = OREDA 2022 manifold failure rate. Pipelines: `flow x price x days/year x failure frequency`.
- Flow is the **plateau** rate (a "worst-case" robust scenario), not a production profile.
- One manifold failure rate for all slot sizes (stated as their main limitation, Sec. 6).

What our model adds (gaps we can claim, checked against the paper text):

1. **Downtime from intervention logistics**: lost production = (mobilisation + waiting + repair time) x
   rate of affected wells. Silva has no vessel, mobilisation or repair-time terms. This is novelty angle 2
   in CLAUDE.md, and Bai & Bai Fig. 6-17 (T_RA + T_AR) supports the structure.
2. **Repair cost** (vessel day rate x days + spare part). Silva counts lost production only.
3. **Tree failures** (one well stops) next to manifold failures (all its wells stop), so the trade-off of
   grouping is explicit. Silva does not model trees.
4. **Field-life NPV with discounting** and a production profile, instead of an undiscounted plateau loss.
5. **Monte Carlo validation** of the expected-value approximation (novelty angle 1). Silva has none.
6. Possibly: failure rate as a function of slot count (Silva's own suggested future work), e.g. rate
   scaled by number of slots or valves.

Supporting citations:

- Bai & Bai (2010) p. 22: clustering saves flowlines and vessel mobilisation, but "workover operations on one
  well of the cluster may interrupt production from others".
- Bai & Bai (2010) Sec. 6.8.2, Eq. 6-12: RAMEX = repair cost + lost production; Fig. 6-17 downtime structure.
- Sales, Stanko & Jäschke (2023): reliability as a fixed uptime penalty per equipment item, independent of
  well grouping; authors call for better downtime/MTTF data.
- Liu et al. (2024): manifold weak points (control valves, insulation, pigging, isolation valves).
- Østebø et al. (2001): reliability in a life-cycle-cost perspective (CAPEX + OPEX + regularity loss).
