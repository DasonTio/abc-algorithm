"""Budget check (post hoc, added 2026-11-08): would a budget of 800 evaluations give the same answers as 2,000?

ABC is deterministic for a given seed, so a run with budget 800 is the first 800 evaluations of the 2,000 run.
Re-runs ABC and random search with budget 800 (SN=10, limit=45, seeds 100-109) on the development,
validation and transfer earthquakes and compares with the saved 2,000-evaluation runs.
Writes results/budget_check.csv and prints a summary. Not used to change any reported result.
"""
import os, sys
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import run_experiments as R

R.BUDGET = 800
rows, curves = [], {}
for role in ("dev", "validation", "transfer_kyushu", "transfer_kinki"):
    for e in R.events(role):
        for s in range(100, 110):
            R.run_method(role, e, "ABC", s, rows, curves, SN=10, limit=45)
            R.run_method(role, e, "random search", s, rows, curves)
new = pd.DataFrame(rows).assign(budget=800)
old = pd.concat([pd.read_csv(os.path.join(R.RES, f), dtype={"event_id": str})
                 for f in ("runs_final.csv", "runs_validation.csv", "runs_transfer.csv")])
old = old[old.method.isin(["ABC", "random search"])].assign(budget=2000)
old["scenario"] = old.scenario.replace({"final_dev": "dev"})
both = pd.concat([new, old[new.columns]], ignore_index=True)
both = both[both.scenario.isin(["dev", "validation", "transfer_kyushu", "transfer_kinki"])]
both.to_csv(os.path.join(R.RES, "budget_check.csv"), index=False)
ev = both.groupby(["scenario", "method", "budget", "event_id"]).agg(J=("J", "median"), km=("epi_err_km", "median")).reset_index()
print(ev.groupby(["method", "budget"]).agg(J=("J", "median"), km=("km", "median")).round(4))
print(both.groupby(["method", "budget"]).agg(J=("J", "median"), km=("epi_err_km", "median"), km_p90=("epi_err_km", lambda s: s.quantile(.9)), km_max=("epi_err_km", "max")).round(3))
a = both[both.method == "ABC"].pivot_table(index=["event_id", "seed"], columns="budget", values=["J", "epi_err_km"])
same = (a[("J", 800)] - a[("J", 2000)]).abs() < 1e-4
print("ABC runs where J(800) is within 1e-4 of J(2000):", round(same.mean() * 100, 1), "%")
d = (a[("epi_err_km", 800)] - a[("epi_err_km", 2000)])
print("location change 800 vs 2000: median", round(d.abs().median(), 3), "km; >1 km in", round((d.abs() > 1).mean() * 100, 1), "% of runs; max", round(d.abs().max(), 1))
