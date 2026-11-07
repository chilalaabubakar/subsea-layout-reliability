# MET Norway NORA3 wave hindcast - raw downloads

`nora3_hs_solveig.csv`: hourly total significant wave height Hs [m] at the NORA3 WAM 3 km grid
point nearest the Solveig manifold (row 413, col 2028; 58.6795 N, 2.2036 E; model depth 99 m),
2014-01-01 to 2023-12-31. Downloaded with:

    python scripts/download_nora3_hs.py 413 2028 2014 2023 data/raw/metno/nora3_hs_solveig.csv

Source: https://thredds.met.no/thredds/catalog/windsurfer/mywavewam3km_files/catalog.html
Licence: CC BY 4.0, credit MET Norway. Reference: Breivik et al. (2022), J. Geophys. Res.
Oceans 127, e2021JC018196. Times are UTC. Do not edit; the download script is resumable.
