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

Resulting installed unit costs (config/base_case.yaml): tree 6.0 MUSD; manifold 2-slot 4.35, 4-slot 5.25, 6-slot 6.15, 8-slot 6.75 MUSD.

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

## Mahmoudi (2021): critical failure rates of subsea control module (SCM) components (OREDA)

Mahmoudi, J. (2021). SIL analysis of subsea control system components based on a typical OREDA
database. *Quality and Reliability Engineering International* 37, 3297-3313. https://doi.org/10.1002/qre.2909

- Sec. 1: OREDA classifies failures as critical, degraded, incipient, unknown. Sec. 3: here
  lambda_crit = lambda_D (dangerous) + lambda_ST (spurious trip).
- Table 7 (per 10^6 h), SCM subunit, lambda_crit: subsea electronic module (SEM) **5.1550**; solenoid control
  valve 0.3169; power/signal coupler 0.1203; hydraulic coupling 0.0349; power supply unit 0.8881; check valve
  0.2146; valve other 1.5089. (Spurious trip only, lambda_ST: SEM 0.4472, PSU 0.4037, valve other 0.5102.)
- Data are "exemplary" from two unnamed OREDA versions (OD1 newer than OD2); Tables 5-6 give units, failures and
  time in service.
- **Our use:** one of each SCM component in series = 8.24e-6/h = **0.072 per year** (critical). This is a lower bound:
  a real SCM has many solenoid control valves (the IRF 2018 paper mentions 20 control functions). With 20 valves it
  would be 14.3e-6/h = 0.125 per year (our assumption).
- Note: in SIL terms "dangerous" means fail-on-demand, which does not by itself stop production; a spurious trip does.
  For lost-production purposes, all critical failures are a conservative choice.

## Silva, da Hora & Fernandes (2018), IRF2018: control system cross-check

Silva, A.H.M., da Hora, H., Fernandes, R. (2018). Reliability assessment of a subsea electro-hydraulic control
system. Proc. IRF2018, Lisbon, paper 7053. ISBN 978-989-20-8313-1.

- Fault tree of "loss of well control" (topside MCS + umbilical + SCM), OREDA data: failure probability 17.35 % at
  7,400 h and 67.52 % at 26,508 h. Equivalent constant rate (our calculation, lambda = -ln(1-P)/t):
  2.6e-5/h = 0.23 per year (7,400 h) and 4.2e-5/h = 0.37 per year (26,508 h).
- Largest contributors: topside master control station (MCS A and B), SCM directional control valve leakage,
  SCM sensors and SEMs. Includes topside items, so it is an upper cross-check for a well's control system.

## Schneider (Lisbon MSc thesis): DNV (2009) pipeline and flexible line failure frequencies

Schneider, K. *Risk and Reliability Analysis of a Subsea System for Oil Production*. MSc thesis, Instituto Superior
Técnico, Universidade de Lisboa. Tables 11-14 from DNV (2009) (*Recommended failure rates for pipelines*).

- Table 11 (well stream / small pipelines, unprocessed fluid): Alternative 1 f_km = 5.0e-4 per km-year;
  Alternative 2 f_km = 2.5e-4 per km-year + f_pipeline = 1.4e-3 per year; dragged anchor 1.9e-7 per crossing per year.
- Table 13 (flexible, midline): 11 leaks, 3447 km-years, **2.3e-4 per km-year**; 2.8e-5 per pipe-year.
  Note: 11/3447 = 3.2e-3, so the printed 2.3e-4 looks inconsistent; Silva & Guedes Soares (2025) give
  2.1e-3 per km-year for flexible (DNV GL 2017). Use 2.1e-3 and treat 2.3e-4 as doubtful.
- Table 14 risers: steel <=16" 9.1e-4, >=18" 1.2e-4, flexible dynamic 4.5e-4 per riser-year.
- No tree, manifold or umbilical rates.

## Thies, Smith & Johanning (2012): umbilical failure rate (OREDA 2002)

Thies, P.R., Smith, G.H., Johanning, L. (2012). Addressing failure rate uncertainties of marine energy
converters. *Renewable Energy* 44, 359-367. https://doi.org/10.1016/j.renene.2012.02.007

- Sec. 5.2.1: prior taken from OREDA (2002) handbook p. 811 (their ref. [35]) for a (dynamic) umbilical:
  "nine umbilical units with two reported failures, external leakage and transmission failure".
- Mean failure rate **4.2669 per 10^6 h** (sd 4.8281 per 10^6 h), "MTTF = 26.7 years with sd 23.6 years";
  i.e. **0.037 per year per umbilical**. 90 % interval 0.2-14 per 10^6 h (Fig. 6), i.e. 0.002-0.12 per year.
- Limitation: very small sample (9 units, 2 failures), per unit not per km, dynamic umbilical (Thies discuss
  oil and gas umbilicals with hydraulic + electrical lines). Wide range, good for sensitivity.

## Zhang et al. (2025): control system maintenance, evidence on shutdown scope and repair time

Zhang, Y., Cai, B., Gao, C., Zhao, Y., Shao, X., Yang, C. (2025). A system-centred predictive maintenance
re-optimization method based on multi-agent deep reinforcement learning. *Expert Systems With Applications*
274, 127034. https://doi.org/10.1016/j.eswa.2025.127034

- Sec. 3.3: control system components (MCS, EPU, HPU, SCM, umbilical) "are connected in series; thus, any
  component failure in the system can cause system failure, leading to system shutdown".
- Sec. 3.3: South China Sea case: "all the production wells of platform A ... were temporarily shut down because
  of communication failure, and the replacement of subsea communication cables took only 6 days".
  Evidence that one umbilical/communication failure stops every well it serves, and for a repair duration.
- Table 1 "failure rate/month" values (MCS 0.089, EPU 0.0127, HPU 0.06, SCM 0.018, umbilical 0.0044) are
  **degradation-model parameters** simulated from OREDA, not failure rates. Not used as lambda.

## Harahap (2019), NTNU MSc thesis: OREDA subsea data fields (no values)

Harahap, V.A. (2019). *Recommendations to Improve the Quality and the Automation of the OREDA Data
Process*. MSc thesis, NTNU, Department of Mechanical and Industrial Engineering.

- Sec. 2 (p. 20-21): OREDA subsea failure events record "type of main intervention vessel", "main vessel
  time" (on location, "excluding sailing, waiting and idle time"), support vessel and time, maintenance
  resource (diver or ROV), and "Mobilization time: records number of days required to mobilize the
  intervention vessel until it is ready". Downtime is "calendar time ... which includes the mobilization of
  resources or spare and all the preparation".
- Use: supports the structure of our downtime model (mobilisation + waiting + active repair are recorded
  separately in OREDA). Gives no numeric values.

## Hjelle (2018), UiS MSc thesis (preview, Ch. 1-2 only): qualitative

Hjelle, E.I. (2018). MSc thesis, Marine & offshore technology / Marine operations, University of
Stavanger (pendulum installation method for subsea hardware in ultradeep water). Only a 24-page preview
was available (front matter and Ch. 1-2).

- p. 11: installation cost drivers are "the time spent on the operation, and the cost of the vessels
  available in the region", hence vessels "with low day-rates" and "low mobilisation cost" are preferred;
  "there is a significant probability of long periods of waiting on weather".
- The full thesis cites DNV-OS-H101 (2011) alpha-factor tables and required weather windows (thesis
  Fig. 3-9 to 3-11, pp. 57-59) and analyses a manifold lift at Hs = 2 m, Tp = 8 s (Table 6-1). Not in the
  preview; the Hs limit in our config remains a placeholder.

## DNV-ST-N001 (Dec. 2023), Marine operations and marine warranty: weather-restricted operations

DNV (2023). DNV-ST-N001 *Marine operations and marine warranty*, edition December 2023. DNV AS.
(Licensed copy; do not commit or redistribute the PDF. Only short values are recorded here.)

- Table 1-4 definitions: weather window = period with forecast conditions <= OP_WF; OP_WF = alpha x OP_LIM;
  operation reference period T_R = T_POP + T_C.
- [2.6.4.2]: if not assessed in detail, T_R >= 2 x T_POP (guidance: T_C = 50 % of T_POP acceptable only
  for operations with an extensive experience basis). [2.6.4.3]: T_C < 6 h normally not acceptable.
- [2.6.7.2]: weather restricted requires T_R < 96 h and T_POP < 72 h. [2.6.5.2], [2.6.7.8]: longer
  operations can be planned with stops in a safe condition.
- [2.6.8.2]: OP_LIM not greater than the minimum of design conditions, safe working limits and "weather
  restrictions for equipment (e.g. ROV and cranes)" -> OP_LIM is vessel/equipment specific.
- [2.6.10.4]: North Sea and Norwegian Sea alpha tables per Table 2-1 (forecast level, monitoring, LRFD/ASD).
- Table 2-16: forecast level B (moderate) for "offshore lifting", "subsea installation".
- **Table 2-4** (LRFD, level A2 or B, no environmental monitoring), alpha by T_POP row and OP_LIM Hs:

  | T_POP | Hs = 1 | Hs = 2 | Hs = 4 | Hs >= 6 |
  |---|---|---|---|---|
  | <= 12 h | 0.68 | 0.80 | 0.83 | 0.84 |
  | <= 24 h | 0.66 | 0.77 | 0.80 | 0.82 |
  | <= 36 h | 0.65 | 0.75 | 0.77 | 0.80 |
  | <= 48 h | 0.63 | 0.71 | 0.75 | 0.78 |
  | <= 72 h | 0.58 | 0.66 | 0.71 | 0.76 |

  Linear interpolation between Hs columns. Used in config `weather.alpha_table`.

## NORA3 wave hindcast at Solveig (MET Norway): North Sea weather statistics

Breivik et al. (2022), J. Geophys. Res. Oceans 127, e2021JC018196; data CC BY 4.0, MET Norway. Hourly Hs at
58.6795 N, 2.2036 E (model depth 99 m), downloaded with scripts/download_nora3_hs.py.

- Cross-check: share of hours with Hs < 2.5 m = 0.65 (first 7 years), at the low end of the 65-80 % quoted for
  the North Sea by industry sources (nodynamics.com, not peer reviewed).

## Failure-rate summary (candidates for step 5)

| Component | Rate | Per year | Source | Basis |
|---|---|---|---|---|
| Manifold | 23.82e-6/h | 0.209 | Silva & Guedes Soares 2025 (OREDA 2022) | all failure modes |
| Manifold (cross-check) | 41.4e-6/h | 0.363 | Liu et al. 2024 (OREDA 2015) | 23 components, series |
| Tree, structure and valves | 2.46e-7/h (upper 2.05e-6) | 0.0022 (0.018) | Bai & Bai Table 11-14 (OREDA 2002) | 8 components |
| Tree SCM (controls) | 8.24e-6/h | 0.072 | Mahmoudi 2021 Table 7 (OREDA) | critical, one of each component |
| **Tree total (base)** | 8.49e-6/h | **0.074** | sum of the two rows above | |
| Well control system (cross-check) | 2.6-4.2e-5/h | 0.23-0.37 | IRF 2018 (OREDA) | incl. topside MCS |
| Rigid flowline | 2.4e-4 per km-yr | | DNV GL 2017 via Silva 2025 | small diameter |
| Flexible flowline | 2.1e-3 per km-yr | | DNV GL 2017 via Silva 2025 | |
| Umbilical | 4.27e-6/h per unit | 0.037 (range 0.002-0.12) | Thies et al. 2012 (OREDA 2002 p. 811) | 9 units, 2 failures |

Consistency: with the SCM included, manifold/tree = 0.209/0.074, about 3 (was about 100 without controls).
The manifold rate counts all failure modes while the SCM rate counts critical failures only, so the
manifold rate is probably still high relative to the tree. Test with the sensitivity analysis.

## Still needed

- Failure rates: a critical-only manifold rate would help; a per-km umbilical rate (current one is per unit, small sample). Sources: published papers/theses quoting OREDA (2009 or later editions); PARLOC
  (UK pipeline and riser loss of containment) for flowlines, see Bai p. 300.
- Repair durations and vessel waiting/mobilization times.
- Common cost year: escalate Kaiser (2014) and Bai (2007/2009) to one year.
