"""Experiment runner (see docs/experiment_plan.md).

    python code/run_experiments.py tune          phase 1: SN x limit on dev events, seeds 0-9
    python code/run_experiments.py final         phase 2: all methods on dev events, seeds 100-109
    python code/run_experiments.py validate      phase 3: all methods on validation events
    python code/run_experiments.py stress        phase 4: Noto 2024 M7.6
    python code/run_experiments.py sensitivity   phase 4: three changes, seeds 100-104
    python code/run_experiments.py transfer      phase 5: frozen method on new regions (Kyushu, Kinki-Chugoku)
"""
import json, os, sys, time, platform
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import model
from model import Objective, Event, LOWER, UPPER, D, epicentral_km, region_bounds
from baselines import current_practice, heuristic, random_search
import bee_colony as bees

BUDGET = 2000
VERSION = "v1"
RES = os.path.join(ROOT, "results")
GRID = np.arange(10, BUDGET + 1, 10)                     # convergence curve sampled every 10 evaluations
C = json.load(open(os.path.join(RES, "offset_calibration.json")))["c"]
I = pd.read_csv(os.path.join(ROOT, "data/processed/intensities.csv"), dtype={"event_id": str, "station_code": str})
HYP = pd.read_csv(os.path.join(ROOT, "data/processed/hypocentres.csv"), dtype={"event_id": str}).set_index("event_id")
EV = pd.read_csv(os.path.join(ROOT, "config/events.csv"), dtype={"event_id": str})


def region_of(e):
    r = EV.set_index("event_id").region.get(e) if "region" in EV.columns else None
    return r if isinstance(r, str) and r else "niigata"


def events(role):
    return EV[EV.role == role].event_id.tolist()


def errors(e, x):
    h = HYP.loc[e]
    return float(epicentral_km(h.lat, h.lon, x[0], x[1])), float(x[2] - h.mag_jma)


def record(scenario, e, method, settings, seed, J, x, f, n, t, curve=None, scouts=None):
    comp = J.components(x)
    km, dM = errors(e, x)
    row = dict(scenario=scenario, version=VERSION, event_id=e, method=method, settings=settings, seed=seed,
               evaluations=n, runtime_s=round(t, 4), J=f, J_high=comp["J_high"], J_low=comp["J_low"],
               violation=comp["violation"], feasible=comp["violation"] == 0,
               lat=x[0], lon=x[1], M=x[2], epi_err_km=km, M_err=dM, scouts=scouts)
    c = None
    if curve is not None:
        cur = np.asarray(curve)
        c = cur[np.minimum(GRID, len(cur)) - 1]
    return row, c


def run_method(scenario, e, method, seed, rows, curves, SN=10, limit=None, J_kwargs=None, rows_df=None):
    rdf = I[I.event_id == e] if rows_df is None else rows_df
    lo, hi = region_bounds(region_of(e))
    J = Objective(Event(e, rdf), c=C, lower=lo, upper=hi, **(J_kwargs or {}))
    t0 = time.perf_counter()
    if method.startswith("ABC"):
        r = bees.abc(J, lo, hi, budget=BUDGET, seed=seed, SN=SN, limit=limit)
        out = record(scenario, e, method, f"SN={SN},limit={limit}", seed, J, r["best_x"], r["best_f"], r["n_evals"],
                     time.perf_counter() - t0, r["curve"], r["scouts"])
    elif method == "random search":
        x, f, curve = random_search(J, BUDGET, seed)
        out = record(scenario, e, method, "uniform", seed, J, x, f, J.n_evals, time.perf_counter() - t0, curve)
    else:
        fn = current_practice if method == "current practice" else heuristic
        x, f = fn(J, rdf)
        out = record(scenario, e, method, "1-D M grid", seed, J, x, f, J.n_evals, time.perf_counter() - t0)
    rows.append(out[0])
    if out[1] is not None:
        curves[f"{method}|{e}|{seed}"] = out[1]


def save(name, rows, curves):
    pd.DataFrame(rows).to_csv(os.path.join(RES, f"runs_{name}.csv"), index=False)
    if curves:
        np.savez_compressed(os.path.join(RES, f"curves_{name}.npz"), grid=GRID, **curves)
    print(f"saved results/runs_{name}.csv ({len(rows)} runs)")


def chosen():
    return json.load(open(os.path.join(RES, "chosen_params.json")))


def phase_methods(scenario, evs, seeds, setting):
    rows, curves = [], {}
    for e in evs:
        for s in seeds:
            run_method(scenario, e, "ABC", s, rows, curves, SN=setting["SN"], limit=setting["limit"])
            run_method(scenario, e, "ABC no scouts", s, rows, curves, SN=setting["SN"], limit=None)
            run_method(scenario, e, "random search", s, rows, curves)
        run_method(scenario, e, "current practice", None, rows, curves)
        run_method(scenario, e, "heuristic", None, rows, curves)
    return rows, curves


def tune():
    rows, curves = [], {}
    for SN in (10, 30):
        for limit in (5 * D, 15 * D):
            for e in events("dev"):
                for s in range(10):
                    run_method("tune", e, f"ABC SN={SN} limit={limit}", s, rows, curves, SN=SN, limit=limit)
    save("tune", rows, curves)
    df = pd.DataFrame(rows)
    table = (df.groupby(["method", "event_id"]).J.median().groupby("method").mean()
             .rename("mean_of_event_median_J").reset_index().sort_values("mean_of_event_median_J"))
    best = table.iloc[0]
    close = table[table.mean_of_event_median_J <= best.mean_of_event_median_J * 1.01]
    pick = close.assign(SN=close.method.str.extract(r"SN=(\d+)")[0].astype(int)).sort_values("SN").iloc[0]
    SN = int(pick.method.split("SN=")[1].split()[0]); limit = int(pick.method.split("limit=")[1])
    json.dump({"SN": SN, "limit": limit, "rule": "lowest mean over dev events of median final J (ties <1%: smaller SN)",
               "table": table.to_dict("records")}, open(os.path.join(RES, "chosen_params.json"), "w"), indent=2)
    print(table.to_string(index=False)); print("chosen:", SN, limit)


def final():
    save("final", *phase_methods("final_dev", events("dev"), range(100, 110), chosen()))


def validate():
    save("validation", *phase_methods("validation", events("validation"), range(100, 110), chosen()))


def stress():
    save("stress", *phase_methods("stress", events("stress_test"), range(100, 110), chosen()))


def transfer():
    rows, curves = [], {}
    for role in ("transfer_kyushu", "transfer_kinki", "transfer_stress"):
        r, c = phase_methods(role, events(role), range(100, 110), chosen())
        rows += r; curves.update(c)
    save("transfer", rows, curves)


def sensitivity():
    st = chosen(); rows, curves = [], {}
    seeds = range(100, 105)
    for e in events("dev"):
        rdf = I[I.event_id == e]
        strongest = rdf.instr_lower.idxmax()
        top = rdf[rdf.instr_lower == rdf.instr_lower.max()]
        for s in seeds:
            run_method("sens_original", e, "ABC", s, rows, curves, SN=st["SN"], limit=st["limit"])
            run_method("sens_drop_strongest", e, "ABC", s, rows, curves, SN=st["SN"], limit=st["limit"],
                       rows_df=rdf.drop(index=strongest))
            run_method("sens_weights_0.8_0.2", e, "ABC", s, rows, curves, SN=st["SN"], limit=st["limit"],
                       J_kwargs={"w_high": 0.8, "w_low": 0.2})
            # stricter constraint: epicentre within 50 km of the strongest-shaking station(s)
            lat0, lon0 = top.lat.mean(), top.lon.mean()
            J = Objective(Event(e, rdf), c=C)
            base = J
            class Restricted:
                n_evals = 0
                def __call__(self, x):
                    self.n_evals += 1
                    d = float(epicentral_km(lat0, lon0, x[0], x[1]))
                    return base(x) if d <= 50 else model.INFEASIBLE + (d - 50)
            R = Restricted()
            t0 = time.perf_counter()
            r = bees.abc(R, LOWER, UPPER, budget=BUDGET, seed=s, SN=st["SN"], limit=st["limit"])
            row, cur = record("sens_within_50km", e, "ABC", f"SN={st['SN']},limit={st['limit']}", s, J,
                              r["best_x"], r["best_f"], r["n_evals"], time.perf_counter() - t0, r["curve"], r["scouts"])
            row["feasible"] = bool(r["best_f"] < model.INFEASIBLE)
            rows.append(row)
    save("sensitivity", rows, curves)


if __name__ == "__main__":
    with open(os.path.join(RES, "environment.txt"), "w") as f:
        f.write(f"python {platform.python_version()}\nnumpy {np.__version__}\npandas {pd.__version__}\n"
                f"platform {platform.platform()}\n")
    {"tune": tune, "final": final, "validate": validate, "stress": stress, "sensitivity": sensitivity,
     "transfer": transfer}[sys.argv[1]]()
