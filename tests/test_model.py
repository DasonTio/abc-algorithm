"""Checks of the forward model and objective (no network). Run: python tests/test_model.py"""
import os, sys
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "code"))
from model import Event, Objective, predict_intensity, INFEASIBLE, LOWER, UPPER

CLASS = [("1", .5, 1.5), ("2", 1.5, 2.5), ("3", 2.5, 3.5), ("4", 3.5, 4.5), ("5-", 4.5, 5.0),
         ("5+", 5.0, 5.5), ("6-", 5.5, 6.0), ("6+", 6.0, 6.5), ("7", 6.5, 7.0)]


def synthetic_event(truth, n=300, seed=0, c=0.0):
    """Stations around a known source; each reading is the class that contains the exact prediction."""
    rng = np.random.default_rng(seed)
    lat = truth[0] + rng.uniform(-1.2, 1.2, n)
    lon = truth[1] + rng.uniform(-1.5, 1.5, n)
    p = predict_intensity(truth, lat, lon, c)
    rows = []
    for la, lo, v in zip(lat, lon, p):
        for lab, a, b in CLASS:
            if a <= v < b or (lab == "7" and v >= 6.5):
                rows.append(dict(lat=la, lon=lo, intensity=lab, instr_lower=a, instr_upper=b))
                break
    return Event("synthetic", pd.DataFrame(rows))


def run():
    truth = np.array([37.29, 138.87, 6.8])
    ev = synthetic_event(truth)
    J = Objective(ev)
    # 1. the true source explains every synthetic reading exactly
    assert J(truth) == 0.0, J(truth)
    comp = J.components(truth)
    assert comp["high_inside_class"] == 1.0 and comp["low_wrongly_4plus"] == 0.0
    # 2. moving the source away makes J worse, and further is worse still
    j10 = J(truth + [0.09, 0, 0])            # about 10 km north
    j30 = J(truth + [0.27, 0, 0])            # about 30 km north
    assert 0 < j10 < j30, (j10, j30)
    # 3. a too-large magnitude is punished by the one-sided term (quiet stations predicted 4+)
    big = J.components(truth + [0, 0, 1.0])
    assert big["low_wrongly_4plus"] > 0 and big["J_low"] > 0
    # 4. infeasible candidates rank below every feasible one, by the size of the violation
    bad1, bad2 = J([37.3, 138.9, 3.0]), J([37.3, 138.9, -2.0])
    assert INFEASIBLE < bad1 < bad2
    worst_feasible = J(UPPER)                    # a far corner of the box is still feasible
    assert worst_feasible < INFEASIBLE
    # 5. the evaluation counter counts every call, feasible or not
    assert J.n_evals == 6, J.n_evals            # 6 calls of J(); components() is a diagnostic, not counted
    # 6. offset c: data generated with c=0.4 is fit exactly when the model uses c=0.4
    ev2 = synthetic_event(truth, c=0.4, seed=1)
    assert Objective(ev2, c=0.4)(truth) == 0.0 and Objective(ev2, c=0.0)(truth) > 0
    print("all model tests passed")


if __name__ == "__main__":
    run()
