# MET Norway NORA3 wave hindcast - raw downloads

`nora3_hs_solveig.csv`: hourly total significant wave height Hs [m] at the NORA3 WAM 3 km grid
point nearest the Solveig manifold (row 413, col 2028; 58.6795 N, 2.2036 E; model depth 99 m),
2014-01-01 to 2023-12-31. Downloaded with:

    python scripts/download_nora3_hs.py 413 2028 2014 2023 data/raw/metno/nora3_hs_solveig.csv

Source: https://thredds.met.no/thredds/catalog/windsurfer/mywavewam3km_files/catalog.html
Licence: CC BY 4.0, credit MET Norway. Reference: Breivik et al. (2022), J. Geophys. Res.
Oceans 127, e2021JC018196. Times are UTC. Do not edit; the download script is resumable.

`nora3_hs_solveig_2024.csv`: the same grid point for 2024-01-01 to 2024-12-31, downloaded with:

    python scripts/download_nora3_hs.py 413 2028 2024 2024 data/raw/metno/nora3_hs_solveig_2024.csv

It is a run-out only. `scripts/weather_windows.py` uses its hours to complete weather windows of
repairs whose vessel is ready late in 2023; start hours are always 2014-2023. Same source and licence.

`nora3_hs_vigdis.csv` (2014-2023) and `nora3_hs_vigdis_2024.csv` (run-out year): the same series at the
grid point nearest the Vigdis field (row 483, col 1972; 61.368 N, 2.094 E), downloaded with:

    python scripts/download_nora3_hs.py 483 1972 2014 2023 data/raw/metno/nora3_hs_vigdis.csv 6
    python scripts/download_nora3_hs.py 483 1972 2024 2024 data/raw/metno/nora3_hs_vigdis_2024.csv 6
