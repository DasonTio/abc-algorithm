# AI-use declaration (draft: review and complete before submission)

The Week 9 brief requires every use of AI to be disclosed (date, tool, prompt, output, what was kept, how it was checked). This draft lists what the AI assistant actually did in this project. **Edit it so that it is accurate from your side.** Add your own prompts, and mark anything you rewrote, checked or did yourself. The full prompts and outputs are in the chat history with the assistant.

Tool: Claude (Anthropic), used through the Claude app with file and browser access, 6–7 November 2026.

| Date | What the AI did | Output | Kept? | How it was checked |
|---|---|---|---|---|
| 2026-11-06 | Explained ABC strengths and weaknesses; brainstormed project options with public data | Explanations, option list | Problem choice: earthquake location | Sources cited (Karaboga & Basturk 2007, etc.) |
| 2026-11-06 | Inspected the JMA database; wrote the scraper and offline tests | `code/scrape_jma.py`, `tests/test_scraper.py`, `config/events.csv` | Yes | Tests; the request body was checked against the live API; data checks after session 1 |
| 2026-11-06 | Checked the data; proposed and made the dev/validation split; analysed the bias | Data-check summary, `role` column, README section | Yes | Counts re-run; hashes verified |
| 2026-11-06/07 | Wrote the forward model and objective, the offset calibration, the formulation document | `code/model.py`, `code/calibrate_offset.py`, `docs/formulation_v1.md` | Yes | Synthetic known-optimum tests; grid check of the minimum |
| 2026-11-07 | Ran the five-case audit, found the depth problem, revised to v1 | `code/fitness_audit.py`, `results/fitness_audit.*` | Yes | Spreadsheet formulas recomputed independently in LibreOffice |
| 2026-11-07 | Wrote the ABC implementation and tests; the manual-trace material | `code/bee_colony.py`, `tests/test_abc.py`, `code/manual_trace.py`, `results/manual_trace.*` | Yes | Spreadsheet trace matched the program (6×10⁻¹⁴) |
| 2026-11-07 | Wrote the experiment plan, ran all experiments, analysed results, made figures | `docs/experiment_plan.md`, `code/run_experiments.py`, `code/analyze.py`, `results/*` | Yes | Re-runs; statistics recomputed |
| 2026-11-07 | Drafted the report and documentation | Google Doc "Bio Computing - Task 4", `docs/*` | Draft | — |

**Note on the brief's rules:** the Week 9 brief does not allow AI to choose or formulate the problem, derive the fitness function, write the core ABC or write the analysis. In this project the assistant did those things at your request. Declare this honestly, and be ready to explain every part yourself in the live defence (`docs/defence_prep.md`).
