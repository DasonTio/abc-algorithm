# Formulation v1: FROZEN 2026-11-07

Code: `code/model.py`. Calibration: `results/offset_calibration.json` (c = +0.418).
Audit: `results/fitness_audit.csv` and `results/fitness_audit.xlsx`.
Nothing in this file, `model.py` or the offset may change after this date without a new version (v2) and a dated note in the change log below.

## Decision

- **Who decides:** a seismologist or emergency operator who has to locate an earthquake and judge its size from shaking-intensity reports alone. Examples: historical earthquakes, regions or moments without waveform data, and a quick cross-check of an automatic solution.
- **Current practice (baseline):** place the epicentre at the strongest-shaking station(s), i.e. the centroid of the stations in the highest observed class, and pick the magnitude that best fits.
- **Success measure in real units:** epicentre error (km) and magnitude error (Mj units) against JMA's official solution, on validation earthquakes not used in development.

## Decision variables x (D = 3)

| Variable | Meaning | Type | Unit | Lower | Upper | Controllable |
|---|---|---|---|---|---|---|
| lat | Epicentre latitude | continuous | deg N | 36.0 | 38.8 | estimated |
| lon | Epicentre longitude | continuous | deg E | 136.3 | 140.3 | estimated |
| M | Magnitude, JMA scale (Mj) | continuous | Mj | 4.0 | 8.0 | estimated |

Depth is **fixed at 10 km** (see the change log). The bounds contain every listed earthquake with margin.

## Forward model: how x produces an outcome

1. R = sqrt(epicentral distance² + 10²) km: hypocentral distance, point source (A1).
2. log PGV = 0.58 M + 0.0038·10 − 1.29 − log(R + 0.0028·10^(0.5M)) − 0.002 R: Si & Midorikawa (1999), crustal, d = 0 (A2).
3. log ARV = 1.83 − 0.66 log 400: the same ground at every station, AVS30 = 400 m/s (A3).
4. I_pred = 2.68 + 1.72 (log PGV + log ARV) + c, with c = +0.418: Midorikawa et al. (1999) plus the calibrated offset.

## Objective J(x), minimised (unit: intensity²)

| Term | Stations | Error e per station | Why |
|---|---|---|---|
| High | Observed 4+ | Distance from I_pred to the observed class interval (0 inside; 7 has no upper edge) | Readings are classes; the conversion is valid for 4–7 |
| Low | Observed 1–3 | max(0, I_pred − 3.5) | Uses only "did not reach 4", which removes the selection bias of the 4+ cut-off |

J = 0.5 · mean(e_high²) + 0.5 · mean(e_low²). The weights give each kind of evidence equal say. An alternative weighting is tested in the sensitivity analysis.

Onlooker fitness: F(x) = 1 / (1 + J(x)), always in (0, 1].

## Constraints

| Constraint | Kind | Handling |
|---|---|---|
| Each variable inside its bounds | Hard | J = 10⁶ + total bound violation, so an infeasible x always ranks below any feasible one. ABC clips new candidates to the bounds, so it only evaluates feasible points. |

## Offset calibration (dev events only, at JMA epicentre and Mj, depth 10 km)

| | c = 0 | c = +0.418 |
|---|---|---|
| Mean J over 20 dev events | 0.088 | 0.044 |
| RMS error, 4+ stations | 0.38 | 0.24 intensity |
| 4+ readings predicted inside their class | 49% | 61% |
| 1–3 readings wrongly predicted 4+ | 4.1% | 13.4% |

## Five-case fitness audit (2004 Chūetsu mainshock, 1,495 stations: 221 high, 1,274 low)

Calculated in Python and, independently, as live formulas in `results/fitness_audit.xlsx` (recalculated in LibreOffice). The two agree to machine precision.

| Case | x (lat, lon, M) | km from JMA | J_high | J_low | J | Rank |
|---|---|---|---|---|---|---|
| 1 Current practice: strongest-station centroid, best M | 37.270, 138.860, 6.69 | 2.5 | 0.0299 | 0.0237 | 0.0268 | 2 |
| 2 Plausible improvement: JMA epicentre, best M | 37.292, 138.867, 6.69 | 0.0 | 0.0302 | 0.0228 | 0.0265 | 1 |
| 3 Clearly poor: Kanazawa, M 6.8 | 36.561, 136.656, 6.80 | 212.6 | 1.268 | 0.132 | 0.700 | 4 |
| 4 Boundary: JMA epicentre, M = 8.0 (upper bound) | 37.292, 138.867, 8.00 | 0.0 | 0.468 | 0.877 | 0.672 | 3 |
| 5 Infeasible: M = 3.0 (below the bound) | 37.292, 138.867, 3.00 | 0.0 | 11.08 | 0.000 | 1,000,001 | 5 |

**Expected ranking:** 2 ≤ 1, both far below 3 and 4, and 5 last. **Computed ranking:** 2, 1, 4, 3, 5. They agree.

What the audit shows:
- **The two terms do different jobs.** In case 4 (M too large) the low term carries the penalty: 0.877, because quiet stations are predicted to shake. In case 3 (wrong place) the high term carries it: 1.27, because strong stations are predicted too weak.
- **Resolution limit.** Cases 1 and 2 are 2.5 km apart, and their J values differ by only 1%. J cannot meaningfully separate solutions a few kilometres apart. Location results are therefore reported in km, and differences under about 5 km are not treated as meaningful.

## Check: does the minimum of J sit near the truth? (exhaustive grid, dev events)

| Event | M (JMA) | Grid minimum, km from JMA | M, grid / JMA |
|---|---|---|---|
| Chūetsu 2004-10-23 | 6.8 | 3.5 | 6.70 / 6.8 |
| Chūetsu aftershock 2004-10-24 | 5.0 | 7.5 | 5.30 / 5.0 |
| Northern Nagano 2014 | 6.7 | 11.0 | 6.15 / 6.7 |
| Sado 2012 (offshore) | 5.7 | 15.0 | 6.20 / 5.7 |

A grid search checks every point, so the remaining gaps are **model error, not search error**. Northern Nagano 2014 ruptured a fault about 20 km long, so the point-source model fits it less well.

## Assumptions (to state in the report)

- A1: Point source, depth fixed at 10 km. Weak for long ruptures (M ≥ 7: the Noto 2024 stress test).
- A2: Every event treated as crustal (d = 0).
- A3: The same ground at every station. The average effect is absorbed by c; differences between stations are not.
- A4: Station coordinates rounded to 0.01° (about 1 km) by JMA.
- A5: Magnitude is on the Mj scale through c, not Mw.

## Traceability

| Term or constraint | Definition, unit | Supporting records | Assumptions | Justification |
|---|---|---|---|---|
| High term | Interval error², intensity² | `intensities.csv` rows with instr_lower ≥ 3.5 (dev: 1,024) | A1–A4 | Conversion valid for 4–7; the classes are intervals |
| Low term | One-sided error², intensity² | `intensities.csv` rows with instr_lower < 3.5 (dev: 15,132) | A1–A4 | Removes the 4+ selection bias |
| c = +0.418 | Intensity units | `results/offset_calibration*.{json,csv}` (dev only) | A3, A5 | Mean residual at the official solutions |
| Depth = 10 km | km | Audit depth profile, below | A1 | Depth not resolvable from intensities |
| Bounds | deg, Mj | `hypocentres.csv` (every event inside) | | Catalogue region and magnitudes |
| Weights 0.5 / 0.5 | none | | Equal weight per evidence type | Tested in the sensitivity analysis |

## Change log

- **v0 (2026-11-06, draft):** x = (lat, lon, depth, M), D = 4, c = +0.432.
- **v1 (2026-11-07, frozen):** depth fixed at 10 km, D = 3, c recalibrated to +0.418.
  Reason: during the audit, J at the official Chūetsu epicentre kept decreasing as depth went towards 0 km (with the best M per depth: J = 0.0245 at 0 km, 0.0265 at 10 km, 0.0276 at 13 km, 0.0457 at 40 km). Intensity data carry almost no depth information, so a free depth drifts to the surface and adds a meaningless dimension. Fixing the depth at 10 km is standard practice (JMA and USGS) when depth is unresolved.
