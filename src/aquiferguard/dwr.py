"""California DWR monthly groundwater levels and site handling.

Head is stored in meters. Missing months stay missing; they are not interpolated.
Co-located screens within SITE_RADIUS_M share a site id so a well split cannot
put two screens from the same pad on opposite sides.

Published coordinates are trusted when they sit near the Mount Diablo township
implied by the state well number, or, for counties on another baseline, inside
that county. Untrusted coordinates still keep the hydrograph, as its own site,
and are not sent to the InSAR sampler.
"""

from __future__ import annotations

import csv
import hashlib
import math
from pathlib import Path

import numpy as np

from .forecast import LAGS
from .synth import Well

FT_TO_M = 0.3048
GOOD_QC = frozenset({"1", "2", "10"})
MIN_ORIGINS = 24
SITE_RADIUS_M = 200.0
# Mount Diablo Base and Meridian, used only as a consistency check.
MD_LAT = 37 + 52 / 60 + 54 / 3600
MD_LON = -(121 + 54 / 60 + 47 / 3600)
COORD_TOLERANCE_M = 25_000.0

# Counties surveyed from a baseline other than Mount Diablo.
OTHER_BASELINE_BOX = {
    "Humboldt": (40.0, 41.5, -124.5, -123.4),
    "Del Norte": (41.4, 42.1, -124.5, -123.5),
    "Riverside": (33.4, 34.1, -117.7, -114.4),
    "San Bernardino": (33.9, 35.8, -117.7, -114.1),
    "Imperial": (32.6, 33.5, -116.2, -114.4),
    "San Diego": (32.5, 33.5, -117.6, -116.0),
    "Orange": (33.4, 33.9, -118.1, -117.4),
    "Los Angeles": (33.7, 34.9, -118.9, -117.6),
    "Ventura": (34.0, 34.9, -119.5, -118.6),
    "Santa Barbara": (34.4, 35.1, -120.7, -119.4),
}


def add_months(ym: str, k: int) -> str:
    year, month = int(ym[:4]), int(ym[5:7])
    month += k
    year += (month - 1) // 12
    month = (month - 1) % 12 + 1
    return f"{year:04d}-{month:02d}"


def month_index(ym: str, year0: int) -> int:
    year, month = int(ym[:4]), int(ym[5:7])
    return (year - year0) * 12 + (month - 1)


def good_head_m(qc: str, wse: str) -> float | None:
    """Return elevation in meters when the published quality code is good."""
    if qc.strip() not in GOOD_QC:
        return None
    text = wse.strip()
    if not text:
        return None
    value = float(text)
    if not math.isfinite(value):
        return None
    return value * FT_TO_M


def _township_parts(station: str) -> tuple[int, str, int, str] | None:
    digits = ""
    i = 0
    while i < len(station) and station[i].isdigit():
        digits += station[i]
        i += 1
    if not digits or i >= len(station) or station[i] not in "NS":
        return None
    ns = station[i]
    i += 1
    rng = ""
    while i < len(station) and station[i].isdigit():
        rng += station[i]
        i += 1
    if not rng or i >= len(station) or station[i] not in "EW":
        return None
    return int(digits), ns, int(rng), station[i]


def township_center(station: str) -> tuple[float, float] | None:
    """Approximate township center on the Mount Diablo baseline, in degrees."""
    parts = _township_parts(station)
    if parts is None:
        return None
    township, ns, rng, ew = parts
    sign = 1.0 if ns == "N" else -1.0
    lat = MD_LAT + sign * township * 6.0 / 69.0
    miles_per_deg = 69.172 * math.cos(math.radians(lat))
    sign_ew = 1.0 if ew == "E" else -1.0
    lon = MD_LON + sign_ew * rng * 6.0 / miles_per_deg
    return lat, lon


def distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    dy = (lat1 - lat2) * 111_320.0
    dx = (lon1 - lon2) * 111_320.0 * math.cos(math.radians((lat1 + lat2) / 2.0))
    return math.hypot(dx, dy)


def coordinates_trusted(station: str, lat: float, lon: float, county: str) -> bool:
    if not (32.4 <= lat <= 42.1 and -124.5 <= lon <= -114.0):
        return False
    center = township_center(station)
    if center is not None and distance_m(lat, lon, center[0], center[1]) <= COORD_TOLERANCE_M:
        return True
    box = OTHER_BASELINE_BOX.get(county)
    if box is None:
        return False
    return box[0] <= lat <= box[1] and box[2] <= lon <= box[3]


def _find(parent: list[int], i: int) -> int:
    while parent[i] != i:
        parent[i] = parent[parent[i]]
        i = parent[i]
    return i


def assign_sites(records: list[dict], radius_m: float = SITE_RADIUS_M) -> dict[str, str]:
    """Map station -> site id. Untrusted coordinates are never merged."""
    trusted = [r for r in records if r["coord_ok"]]
    parent = list(range(len(trusted)))
    for i in range(len(trusted)):
        for j in range(i + 1, len(trusted)):
            a, b = trusted[i], trusted[j]
            if distance_m(a["latitude"], a["longitude"], b["latitude"], b["longitude"]) <= radius_m:
                ra, rb = _find(parent, i), _find(parent, j)
                if ra != rb:
                    parent[rb] = ra
    groups: dict[int, list[str]] = {}
    for i, row in enumerate(trusted):
        groups.setdefault(_find(parent, i), []).append(row["station"])
    sites = {r["station"]: r["station"] for r in records}
    for members in groups.values():
        site = min(members)
        for station in members:
            sites[station] = site
    return sites


def split_site_ids(site_ids: list[str], seed: int = 0, train_frac: float = 0.5,
                   cal_frac: float = 0.25) -> tuple[set[str], set[str], set[str]]:
    """Hold out whole sites. The ranking is a hash, so it does not depend on NumPy."""
    ranked = sorted(site_ids, key=lambda s: hashlib.sha256(f"{seed}:{s}".encode()).hexdigest())
    n_train = int(len(ranked) * train_frac)
    n_cal = int(len(ranked) * cal_frac)
    train = set(ranked[:n_train])
    cal = set(ranked[n_train:n_train + n_cal])
    test = set(ranked[n_train + n_cal:])
    return train, cal, test


def _dense(values: dict[str, float], year0: int, n_months: int) -> np.ndarray:
    out = np.full(n_months, np.nan)
    for ym, value in values.items():
        index = month_index(ym, year0)
        if 0 <= index < n_months:
            out[index] = value
    return out


def count_origins(head: np.ndarray, horizon: int = 6) -> int:
    n = 0
    last = len(head) - horizon
    for t in range(LAGS, last):
        window = head[t - LAGS + 1:t + 1]
        if np.isfinite(window).all() and np.isfinite(head[t + horizon]):
            n += 1
    return n


def _own_origin_count(months: dict[str, float], horizon: int) -> int:
    year0 = min(int(ym[:4]) for ym in months)
    last = max(month_index(ym, year0) for ym in months)
    return count_origins(_dense(months, year0, last + 1), horizon)


def wells_from_series(series: dict[str, dict[str, float]], meta: dict[str, dict],
                      insar: dict[str, dict[str, float]] | None = None,
                      min_origins: int = MIN_ORIGINS, horizon: int = 6) -> list[Well]:
    """Build calendar-aligned wells. Index 0 is January of the earliest year.

    Eligibility and site ids use only stations that already have enough origins
    on their own record, so a short neighboring well cannot change a site id.
    """
    present = [
        s for s, months in series.items()
        if s in meta and months and _own_origin_count(months, horizon) >= min_origins
    ]
    if not present:
        return []
    months = [ym for s in present for ym in series[s]]
    if insar:
        months.extend(ym for site in insar.values() for ym in site)
    year0 = min(int(ym[:4]) for ym in months)
    last = max(month_index(ym, year0) for ym in months)
    n_months = last + 1
    records = [{**meta[s], "station": s} for s in present]
    sites = assign_sites(records)
    wells = []
    for station in sorted(present):
        info = meta[station]
        head = _dense(series[station], year0, n_months)
        site = sites[station]
        disp_map = (insar or {}).get(site, {})
        displacement = _dense(disp_map, year0, n_months) if disp_map else np.full(n_months, np.nan)
        wells.append(Well(
            head=head,
            rain=np.full(n_months, np.nan),
            pumping=np.full(n_months, np.nan),
            station=station,
            site_id=site,
            latitude=float(info["latitude"]),
            longitude=float(info["longitude"]),
            county=info.get("county", ""),
            coord_ok=bool(info.get("coord_ok", True)),
            displacement=displacement,
        ))
    return wells


def load_raw_series(station_csv: Path, monthly_csv: Path) -> tuple[dict, dict]:
    """Read the DWR station file and the monthly-mean file. Head is converted to meters."""
    meta = {}
    with station_csv.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            try:
                lat, lon = float(row["LATITUDE"]), float(row["LONGITUDE"])
            except ValueError:
                continue
            station = row["STATION"].strip()
            county = row.get("COUNTY_NAME", "").strip()
            meta[station] = {
                "latitude": lat,
                "longitude": lon,
                "county": county,
                "basin": row.get("BASIN_NAME", "").strip(),
                "coord_ok": coordinates_trusted(station, lat, lon, county),
            }
    series: dict[str, dict[str, list[float]]] = {}
    with monthly_csv.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            head = good_head_m(row.get("WSE_QC", ""), row.get("WSE", ""))
            if head is None:
                continue
            station = row["STATION"].strip()
            if station not in meta:
                continue
            series.setdefault(station, {}).setdefault(row["MSMT_DATE"][:7], []).append(head)
    averaged = {
        station: {ym: float(np.mean(vals)) for ym, vals in months.items()}
        for station, months in series.items()
    }
    return meta, averaged


def load_snapshot(wells_csv: Path, insar_csv: Path | None = None,
                  min_origins: int = MIN_ORIGINS) -> list[Well]:
    """Load the committed snapshot written by research/fetch_real.py."""
    series: dict[str, dict[str, float]] = {}
    meta: dict[str, dict] = {}
    with wells_csv.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            station = row["station"]
            series.setdefault(station, {})[row["month"]] = float(row["head_m"])
            meta[station] = {
                "latitude": float(row["latitude"]),
                "longitude": float(row["longitude"]),
                "county": row.get("county", ""),
                "basin": row.get("basin", ""),
                "coord_ok": row.get("coord_ok", "1") == "1",
            }
    insar: dict[str, dict[str, float]] = {}
    if insar_csv is not None and insar_csv.exists():
        with insar_csv.open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                insar.setdefault(row["site_id"], {})[row["month"]] = float(row["displacement_m"])
    return wells_from_series(series, meta, insar, min_origins=min_origins)


def write_snapshot(wells: list[Well], series: dict[str, dict[str, float]], meta: dict[str, dict],
                   wells_csv: Path) -> None:
    wells_csv.parent.mkdir(parents=True, exist_ok=True)
    kept = {w.station for w in wells}
    with wells_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=[
            "station", "site_id", "latitude", "longitude", "county", "basin",
            "month", "head_m", "coord_ok"])
        writer.writeheader()
        site_of = {w.station: w.site_id for w in wells}
        for station in sorted(kept):
            info = meta[station]
            for ym in sorted(series[station]):
                writer.writerow({
                    "station": station,
                    "site_id": site_of[station],
                    "latitude": f"{info['latitude']:.6f}",
                    "longitude": f"{info['longitude']:.6f}",
                    "county": info.get("county", ""),
                    "basin": info.get("basin", ""),
                    "month": ym,
                    "head_m": f"{series[station][ym]:.6f}",
                    "coord_ok": "1" if info["coord_ok"] else "0",
                })


def site_points(wells: list[Well]) -> list[tuple[str, float, float]]:
    """One InSAR sample location per trusted site: the mean of its well coordinates."""
    buckets: dict[str, list[Well]] = {}
    for well in wells:
        if not math.isfinite(well.latitude):
            continue
        buckets.setdefault(well.site_id, []).append(well)
    points = []
    for site, members in sorted(buckets.items()):
        lat = float(np.mean([w.latitude for w in members]))
        lon = float(np.mean([w.longitude for w in members]))
        points.append((site, lat, lon))
    return points
