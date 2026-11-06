"""Download the DWR monthly snapshot and sample TRE Altamira displacement at well sites.

The study reads data/wells_monthly.csv and data/insar_monthly.csv. Raw DWR files
stay in data/raw and are not required after this script has written the snapshot.

InSAR values are the image-service pixel in feet, converted to meters with 0.3048.
That unit is the one stated on the DWR vertical-displacement image service.
"""

from __future__ import annotations

import csv
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aquiferguard.dwr import (
    FT_TO_M,
    load_raw_series,
    load_snapshot,
    site_points,
    wells_from_series,
    write_snapshot,
)

CATALOG = "https://gis.water.ca.gov/arcgisimg/rest/services/SAR?f=pjson"
SERVICE = (
    "https://gis.water.ca.gov/arcgisimg/rest/services/SAR/"
    "Vertical_Displacement_TRE_ALTAMIRA_Total_Since_20150613_{date}/ImageServer/getSamples"
)
PREFIX = "SAR/Vertical_Displacement_TRE_ALTAMIRA_Total_Since_20150613_"
GROUNDWATER_URL = (
    "https://data.cnra.ca.gov/dataset/618c73fe-b28c-4399-a824-43d0278fe974/"
    "resource/16f256f8-35a4-4cab-ae02-399a2914c282/download/gwl-monthly.csv"
)
STATION_URL = (
    "https://data.cnra.ca.gov/dataset/618c73fe-b28c-4399-a824-43d0278fe974/"
    "resource/03967113-1556-4100-af2c-b16a4d41b9d0/download/gwl-stations.csv"
)
BATCH = 40


def _get_json(url: str) -> dict:
    request = urllib.request.Request(url, headers={"User-Agent": "aquiferguard-realdata"})
    with urllib.request.urlopen(request, timeout=90) as response:
        return json.loads(response.read().decode())


def catalog_dates() -> list[str]:
    body = _get_json(CATALOG)
    dates = []
    for service in body.get("services", []):
        name = service.get("name", "")
        stamp = name[len(PREFIX):]
        if name.startswith(PREFIX) and stamp.isdigit() and len(stamp) == 8:
            dates.append(stamp)
    if not dates:
        raise RuntimeError("no TRE Altamira cumulative services in the SAR catalog")
    return sorted(set(dates))


def _sample_batch(day: str, points: list[tuple[str, float, float]]) -> dict[str, float]:
    geometry = {
        "points": [[lon, lat] for _, lat, lon in points],
        "spatialReference": {"wkid": 4326},
    }
    query = urllib.parse.urlencode({
        "geometry": json.dumps(geometry, separators=(",", ":")),
        "geometryType": "esriGeometryMultipoint",
        "f": "json",
    })
    body = _get_json(SERVICE.format(date=day) + "?" + query)
    if "error" in body:
        raise RuntimeError(f"{day}: {body['error']}")
    samples = body.get("samples", [])
    out = {}
    for sample in samples:
        index = sample.get("locationId")
        if index is None or not (0 <= index < len(points)):
            continue
        raw = sample.get("value")
        if raw in (None, ""):
            continue
        out[points[index][0]] = float(raw) * FT_TO_M
    return out


def sample_date(day: str, points: list[tuple[str, float, float]]):
    last = "no attempt"
    for attempt in range(4):
        try:
            found = {}
            for start in range(0, len(points), BATCH):
                found.update(_sample_batch(day, points[start:start + BATCH]))
            return day, found, None
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, RuntimeError, ValueError, OSError) as exc:
            last = f"{type(exc).__name__}: {exc}"
            time.sleep(1.5 * (attempt + 1))
    return day, {}, last


def _load_partial(path: Path) -> tuple[dict[str, dict[str, float]], set[str]]:
    insar: dict[str, dict[str, float]] = {}
    done: set[str] = set()
    if not path.exists():
        return insar, done
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            done.add(row["date"])
            if row["displacement_m"]:
                insar.setdefault(row["site_id"], {})[row["month"]] = float(row["displacement_m"])
    return insar, done


def _append_partial(path: Path, day: str, found: dict[str, float], sites: list[str]) -> None:
    new = not path.exists()
    month = f"{day[:4]}-{day[4:6]}"
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["date", "site_id", "month", "displacement_m"])
        if new:
            writer.writeheader()
        # One row per site, including blanks, so a finished date is recognizable on resume.
        for site in sites:
            value = found.get(site)
            writer.writerow({
                "date": day,
                "site_id": site,
                "month": month,
                "displacement_m": "" if value is None else f"{value:.6f}",
            })


def main() -> None:
    raw = ROOT / "data" / "raw"
    out = ROOT / "data"
    out.mkdir(parents=True, exist_ok=True)
    station_csv, monthly_csv = raw / "gwl-stations.csv", raw / "gwl-monthly.csv"
    if not station_csv.exists() or not monthly_csv.exists():
        raise SystemExit(f"missing raw DWR files in {raw}; download stations and gwl-monthly first")
    meta, series = load_raw_series(station_csv, monthly_csv)
    wells = wells_from_series(series, meta)
    wells_csv = out / "wells_monthly.csv"
    write_snapshot(wells, series, meta, wells_csv)
    reloaded = load_snapshot(wells_csv, None)
    left = {w.station: w.site_id for w in wells}
    right = {w.station: w.site_id for w in reloaded}
    if left != right:
        raise SystemExit("site ids changed when the snapshot was reloaded; InSAR was not sampled")
    trusted = [w for w in wells if w.coord_ok]
    points = site_points(trusted)
    print(f"wells {len(wells)} sites {len({w.site_id for w in wells})} "
          f"untrusted {sum(not w.coord_ok for w in wells)} insar_sites {len(points)}")
    dates = catalog_dates()
    partial = out / "_insar_partial.csv"
    _, done = _load_partial(partial)
    pending = [day for day in dates if day not in done]
    print(f"insar dates {len(dates)} already_done {len(done)} pending {len(pending)}")
    sites = [site for site, _, _ in points]
    failures = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(sample_date, day, points) for day in pending]
        for i, future in enumerate(as_completed(futures), start=1):
            day, found, error = future.result()
            if error:
                failures.append({"date": day, "error": error[:200]})
                print(f"fail {day} {error[:200]}")
            else:
                _append_partial(partial, day, found, sites)
            if i % 10 == 0 or i == len(pending):
                print(f"sampled {i}/{len(pending)}")
    if len(failures) > max(3, len(dates) // 4):
        raise SystemExit(f"{len(failures)} InSAR dates failed; snapshot was not finalized")
    insar, _ = _load_partial(partial)
    n_values = sum(len(months) for months in insar.values())
    if n_values == 0:
        raise SystemExit("InSAR sampling returned no finite displacement values")
    insar_csv = out / "insar_monthly.csv"
    with insar_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["site_id", "month", "displacement_m"])
        writer.writeheader()
        for site in sorted(insar):
            for month in sorted(insar[site]):
                writer.writerow({
                    "site_id": site,
                    "month": month,
                    "displacement_m": f"{insar[site][month]:.6f}",
                })
    manifest = {
        "retrieved": datetime.now(timezone.utc).date().isoformat(),
        "groundwater_source": (
            "California DWR Continuous Groundwater Level Measurements, monthly mean "
            "water-surface elevation, quality codes 1, 2 and 10"
        ),
        "groundwater_url": GROUNDWATER_URL,
        "station_url": STATION_URL,
        "insar_source": (
            "DWR TRE ALTAMIRA cumulative vertical displacement since 2015-06-13, "
            "sampled at well sites from the public image services; feet converted to meters"
        ),
        "insar_url": "https://gis.water.ca.gov/arcgisimg/rest/services/SAR",
        "insar_dates": dates,
        "insar_failed_dates": failures,
        "feet_to_meters": FT_TO_M,
        "n_wells": len(wells),
        "n_untrusted_wells": sum(not w.coord_ok for w in wells),
        "n_insar_sites_requested": len(points),
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {wells_csv.name}, {insar_csv.name}, failures {len(failures)}")


if __name__ == "__main__":
    main()
