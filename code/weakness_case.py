"""Weakness case and landscape figure.

For two dev events (Chuetsu 2004 onshore, Sado 2012 offshore), map min over M of J(lat, lon, M)
on a grid around the official epicentre, and mark the stations, JMA's answer and the grid minimum.
For Sado 2012 the grid minimum is a feasible candidate that scores BETTER than JMA's answer while
being about 15 km away: a flaw of the objective (model), not of the search.

    python code/weakness_case.py  -> results/weakness_case.csv, results/fig_landscape.png
"""
import json, os, sys
import numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from model import Objective, Event, epicentral_km

RES = os.path.join(ROOT, "results")
C = json.load(open(os.path.join(RES, "offset_calibration.json")))["c"]
I = pd.read_csv(os.path.join(ROOT, "data/processed/intensities.csv"), dtype={"event_id": str})
HYP = pd.read_csv(os.path.join(ROOT, "data/processed/hypocentres.csv"), dtype={"event_id": str}).set_index("event_id")
CASES = [("20041023175600", "Chūetsu 2004 M6.8 (onshore)"), ("20120208210137", "Sado 2012 M5.7 (offshore)")]
M_GRID = np.arange(4.5, 7.81, 0.05)

fig, axes = plt.subplots(1, 2, figsize=(12, 5.4))
rows = []
for ax, (e, title) in zip(axes, CASES):
    h = HYP.loc[e]; rdf = I[I.event_id == e]; J = Objective(Event(e, rdf), c=C)
    lats = np.arange(h.lat - 0.6, h.lat + 0.6001, 0.02); lons = np.arange(h.lon - 0.75, h.lon + 0.7501, 0.025)
    Z = np.full((len(lats), len(lons)), np.nan); Mz = np.zeros_like(Z)
    for a, la in enumerate(lats):
        for b, lo in enumerate(lons):
            v = [J([la, lo, m]) for m in M_GRID]; k = int(np.argmin(v)); Z[a, b] = v[k]; Mz[a, b] = M_GRID[k]
    a, b = np.unravel_index(np.nanargmin(Z), Z.shape)
    gx = (lats[a], lons[b], Mz[a, b])
    truth = (h.lat, h.lon, h.mag_jma)
    jt, jg = J(truth), J(gx)
    ct, cg = J.components(truth), J.components(gx)
    rows += [dict(event=title, candidate="JMA official", lat=truth[0], lon=truth[1], M=truth[2], km_from_JMA=0.0, J=jt,
                  J_high=ct["J_high"], J_low=ct["J_low"]),
             dict(event=title, candidate="minimum of J (grid)", lat=gx[0], lon=gx[1], M=gx[2],
                  km_from_JMA=float(epicentral_km(h.lat, h.lon, gx[0], gx[1])), J=jg, J_high=cg["J_high"], J_low=cg["J_low"])]
    im = ax.pcolormesh(lons, lats, np.log10(Z), cmap="viridis_r", shading="auto")
    near = rdf[(rdf.lat.between(lats[0], lats[-1])) & (rdf.lon.between(lons[0], lons[-1]))]
    hi = near[near.instr_lower >= 3.5]; lo = near[near.instr_lower < 3.5]
    ax.scatter(lo.lon, lo.lat, s=6, c="white", edgecolors="none", alpha=.7, label="stations 1–3")
    ax.scatter(hi.lon, hi.lat, s=14, c="#c4511c", edgecolors="k", linewidths=.3, label="stations 4+")
    ax.plot(h.lon, h.lat, "*", ms=16, mfc="gold", mec="k", label=f"JMA: M{h.mag_jma}, J={jt:.3f}")
    ax.plot(gx[1], gx[0], "X", ms=11, mfc="red", mec="k", label=f"min J: M{gx[2]:.2f}, J={jg:.3f}")
    ax.set_title(title, fontsize=10); ax.set_xlabel("longitude"); ax.set_ylabel("latitude")
    ax.set_aspect(1 / np.cos(np.radians(h.lat))); ax.legend(fontsize=7, loc="lower right")
    fig.colorbar(im, ax=ax, label="log10 (min over M of J)")
fig.suptitle("Objective landscape: best magnitude at each point. Yellow = lower J (better)", fontsize=11)
fig.tight_layout(); fig.savefig(os.path.join(RES, "fig_landscape.png"), dpi=160)
out = pd.DataFrame(rows); out.to_csv(os.path.join(RES, "weakness_case.csv"), index=False)
print(out.round(4).to_string(index=False))
