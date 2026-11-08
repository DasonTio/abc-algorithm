"""Non-ABC methods used for comparison.

current_practice : epicentre at the strongest-shaking station(s) (centroid of the stations in the
                   highest observed class), magnitude by a 1-D grid search on J.
heuristic        : epicentre at the centroid of all 4+ stations weighted by how far above 3.5 they
                   shook, magnitude by the same 1-D grid search.
random_search    : uniform random points inside the bounds, same evaluation budget as ABC.

The magnitude grid (4.0 to 8.0 in steps of 0.01 = 401 evaluations) is counted in the evaluations.
"""
import numpy as np
from model import LOWER, UPPER

M_GRID = np.round(np.arange(4.0, 8.0001, 0.01), 2)


def _best_magnitude(J, lat, lon):
    vals = [J([lat, lon, m]) for m in M_GRID]
    k = int(np.argmin(vals))
    return np.array([lat, lon, M_GRID[k]]), float(vals[k])


def current_practice(J, rows):
    """rows: DataFrame of one event's readings (lat, lon, instr_lower)."""
    top = rows[rows.instr_lower == rows.instr_lower.max()]
    return _best_magnitude(J, top.lat.mean(), top.lon.mean())


def heuristic(J, rows):
    hi = rows[rows.instr_lower >= 3.5]
    w = (hi.instr_lower + hi.instr_upper.clip(upper=7.0)) / 2 - 3.5
    return _best_magnitude(J, np.average(hi.lat, weights=w), np.average(hi.lon, weights=w))


def random_search(J, budget, seed):
    rng = np.random.default_rng(seed)
    lo, hi = getattr(J, "lower", LOWER), getattr(J, "upper", UPPER)
    best_x, best_f, curve = None, np.inf, []
    for _ in range(budget):
        x = lo + rng.random(len(lo)) * (hi - lo)
        f = J(x)
        if f < best_f:
            best_x, best_f = x, f
        curve.append(best_f)
    return best_x, best_f, curve
