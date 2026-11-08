"""Figure explaining the formulation: how a candidate x becomes the score J.

(a) the pipeline from x to J and F, (b) the forward model against real station data
(2004 Chuetsu, at JMA's epicentre), (c) the two penalty shapes.

    python code/fig_formulation.py  -> results/fig_formulation.png
"""
import json, os, sys
import numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
from model import predict_intensity, epicentral_km, DEPTH_KM

RES = os.path.join(ROOT, "results")
C = json.load(open(os.path.join(RES, "offset_calibration.json")))["c"]
EVENT = "20041023175600"
I = pd.read_csv(os.path.join(ROOT, "data/processed/intensities.csv"), dtype={"event_id": str})
h = pd.read_csv(os.path.join(ROOT, "data/processed/hypocentres.csv"), dtype={"event_id": str}).set_index("event_id").loc[EVENT]
rows = I[I.event_id == EVENT].copy()
rows["dist"] = epicentral_km(h.lat, h.lon, rows.lat.to_numpy(), rows.lon.to_numpy())

BLUE, GREY, ORANGE, INK = "#1f5fbf", "#8a8f98", "#d4700a", "#222222"
fig = plt.figure(figsize=(13, 8.2))
gs = fig.add_gridspec(2, 2, height_ratios=[0.75, 1.15], width_ratios=[1.35, 1], hspace=0.28, wspace=0.22)
axA = fig.add_subplot(gs[0, :]); axB = fig.add_subplot(gs[1, 0]); axC = fig.add_subplot(gs[1, 1])

# (a) pipeline
axA.set_xlim(0, 100); axA.set_ylim(0, 33); axA.axis("off")
boxes = [
    (1, 10, 15, 14, "Candidate x\n(lat, lon, M)\nchosen by a bee", BLUE),
    (19.5, 10, 15, 14, "Distance R to\nevery station\n(depth fixed 10 km)", INK),
    (38, 10, 17, 14, "Predicted intensity\nat each station\nI = f(M, R) + c", INK),
    (58.5, 17.5, 19, 10, "Strong stations (4+):\ngap to reported class²\n→ J_high", INK),
    (58.5, 3, 19, 10, "Weak stations (1–3):\nexcess above 3.5²\n→ J_low", INK),
    (81, 10, 18, 14, "J = 0.5·J_high + 0.5·J_low\n(lower = better)\nF = 1/(1+J) for onlookers", BLUE),
]
for x, y, w, hgt, txt, col in boxes:
    axA.add_patch(FancyBboxPatch((x, y), w, hgt, boxstyle="round,pad=0.4,rounding_size=1.2", fc="white", ec=col, lw=1.6))
    axA.text(x + w / 2, y + hgt / 2, txt, ha="center", va="center", fontsize=9.5, color=INK)
arr = dict(arrowstyle="-|>", color=INK, lw=1.3)
for a, b in (((16.4, 17), (19.1, 17)), ((34.9, 17), (37.6, 17)), ((55.4, 18.5), (58.1, 22.5)), ((55.4, 15.5), (58.1, 8)),
             ((77.9, 22.5), (80.6, 18.5)), ((77.9, 8), (80.6, 15.5))):
    axA.annotate("", xy=b, xytext=a, arrowprops=arr)
axA.text(46.5, 31.2, "Si & Midorikawa (1999) + Midorikawa et al. (1999); c = +0.418 fitted on development events",
         ha="center", fontsize=8.5, color=GREY)
axA.text(46.5, 1.0, "outside the search area: J = 10⁶ + distance outside (always ranked last)", ha="center", fontsize=8.5, color=GREY)
axA.set_title("(a) From one guess to one score", loc="left", fontsize=11)

# (b) forward model vs real data
d = np.linspace(1, 250, 400)
for M, ls in ((6.0, ":"), (6.8, "-"), (7.5, "--")):
    pred = predict_intensity((h.lat, h.lon, M), h.lat + d / 111.2, np.full_like(d, h.lon), c=C)
    axB.plot(d, pred, color=BLUE, ls=ls, lw=2 if M == 6.8 else 1.4, label=f"model, M {M}" + (" (JMA's answer)" if M == 6.8 else ""))
hi = rows[rows.instr_lower >= 3.5]; lo = rows[rows.instr_lower < 3.5]
axB.vlines(hi.dist, hi.instr_lower, hi.instr_upper.clip(upper=7.0), color=INK, lw=1, alpha=0.55, label="strong station: reported class (4+)")
axB.scatter(lo.dist, lo.instr_mid, s=3, color=GREY, alpha=0.35, label="weak station (1–3), class midpoint")
axB.axhline(3.5, color=ORANGE, lw=1.2, ls="--"); axB.text(3, 3.32, "3.5: boundary between intensity 3 and 4", ha="left", va="top", fontsize=8.5, color=ORANGE)
axB.set_xlim(0, 250); axB.set_ylim(0, 7.2); axB.set_xlabel("distance from epicentre (km)"); axB.set_ylabel("JMA intensity")
axB.grid(alpha=0.25); axB.legend(fontsize=8, loc="upper right", frameon=False)
axB.set_title("(b) Forward model against 1,495 stations, Chūetsu 2004", loc="left", fontsize=11)

# (c) penalty shapes
p = np.linspace(2.5, 6.5, 400)
e_hi = np.where(p < 4.5, 4.5 - p, np.where(p > 5.0, p - 5.0, 0)) ** 2
e_lo = np.maximum(p - 3.5, 0) ** 2
axC.plot(p, e_hi, color=INK, lw=2, label="strong station reported 5− (class 4.5–5.0)")
axC.plot(p, e_lo, color=GREY, lw=2, ls="--", label="weak station reported 1–3")
axC.axvspan(4.5, 5.0, color=INK, alpha=0.08); axC.text(4.75, 0.12, "inside\nclass:\nno\npenalty", ha="center", va="bottom", fontsize=8)
axC.axvline(3.5, color=ORANGE, lw=1, ls="--")
axC.set_xlabel("predicted intensity at the station"); axC.set_ylabel("penalty (intensity²)")
axC.set_ylim(0, 3); axC.grid(alpha=0.25); axC.legend(fontsize=8.5, loc="upper center", bbox_to_anchor=(0.5, -0.17), frameon=False)
axC.set_title("(c) How one station is penalised", loc="left", fontsize=11)

fig.savefig(os.path.join(RES, "fig_formulation.png"), dpi=160, bbox_inches="tight")
print("saved results/fig_formulation.png")
