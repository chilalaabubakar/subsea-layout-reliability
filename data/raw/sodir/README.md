# Sodir (Norwegian Offshore Directorate) fact pages - raw downloads

Source: https://factpages.sodir.no, "Table view" exports as CSV. Licence: Norwegian Licence for
Open Government Data (NLOD). Downloaded 2026-11-07.

| File | Table | URL (rs:Format=CSV) |
|---|---|---|
| wellbore_development_all.csv | Wellbore > Development > All | `.../tableview/wellbore_development_all` |
| facility_fixed.csv | Facility > Fixed | `.../tableview/facility_fixed` |
| facility_moveable.csv | Facility > Moveable | `.../tableview/facility_moveable` |
| field_production_monthly.csv | Field > Production > Monthly | `.../tableview/field_production_monthly` |

Full URL pattern:
`https://factpages.sodir.no/public?/Factpages/external/tableview/<TABLE>&rs:Command=Render&rc:Toolbar=false&rc:Parameters=f&IpAddress=not_used&CultureCode=en&rs:Format=CSV&Top100=false`

These files are raw inputs; do not edit. `scripts/prepare_solveig.py` turns them into
`config/field_solveig.yaml` and `data/processed/solveig_production.csv`.
