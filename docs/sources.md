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

## Still needed (placeholders in config)

- `capex.xmas_tree`, `capex.manifold`, `manifold.slots`.
- Best lead: Bai, Y. & Bai, Q. *Subsea Engineering Handbook* (Elsevier, 2010; 2nd ed. 2019),
  chapter "Subsea Cost Estimation". It is the original source of the pipe costs above and has
  cost tables for subsea equipment. Available on ScienceDirect through most university libraries.
