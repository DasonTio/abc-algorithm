"""Five-case fitness audit on the 2004 Chuetsu mainshock (dev event 20041023175600).

Writes
  results/fitness_audit.csv   J and its parts for the five cases (computed by model.py)
  results/fitness_audit.xlsx  the same calculation as live spreadsheet formulas, one row per station,
                              so every number can be checked by hand (open in Excel / Numbers / LibreOffice)

Cases (x = lat, lon, M; depth fixed at 10 km):
  1 current practice      : centroid of the strongest-shaking stations, M by 1-D grid
  2 plausible improvement : JMA official epicentre, M by 1-D grid
  3 clearly poor          : epicentre in Kanazawa (about 213 km away), M 6.8
  4 boundary              : JMA epicentre, M at its upper bound 8.0
  5 infeasible            : JMA epicentre, M = 3.0 (below the lower bound 4.0)
Expected ranking: 2 <= 1 << {3, 4} < 5 (3 and 4 are both clearly poor; their order is not predicted).
"""
import json, os, sys
import numpy as np, pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from model import Objective, Event, epicentral_km, LOG_ARV, DEPTH_KM, LOWER, UPPER, INFEASIBLE
from baselines import current_practice, _best_magnitude

EVENT = "20041023175600"
JMA = (37.2917, 138.8670, 6.8)
KANAZAWA = (36.5613, 136.6562)

I = pd.read_csv(os.path.join(ROOT, "data/processed/intensities.csv"), dtype={"event_id": str})
rows = I[I.event_id == EVENT].reset_index(drop=True)
c = json.load(open(os.path.join(ROOT, "results/offset_calibration.json")))["c"]
J = Objective(Event(EVENT, rows), c=c)

x1, _ = current_practice(J, rows)
x2, _ = _best_magnitude(J, JMA[0], JMA[1])
cases = [
    ("1 current practice", "centroid of strongest stations, M by 1-D grid", x1),
    ("2 plausible improvement", "JMA official epicentre, M by 1-D grid", x2),
    ("3 clearly poor", "epicentre in Kanazawa, M 6.8", np.array([*KANAZAWA, 6.8])),
    ("4 boundary", "JMA epicentre, M = 8.0 (upper bound)", np.array([JMA[0], JMA[1], 8.0])),
    ("5 infeasible", "JMA epicentre, M = 3.0 (below lower bound)", np.array([JMA[0], JMA[1], 3.0])),
]
out = []
for name, desc, x in cases:
    comp = J.components(x)
    out.append(dict(case=name, description=desc, lat=round(x[0], 4), lon=round(x[1], 4), M=round(x[2], 2),
                    km_from_JMA=round(float(epicentral_km(JMA[0], JMA[1], x[0], x[1])), 1),
                    J=J(x), J_high=comp["J_high"], J_low=comp["J_low"], violation=comp["violation"],
                    rms_high=comp["rms_high"], high_inside_class=comp["high_inside_class"],
                    low_wrongly_4plus=comp["low_wrongly_4plus"]))
res = pd.DataFrame(out)
res["rank"] = res.J.rank().astype(int)
res.to_csv(os.path.join(ROOT, "results/fitness_audit.csv"), index=False)

# ------------------------------------------------------------------ spreadsheet with live formulas
wb = Workbook()
ws = wb.active; ws.title = "summary"
bold, blue = Font(bold=True), Font(color="0000FF")
ws["A1"] = "Five-case fitness audit, 2004 Chuetsu mainshock (event 20041023175600)"; ws["A1"].font = bold
params = [("c (offset)", c), ("depth_km (fixed)", DEPTH_KM), ("logARV = 1.83-0.66*log10(400)", LOG_ARV),
          ("low edge (top of intensity 3)", 3.5), ("w_high", 0.5), ("w_low", 0.5), ("infeasible base", INFEASIBLE)]
for k, (lab, v) in enumerate(params):
    ws.cell(3 + k, 1, lab); ws.cell(3 + k, 2, float(v)).font = blue          # inputs in blue: B3..B9
P = {"c": "summary!$B$3", "dep": "summary!$B$4", "arv": "summary!$B$5", "edge": "summary!$B$6",
     "wh": "summary!$B$7", "wl": "summary!$B$8", "inf": "summary!$B$9"}
head = ["case", "description", "lat", "lon", "M", "violation", "J_high", "J_low", "J (spreadsheet)", "J (python)", "difference"]
for j, h in enumerate(head):
    ws.cell(12, 1 + j, h).font = bold
n = len(rows); first, last = 2, n + 1
for k, (name, desc, x) in enumerate(cases):
    r = 13 + k
    ws.cell(r, 1, name); ws.cell(r, 2, desc)
    for j, v in enumerate(x):
        ws.cell(r, 3 + j, float(v)).font = blue
    lo = [-1, *LOWER]; up = [-1, *UPPER]
    ws.cell(r, 6, f"=MAX({lo[1]}-C{r},0)+MAX(C{r}-{up[1]},0)+MAX({lo[2]}-D{r},0)+MAX(D{r}-{up[2]},0)+MAX({lo[3]}-E{r},0)+MAX(E{r}-{up[3]},0)")
    col_err = 10 + 3 * k                                                    # error column of case k in "stations"
    from openpyxl.utils import get_column_letter as L
    e = L(col_err)
    ws.cell(r, 7, f"=SUMPRODUCT((stations!$E${first}:$E${last}=\"high\")*stations!{e}{first}:{e}{last}^2)/COUNTIF(stations!$E${first}:$E${last},\"high\")")
    ws.cell(r, 8, f"=SUMPRODUCT((stations!$E${first}:$E${last}=\"low\")*stations!{e}{first}:{e}{last}^2)/COUNTIF(stations!$E${first}:$E${last},\"low\")")
    ws.cell(r, 9, f"=IF(F{r}>0,{P['inf']}+F{r},{P['wh']}*G{r}+{P['wl']}*H{r})")
    ws.cell(r, 10, float(res.J[k]))
    ws.cell(r, 11, f"=I{r}-J{r}")
ws["A19"] = "Inputs in blue. 'J (python)' is from code/model.py; 'difference' should be ~0 (rounding only)."
ws["A20"] = "Expected ranking: 2 <= 1, both far below 3 and 4, and 5 (infeasible) last."

st = wb.create_sheet("stations")
sh = ["station_name", "lat", "lon", "intensity", "group", "class_lower", "class_upper"]
for k, (name, *_ ) in enumerate(cases):
    sh += [f"R_km case{k+1}", f"I_pred case{k+1}", f"error case{k+1}"]
for j, h in enumerate(sh):
    st.cell(1, 1 + j, h).font = bold
from openpyxl.utils import get_column_letter as L
for i, s in rows.iterrows():
    r = i + 2
    hi = s.instr_lower >= 3.5
    st.cell(r, 1, s.station_name_ja); st.cell(r, 2, float(s.lat)); st.cell(r, 3, float(s.lon))
    st.cell(r, 4, s.intensity); st.cell(r, 5, "high" if hi else "low")
    st.cell(r, 6, float(s.instr_lower)); st.cell(r, 7, 99.0 if s.intensity == "7" else float(s.instr_upper))
    for k in range(5):
        cr = 13 + k
        Rc = L(8 + 3 * k); Ic = L(9 + 3 * k); Ec = L(10 + 3 * k)
        lat, lon, M = f"summary!$C${cr}", f"summary!$D${cr}", f"summary!$E${cr}"
        epi = (f"12742*ASIN(SQRT(SIN((B{r}-{lat})*PI()/360)^2+COS({lat}*PI()/180)*COS(B{r}*PI()/180)"
               f"*SIN((C{r}-{lon})*PI()/360)^2))")
        st[f"{Rc}{r}"] = f"=SQRT(({epi})^2+{P['dep']}^2)"
        st[f"{Ic}{r}"] = (f"=2.68+1.72*(0.58*{M}+0.0038*{P['dep']}-1.29-LOG10({Rc}{r}+0.0028*10^(0.5*{M}))"
                         f"-0.002*{Rc}{r}+{P['arv']})+{P['c']}")
        st[f"{Ec}{r}"] = (f"=IF(E{r}=\"high\",IF({Ic}{r}<F{r},F{r}-{Ic}{r},IF({Ic}{r}>G{r},{Ic}{r}-G{r},0)),"
                         f"MAX(0,{Ic}{r}-{P['edge']}))")
st.cell(1, 23, "Intensity 7 has no upper edge: class_upper is set to 99.")
wb.save(os.path.join(ROOT, "results/fitness_audit.xlsx"))

pd.set_option("display.width", 200)
print(res[["case", "lat", "lon", "M", "km_from_JMA", "J", "J_high", "J_low", "violation", "rank"]].round(5).to_string(index=False))
