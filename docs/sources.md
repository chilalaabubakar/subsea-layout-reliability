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

## Still needed (placeholders in config)

- `capex.xmas_tree`, `capex.manifold`, `manifold.slots`.
- Candidate: Superstructure optimization of subsea processing layouts, *J. Petrol. Explor.
  Prod. Technol.* (2023), https://doi.org/10.1007/s13202-023-01624-3 (open access; unit costs
  and size factors). Not read yet: the Springer site could not be downloaded from the
  cloud session.
