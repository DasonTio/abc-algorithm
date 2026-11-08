"""Run ABC on ONE earthquake, with optional changes. Built for the live defence.

Examples (from the Task 4 folder):
    python3 code/run_single.py 20041023175600 --seed 3
    python3 code/run_single.py 20041023175600 --seed 3 --drop-station 3710044        # lose one reading
    python3 code/run_single.py 20041023175600 --seed 3 --max-M 6.5                   # tighter bound
    python3 code/run_single.py 20041023175600 --seed 3 --exclude-box 37.2 37.4 138.8 139.0   # blocked area
    python3 code/run_single.py 20041023175600 --seed 3 --c 0.3 --w-high 0.8 --w-low 0.2
    python3 code/run_single.py 20041023175600 --seed 3 --score 37.29 138.87 6.8      # just score one candidate

Prints the answer, its error against JMA, J and its two parts, evaluations and scouts.
"""
import argparse, json, os, sys
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import model
from model import Objective, Event, epicentral_km
from baselines import current_practice
import bee_colony as bees

p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
p.add_argument("event_id")
p.add_argument("--seed", type=int, default=100)
p.add_argument("--budget", type=int, default=2000)
p.add_argument("--SN", type=int, default=None, help="default: results/chosen_params.json")
p.add_argument("--limit", type=float, default=None, help="default: results/chosen_params.json; 0 = no scouts")
p.add_argument("--c", type=float, default=None, help="intensity offset (default: calibrated value)")
p.add_argument("--w-high", type=float, default=0.5)
p.add_argument("--w-low", type=float, default=0.5)
p.add_argument("--min-M", type=float, default=None)
p.add_argument("--max-M", type=float, default=None)
p.add_argument("--drop-station", nargs="*", default=[], help="station codes to remove")
p.add_argument("--exclude-box", type=float, nargs=4, metavar=("LAT0", "LAT1", "LON0", "LON1"),
               help="epicentre may not lie inside this box (e.g. a blocked area)")
p.add_argument("--score", type=float, nargs=3, metavar=("LAT", "LON", "M"), help="only score this candidate")
a = p.parse_args()

RES = os.path.join(ROOT, "results")
I = pd.read_csv(os.path.join(ROOT, "data/processed/intensities.csv"), dtype={"event_id": str, "station_code": str})
H = pd.read_csv(os.path.join(ROOT, "data/processed/hypocentres.csv"), dtype={"event_id": str}).set_index("event_id")
rows = I[(I.event_id == a.event_id) & (~I.station_code.isin(a.drop_station))]
if rows.empty:
    sys.exit("no readings for that event id")
ch = json.load(open(os.path.join(RES, "chosen_params.json")))
SN = a.SN or ch["SN"]
limit = ch["limit"] if a.limit is None else (None if a.limit == 0 else a.limit)
c = json.load(open(os.path.join(RES, "offset_calibration.json")))["c"] if a.c is None else a.c
lower, upper = model.LOWER.copy(), model.UPPER.copy()
if a.min_M is not None: lower[2] = a.min_M
if a.max_M is not None: upper[2] = a.max_M
base = Objective(Event(a.event_id, rows), c=c, w_high=a.w_high, w_low=a.w_low)


def J(x):
    if a.exclude_box:
        la0, la1, lo0, lo1 = a.exclude_box
        if la0 <= x[0] <= la1 and lo0 <= x[1] <= lo1:
            base.n_evals += 1
            return model.INFEASIBLE + 1.0
    if np.any(np.asarray(x) < lower) or np.any(np.asarray(x) > upper):
        base.n_evals += 1
        return model.INFEASIBLE + float(np.maximum(lower - x, 0).sum() + np.maximum(np.asarray(x) - upper, 0).sum())
    return base(x)


h = H.loc[a.event_id]


def show(label, x, f):
    comp = base.components(x)
    print(f"{label}: lat {x[0]:.4f}, lon {x[1]:.4f}, M {x[2]:.2f} | J {f:.5f} (high {comp['J_high']:.5f}, low {comp['J_low']:.5f})"
          f" | {epicentral_km(h.lat, h.lon, x[0], x[1]):.1f} km from JMA, M error {x[2] - h.mag_jma:+.2f}")


print(f"event {a.event_id} {h.region_ja} | JMA: lat {h.lat}, lon {h.lon}, M {h.mag_jma} | "
      f"stations: {int((rows.instr_lower >= 3.5).sum())} at 4+, {int((rows.instr_lower < 3.5).sum())} at 1-3 | c {c:+.3f}")
if a.score:
    x = np.array(a.score); show("candidate", x, J(x)); sys.exit()
r = bees.abc(J, lower, upper, budget=a.budget, seed=a.seed, SN=SN, limit=limit)
show(f"ABC (SN={SN}, limit={limit}, seed={a.seed})", r["best_x"], r["best_f"])
print(f"evaluations {r['n_evals']}, cycles {r['cycles']}, scouts {r['scouts']} at evaluations {r['scout_evals'][:10]}")
x, f = current_practice(lambda v: J(v), rows)
show("current practice", x, f)
