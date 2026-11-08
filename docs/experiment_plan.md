# Experiment plan, written 2026-11-07, before the main experiments

Formulation: v1 (frozen 2026-11-07, `docs/formulation_v1.md`). D = 3 (lat, lon, M).

## Common settings
- Budget: **2,000 objective evaluations per run** for every method. Every call of J counts.
- Seeds: **0–9 for tuning**, **100–109 for final runs**. Seeds are never reused across these roles.
- Saved for every run (`results/runs_*.csv`, one row per run): scenario, formulation version, method, settings, seed, evaluations, runtime, best J, J_high, J_low, bound violation, best x, epicentre error (km) and magnitude error against JMA.
- Convergence: best-so-far J after every evaluation (`results/curves_*.npz`).
- Software versions: `results/environment.txt`.

## Phase 1: parameter study (dev events only, seeds 0–9)
| SN | limit | Note |
|---|---|---|
| 10 | 15 (5D) | |
| 10 | 45 (15D) | |
| 30 | 15 (5D) | |
| 30 | 45 (15D) | |

20 dev events × 4 settings × 10 seeds = 800 runs.
**Selection rule, fixed in advance:** lowest mean over dev events of the median final J. Ties (difference < 1%) go to the smaller SN. The rule uses only J, never the JMA answer, because a real user would not know the answer.

## Phase 2: final comparison (dev events, seeds 100–109)
| Method | Runs per event | Notes |
|---|---|---|
| ABC, selected setting | 10 | |
| Random search | 10 | Uniform in the bounds, 2,000 evaluations |
| Current practice | 1 | Strongest-station centroid + magnitude grid (401 evaluations); deterministic |
| Simple heuristic | 1 | 4+ stations' weighted centroid + magnitude grid (401 evaluations); deterministic |
| ABC without scouts | 10 | Same setting, limit = ∞ (ablation) |

Reported per method: median and IQR of final J, best and worst; epicentre error (km); |M error|; feasibility rate; number of runs without a feasible solution; runtime; scout events per run. Convergence plot: median best-so-far J against evaluations, with an IQR band.

## Phase 3: validation (after phases 1–2, nothing changed)
- Observation session 2: re-download the 13 validation events (`--session 2026-11-07_s2`) and rebuild. (Done on 7 Nov; the copy was byte-identical to session 1 and was removed on 8 Nov. See the diary.)
- Run the phase-2 methods with the same settings and seeds 100–109.
- Compare the epicentre and magnitude errors with the dev results. Predicted outcome before looking: similar location errors (about 5–15 km) and a larger magnitude error, because c was fitted on other regions.

## Phase 4: stress test and sensitivity
- Stress test: Noto 2024 M7.6, all phase-2 methods. Expected: the point-source model fits poorly.
- Sensitivity, 5 seeds (100–104) on dev events, compared with the same 5 seeds on the original:
  1. Change one measured input: remove the single strongest reading of each event.
  2. Stricter constraint: the epicentre must lie within 50 km of the strongest-shaking station.
  3. Alternative weight: w_high = 0.8, w_low = 0.2.
- Weakness case: a feasible candidate that scores better than JMA's answer but is wrong, to separate model flaws from search failures.

## What would count as failure
- ABC not better than random search at 2,000 evaluations: report it as a result.
- ABC worse than current practice on location: report it, and explain whether J or the search is to blame by comparing J values.
