# Experiment diary

Dated record of what was done, what went wrong and what was changed. Times are JST.

## 2026-11-06 (Fri)
- Chose the problem: locating earthquakes from JMA shaking-intensity reports with ABC (continuous variables, ground truth available).
- Inspected the JMA intensity database (a JavaScript app; it POSTs to `api/`). Wrote `scrape_jma.py` (standard library only, raw responses saved with SHA-256).
- **Observation session 1 (16:32–16:34):** catalogue (178 earthquakes with maximum intensity 5+ since 1997; 43 shallow events in the Niigata/Hokuriku box) and all 43 events, 31,586 station readings. All 44 requests HTTP 200. Data checks passed: no missing events, duplicates or coordinate conflicts; hypocentres match the catalogue exactly.
- Formula check at the official solutions: RMSE 0.44–0.73 intensity, mean residual about +0.45 (predictions too weak).
- Split decided before any modelling: by sequence and region. 20 dev, 13 validation (Chūetsu-oki 2007, Noto 2007, Noto 2020–24), 1 stress test (Noto M7.6), 9 excluded (fewer than 8 readings at 4+).
- Bias analysis on dev only: the per-event residual ranged from −0.32 to +0.99 and correlated with magnitude (−0.65). This pointed to the selection effect of the 4+ cut-off. Added the one-sided low term, then fitted an offset c on dev: c = +0.432 (draft v0, depth free).

## 2026-11-07 (Sat)
- **Five-case audit, first attempt (v0):** the ranking disagreed with expectations. The depth-0 boundary case scored best, and the official solution scored worse than current practice. Depth profile at the official epicentre: J fell steadily towards 0 km. Conclusion: intensities do not resolve depth.
- **Revision → v1:** depth fixed at 10 km (standard practice when depth is unresolved), D = 3, c recalibrated to +0.418. Audit repeated with new cases (boundary = M at its upper bound, infeasible = M below its lower bound). The ranking now matches the expectation (2, 1, 4, 3, 5). The spreadsheet recomputation in LibreOffice agrees with Python to machine precision. **Formulation v1 frozen.**
- Wrote `bee_colony.py`. Renamed it from `abc.py` because that name shadows Python's built-in `abc` module. Tests: sphere optimum, exact budget, monotone curve, synthetic known-optimum earthquake recovered (J < 10⁻³, < 5 km), trial/acceptance rules, scouts on/off, best never lost.
- Manual trace (6 real stations, 3 sources, 1 cycle + forced scout with limit = 0). The first choice of weak stations was about 300 km away, which made the low term trivially zero, so it was replaced by the 3 nearest intensity-3 stations. Spreadsheet vs program: J agrees to 6×10⁻¹⁴; all accept/reject decisions and roulette probabilities are identical.
- Experiment plan written before the main runs (`docs/experiment_plan.md`).
- **Parameter study** (800 runs): all four settings within 1.1%. By the fixed rule (ties go to the smaller SN) the choice is SN = 10, limit = 45 (= 15D).
- **Final dev comparison** (640 runs): ABC has a lower J than current practice, random search and the heuristic on 20/20 events (Wilcoxon p = 1.9×10⁻⁶), but the same location accuracy as current practice (median 7.1 vs 7.2 km). The limit is the model, not the search.
- Stress test (Noto M7.6): ABC 28 km from JMA; current practice 56 km.
- Sensitivity (400 runs): removing the strongest reading moves the answer by up to 35 km. Weights 0.8/0.2 raise the magnitude bias to +0.18. A 50 km search radius changes nothing.
- Weakness case: for Sado 2012 (offshore) the objective's minimum is 14 km from JMA's epicentre and scores better (J 0.013 vs 0.048): a model flaw.
- The objective landscape figure had a wrong caption ("darker = better"). Fixed: yellow = lower J.

- **Observation session 2 (15:09–15:10):** the 13 validation events were re-downloaded after the freeze. A first attempt failed because the command put `--session` after `events` (argparse error); the README order was fixed. All 13 responses were byte-identical to session 1 (same SHA-256). `build` now takes these 13 events from session 2.
- **Validation** (416 runs, seeds 100–109, nothing changed): ABC has a lower J than current practice on 12/13 events, with the 13th tied within 10⁻⁵ (Wilcoxon p = 5×10⁻⁴), and lower than random search and the heuristic on 13/13. Location accuracy is again the same as current practice (median 8.9 vs 9.9 km; 6 better, 7 worse; p = 0.79). New finding: magnitude bias +0.24 (dev +0.02), largest for Noto 2020–24, so the offset c is region-dependent. Outlier: the 2024-01-01 16:12 aftershock (2 min after M7.6) is placed about 90 km off by every method; its 4+ readings are probably mainshock shaking.
- Report section 7 written, conclusion and limitations updated, references [6] and [7] now cited.
- Deadline is tonight, so session 3 is planned for this evening (same day as session 2), and this is stated in the report.

- **Rethink of the sessions (17:55):** sessions 2 and 3 are repeat downloads; they show the source is stable but add no information. The report now says so. To make the later sessions informative, two new regions were collected as a transfer test.
- **Observation session 4 (17:59, Kyushu) and session 5 (18:00, Kinki–Chugoku):** same selection rules (intensity 5+ since 1997, depth ≤ 40 km); 23 + 6 earthquakes, 23,204 readings. The nationwide catalogue was byte-identical to session 1. Split by the session-1 rules before any runs: 17 Kyushu + 5 Kinki transfer events, 5 with Mj ≥ 7.0 as new-region stress tests, 2 excluded (< 8 readings at 4+).
- Code change for the transfer test only: search bounds per region (catalogue box ± 0.3°) in `model.py`; Niigata bounds unchanged. Re-running a validation event reproduced the saved J values exactly.
- **Transfer results** (864 runs, frozen c and settings): Kyushu ABC 5.7 km vs current practice 6.9 km; Kinki 6.7 vs 7.9 km; lower J on 22/22; closer on 13/22 (p = 0.39). No magnitude bias (−0.03, −0.04), unlike Noto (+0.24). Diagnosis: best c per group 0.42 / 0.66 / 0.35 / 0.25, so Noto is the exception. Two coastal failures (Tottori 2016 40 km, western Shimane 2018 27 km): J at ABC's answer is lower than at JMA's, the same weakness as Sado.
- Report: section 7 extended (transfer table and figure), formulation figure and parameter table added in section 3, figures renumbered.

## 2026-11-08 (Sun)
- **Session renumbering and cleanup.** The two repeat downloads of 7 Nov (`2026-11-07_s2`: 13 validation events at 15:09; `2026-11-07_s3`: 2 events at 15:26) were byte-identical to session 1 (all 15 SHA-256 hashes match) and added no information, so they were deleted together with their 15 log rows. The new-region downloads were renumbered: Kyushu (7 Nov 17:59, formerly session 4) is now session 2 (`2026-11-07_s2_kyushu`) and Kinki–Chūgoku (7 Nov 18:00, formerly session 5) is now session 3 (`2026-11-07_s3_kinki`). Dates, times and hashes are unchanged. No result changes: the validation runs used copies identical to the session-1 files that `build` now uses.
- Removed files not needed to build or validate the model: the search animation (`animate_search.py` and its outputs), the post-hoc offset script (the per-region offset diagnosis is also in `analyze_transfer.py`), an unused HTML report builder and an outdated v0 copy of `model.py` outside the project folder.

- **Budget check (19:05, post hoc):** the median convergence curve of the 200 final dev runs has its elbow at about 800 evaluations (median J within 0.4% of its final value), so a smaller budget was considered. `code/budget_check.py` re-ran ABC and random search with budget 800 on the 55 dev, validation and transfer earthquakes (seeds 100–109; a seeded run with budget 800 is the first 800 steps of the 2,000 run). Result: only 59% of ABC runs had reached their final J at 800, 31% would move by more than 1 km (up to 43 km), and the median epicentre error was 7.3 km vs 6.8 km. Random search lost more (12.8 → 16.9 km). Decision: keep the planned budget of 2,000; report the elbow as a finding, not as a new setting, because the budget was fixed before the experiments and the curve comes from the test seeds.

## Still to do
- Report: insert the figures, check references and page count, finish the AI declaration.
