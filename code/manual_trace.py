"""Manual-trace material for ABC: 3 food sources, one full cycle, plus a controlled scout.

Tiny instance: 6 real stations of the 2004 Chuetsu mainshock (3 observed at 4+, 3 at 1-3),
so J can be computed by hand. Every random choice (k, j, phi, roulette pick) is recorded.

Writes
  results/manual_trace_program.csv   the program's own trace (one row per step)
  results/manual_trace.xlsx          the same steps recomputed with live spreadsheet formulas
                                     from the recorded random choices; 'check' columns compare them
Part A: one normal cycle (SN = 3, limit = 6 = 2D, seed 7).
Part B: controlled scout demonstration: continue from the end of part A with limit = 0, so the
        scout phase must abandon the source with the most failures. Labelled as forced.
"""
import json, os, sys
import numpy as np, pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter as L

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from model import Objective, Event, LOWER, UPPER, LOG_ARV, DEPTH_KM
import bee_colony as bees

I = pd.read_csv(os.path.join(ROOT, "data/processed/intensities.csv"), dtype={"event_id": str, "station_code": str})
ev = I[I.event_id == "20041023175600"]
# 3 strongest stations + the 3 intensity-3 stations closest to the official epicentre
from model import epicentral_km
hi = ev[ev.instr_lower >= 3.5].sort_values("instr_lower", ascending=False).head(3)
three = ev[ev.intensity == "3"].copy()
three["d"] = epicentral_km(37.2917, 138.8670, three.lat.to_numpy(float), three.lon.to_numpy(float))
lo = three.sort_values("d").head(3).drop(columns="d")
tiny = pd.concat([hi, lo])
tiny = tiny.reset_index(drop=True)
c = json.load(open(os.path.join(ROOT, "results/offset_calibration.json")))["c"]
J = Objective(Event("tiny", tiny), c=c)

SEED, SN, LIMIT = 7, 3, 6
trA = []
rA = bees.abc(J, LOWER, UPPER, budget=10_000, seed=SEED, SN=SN, limit=LIMIT, trace=trA, max_cycles=1)
trB = []
rB = bees.abc(J, LOWER, UPPER, budget=10_000, seed=SEED + 1, SN=SN, limit=0, trace=trB, max_cycles=1,
              init=rA["final_sources"], init_trials=rA["final_trials"])
rows = []
for part, tr in (("A", trA), ("B forced scout", trB)):
    for t in tr:
        if part.startswith("B") and t["phase"] == "init":
            continue                                   # re-evaluation of part A's final sources
        rows.append({"part": part, **{k: (json.dumps(v) if isinstance(v, list) else v) for k, v in t.items()}})
prog = pd.DataFrame(rows)
prog.to_csv(os.path.join(ROOT, "results/manual_trace_program.csv"), index=False)

# ------------------------------------------------------------------ spreadsheet
wb = Workbook(); bold, blue = Font(bold=True), Font(color="0000FF")
ws = wb.active; ws.title = "stations"
ws.append(["station", "lat", "lon", "intensity", "group", "class_lower", "class_upper"])
for _, s in tiny.iterrows():
    ws.append([s.station_name_ja, float(s.lat), float(s.lon), s.intensity,
               "high" if s.instr_lower >= 3.5 else "low", float(s.instr_lower),
               99.0 if s.intensity == "7" else float(s.instr_upper)])
for k, (lab, v) in enumerate([("c", c), ("depth_km", DEPTH_KM), ("logARV", LOG_ARV), ("low edge", 3.5)]):
    ws.cell(10 + k, 1, lab); ws.cell(10 + k, 2, float(v)).font = blue
ws.cell(15, 1, "bounds"); ws.cell(15, 2, "lat"); ws.cell(15, 3, "lon"); ws.cell(15, 4, "M")
ws.cell(16, 1, "lower"); ws.cell(17, 1, "upper")
for j in range(3):
    ws.cell(16, 2 + j, float(LOWER[j])); ws.cell(17, 2 + j, float(UPPER[j]))
for c0 in "ABCDEFG":
    ws[f"{c0}1"].font = bold
nh = int((tiny.instr_lower >= 3.5).sum()); nl = len(tiny) - nh


def J_formula(r, latc, lonc, Mc):
    """Excel formula for J of the point in cells latc, lonc, Mc of row r (6 stations)."""
    terms_h, terms_l = [], []
    for s in range(2, 2 + len(tiny)):
        epi = (f"12742*ASIN(SQRT(SIN((stations!B{s}-{latc}{r})*PI()/360)^2+COS({latc}{r}*PI()/180)"
               f"*COS(stations!B{s}*PI()/180)*SIN((stations!C{s}-{lonc}{r})*PI()/360)^2))")
        R = f"SQRT(({epi})^2+stations!$B$11^2)"
        Ip = (f"(2.68+1.72*(0.58*{Mc}{r}+0.0038*stations!$B$11-1.29-LOG10({R}+0.0028*10^(0.5*{Mc}{r}))"
              f"-0.002*{R}+stations!$B$12)+stations!$B$10)")
        hi = tiny.instr_lower.iloc[s - 2] >= 3.5
        if hi:
            terms_h.append(f"IF({Ip}<stations!F{s},stations!F{s}-{Ip},IF({Ip}>stations!G{s},{Ip}-stations!G{s},0))^2")
        else:
            terms_l.append(f"MAX(0,{Ip}-stations!$B$13)^2")
    return f"=0.5*({'+'.join(terms_h)})/{nh}+0.5*({'+'.join(terms_l)})/{nl}"


st = wb.create_sheet("steps")
head = ["part", "phase", "i", "k", "j (0=lat,1=lon,2=M)", "phi", "x_i lat", "x_i lon", "x_i M", "x_k[j]",
        "v lat", "v lon", "v M", "J(x_i) before", "J(v) spreadsheet", "J(v) program", "check |diff|",
        "accepted? (J(v) < J(x_i))", "accepted program", "trial before", "trial after"]
st.append(head)
for c0 in range(1, len(head) + 1):
    st.cell(1, c0).font = bold
r = 2
for _, t in prog.iterrows():
    if t.phase not in ("init", "employed", "onlooker", "scout"):
        continue
    v = json.loads(t.v)
    st.cell(r, 1, t.part); st.cell(r, 2, t.phase); st.cell(r, 3, int(t.i))
    if t.phase in ("employed", "onlooker"):
        xo = json.loads(t.x_old); k, j = int(t.k), int(t.j)
        st.cell(r, 4, k); st.cell(r, 5, j); st.cell(r, 6, float(t.phi)).font = blue
        for d in range(3):
            st.cell(r, 7 + d, float(xo[d])).font = blue
        # x_k[j] is recovered from v: v_j = x_ij + phi (x_ij - x_kj) (before clipping)
        xkj = xo[j] - (v[j] - xo[j]) / t.phi if t.phi != 0 else xo[j]
        st.cell(r, 10, float(xkj)).font = blue
        for d in range(3):
            col = L(7 + d)
            if d == j:
                st.cell(r, 11 + d, f"=MIN(MAX({col}{r}+F{r}*({col}{r}-J{r}),stations!{L(2 + d)}$16),stations!{L(2 + d)}$17)")
            else:
                st.cell(r, 11 + d, f"={col}{r}")
        st.cell(r, 14, float(t.f_old))
        st.cell(r, 18, f"=O{r}<N{r}")
        st.cell(r, 19, bool(t.accepted)); st.cell(r, 20, float(t.trial_before)); st.cell(r, 21, float(t.trial_after))
    else:
        for d in range(3):
            st.cell(r, 11 + d, float(v[d])).font = blue
    st.cell(r, 15, J_formula(r, "K", "L", "M"))
    st.cell(r, 16, float(t.f_new))
    st.cell(r, 17, f"=ABS(O{r}-P{r})")
    r += 1
st.cell(r + 1, 1, "Blue = recorded inputs (random choices and the current source). Black = formulas.")
st.cell(r + 2, 1, "x_k[j] is written as recorded: v_j = x_ij + phi*(x_ij - x_kj), then clipped to the bounds.")
st.cell(r + 3, 1, "Part B is a controlled demonstration: limit = 0 forces the scout phase to fire.")

pr = wb.create_sheet("probabilities")
pr.append(["part", "source i", "J(x_i) after employed phase", "F = 1/(1+J)", "p = F / sum(F)", "p program"])
rr = 2
for part, tr in (("A", trA), ("B forced scout", trB)):
    probs = [t for t in tr if t["phase"] == "probabilities"]
    emp_end = [t for t in tr if t["phase"] == "employed"]
    if not probs:
        continue
    F = probs[0]["F"]; P = probs[0]["p"]
    start = rr
    for i in range(SN):
        Ji = 1 / F[i] - 1
        pr.append([part, i, Ji, f"=1/(1+C{rr})", f"=D{rr}/SUM(D{start}:D{start + SN - 1})", P[i]])
        rr += 1
wb.save(os.path.join(ROOT, "results/manual_trace.xlsx"))

pd.set_option("display.width", 250); pd.set_option("display.max_colwidth", 60)
print(tiny[["station_name_ja", "lat", "lon", "intensity"]].to_string(index=False))
show = prog[prog.phase.isin(["init", "employed", "probabilities", "onlooker", "scout", "end_cycle"])]
for _, t in show.iterrows():
    if t.phase in ("employed", "onlooker"):
        print(f"[{t.part}] {t.phase:8s} i={int(t.i)} k={int(t.k)} j={int(t.j)} phi={t.phi:+.4f} J_old={t.f_old:.5f} J_new={t.f_new:.5f} "
              f"{'ACCEPT' if t.accepted else 'reject'} trial {int(t.trial_before)}->{int(t.trial_after)}")
    elif t.phase == "probabilities":
        print(f"[{t.part}] probabilities p={t.p}")
    elif t.phase == "init":
        print(f"[{t.part}] init     i={int(t.i)} x={t.v} J={t.f_new:.5f}")
    elif t.phase == "scout":
        print(f"[{t.part}] SCOUT    i={int(t.i)} old={t.x_old} new={t.v} J={t.f_new:.5f}")
    else:
        print(f"[{t.part}] end cycle best J={t.best_f:.5f} trials={t.trials}")
