"""Forward model and objective J(x) for locating an earthquake from JMA intensity reports.

Decision vector x = (lat, lon, M)   (formulation v1, D = 3)
    lat, lon  epicentre, decimal degrees
    M         magnitude on the JMA scale (Mj), because the offset c is calibrated against Mj
Depth is fixed at DEPTH_KM = 10 km. The fitness audit (2026-11-07) showed that intensity data
cannot resolve depth: J kept falling towards 0 km at the official epicentre. Fixing depth at
10 km is standard practice when depth is unresolved (draft v0 had depth as a 4th variable).

Forward model (one prediction per station):
    R      = sqrt(epicentral_km^2 + depth^2)                       hypocentral distance (point source)
    logPGV = 0.58 M + 0.0038 D - 1.29 - log10(R + 0.0028 * 10^(0.5 M)) - 0.002 R
                                                                    Si & Midorikawa (1999), crustal (d = 0)
    logARV = 1.83 - 0.66 log10(AVS30), AVS30 = 400 m/s for every station
                                                                    Matsuoka & Midorikawa (1994)
    I_pred = 2.68 + 1.72 (logPGV + logARV) + c                      Midorikawa et al. (1999) + offset c

Objective J(x), minimised, unit = intensity^2:
    stations observed at 4+ ("high"):  e = distance from I_pred to the observed class interval
                                       (0 inside; class 7 has no upper edge)
    stations observed at 1-3 ("low"):  e = max(0, I_pred - 3.5)  -> only "this station did not reach 4"
    J = w_high * mean(e_high^2) + w_low * mean(e_low^2),  w_high = w_low = 0.5 by default

Hard constraints: lower <= x <= upper (BOUNDS). Outside the bounds J = INFEASIBLE + total violation,
so an infeasible candidate always ranks below every feasible one and the size of the violation is visible.
"""
import numpy as np

BOUNDS = {                       # name: (lower, upper, unit)
    "lat": (36.0, 38.8, "deg N"),
    "lon": (136.3, 140.3, "deg E"),
    "M": (4.0, 8.0, "Mj"),
}
DEPTH_KM = 10.0
LOWER = np.array([b[0] for b in BOUNDS.values()])
UPPER = np.array([b[1] for b in BOUNDS.values()])
D = len(BOUNDS)
# Search bounds per region (added 2026-11-07 for the transfer test; Niigata values unchanged from v1).
# Rule for new regions: the catalogue search box widened by 0.3 deg on every side; M stays 4.0-8.0.
REGION_BOUNDS = {
    "niigata": (36.0, 38.8, 136.3, 140.3),          # v1 bounds (search box 36.3-38.6 N, 136.6-140.0 E)
    "kyushu":  (30.7, 34.3, 129.2, 132.5),          # search box 31.0-34.0 N, 129.5-132.2 E
    "kinki":   (33.7, 36.1, 131.7, 136.3),          # search box 34.0-35.8 N, 132.0-136.0 E
}


def region_bounds(region="niigata"):
    la0, la1, lo0, lo1 = REGION_BOUNDS[region]
    return np.array([la0, lo0, LOWER[2]]), np.array([la1, lo1, UPPER[2]])
AVS30 = 400.0
LOG_ARV = 1.83 - 0.66 * np.log10(AVS30)
LOW_EDGE = 3.5                   # upper edge of intensity 3
INFEASIBLE = 1e6


def epicentral_km(lat1, lon1, lat2, lon2):
    p = np.pi / 180
    a = np.sin((lat2 - lat1) * p / 2) ** 2 + np.cos(lat1 * p) * np.cos(lat2 * p) * np.sin((lon2 - lon1) * p / 2) ** 2
    return 12742.0 * np.arcsin(np.sqrt(a))


def predict_intensity(x, st_lat, st_lon, c=0.0, dep=DEPTH_KM):
    lat, lon, M = x
    R = np.sqrt(epicentral_km(lat, lon, st_lat, st_lon) ** 2 + dep ** 2)
    log_pgv = 0.58 * M + 0.0038 * dep - 1.29 - np.log10(R + 0.0028 * 10 ** (0.5 * M)) - 0.002 * R
    return 2.68 + 1.72 * (log_pgv + LOG_ARV) + c


def violation(x, lower=LOWER, upper=UPPER):
    x = np.asarray(x, float)
    return float(np.maximum(lower - x, 0).sum() + np.maximum(x - upper, 0).sum())


class Event:
    """Station readings of one earthquake, split into the two groups the objective uses."""

    def __init__(self, event_id, rows):
        """rows: DataFrame with lat, lon, instr_lower, instr_upper, intensity (one earthquake)."""
        self.event_id = event_id
        hi = rows[rows.instr_lower >= 3.5]
        lo = rows[rows.instr_lower < 3.5]
        self.hi_lat, self.hi_lon = hi.lat.to_numpy(float), hi.lon.to_numpy(float)
        self.hi_lower = hi.instr_lower.to_numpy(float)
        self.hi_upper = np.where(hi.intensity.to_numpy() == "7", np.inf, hi.instr_upper.to_numpy(float))
        self.lo_lat, self.lo_lon = lo.lat.to_numpy(float), lo.lon.to_numpy(float)
        self.n_hi, self.n_lo = len(hi), len(lo)


class Objective:
    """J(x) for one event; counts every evaluation (needed for the matched budget)."""

    def __init__(self, event, c=0.0, w_high=0.5, w_low=0.5, lower=LOWER, upper=UPPER):
        self.ev, self.c, self.w_high, self.w_low = event, c, w_high, w_low
        self.lower, self.upper = np.asarray(lower, float), np.asarray(upper, float)
        self.n_evals = 0

    def components(self, x):
        x = np.asarray(x, float)
        p_hi = predict_intensity(x, self.ev.hi_lat, self.ev.hi_lon, self.c)
        e_hi = np.where(p_hi < self.ev.hi_lower, self.ev.hi_lower - p_hi,
                        np.where(p_hi > self.ev.hi_upper, p_hi - self.ev.hi_upper, 0.0))
        if self.ev.n_lo:
            p_lo = predict_intensity(x, self.ev.lo_lat, self.ev.lo_lon, self.c)
            e_lo = np.maximum(p_lo - LOW_EDGE, 0.0)
        else:
            e_lo = np.zeros(0)
        high = float(np.mean(e_hi ** 2)) if len(e_hi) else 0.0
        low = float(np.mean(e_lo ** 2)) if len(e_lo) else 0.0
        return {
            "J_high": high, "J_low": low,
            "rms_high": high ** 0.5,                                   # intensity units
            "high_inside_class": float(np.mean(e_hi == 0)) if len(e_hi) else np.nan,
            "low_wrongly_4plus": float(np.mean(e_lo > 0)) if len(e_lo) else np.nan,
            "violation": violation(x, self.lower, self.upper),
        }

    def __call__(self, x):
        self.n_evals += 1
        v = violation(x, self.lower, self.upper)
        if v > 0:
            return INFEASIBLE + v
        comp = self.components(x)
        return self.w_high * comp["J_high"] + self.w_low * comp["J_low"]


def load_events(intensities_csv, events_csv, roles=None):
    """Return {event_id: Event} and the events table; roles filters e.g. {'dev'}."""
    import pandas as pd
    I = pd.read_csv(intensities_csv, dtype={"event_id": str, "station_code": str})
    ev = pd.read_csv(events_csv, dtype={"event_id": str})
    if roles:
        ev = ev[ev.role.isin(roles)]
    return {e: Event(e, I[I.event_id == e]) for e in ev.event_id}, ev
