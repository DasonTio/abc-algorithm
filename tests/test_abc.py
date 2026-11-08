"""Checks of the ABC implementation (no network). Run: python tests/test_abc.py"""
import os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "code"))
sys.path.insert(0, HERE)
import bee_colony as bees
from model import Objective, LOWER, UPPER, epicentral_km
from test_model import synthetic_event


class Counted:
    def __init__(self, fn):
        self.fn, self.n = fn, 0
    def __call__(self, x):
        self.n += 1
        return self.fn(x)


def run():
    # 1. sphere function: known optimum at the centre of the box
    centre = (LOWER + UPPER) / 2
    sphere = Counted(lambda x: float(np.sum(((np.asarray(x) - centre) / (UPPER - LOWER)) ** 2)))
    r = bees.abc(sphere, LOWER, UPPER, budget=2000, seed=1, SN=10, limit=30)
    assert r["best_f"] < 1e-6, r["best_f"]
    # 2. the budget is exact and every call is counted (initial, neighbours, scouts)
    assert r["n_evals"] == 2000 == sphere.n == len(r["curve"])
    # 3. the best-so-far curve never gets worse
    assert all(b <= a for a, b in zip(r["curve"], r["curve"][1:]))
    # 4. tiny known-optimum earthquake: synthetic readings from a known source are recovered
    truth = np.array([37.29, 138.87, 6.8])
    J = Objective(synthetic_event(truth, n=300))
    r = bees.abc(J, LOWER, UPPER, budget=2000, seed=3, SN=10, limit=30)
    km = epicentral_km(truth[0], truth[1], r["best_x"][0], r["best_x"][1])
    assert r["best_f"] < 1e-3 and km < 5 and abs(r["best_x"][2] - 6.8) < 0.15, (r["best_f"], km, r["best_x"])
    # 5. trace: probabilities sum to 1, trial counters reset on success and grow on failure,
    #    ties count as failures, every candidate stays inside the bounds
    tr = []
    bees.abc(J, LOWER, UPPER, budget=400, seed=5, SN=5, limit=10, trace=tr)
    for t in tr:
        if t["phase"] == "probabilities":
            assert abs(sum(t["p"]) - 1) < 1e-12 and min(t["p"]) > 0
        if t["phase"] in ("employed", "onlooker"):
            assert t["trial_after"] == (0 if t["accepted"] else t["trial_before"] + 1)
            assert t["accepted"] == (t["f_new"] < t["f_old"])
            assert np.all(np.asarray(t["v"]) >= LOWER) and np.all(np.asarray(t["v"]) <= UPPER)
            assert t["k"] != t["i"]
    # 6. scouts fire with a small limit and never with limit=None, and the best is never lost
    flat = Counted(lambda x: 1.0)                                    # every attempt is a tie -> failure
    r = bees.abc(flat, LOWER, UPPER, budget=300, seed=0, SN=5, limit=5)
    assert r["scouts"] > 0
    r = bees.abc(flat, LOWER, UPPER, budget=300, seed=0, SN=5, limit=None)
    assert r["scouts"] == 0
    tr = []
    r = bees.abc(J, LOWER, UPPER, budget=600, seed=2, SN=5, limit=3, trace=tr)
    assert r["scouts"] > 0 and r["best_f"] == min(t.get("f_new", np.inf) for t in tr if "f_new" in t)
    print("all ABC tests passed")


if __name__ == "__main__":
    run()
