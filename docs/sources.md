# Data sources log

One entry per source used in `config/`. Include the exact table/page and any conversion.

## Kaiser (2016): installed flowline and umbilical cost

Kaiser, M.J. (2016). A review of deepwater pipeline construction in the U.S. Gulf of
Mexico: contracts, cost, and installation methods. *Journal of Marine Science and
Application* 15(3), 288-306. https://doi.org/10.1007/s11804-016-1373-7
(open access: https://html.rhhz.net/jmsa/html/20160308.html)

- Table 2, GoM average pipeline cost by project type, 1979-2015, in 2014 USD (MMUSD/mi):

  | Type | OTC/SPE | Press release | All |
  |---|---|---|---|
  | Export | 1.96 | 3.79 | 2.67 |
  | Infield | 3.50 | 3.84 | 3.61 |
  | All | 2.76 | 3.68 | 3.11 |

  Standard deviations are about the size of the means. The distribution is roughly log-normal.
- Sec. 4.2: infield unit cost = (flowline + umbilical cost) / (flowline + umbilical mileage).
  So the figure is the cost **per mile of each line**, and a route with one flowline and one
  umbilical costs about 2 x 3.61 MMUSD/mi.
- Used: 3.61e6 / 1609.344 = **2243 USD/m** for infield and tie-back flowlines and umbilicals.
- Limitations: Gulf of Mexico data only; no split by diameter or between flowline and umbilical;
  2014 USD (not yet escalated). Contract costs include risers, PLETs and jumpers.
- Range for sensitivity: the majority of projects are 1-6 MMUSD/mi (Sec. 5).

## Sales, Stanko & Jäschke (2023): checked, no tree/manifold costs

Sales, L., Stanko, M., Jäschke, J. (2023). Superstructure optimization of subsea processing
layouts. *J. Petrol. Explor. Prod. Technol.* 13, 1575-1589. https://doi.org/10.1007/s13202-023-01624-3
(open access, CC BY 4.0)

- Table A.1 (from Krogstad 2018, originally Bai & Bai 2010): flowline/riser **basic** cost
  Cb (10^6 USD/km), size factor fs, coating Ccoat; Eq. 57: C = (Cb*fs + Ccoat)*L.
  10-in rigid multiphase flowline: (0.230*1.00 + 0.360) = 0.59 MUSD/km. This is far below
  Kaiser's 2.24 MUSD/km installed, which suggests it excludes installation. **Not used**;
  keep only as a cross-check / low end.
- Table C.1: f_inst = 4.208, f_sub = 3, f_I = 1.1035 (applied to processing equipment, not pipes);
  oil price 57.30 USD/bbl, r = 10 %, 8000 h/yr base operating time.
- **Reliability (relevant to steps 5-6 and the literature review):** Eqs. 4-6 reduce annual
  uptime by a fixed "reliability penalty" per installed equipment (e.g. compressor 0.030,
  multiphase pump 0.060, flowlines 0.001), "chosen based on engineering insight". The penalty
  does **not** depend on which wells are connected to the equipment. The authors say
  downtime, MTTF and maintenance cost data should be improved (Conclusions). This is the gap
  this project fills: failure cost that depends on how wells are grouped on manifolds.
- No X-mas tree, manifold or umbilical cost.

## Krogstad (2018) NTNU MSc thesis: checked, no tree/manifold costs

Krogstad, D.S. (2018). Superstructure optimization of early stage offshore oil field
development. MSc thesis, NTNU.
https://jaschke.folk.ntnu.no/Masters/MasterTheses/2018/Krogstad/masterDagKrogstad.pdf

- Table 3.3 is the same pipe cost data, in USD/m, cited to Bai, Y. *Subsea Engineering
  Handbook* (Elsevier, 2010), ref. [32].
- Multiphase pump: about 3 MUSD fixed cost excluding installation (ACES database; DNV 2001
  report gives 1-3 MUSD), Sec. 3.2.5. Useful if subsea pumps are added later.

## Bai & Bai (2010), Chapters 1-2 only: no cost numbers

Bai, Y., Bai, Q. (2010). *Subsea Engineering Handbook*. Gulf Professional Publishing
(Elsevier). ISBN 978-1-85617-689-7.

The uploaded excerpt covers front matter and Chapters 1-2 (book pp. 1-50). It has no unit costs.
Useful qualitative points:

- p. 22, Sec. 1.4.4 (satellite vs clustered wells): clustered systems need fewer flowlines and
  umbilicals, and let one service-vessel deployment service several wells, "thereby saving
  mobilization costs". But "drilling or workover operations on one well of the cluster may
  interrupt production from others". This supports the project's premise that well grouping
  changes both CAPEX and failure/intervention cost.
- pp. 11-12, Sec. 1.2.5: subsea cost is "relatively flat with increasing water depth"; cost
  estimates are covered in **Chapter 6**.
- p. 11: Chapter 5 reviews installation vessels (possible source of vessel types and day rates).

## Bai & Bai (2010), Chapter 6 "Subsea Cost Estimation" (pp. 159-192): used for trees, manifolds, vessels

Same book as above. Cost data are in 2009 USD unless stated (p. 166). Escalate with Eq. 6-5.

Used in `config/base_case.yaml`:

| Parameter | Value | Where |
|---|---|---|
| Tree procurement | C0 2.75 MUSD (2.50-3.00) + Cmisc 0.20 (0.10-0.30) = 2.95 MUSD | p. 174, Eq. 6-6; 5-in, 10 ksi, VXT |
| Tree SIT | 0.20 MUSD (0.10-0.30) | Table 6-2 |
| Tree install | 3 days (2-4) on MODU > 1500 m, 950k USD/day (750-1050k) | p. 182, Table 6-3, Table 6-6 |
| Manifold procurement | C0 3.0 MUSD (2.0-4.0) x slot factor + Cmisc 0.25 (0.15-0.35) | p. 176-177, Eq. 6-7; 4-slot cluster, 10-in, 10 ksi |
| Slot factor (avg) | 2: 0.70, 4: 1.00, 6: 1.30, 8: 1.50, 10: 2.00 | p. 176 |
| Manifold SIT | 0.20 MUSD (0.15-0.25) | Table 6-2 |
| Manifold foundation | 1.0 MUSD suction pile (2007 data) | Table 6-6 |
| Manifold install | 2 days (1-3) on HLV, 400k USD/day (250-550k) | Table 6-4, Table 6-3 |

Resulting installed unit costs: tree 6.0 MUSD; manifold 2-slot 5.25, 4-slot 6.15, 6-slot 7.05, 8-slot 7.65 MUSD.

Cross-check of the line cost (Kaiser 2016): Table 6-6 (2007 GoM example) gives flowline procurement 4.74 MUSD
+ pipe-lay 43.14 MUSD for 52,026 ft (15.86 km) of dual 10-in flowline, about 3.0 MUSD/km of route (1.5 per line),
and umbilical procurement 11.6 MUSD for 25,000 ft (7.62 km), about 1.5 MUSD/km before installation. This is the
same order as Kaiser's 2.24 MUSD/km per line.

Not yet applied (Fig. 6-18 CAPEX steps): tax/transport/spares +2-4 % each, testing 5-10 %, weather allowance
+20-30 % on installation, engineering/PM 5-8 %, insurance 7-11 %, contingency 10-20 %. A uniform factor on all
costs does not change the optimal layout, but it does change the CAPEX vs. failure-cost balance in case 2.

**For step 5 (reliability/maintenance):**

- Table 6-3 vessel day rates (USD/day, min/avg/max): MSV 40k/80k/120k; ROV 35k/50k/65k;
  OSV 20k/30k/40k; HLV 250k/400k/550k; MODU > 1500 m 750k/950k/1050k; pipelay deepwater 800k/1000k/1200k.
- p. 181: mob/demob "from a few hundred thousand dollars to several million dollars".
- Sec. 6.8.2 RAMEX, Eq. 6-12: RA = Cr + Cp (repair cost incl. vessel spread + lost production).
  The model in CLAUDE.md follows this.
- Fig. 6-17 (p. 187-188): downtime = T_RA (waiting for vessel) + T_AR (active repair); lost production
  "is the sum of all of the individual subsea wells". This supports the manifold-shuts-all-its-wells idea.
- p. 187: failures of subsea equipment are covered in **Chapter 11** (possible failure-rate source).

## Bai & Bai (2010), Chapter 11 "Subsea Equipment RBI" (pp. 293-328): tree failure rates only

Same book. Chapter 11 is about risk-based inspection (RBI). Its failure data come from **OREDA 2002**
(Det Norske Veritas, *OREDA Offshore Reliability Data Handbook*, 4th ed.), table "Failure Descriptor
versus Failure Mode, Wellhead & Xmas Tree", OREDA p. 835 (Bai ref. [2]).

**Table 11-14, failure rate of subsea tree components (per hour):**

| Component | Low | Mean | Upper |
|---|---|---|---|
| Connector | 0.24e-9 | 0.24e-8 | 0.2e-7 |
| Flow spool | 0.65e-9 | 0.65e-8 | 0.7e-7 |
| Hydraulic coupling | 0.4e-10 | 0.4e-9 | 0.37e-8 |
| Piping | 0.1e-8 | 0.1e-7 | 0.96e-6 |
| Tubing hanger body | 0.11e-7 | 0.2e-7 | 0.1e-6 |
| Tree guide frame | 0.86e-8 | 0.24e-7 | 0.15e-6 |
| Valve, choke | 0.7e-7 | 0.73e-7 | 0.25e-6 |
| Valve, process isolation | 0.75e-7 | 0.11e-6 | 0.5e-6 |
| **Sum (series system)** | **1.67e-7** | **2.46e-7** | **2.05e-6** |
| per year (x 8760 h) | 1.46e-3 | 2.16e-3 | 1.80e-2 |

- p. 317: Bai's example takes the upper values: "2.05 x 10^-6 per hour or 1.8 x 10^-2 per year".
  Our sum of the upper column gives the same number, which confirms the table was read correctly.
- p. 317: the example assumes a **delay time of 2 days** per tree failure (their assumption).
- Limitation: the table only lists components with recorded failures in Bai's modified Table 11-13.
  It does **not** include the subsea control module (SCM) or the control system, so it is a
  lower estimate of how often a tree stops a well. A rate for the whole tree, including controls,
  is still needed.
- p. 301: failure rate lambda = n/t (failures / time in service), with a 90 % chi-square confidence
  interval. A manifold "can be equal to the pipe" for failure-rate purposes.
- Sec. 11.4 and 11.6 (pipelines, manifolds) give only **qualitative** probability-of-failure categories
  (corrosion, trawling, free span, etc.) and no numeric rates. They are not usable as lambda.
- p. 304: OREDA also gives active repair time per component (hours), which could be used for repair durations.

## Silva & Guedes Soares (2025): manifold failure rate (OREDA 2022) and pipeline failure frequencies (DNV GL 2017)

Silva, L.M.R., Guedes Soares, C. (2025). Optimisation of offshore oilfield development including the
risk of failure of subsea manifolds. *Ocean Engineering* 324, 120668.
https://doi.org/10.1016/j.oceaneng.2025.120668 (open access, CC BY-NC-ND 4.0)

- p. 7, Sec. 4.3: manifold failure rate "according to the OREDA (2022), equals **23.82 (per 10^6 h)**"
  = 0.209 per year, MTTF about 4.8 years. Used for every slot size (their stated limitation, Sec. 6).
- Table 2 (from DNV GL 2017, *Recommended Failure Rates for Pipelines*), small-diameter
  (50.8-406.4 mm) subsea pipelines: **rigid 2.4e-4 per km-year**, **flexible 2.1e-3 per km-year**.
- Eq. 47 (DNV GL 2017): FF = f_km x length + f_pipeline + f_dragged_anchor, with f_km = 4.4e-4 per km-year,
  f_pipeline = 2.3e-3, f_dragged_anchor = 1.9e-7 (units as printed in the paper).
- Sec. 2.2-2.3: OREDA (2022) manifold failure modes; most failing components are connectors, piping and
  valves; "valve, process isolation" most critical; most common mode "external leakage - process medium".
- Table 8 case: 25 wells, 6000 bbl/d plateau per well, 70 USD/bbl, 13 manifold sites, 2 platforms.
- See `docs/literature.md` for how this model differs from ours.

## Liu et al. (2024): manifold component failure rates (OREDA 2015), cross-check

Liu, C., Zhou, C., Tan, L., Cui, J., Xiao, W., Liu, J., Wang, H., Wang, T. (2024). Reliability analysis
of subsea manifold system using FMECA and FFTA. *Scientific Reports* 14, 22873.
https://doi.org/10.1038/s41598-024-73410-y (open access)

- Table 6: 23 bottom-event failure rates (mean m, in 10^-6/h) from OREDA 2015 6th ed. Vol. II
  (their refs. 44-45). Largest: X12 10.64, X4 5.67, X14 4.51, X11 4.21, X8 3.31 (codes in Table 5).
- Sum of the means = 41.44e-6/h, which equals their top-event result F = 0.0000415 (Eq. 32, lambda-cut = 1):
  the fault tree is effectively a series system. That is **0.363 per year**, MTTF about 2.8 years.
- Fuzzy interval [0.1185e-4, 0.6734e-4] per hour (lambda-cut = 0), i.e. 0.10-0.59 per year. Useful
  range for sensitivity.
- Includes pigging module and insulation failures, not all of which stop production.

## Østebø, Kallestad & Grytdal (2001): qualitative only

Østebø, R., Kallestad, O., Grytdal, I. (2001). Subsea reliability - success factors for sustainable
deepwater concept development. OTC 13290, Offshore Technology Conference, Houston.

- No usable numeric failure rates in the text (choke MTBF is shown only as a graph, Fig. 6).
- Åsgard: 16 manifolds with about 50 valves each; the flow control module "can be replaced from a monohull
  vessel in less than 48 hours" (possible evidence for a short repair time on light-vessel interventions).
- Fig. 2: reliability in a life-cycle-cost view (CAPEX + OPEX + regularity loss "REGEX"). Good for the
  introduction.

## Failure-rate summary (candidates for step 5)

| Component | Rate | Per year | Source | Basis |
|---|---|---|---|---|
| Manifold | 23.82e-6/h | 0.209 | Silva & Guedes Soares 2025 (OREDA 2022) | all failure modes |
| Manifold (cross-check) | 41.4e-6/h | 0.363 | Liu et al. 2024 (OREDA 2015) | 23 components, series |
| X-mas tree | 2.46e-7/h (upper 2.05e-6) | 0.0022 (0.018) | Bai & Bai Table 11-14 (OREDA 2002) | 8 components, **no controls** |
| Rigid flowline | 2.4e-4 per km-yr | 0.0036 for 15 km | DNV GL 2017 via Silva 2025 | small diameter |
| Flexible flowline | 2.1e-3 per km-yr | | DNV GL 2017 via Silva 2025 | |
| Umbilical, SCM | none yet | | | |

**Warning: the rates are not on the same basis.** The manifold rate (all OREDA failure modes, 2015/2022)
is about 100 times the tree rate (OREDA 2002, eight structural/valve components, no controls).
Used as-is, this would overstate the advantage of spreading wells over several manifolds. A whole-tree
rate (including the control module) from OREDA 2015/2022 is needed, or both rates should be limited to
critical failures that stop production.

## Still needed

- Failure rates (lambda): **umbilical, subsea control module, and a whole-tree rate** (incl. controls) on the same
  OREDA basis as the manifold rate. Ideally critical-failure rates only. Sources: published papers/theses quoting OREDA (2009 or later editions); PARLOC
  (UK pipeline and riser loss of containment) for flowlines, see Bai p. 300.
- Repair durations and vessel waiting/mobilization times.
- Common cost year: escalate Kaiser (2014) and Bai (2007/2009) to one year.
