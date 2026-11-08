# Live defence preparation (10–12 minutes, no AI)

The lecturer may ask for any of the items below. Practise each one without notes.

## 1. Trace one raw observation into the objective

**Raw record:** `data/raw/2026-11-06/event_20041023175600.json`, station code 3710044, 長岡市東川口＊ (Nagaoka, Higashikawaguchi), lat 37.27, lon 138.86, intensity 震度７ (char "7").

1. `scrape_jma.py build` turns it into a row of `intensities.csv`: intensity "7", interval [6.5, 7.0], where 7.0 really means "no upper edge".
2. `model.Event` puts it in the **high** group (lower edge 6.5 ≥ 3.5) with upper edge = ∞.
3. For a candidate x, its error enters J_high. Example, at JMA's answer x = (37.2917, 138.8670, M 6.8), depth fixed at 10 km:

| Step | Value |
|---|---|
| Epicentral distance (haversine) | 2.491 km |
| R = √(2.491² + 10²) | 10.306 km |
| 0.58 M | 3.944 |
| 0.0038 D | 0.038 |
| log10(R + 0.0028·10^(0.5M)) = log10(10.306 + 7.033) | 1.2390 |
| 0.002 R | 0.0206 |
| log PGV = 3.944 + 0.038 − 1.29 − 1.2390 − 0.0206 | 1.4324 |
| log ARV = 1.83 − 0.66 log10(400) | 0.1126 |
| I_pred = 2.68 + 1.72 (1.4324 + 0.1126) + 0.418 | **5.755** |
| Error: observed class starts at 6.5, so e = 6.5 − 5.755 | 0.745 |
| Contribution to J_high | 0.745² / 221 = 0.00251 (221 high stations), times weight 0.5 |

Point to discuss: even at the official answer, the strongest station is under-predicted by a full class. A point source cannot reproduce near-fault shaking (assumption A1).

## 2. Calculate one candidate's score
Use `results/fitness_audit.xlsx`: each case's J is a live formula over the 1,495 stations. By hand, use the 6-station instance in `results/manual_trace.xlsx`.
- J = 0.5 · mean(e_high²) + 0.5 · mean(e_low²)
- Check from the command line: `python3 code/run_single.py 20041023175600 --score 37.2917 138.867 6.8` gives J 0.02967 (high 0.02308, low 0.03626).

## 3. Explain an employed-bee update (from the manual trace, part A, first employed step)
- Source i = 0: x₀ = (37.7503, 139.8889, 7.1027), J = 2.14898
- Random choices: partner k = 1, x₁ = (36.6306, 137.5007, 7.4942); dimension j = 1 (longitude); φ = −0.3939
- v₀,lon = 139.8889 + (−0.3939)(139.8889 − 137.5007) = 139.8889 − 0.9408 = **138.9481** (inside the bounds)
- J(v) = 1.15955 < 2.14898, so it is **accepted** and trial₀ is reset to 0.

## 4. Explain the onlooker probabilities (same cycle)
After the employed phase: J = (1.15955, 1.58292, 2.90297) → F = 1/(1+J) = (0.46306, 0.38716, 0.25622) → p = F / ΣF = (0.4185, 0.3499, 0.2316).
- Weakness to mention: with F = 1/(1+J), small differences in J give almost equal probabilities, so selection pressure is weak late in the run.

## 5. Explain a scout event
- Manual trace part B (forced, limit = 0): source 1 had the most failures (trial 4), so it was abandoned and replaced at random (J = 4.00). The best-so-far (1.15955) was **not** lost, because it is stored separately.
- In the real runs (limit = 45 = 15D), scouts are rare (median 1 per run). The ablation shows they rarely change the median but prevent bad outliers: worst dev J 0.043 with scouts vs 0.093 without.

## 6. Apply an unseen change and rerun with a given seed
| Change the lecturer might ask for | Command |
|---|---|
| A station's reading is lost | `python3 code/run_single.py <event> --seed <s> --drop-station <code>` |
| A blocked or forbidden area for the epicentre | `... --exclude-box LAT0 LAT1 LON0 LON1` |
| Tighter magnitude range | `... --min-M 5 --max-M 6.5` |
| Different offset or weights | `... --c 0.3 --w-high 0.8 --w-low 0.2` |
| No scouts / different colony | `... --limit 0` / `... --SN 30 --limit 15` |
Explain the result by comparing J_high and J_low before and after.

## 7. Why does a poor or infeasible candidate get its score?
- Kanazawa (213 km away): strong stations predicted far too weak → J_high = 1.27 dominates.
- M = 8.0 at the right place: quiet stations predicted at 4+ → J_low = 0.88 dominates.
- M = 3.0: outside the bounds → J = 10⁶ + violation (1.0), always ranked last.

## 8. Key numbers to remember
- 43 earthquakes scraped (31,586 readings); 20 dev / 13 validation / 1 stress / 9 excluded.
- Formulation v1: x = (lat, lon, M), depth 10 km, c = +0.418, weights 0.5/0.5, budget 2,000.
- Chosen ABC: SN = 10, limit = 45. All four settings were within 1.1%.
- Dev: ABC has a lower J than current practice on 20/20 events (Wilcoxon p = 1.9×10⁻⁶), but the same location error (7.1 vs 7.2 km). The model limits accuracy, not the search.
- Validation (13 reserved events, session-2 data): ABC lower J than current practice on 12/13 (13th tied; p = 5×10⁻⁴), location 8.9 vs 9.9 km (no significant difference, p = 0.79). Magnitude bias +0.24 on Noto: the offset c was fitted on Niigata/Nagano and does not transfer. Outlier: 2024-01-01 16:12 aftershock, about 90 km off for every method (mainshock shaking in its readings).
