"""Artificial Bee Colony (Karaboga & Basturk, 2007), written for this project.

Minimises J(x) inside box bounds. One food source = one candidate solution x = (lat, lon, M).
Nectar quality = selection fitness F(x) = 1 / (1 + J(x)).

Per cycle:
  1. Employed phase: every source i tries one neighbour.
       k  = random partner, k != i          j  = random dimension
       phi ~ U(-1, 1)                       v  = x_i, but v_j = x_ij + phi * (x_ij - x_kj)
       v_j is clipped to the bounds (so every evaluated point is feasible)
       greedy: v replaces x_i only if J(v) < J(x_i) (strictly; a tie counts as a failure)
       trial_i = 0 on success, trial_i + 1 on failure
  2. Probabilities p_i = F_i / sum(F), computed ONCE, after the employed phase.
  3. Onlooker phase: SN attempts. Each picks a source by roulette on p, then the same
     neighbour move, greedy choice and trial update as in step 1.
  4. Scout phase: the source with the most failures is abandoned if trial >= limit
     (at most one scout per cycle). It is replaced by a uniform random point and trial = 0.
`limit` therefore counts failed improvement ATTEMPTS on a source (employed + onlooker),
not cycles. limit = None (or inf) switches scouts off (ablation).

Evaluation budget: every call of J counts: initial sources, every neighbour (accepted or not)
and every scout. The run stops as soon as the budget is used, even in the middle of a phase.
The best solution ever evaluated is kept separately, so a scout can never lose it.
"""
import numpy as np


class Budget(Exception):
    pass


def abc(J, lower, upper, budget, seed, SN=10, limit=None, trace=None, init=None, init_trials=None,
        max_cycles=None):
    """Return dict(best_x, best_f, curve, n_evals, cycles, scouts, scout_evals).

    trace       : list to append one dict per step to (for the manual trace), or None
    init        : optional (SN, D) array of starting sources (otherwise uniform random)
    init_trials : optional starting trial counters (used for the controlled scout demonstration)
    max_cycles  : optional stop after this many cycles (manual trace)
    """
    lower, upper = np.asarray(lower, float), np.asarray(upper, float)
    D = len(lower)
    rng = np.random.default_rng(seed)
    limit = np.inf if limit is None else limit
    state = {"n": 0, "best_x": None, "best_f": np.inf}
    curve, scout_evals = [], []

    def f(x):
        if state["n"] >= budget:
            raise Budget
        v = J(x)
        state["n"] += 1
        if v < state["best_f"]:
            state["best_f"], state["best_x"] = v, np.array(x, float)
        curve.append(state["best_f"])
        return v

    def log(**kw):
        if trace is not None:
            trace.append({"eval": state["n"], **kw})

    X = np.array(init, float) if init is not None else lower + rng.random((SN, D)) * (upper - lower)
    fx = np.full(SN, np.inf)
    trials = np.array(init_trials, float) if init_trials is not None else np.zeros(SN)
    cycles = 0

    def try_neighbour(i, phase):
        k = rng.choice([s for s in range(SN) if s != i])
        j = int(rng.integers(D))
        phi = float(rng.uniform(-1, 1))
        v = X[i].copy()
        v[j] = np.clip(X[i, j] + phi * (X[i, j] - X[k, j]), lower[j], upper[j])
        fv = f(v)
        ok = fv < fx[i]
        log(phase=phase, i=i, k=int(k), j=j, phi=phi, x_old=X[i].tolist(), v=v.tolist(),
            f_old=float(fx[i]), f_new=float(fv), accepted=bool(ok), trial_before=float(trials[i]))
        if ok:
            X[i], fx[i], trials[i] = v, fv, 0
        else:
            trials[i] += 1
        trace and trace[-1].update(trial_after=float(trials[i]))

    try:
        for i in range(SN):
            fx[i] = f(X[i])
            log(phase="init", i=i, x_old=None, v=X[i].tolist(), f_new=float(fx[i]))
        while max_cycles is None or cycles < max_cycles:
            for i in range(SN):                                         # employed bees
                try_neighbour(i, "employed")
            F = 1.0 / (1.0 + fx)                                        # J >= 0 -> F in (0, 1]
            p = F / F.sum()
            log(phase="probabilities", p=p.tolist(), F=F.tolist())
            for _ in range(SN):                                         # onlooker bees
                i = int(rng.choice(SN, p=p))
                try_neighbour(i, "onlooker")
            i = int(np.argmax(trials))                                  # scout bee
            if trials[i] >= limit:
                old = X[i].copy()
                X[i] = lower + rng.random(D) * (upper - lower)
                fx[i], trials[i] = f(X[i]), 0
                scout_evals.append(state["n"])
                log(phase="scout", i=i, x_old=old.tolist(), v=X[i].tolist(), f_new=float(fx[i]))
            cycles += 1
            log(phase="end_cycle", best_f=state["best_f"], best_x=None if state["best_x"] is None else state["best_x"].tolist(),
                trials=trials.tolist())
    except Budget:
        pass
    return {"best_x": state["best_x"], "best_f": state["best_f"], "curve": curve, "n_evals": state["n"],
            "cycles": cycles, "scouts": len(scout_evals), "scout_evals": scout_evals,
            "final_sources": X.copy(), "final_f": fx.copy(), "final_trials": trials.copy()}
