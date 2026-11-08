# Data dictionary

All files are UTF-8 CSV unless noted. Japanese names are kept exactly as JMA publishes them.

## Raw data (`data/raw/`)

| File | Contents |
|---|---|
| `<session>/event_<id>.json` | JMA response for one earthquake, saved untouched: `hyp` (official solution) and `int` (one entry per station) |
| `<session>/event_<id>.meta.json` | URL, form data, UTC retrieval time, HTTP status, bytes, SHA-256 of the JSON |
| `<session>/catalogue_*.json` | JMA catalogue search response (session 1) |
| `scrape_log.csv` | One row per request: `retrieved_utc, file, mode, event_id, http_status, bytes, sha256` |

Raw station fields in `int`: `name` (station name; "＊" marks non-JMA stations, see README), `lat`, `lon` (0.01°), `code` (station code), `int` (intensity label, e.g. 震度５弱), `char` (1–4, A–D, 7), `mark`, `zidx` (map drawing order).

## Processed data (`data/processed/`, built by `scrape_jma.py build`)

### hypocentres.csv (one row per earthquake)
| Column | Type | Unit | Meaning |
|---|---|---|---|
| event_id | text | | JMA id = origin time YYYYMMDDhhmmss (JST) |
| origin_time_jst | text | JST | Origin time |
| region_ja | text | | JMA epicentre region name |
| lat, lon | float | deg | JMA official epicentre (the reference "truth") |
| depth_km | float | km | JMA official depth |
| mag_jma | float | Mj | JMA magnitude |
| max_intensity | text | | Strongest intensity observed |
| n_stations | int | | Station readings in the event |
| session | text | | Observation session folder the data came from |

### intensities.csv (one row per station reading)
| Column | Type | Unit | Meaning |
|---|---|---|---|
| event_id | text | | Earthquake |
| station_code, station_name_ja | text | | Station |
| lat, lon | float | deg | Station position (0.01°) |
| intensity_ja | text | | Original label |
| intensity | text | | 1, 2, 3, 4, 5-, 5+, 6-, 6+, 7 |
| instr_lower, instr_upper | float | JMA instrumental intensity | Interval of the class: 1 = [0.5, 1.5) … 5- = [4.5, 5.0) … 7 = [6.5, ∞), stored as 7.0 |
| instr_mid | float | | Midpoint (descriptive only; the model uses the interval) |
| session | text | | Observation session |

## Configuration (`config/`)
| File | Columns |
|---|---|
| events.csv | `event_id, origin_time_jst, region_ja, lat, lon, depth_km, mag_jma, max_intensity, role, reason`. Role is dev, validation, stress_test or exclude. |
| events_candidates.csv | The catalogue filter output (same first 8 columns) |

## Results (`results/`)
| File | Contents |
|---|---|
| offset_calibration.json / _per_event.csv | Fitted offset c and per-event fit at the official solutions |
| fitness_audit.csv / .xlsx | Five-case audit (Python and live-formula versions) |
| manual_trace_program.csv / manual_trace.xlsx | Program trace of one ABC cycle plus the forced scout, and the spreadsheet recomputation |
| chosen_params.json | Selected SN and limit, the selection rule and the parameter-study table |
| runs_{tune,final,validation,stress,sensitivity}.csv | One row per run (columns below) |
| curves_*.npz | Best-so-far J every 10 evaluations; key = `method|event_id|seed`, plus `grid` |
| summary_*.csv, per_event_*.csv | Aggregates produced by `analyze.py` |
| weakness_case.csv, fig_landscape.png | Objective landscape and the Sado 2012 weakness case |
| fig_*.png | Figures |
| environment.txt | Python and package versions used |

### runs_*.csv columns
| Column | Meaning |
|---|---|
| scenario | tune, final_dev, validation, stress, sens_original, sens_drop_strongest, sens_weights_0.8_0.2, sens_within_50km |
| version | Formulation version (v1) |
| event_id, method, settings, seed | What was run (seed empty for deterministic methods) |
| evaluations, runtime_s | Objective evaluations used; wall time in seconds |
| J, J_high, J_low | Final objective and its two parts (intensity²) |
| violation, feasible | Bound violation of the answer; True if within all bounds |
| lat, lon, M | The answer |
| epi_err_km | Distance from JMA's epicentre, km |
| M_err | Answer M minus JMA Mj |
| scouts | Number of scout events in the run (ABC only) |
