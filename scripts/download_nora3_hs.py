"""Download hourly significant wave height (Hs) at one grid point from MET Norway NORA3.

Data: NORA3 WAM 3 km wave hindcast (MET Norway), daily files on
https://thredds.met.no/thredds/catalog/windsurfer/mywavewam3km_files/catalog.html
Licence: CC BY 4.0 (credit: MET Norway). Reference: Breivik, Ø., Carrasco, A., Haakenstad, H.,
Aarnes, O.J., Behrens, A., Bidlot, J.-R., Björkqvist, J.-V., Bohlinger, P., Furevik, B.R.,
Staneva, J., Reistad, M. (2022). The impact of a reduced high-wind Charnock parameter on wave
growth with application to the North Sea, the Norwegian Sea, and the Arctic Ocean.
J. Geophys. Res. Oceans 127, e2021JC018196.

Usage:  python scripts/download_nora3_hs.py ROW COL YEAR0 YEAR1 OUT.csv
        (Solveig: 413 2028 2014 2023 data/raw/metno/nora3_hs_solveig.csv)
Resumable: days already in OUT.csv are skipped. One small OPeNDAP request per day.
"""
import csv
import datetime as dt
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

BASE = "https://thredds.met.no/thredds/dodsC/windsurfer/mywavewam3km_files"


def parse(text: str) -> tuple[list[float], list[float]]:
    """Parse an OPeNDAP .ascii response with `time[...]` and `hs.hs[...]` blocks."""
    body = text.split("-" * 20, 1)[1]
    t_block = body.split("time[", 1)[1].split("hs.hs[", 1)[0]
    times = [float(v) for v in t_block.split("\n", 1)[1].replace("\n", ",").split(",") if v.strip()]
    hs_block = body.split("hs.hs[", 1)[1].split("\n", 1)[1]
    hs = [float(line.split(",")[1]) for line in hs_block.splitlines() if line.startswith("[")]
    return times, hs


def day(row: int, col: int, d: dt.date) -> list[tuple[str, float]]:
    url = (f"{BASE}/{d:%Y}/{d:%m}/{d:%Y%m%d}_MyWam3km_hindcast.nc.ascii?"
           + urllib.parse.quote(f"hs[0:23][{row}:{row}][{col}:{col}],time[0:23]", safe=":,"))
    for attempt in range(5):
        try:
            text = urllib.request.urlopen(url, timeout=120).read().decode()
            break
        except Exception:                     # transient network errors: back off and retry
            if attempt == 4:
                raise
            time.sleep(2 ** attempt)
    t, hs = parse(text)
    if len(t) != len(hs):
        raise ValueError(f"{d}: {len(t)} times but {len(hs)} Hs values")
    stamps = [dt.datetime.fromtimestamp(s, dt.UTC).strftime("%Y-%m-%dT%H:%M") for s in t]
    return list(zip(stamps, hs))


def main(row, col, y0, y1, out):
    out = Path(out)
    done = set()
    if out.exists():
        with out.open() as f:
            done = {r["time"][:10] for r in csv.DictReader(f)}
    new = not out.exists()
    with out.open("a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["time", "hs_m"])
        d, end, n = dt.date(y0, 1, 1), dt.date(y1, 12, 31), 0
        while d <= end:
            if d.isoformat() not in done:
                for s, h in day(row, col, d):
                    w.writerow([s, f"{h:.3f}"])
                f.flush()
                n += 1
                if n % 100 == 0:
                    print(f"{d} done ({n} new days)", flush=True)
            d += dt.timedelta(days=1)
    print("finished", flush=True)


if __name__ == "__main__":
    a = sys.argv[1:]
    main(int(a[0]), int(a[1]), int(a[2]), int(a[3]), a[4])
