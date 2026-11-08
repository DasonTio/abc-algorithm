"""Estimate the global intensity offset c from the development earthquakes only.

For every dev event, J is evaluated at JMA's official epicentre and magnitude (lat, lon, Mj),
with depth fixed at 10 km as in the model.
c is the value that minimises the average J over the dev events (1-D grid, then refined).
Writes results/offset_calibration.json and results/offset_calibration_per_event.csv.

Run from the Task 4 folder:  python code/calibrate_offset.py
"""
import json, os, sys, datetime as dt
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from model import Objective, load_events

events, table = load_events(os.path.join(ROOT, "data/processed/intensities.csv"),
                            os.path.join(ROOT, "config/events.csv"), roles={"dev"})
hyp = pd.read_csv(os.path.join(ROOT, "data/processed/hypocentres.csv"), dtype={"event_id": str}).set_index("event_id")
truth = {e: np.array([hyp.loc[e, "lat"], hyp.loc[e, "lon"], hyp.loc[e, "mag_jma"]], float)
         for e in events}


def mean_J(c):
    return float(np.mean([Objective(events[e], c=c)(truth[e]) for e in events]))


grid = np.round(np.arange(-0.5, 1.5001, 0.01), 2)
vals = np.array([mean_J(c) for c in grid])
c_best = float(grid[vals.argmin()])
fine = np.round(np.arange(c_best - 0.01, c_best + 0.01001, 0.001), 3)
c_best = float(fine[np.argmin([mean_J(c) for c in fine])])

rows = []
for e in events:
    for label, c in (("c=0", 0.0), ("c=best", c_best)):
        o = Objective(events[e], c=c)
        comp = o.components(truth[e])
        rows.append(dict(event_id=e, setting=label, c=c, J=o(truth[e]), n_high=events[e].n_hi, n_low=events[e].n_lo,
                         rms_high=comp["rms_high"], high_inside_class=comp["high_inside_class"],
                         low_wrongly_4plus=comp["low_wrongly_4plus"]))
per = pd.DataFrame(rows)
os.makedirs(os.path.join(ROOT, "results"), exist_ok=True)
per.to_csv(os.path.join(ROOT, "results/offset_calibration_per_event.csv"), index=False)
summary = per.groupby("setting")[["J", "rms_high", "high_inside_class", "low_wrongly_4plus"]].mean().round(4)
out = {
    "c": c_best, "fitted_on": "dev events at JMA official epicentre and Mj, depth fixed at 10 km", "n_events": len(events),
    "n_high_readings": int(sum(ev.n_hi for ev in events.values())),
    "n_low_readings": int(sum(ev.n_lo for ev in events.values())),
    "objective": "0.5*mean(interval error^2, 4+) + 0.5*mean(max(0, pred-3.5)^2, 1-3)",
    "mean_J_c0": mean_J(0.0), "mean_J_best": mean_J(c_best),
    "grid": {"from": -0.5, "to": 1.5, "step": 0.01, "refined_step": 0.001},
    "created": dt.datetime.now().isoformat(timespec="seconds"),
}
json.dump(out, open(os.path.join(ROOT, "results/offset_calibration.json"), "w"), indent=2)
print(f"c = {c_best:+.3f} (mean J {out['mean_J_c0']:.4f} at c=0 -> {out['mean_J_best']:.4f})")
print(summary.to_string())
