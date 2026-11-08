"""Transfer test analysis: does the method frozen on Niigata-Hokuriku work in other regions?

Reads runs_final.csv (dev), runs_validation.csv, runs_transfer.csv. Writes
results/summary_transfer.csv, results/per_event_transfer.csv, results/transfer_offset_by_region.csv,
results/fig_transfer.png.
The offset table is a DIAGNOSIS only (c refitted per region at JMA's answer); the runs all use the frozen c.

    python code/analyze_transfer.py
"""
import json, os, sys
import numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.stats import wilcoxon

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
from model import Objective, Event, region_bounds

RES = os.path.join(ROOT, "results")
EV = pd.read_csv(os.path.join(ROOT, "config/events.csv"), dtype={"event_id": str})
HYP = pd.read_csv(os.path.join(ROOT, "data/processed/hypocentres.csv"), dtype={"event_id": str}).set_index("event_id")
I = pd.read_csv(os.path.join(ROOT, "data/processed/intensities.csv"), dtype={"event_id": str})
C = json.load(open(os.path.join(RES, "offset_calibration.json")))["c"]

r = pd.concat([pd.read_csv(os.path.join(RES, f), dtype={"event_id": str})
               for f in ("runs_final.csv", "runs_validation.csv", "runs_transfer.csv")])
GROUPS = [("final_dev", "Niigata dev\n(20, tuned on)"), ("validation", "Niigata validation\n(13, reserved)"),
          ("transfer_kyushu", "Kyushu\n(17, session 2)"), ("transfer_kinki", "Kinki–Chūgoku\n(5, session 3)"),
          ("transfer_stress", "New-region M≥7\n(5, stress)")]
METHODS = ["ABC", "current practice", "random search", "heuristic", "ABC no scouts"]

ev = (r.groupby(["scenario", "method", "event_id"])
       .agg(J=("J", "median"), epi_km=("epi_err_km", "median"), M_err=("M_err", "median")).reset_index())
ev.to_csv(os.path.join(RES, "per_event_transfer.csv"), index=False)

from analyze import summary
rows, tests = [], []
for sc, label in GROUPS:
    s_ = summary(r[r.scenario == sc], f"transfer_{sc}") if sc.startswith("transfer") else None
    if s_ is not None:
        rows.append(s_.assign(group=label.replace("\n", " ")))
    d = ev[ev.scenario == sc]
    a = d[d.method == "ABC"].set_index("event_id"); cp = d[d.method == "current practice"].set_index("event_id").loc[a.index]
    rs = d[d.method == "random search"].set_index("event_id").loc[a.index]
    tests.append(dict(group=label.replace("\n", " "), events=len(a),
                      abc_lower_J_than_cp=int((a.J < cp.J).sum()), p_J=wilcoxon(a.J, cp.J).pvalue,
                      abc_closer_than_cp=int((a.epi_km < cp.epi_km).sum()), p_km=wilcoxon(a.epi_km, cp.epi_km).pvalue,
                      abc_closer_than_random=int((a.epi_km < rs.epi_km).sum()), p_km_random=wilcoxon(a.epi_km, rs.epi_km).pvalue,
                      p_absM=wilcoxon(a.M_err.abs(), cp.M_err.abs()).pvalue,
                      M_bias_abc=a.M_err.mean(), M_bias_cp=cp.M_err.mean()))
summ = pd.concat(rows)
pd.DataFrame(tests).to_csv(os.path.join(RES, "tests_transfer.csv"), index=False)
summ.to_csv(os.path.join(RES, "summary_transfer.csv"), index=False)

# diagnosis: which offset c would each region want? (fitted at JMA's answer, same procedure as calibrate_offset.py)
def fit_c(ids):
    objs = []
    for e in ids:
        reg = EV.set_index("event_id").region.get(e, "niigata"); reg = reg if isinstance(reg, str) else "niigata"
        lo, hi = region_bounds(reg); h = HYP.loc[e]
        objs.append((Objective(Event(e, I[I.event_id == e]), lower=lo, upper=hi), np.array([h.lat, h.lon, h.mag_jma])))
    f = lambda c: np.mean([Objective(o.ev, c=c, lower=o.lower, upper=o.upper)(t) for o, t in objs])
    g = np.round(np.arange(-0.5, 1.5001, 0.01), 2); return float(g[np.argmin([f(c) for c in g])])
offs = [dict(group=label.replace("\n", " "), c_fitted=fit_c(EV[EV.role == role].event_id))
        for role, label in (("dev", GROUPS[0][1]), ("validation", GROUPS[1][1]),
                            ("transfer_kyushu", GROUPS[2][1]), ("transfer_kinki", GROUPS[3][1]))]
pd.DataFrame(offs).to_csv(os.path.join(RES, "transfer_offset_by_region.csv"), index=False)

# figure: per-event median errors, ABC vs current practice, by region
COL = {"ABC": "#1f5fbf", "current practice": "#8a8f98"}
fig, axes = plt.subplots(1, 2, figsize=(12.5, 4.6))
for ax, col, ylab in ((axes[0], "epi_km", "epicentre error vs JMA (km)"), (axes[1], "M_err", "magnitude error, estimate − JMA (Mj)")):
    for k, (sc, label) in enumerate(GROUPS):
        for j, m in enumerate(("ABC", "current practice")):
            vals = ev[(ev.scenario == sc) & (ev.method == m)][col].to_numpy()
            pos = k * 3 + j
            b = ax.boxplot(vals, positions=[pos], widths=0.8, patch_artist=True, showfliers=False)
            for part in ("boxes",):
                for p in b[part]: p.set(facecolor=COL[m], alpha=0.35, edgecolor=COL[m])
            for p in b["medians"]: p.set(color=COL[m], lw=2)
            ax.scatter(np.full(len(vals), pos) + np.random.default_rng(k * 7 + j).uniform(-0.18, 0.18, len(vals)), vals,
                       s=12, color=COL[m], zorder=3)
    ax.set_xticks([k * 3 + 0.5 for k in range(len(GROUPS))]); ax.set_xticklabels([g[1] for g in GROUPS], fontsize=8.5)
    ax.set_ylabel(ylab); ax.grid(axis="y", alpha=0.25)
    for k in range(1, len(GROUPS)):
        ax.axvline(k * 3 - 1, color="#ddd", lw=1)
axes[1].axhline(0, color="#444", lw=1)
axes[0].set_title("Epicentre error per earthquake (median of 10 runs)", loc="left", fontsize=11)
axes[1].set_title("Magnitude error per earthquake", loc="left", fontsize=11)
from matplotlib.patches import Patch
fig.legend(handles=[Patch(color=COL[m], alpha=0.6, label=m) for m in COL], loc="upper right", ncol=2, frameon=False)
fig.suptitle("Frozen method (c = +0.418, SN = 10, limit = 45) applied unchanged to new regions", x=0.01, ha="left", fontsize=11)
fig.tight_layout(rect=(0, 0, 1, 0.94))
fig.savefig(os.path.join(RES, "fig_transfer.png"), dpi=160)
print(summ[["group","method","runs","events","J_median","J_IQR","J_best","J_worst","epi_km_median","epi_km_IQR","abs_M_err_median","M_err_mean","feasible_rate","runtime_s_median"]].round(4).to_string(index=False))
print(pd.DataFrame(tests).round(4).to_string(index=False)); print(pd.DataFrame(offs).to_string(index=False))
