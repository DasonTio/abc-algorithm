"""Tables and figures from the run logs.

    python code/analyze.py            -> results/summary_*.csv, results/fig_*.png
Uses whichever of runs_tune / runs_final / runs_validation / runs_stress / runs_sensitivity exist.
"""
import os, sys, json
import numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RES = os.path.join(ROOT, "results")
ORDER = ["ABC", "ABC no scouts", "random search", "heuristic", "current practice"]
COL = {"ABC": "#1f5fae", "ABC no scouts": "#7aa6d6", "random search": "#c4511c", "heuristic": "#8a8a8a", "current practice": "#222222"}


def q(s, p):
    return float(np.percentile(s, p))


def summary(df, name):
    rows = []
    for m in [m for m in ORDER if m in df.method.unique()]:
        g = df[df.method == m]
        rows.append(dict(method=m, runs=len(g), events=g.event_id.nunique(),
                         J_median=g.J.median(), J_IQR=q(g.J, 75) - q(g.J, 25), J_best=g.J.min(), J_worst=g.J.max(),
                         epi_km_median=g.epi_err_km.median(), epi_km_IQR=q(g.epi_err_km, 75) - q(g.epi_err_km, 25),
                         abs_M_err_median=g.M_err.abs().median(), M_err_mean=g.M_err.mean(),
                         feasible_rate=g.feasible.mean(), runs_no_feasible=int((~g.feasible).sum()),
                         evaluations_median=g.evaluations.median(), runtime_s_median=g.runtime_s.median(),
                         scouts_median=g.scouts.median() if "scouts" in g and g.scouts.notna().any() else np.nan))
    out = pd.DataFrame(rows)
    out.to_csv(os.path.join(RES, f"summary_{name}.csv"), index=False)
    return out


def per_event_gap(df):
    """Gap of each run to the best J any method found for that event (a reference optimum)."""
    ref = df.groupby("event_id").J.min().rename("J_ref")
    d = df.join(ref, on="event_id")
    d["gap"] = d.J - d.J_ref
    return d


def convergence(npz_path, name, title):
    z = np.load(npz_path)
    grid = z["grid"]
    keys = [k for k in z.files if k != "grid"]
    runs = pd.read_csv(os.path.join(RES, f"runs_{name}.csv"), dtype={"event_id": str})
    ref = runs.groupby("event_id").J.min()
    fig, ax = plt.subplots(figsize=(7, 4.2))
    for m in [m for m in ORDER if any(k.startswith(m + "|") for k in keys)]:
        M = np.array([z[k] - ref[k.split("|")[1]] for k in keys if k.split("|")[0] == m])
        med, lo, hi = np.median(M, 0), np.percentile(M, 25, 0), np.percentile(M, 75, 0)
        ax.plot(grid, med + 1e-6, color=COL[m], label=m)
        ax.fill_between(grid, lo + 1e-6, hi + 1e-6, color=COL[m], alpha=.18)
    for m in ("current practice", "heuristic"):
        g = per_event_gap(runs)
        g = g[g.method == m]
        if len(g):
            ax.axhline(g.gap.median() + 1e-6, color=COL[m], ls="--", lw=1, label=f"{m} (median, 401 evals)")
    ax.set_yscale("log"); ax.set_xlabel("objective evaluations"); ax.set_ylabel("J − best J found for the event (log)")
    ax.set_title(title, fontsize=10); ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(os.path.join(RES, f"fig_convergence_{name}.png"), dpi=160); plt.close(fig)


def errors_plot(df, name, title):
    ms = [m for m in ORDER if m in df.method.unique()]
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    axes[0].boxplot([df[df.method == m].epi_err_km for m in ms], tick_labels=[m.replace(" ", "\n") for m in ms])
    axes[0].set_ylabel("epicentre error vs JMA (km)")
    axes[1].boxplot([df[df.method == m].M_err for m in ms], tick_labels=[m.replace(" ", "\n") for m in ms])
    axes[1].axhline(0, color="grey", lw=.8); axes[1].set_ylabel("magnitude error, estimate − JMA (Mj)")
    fig.suptitle(title, fontsize=10); fig.tight_layout()
    fig.savefig(os.path.join(RES, f"fig_errors_{name}.png"), dpi=160); plt.close(fig)


def main():
    pd.set_option("display.width", 250)
    if os.path.exists(os.path.join(RES, "runs_tune.csv")):
        t = pd.read_csv(os.path.join(RES, "runs_tune.csv"), dtype={"event_id": str})
        tab = t.groupby("method").agg(J_median=("J", "median"), J_mean=("J", "mean"), epi_km_median=("epi_err_km", "median"),
                                      scouts_median=("scouts", "median")).reset_index()
        tab.to_csv(os.path.join(RES, "summary_tune.csv"), index=False)
        print("== parameter study (dev, seeds 0-9)\n", tab.round(5).to_string(index=False))
    for name, title in (("final", "Development events (20), seeds 100–109"),
                        ("validation", "Validation events (13), seeds 100–109, session-2 data"),
                        ("stress", "Stress test: Noto 2024 M7.6")):
        p = os.path.join(RES, f"runs_{name}.csv")
        if not os.path.exists(p):
            continue
        df = pd.read_csv(p, dtype={"event_id": str})
        s = summary(df, name)
        print(f"\n== {name}\n", s.round(4).to_string(index=False))
        errors_plot(df, name, title)
        if os.path.exists(os.path.join(RES, f"curves_{name}.npz")) and name != "stress":
            convergence(os.path.join(RES, f"curves_{name}.npz"), name, title)
        g = per_event_gap(df)
        abc = g[g.method == "ABC"]
        print("ABC runs within 1e-4 of the best J found for their event: %.0f%%" % (100 * (abc.gap < 1e-4).mean()))
        if name in ("final", "validation"):
            pe = df.groupby(["event_id", "method"]).agg(J=("J", "median"), km=("epi_err_km", "median"), dM=("M_err", "median")).unstack("method")
            pe.round(3).to_csv(os.path.join(RES, f"per_event_{name}.csv"))
    p = os.path.join(RES, "runs_sensitivity.csv")
    if os.path.exists(p):
        s = pd.read_csv(p, dtype={"event_id": str})
        base = s[s.scenario == "sens_original"].set_index(["event_id", "seed"])
        rows = []
        for sc in sorted(s.scenario.unique()):
            g = s[s.scenario == sc].set_index(["event_id", "seed"])
            d = g.join(base[["epi_err_km", "M_err", "lat", "lon", "M"]], rsuffix="_orig")
            from model import epicentral_km
            moved = epicentral_km(d.lat_orig.values, d.lon_orig.values, d.lat.values, d.lon.values)
            rows.append(dict(scenario=sc, runs=len(g), feasible_rate=g.feasible.mean(),
                             epi_km_median=g.epi_err_km.median(), abs_M_err_median=g.M_err.abs().median(),
                             M_err_mean=g.M_err.mean(), answer_moved_km_median=float(np.median(moved)),
                             answer_moved_km_max=float(np.max(moved)), dM_vs_original_median=float(np.median(d.M - d.M_orig))))
        out = pd.DataFrame(rows)
        out.to_csv(os.path.join(RES, "summary_sensitivity.csv"), index=False)
        print("\n== sensitivity (dev, seeds 100-104)\n", out.round(3).to_string(index=False))


if __name__ == "__main__":
    sys.path.insert(0, HERE)
    main()
