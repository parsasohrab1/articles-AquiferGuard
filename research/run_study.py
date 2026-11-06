"""Write research/results.json from the synthetic study and the DWR well study.

Usage:
    python research/run_study.py --out research/results.json
    python research/run_study.py --check
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aquiferguard.dwr import load_snapshot
from aquiferguard.evaluate import run_real, run_synthetic


def build() -> dict:
    data = ROOT / "data"
    manifest = json.loads((data / "manifest.json").read_text(encoding="utf-8"))
    wells = load_snapshot(data / "wells_monthly.csv", data / "insar_monthly.csv")
    return {"synthetic": run_synthetic(), "real": run_real(wells, manifest)}


def _same(left, right) -> bool:
    if isinstance(left, dict) and isinstance(right, dict):
        return left.keys() == right.keys() and all(_same(left[k], right[k]) for k in left)
    if isinstance(left, list) and isinstance(right, list):
        return len(left) == len(right) and all(_same(a, b) for a, b in zip(left, right, strict=True))
    if isinstance(left, float) and isinstance(right, float):
        return math.isclose(left, right, rel_tol=1e-6, abs_tol=1e-6)
    return left == right


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=str(ROOT / "research" / "results.json"))
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    fresh = build()
    path = Path(args.out)
    if args.check:
        saved = json.loads(path.read_text(encoding="utf-8"))
        if not _same(saved, fresh):
            raise SystemExit("results.json does not match a fresh run")
        print("results.json matches a fresh run")
        return
    path.write_text(json.dumps(fresh, indent=2) + "\n", encoding="utf-8")
    real = fresh["real"]["test"]
    print(
        f"wells {fresh['real']['n_wells']} "
        f"mae_ridge {real['mae_ridge_m']:.4f} "
        f"mae_persistence {real['mae_persistence_m']:.4f} "
        f"mae_simple {real['mae_simple_regression_m']:.4f} "
        f"coverage {real['coverage']:.4f}"
    )


if __name__ == "__main__":
    main()
