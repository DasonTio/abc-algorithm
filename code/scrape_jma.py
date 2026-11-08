"""Scraper for the JMA seismic intensity database (気象庁 震度データベース検索).

Source: https://www.data.jma.go.jp/eqdb/data/shindo/index.html
The page is a JavaScript app that POSTs form data to `api/`:
    mode=search  -> list of earthquakes (catalogue)
    mode=event   -> one earthquake: official hypocentre ("hyp") + every station's intensity ("int")

Every response is saved untouched under data/raw/<session>/ together with a JSON
sidecar (URL, form data, UTC time, HTTP status, SHA-256), and one line per request
is appended to data/raw/scrape_log.csv. One run = one dated observation session.

Commands (run from the Task 4 folder):
    python code/scrape_jma.py search                   # catalogue -> config/events_candidates.csv
    python code/scrape_jma.py events                   # download every event in config/events.csv
    python code/scrape_jma.py events --ids 20041023175600 20070716101322
    python code/scrape_jma.py --session 2026-11-07_s2_kyushu search --box 31.0 34.0 129.5 132.2 --out events_candidates_kyushu.csv
    python code/scrape_jma.py build                    # raw JSON -> data/processed/*.csv

Only the Python standard library is used. Requests are spaced (default 2 s) and
retried with back-off; files that already exist in the session are skipped.
"""
import argparse, csv, datetime as dt, glob, hashlib, json, os, sys, time
import urllib.parse, urllib.request, urllib.error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API = "https://www.data.jma.go.jp/eqdb/data/shindo/api/"
UA = "Mozilla/5.0 (research scraper; NUT bio-inspired computing coursework)"
RAW = os.path.join(ROOT, "data", "raw")
PROC = os.path.join(ROOT, "data", "processed")
CONFIG = os.path.join(ROOT, "config")

# JMA intensity classes -> instrumental intensity interval [lower, upper)
# (JMA: intensity 1 = 0.5-1.5, ..., 5-lower = 4.5-5.0, 5-upper = 5.0-5.5, 6-lower = 5.5-6.0,
#  6-upper = 6.0-6.5, 7 = 6.5 and above; 7.0 is used as the practical upper end)
CLASSES = {
    "1": ("1", 0.5, 1.5), "2": ("2", 1.5, 2.5), "3": ("3", 2.5, 3.5), "4": ("4", 3.5, 4.5),
    "A": ("5-", 4.5, 5.0), "B": ("5+", 5.0, 5.5), "C": ("6-", 5.5, 6.0), "D": ("6+", 6.0, 6.5),
    "7": ("7", 6.5, 7.0),
}


def now_utc():
    return dt.datetime.now(dt.timezone.utc)


def post(form, delay, retries=4):
    """POST url-encoded form data (PHP-style `key[]` for lists). Returns (status, bytes)."""
    pairs = []
    for k, v in form.items():
        for x in (v if isinstance(v, list) else [v]):
            pairs.append((f"{k}[]" if isinstance(v, list) else k, str(x)))
    body = urllib.parse.urlencode(pairs).encode()
    req = urllib.request.Request(API, data=body, method="POST", headers={
        "User-Agent": UA, "Content-Type": "application/x-www-form-urlencoded",
        "Referer": "https://www.data.jma.go.jp/eqdb/data/shindo/index.html"})
    for attempt in range(retries):
        time.sleep(delay if attempt == 0 else delay * 2 ** attempt)
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.status, r.read()
        except (urllib.error.URLError, TimeoutError) as e:
            print(f"  attempt {attempt + 1} failed: {e}", file=sys.stderr)
    raise RuntimeError("request failed after retries")


def save_raw(session_dir, name, form, status, content, log_rows):
    os.makedirs(session_dir, exist_ok=True)
    path = os.path.join(session_dir, name + ".json")
    with open(path, "wb") as f:
        f.write(content)
    meta = {"url": API, "method": "POST", "form": form, "retrieved_utc": now_utc().isoformat(),
            "http_status": status, "bytes": len(content), "sha256": hashlib.sha256(content).hexdigest()}
    with open(os.path.join(session_dir, name + ".meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    log_rows.append([meta["retrieved_utc"], os.path.relpath(path, ROOT), form.get("mode"),
                     form.get("id", ""), status, len(content), meta["sha256"]])
    return path


def append_log(rows):
    os.makedirs(RAW, exist_ok=True)
    log = os.path.join(RAW, "scrape_log.csv")
    new = not os.path.exists(log)
    with open(log, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["retrieved_utc", "file", "mode", "event_id", "http_status", "bytes", "sha256"])
        w.writerows(rows)


# ------------------------------------------------------------------ commands
def cmd_search(a):
    form = {"mode": "search", "dateTimeF": [a.start, "00:00"], "dateTimeT": [a.end, "23:59"],
            "mag": ["0.0", "9.9"], "dep": ["000", "999"], "epi": ["99"], "pref": ["99"],
            "city": ["99"], "station": ["99"], "obsInt": "1", "maxInt": a.max_int,
            "additionalC": "false", "Sort": "S0", "Comp": "C0", "seisCount": "false", "observed": "false"}
    session = os.path.join(RAW, a.session)
    log = []
    status, content = post(form, a.delay)
    save_raw(session, f"catalogue_{a.start}_{a.end}_max{a.max_int}", form, status, content, log)
    append_log(log)
    res = json.loads(content)["res"]
    if not isinstance(res, list):
        sys.exit(f"JMA answered: {res}")
    lat0, lat1, lon0, lon1 = a.box
    rows = []
    for e in res:
        la, lo = float(e["lat"]), float(e["lon"])
        dep = float(e["dep"].replace("km", "").strip() or "nan")
        if lat0 <= la <= lat1 and lon0 <= lo <= lon1 and dep <= a.max_depth:
            rows.append([e["id"], e["ot"], e["name"], la, lo, dep, e["mag"], e["maxI"]])
    os.makedirs(CONFIG, exist_ok=True)
    out = os.path.join(CONFIG, a.out)
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["event_id", "origin_time_jst", "region_ja", "lat", "lon", "depth_km", "mag_jma", "max_intensity"])
        w.writerows(rows)
    print(f"{len(res)} earthquakes in catalogue, {len(rows)} inside box -> {os.path.relpath(out, ROOT)}")


def read_event_ids(path, role=None):
    with open(path, encoding="utf-8") as f:
        return [r["event_id"].strip() for r in csv.DictReader(f)
                if r["event_id"].strip() and not r["event_id"].startswith("#")
                and (role is None or r.get("role", "").strip() == role)]


def cmd_events(a):
    ids = a.ids or read_event_ids(os.path.join(CONFIG, a.list), a.role)
    session = os.path.join(RAW, a.session)
    log = []
    try:
        for k, eid in enumerate(ids, 1):
            name = f"event_{eid}"
            if os.path.exists(os.path.join(session, name + ".json")):
                print(f"[{k}/{len(ids)}] {eid} already in session, skipped"); continue
            form = {"mode": "event", "id": eid}
            status, content = post(form, a.delay)
            res = json.loads(content).get("res")
            if not isinstance(res, dict):
                print(f"[{k}/{len(ids)}] {eid}: JMA answered {res!r}, not saved"); continue
            save_raw(session, name, form, status, content, log)
            print(f"[{k}/{len(ids)}] {eid}: {len(res['int'])} stations, M{res['hyp'][0]['mag']} {res['hyp'][0]['name']}")
    finally:
        append_log(log)


def cmd_build(a):
    """Combine the newest raw copy of every event into two tidy tables."""
    files = {}
    for p in sorted(glob.glob(os.path.join(RAW, "*", "event_*.json"))):
        if p.endswith(".meta.json"):
            continue
        files[os.path.basename(p)] = p                     # later sessions overwrite earlier ones
    os.makedirs(PROC, exist_ok=True)
    hyp_rows, int_rows, unknown = [], [], set()
    for p in sorted(files.values()):
        res = json.load(open(p, encoding="utf-8"))["res"]
        session = os.path.basename(os.path.dirname(p))
        h = res["hyp"][0]
        hyp_rows.append([h["id"], h["ot"], h["name"], h["lat"], h["lon"], h["dep"].replace("km", "").strip(),
                         h["mag"], h["maxI"], len(res["int"]), session])
        for s in res["int"]:
            if s["char"] not in CLASSES:
                unknown.add(s["int"]); continue
            label, lo, hi = CLASSES[s["char"]]
            int_rows.append([h["id"], s["code"], s["name"], s["lat"], s["lon"], s["int"], label,
                             lo, hi, round((lo + hi) / 2, 2), session])
    with open(os.path.join(PROC, "hypocentres.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["event_id", "origin_time_jst", "region_ja", "lat", "lon", "depth_km", "mag_jma",
                    "max_intensity", "n_stations", "session"])
        w.writerows(hyp_rows)
    with open(os.path.join(PROC, "intensities.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["event_id", "station_code", "station_name_ja", "lat", "lon", "intensity_ja",
                    "intensity", "instr_lower", "instr_upper", "instr_mid", "session"])
        w.writerows(int_rows)
    print(f"{len(hyp_rows)} events, {len(int_rows)} station readings -> data/processed/")
    if unknown:
        print("intensity labels not mapped (left out):", sorted(unknown))


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--delay", type=float, default=2.0, help="seconds between requests (default 2)")
    p.add_argument("--session", default=dt.date.today().isoformat(),
                   help="session folder name under data/raw (default: today's date)")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("search", help="download the earthquake catalogue and list candidates")
    s.add_argument("--start", default="1997-01-01")
    s.add_argument("--end", default="2026-11-04", help="last date JMA has data for (it rejects later dates)")
    s.add_argument("--max-int", default="B", help="minimum max intensity code: 1-4, A=5-, B=5+, C=6-, D=6+, 7")
    s.add_argument("--box", type=float, nargs=4, default=[36.3, 38.6, 136.6, 140.0],
                   metavar=("LAT_MIN", "LAT_MAX", "LON_MIN", "LON_MAX"))
    s.add_argument("--max-depth", type=float, default=40.0)
    s.add_argument("--out", default="events_candidates.csv", help="candidate list written to config/ (one per region)")
    e = sub.add_parser("events", help="download hypocentre + station intensities per event")
    e.add_argument("--list", default="events.csv", help="CSV in config/ with an event_id column")
    e.add_argument("--ids", nargs="*", help="event ids instead of the list")
    e.add_argument("--role", help="only events with this role in the list (dev, validation, stress_test, exclude)")
    sub.add_parser("build", help="raw JSON -> data/processed/hypocentres.csv and intensities.csv")
    a = p.parse_args(argv)
    {"search": cmd_search, "events": cmd_events, "build": cmd_build}[a.cmd](a)


if __name__ == "__main__":
    main()
