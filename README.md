# Task 4 – ABC: locating earthquakes from shaking reports

Week 9 assignment (Artificial Bee Colony). Using only the shaking intensity reported by seismic
stations, estimate an earthquake's epicentre, depth and magnitude with ABC, and compare the
estimate with JMA's official solution.

Status (2026-11-08): three observation sessions (1: Niigata–Hokuriku, 6 Nov; 2: Kyushu, 7 Nov; 3: Kinki–Chūgoku,
7 Nov); formulation v1 frozen after the five-case audit; ABC implemented, traced by hand and tested; parameter study,
final dev comparison, validation, stress test, sensitivity and the new-region transfer test done.
Report: Google Doc "Bio Computing - Task 4".

## Folder layout

```
Task 4 - ABC Earthquake Epicentre/
├── README.md, requirements.txt
├── config/events.csv            earthquakes, with role (dev / validation / stress_test / exclude) and reason
├── code/
│   ├── scrape_jma.py            scraper (standard library only)
│   ├── model.py                 forward model and objective J(x)  (formulation v1)
│   ├── calibrate_offset.py      offset c from dev events
│   ├── fitness_audit.py         five-case audit (CSV + spreadsheet with live formulas)
│   ├── bee_colony.py            the ABC implementation
│   ├── manual_trace.py          3-source, 1-cycle trace + forced scout (CSV + spreadsheet)
│   ├── baselines.py             current practice, heuristic, random search
│   ├── run_experiments.py       tune / final / validate / stress / sensitivity
│   ├── analyze.py               tables and figures
│   ├── weakness_case.py         objective landscape and the Sado 2012 weakness case
│   └── run_single.py            one event, one seed, optional changes (for the live defence)
├── tests/                       test_scraper.py, test_model.py, test_abc.py (all offline)
├── docs/
│   ├── formulation_v1.md        FROZEN formulation, audit, traceability, change log
│   ├── experiment_plan.md       written before the main runs
│   ├── experiment_diary.md      dated record of what happened
│   ├── data_dictionary.md
│   ├── defence_prep.md          worked numbers and commands for the live defence
│   └── ai_use_declaration.md    draft, complete before submission
├── data/raw/<session>/          untouched JMA responses + metadata; scrape_log.csv
├── data/processed/              hypocentres.csv, intensities.csv
└── results/                     run logs, summaries, audit, trace, figures, environment.txt
```

## How to run (on your Mac, in Terminal)

```bash
cd ~/Documents/Programming/Python/biocomputing/"Task 4 - ABC Earthquake Epicentre"
pip3 install -r requirements.txt                       # numpy, pandas, matplotlib, openpyxl, scipy
python3 tests/test_scraper.py && python3 tests/test_model.py && python3 tests/test_abc.py

# data (each run of `events` = one dated observation session)
# session 1: Niigata-Hokuriku (default box 36.3-38.6 N, 136.6-140.0 E), 6 Nov 2026
python3 code/scrape_jma.py --session 2026-11-06 search
python3 code/scrape_jma.py --session 2026-11-06 events
# session 2: Kyushu, 7 Nov 2026
python3 code/scrape_jma.py --session 2026-11-07_s2_kyushu search --box 31.0 34.0 129.5 132.2 --out events_candidates_kyushu.csv
python3 code/scrape_jma.py --session 2026-11-07_s2_kyushu events --list events_candidates_kyushu.csv
# session 3: Kinki-Chugoku, 7 Nov 2026
python3 code/scrape_jma.py --session 2026-11-07_s3_kinki search --box 34.0 35.8 132.0 136.0 --out events_candidates_kinki.csv
python3 code/scrape_jma.py --session 2026-11-07_s3_kinki events --list events_candidates_kinki.csv
python3 code/scrape_jma.py build

# model and checks
python3 code/calibrate_offset.py        # c from dev events
python3 code/fitness_audit.py           # five-case audit
python3 code/manual_trace.py            # hand-trace material

# experiments (about 4 + 4 + 1 + 3 minutes)
python3 code/run_experiments.py tune
python3 code/run_experiments.py final
python3 code/run_experiments.py validate
python3 code/run_experiments.py stress
python3 code/run_experiments.py sensitivity
python3 code/run_experiments.py transfer        # new regions (sessions 2-3)
python3 code/analyze_transfer.py
python3 code/fig_formulation.py
python3 code/analyze.py
python3 code/weakness_case.py
python3 code/budget_check.py           # post-hoc check: budget 800 vs 2,000

# one event, one seed, with a change (live defence)
python3 code/run_single.py 20041023175600 --seed 3 --drop-station 3710044
```

## Data source

**JMA seismic intensity database** (気象庁 震度データベース検索): https://www.data.jma.go.jp/eqdb/data/shindo/index.html

The page is a JavaScript app. The scraper calls the same endpoint the page uses:

| Request (POST to `api/`) | Returns |
|---|---|
| `mode=search` + date range and filters | List of earthquakes: id, origin time, region, lat, lon, depth, magnitude (JMA), maximum intensity |
| `mode=event`, `id=<YYYYMMDDhhmmss>` | `hyp`: JMA's official hypocentre. `int`: every station's intensity class, coordinates and code |

Notes from the source:
- The database rejects end dates after its latest update (2026-11-04 at the time of writing).
- Municipal and NIED stations are included from 1997 onwards. For Niigata that is from 10 Nov 1997, and NIED from 26 May 2004 (JMA disclaimer page).
- Station coordinates are given to 0.01° (about 1 km).
- Terms: JMA website content can be reused with credit to the source (Japanese government standard terms of use). Cite it as "Japan Meteorological Agency, Seismic Intensity Database". Requests are spaced 2 s apart to keep the load low.

## Observation sessions (for the brief's "30 measurements over 3 sessions")

Each run of `events` with its own `--session` name is one dated observation session. The raw responses, the request metadata and the SHA-256 hashes show exactly what was received and when.

| Session | Folder | When (JST) | Region | Earthquakes | Used for |
|---|---|---|---|---|---|
| 1 | `data/raw/2026-11-06` | 6 Nov 2026, 16:32 | Niigata–Hokuriku | 43 | Development (build and tune), validation (reserved), stress test |
| 2 | `data/raw/2026-11-07_s2_kyushu` | 7 Nov 2026, 17:59 | Kyushu | 23 | Transfer test: frozen method, nothing re-tuned |
| 3 | `data/raw/2026-11-07_s3_kinki` | 7 Nov 2026, 18:00 | Kinki–Chūgoku | 6 | Transfer test: frozen method, nothing re-tuned |

The nationwide catalogue (178 earthquakes) was downloaded in all three sessions and was byte-identical each time,
so the source did not change. Two earlier repeat downloads of session-1 events (7 Nov) were identical to session 1
and were removed on 8 Nov (see `docs/experiment_diary.md`).

## Processed tables

**hypocentres.csv**: one row per event: `event_id, origin_time_jst, region_ja, lat, lon, depth_km, mag_jma, max_intensity, n_stations, session`

**intensities.csv**: one row per station reading:

| Column | Meaning |
|---|---|
| `event_id`, `station_code`, `station_name_ja`, `lat`, `lon` | Station and event |
| `intensity_ja` | Original label, e.g. 震度５弱 |
| `intensity` | Short label: 1, 2, 3, 4, 5-, 5+, 6-, 6+, 7 |
| `instr_lower`, `instr_upper` | Instrumental intensity interval of the class (JMA definition), e.g. 5- = [4.5, 5.0) |
| `instr_mid` | Midpoint of the interval (7 is capped at 7.0) |
| `session` | Which session folder the reading came from |

JMA reports intensity **classes**, not exact values. Whether the model uses the midpoint or the whole interval is a modelling decision to record in the formulation.

## Data split (decided 2026-11-06, before any modelling)

Split by earthquake sequence and region, not by individual earthquake. Aftershocks of one sequence
share stations and wave paths, so a random split would leak information from development into validation.

| Role | Events | Readings (all / intensity 4+) | Which earthquakes | Why |
|---|---|---|---|---|
| `dev` | 20 | 16156 / 1024 | 2004-05 Chuetsu sequence (14), northern Nagano 2011-2026 (4), Sado 2012, Tochigi 2013 | Build, check and tune the model and ABC. The Chuetsu sequence is the Nagaoka case. |
| `validation` | 13 | 10701 / 691 | Chuetsu-oki 2007 (2), Noto offshore 2007 (1), Noto 2020-2024 (10) | Reserved. Not used until the model and ABC settings are frozen. Different regions test whether the method generalises. 13 of 34 usable events = 38% (the brief asks for at least 20%). |
| `stress_test` | 1 | 2846 / 419 | Noto M7.6, 1 Jan 2024 | Fault about 150 km long; a point-source model should fail. Reported separately as a model-limit case. |
| `exclude` | 9 | 1883 / 32 | Small events with 1-6 stations at intensity 4+ | Fewer than 8 usable readings (2 per unknown) cannot constrain 4 unknowns. |

Rule for `exclude`: fewer than 8 stations with intensity 4+ (2 readings per unknown parameter).
The role and the reason for each earthquake are in `config/events.csv`.

The Kyushu (session 2) and Kinki–Chūgoku (session 3) earthquakes were split by the same rules before any runs:
17 + 5 transfer events, 5 with Mj ≥ 7.0 kept as a new-region stress test, 2 excluded (fewer than 8 readings at 4+).

## Model reference (implemented in code/model.py; see docs/formulation_v1.md)

Formulas used in Japan's national seismic hazard maps:
- Si & Midorikawa (1999), peak ground velocity on stiff soil:
  log PGV = 0.58 M + 0.0038 D + d − 1.29 − log(X + 0.0028·10^(0.5 M)) − 0.002 X
  (d = 0 for crustal earthquakes; X = distance to the fault in km; D = depth in km)
- Midorikawa et al. (1999), velocity to JMA instrumental intensity: I = 2.68 + 1.72 log PGV (valid for 4 ≤ I ≤ 7)

Source: Headquarters for Earthquake Research Promotion, hazard map methodology,
https://jishin.go.jp/main/choukihyoka/04mar_kakuritsu/setsumei_3.pdf
