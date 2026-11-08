"""Offline tests: the scraper is run against recorded-format responses (no network)."""
import csv, json, os, shutil, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "code"))
import scrape_jma as S

EVENT = {"res": {"hyp": [{"id": "20041023175600", "ot": "2004/10/23 17:56:00.3", "name": "新潟県中越地方",
                          "lat": "37.2917", "lon": "138.8670", "dep": "13 km", "mag": "6.8", "maxI": "震度７"}],
                 "int": [{"name": "長岡市東川口＊", "lat": "37.27", "lon": "138.86", "code": "3710044", "int": "震度７", "char": "7", "mark": "S7", "zidx": "11"},
                         {"name": "長岡市古志竹沢＊", "lat": "37.33", "lon": "138.89", "code": "3710033", "int": "震度６強", "char": "D", "mark": "SD", "zidx": "10"},
                         {"name": "A", "lat": "37.0", "lon": "139.0", "code": "1", "int": "震度５弱", "char": "A", "mark": "SA", "zidx": "7"},
                         {"name": "B", "lat": "36.0", "lon": "140.0", "code": "2", "int": "震度１", "char": "1", "mark": "S1", "zidx": "1"}]}}
CATALOGUE = {"res": [{"id": "20041023175600", "ot": "2004/10/23 17:56:00.3", "name": "新潟県中越地方", "lat": "37.2917", "lon": "138.8670", "dep": "13 km", "mag": "6.8", "maxI": "震度７"},
                     {"id": "20110311144618", "ot": "2011/03/11 14:46:18.1", "name": "三陸沖", "lat": "38.1033", "lon": "142.8600", "dep": "24 km", "mag": "9.0", "maxI": "震度７"}],
             "str": []}


def run():
    tmp = tempfile.mkdtemp()
    S.ROOT, S.RAW, S.PROC, S.CONFIG = tmp, f"{tmp}/data/raw", f"{tmp}/data/processed", f"{tmp}/config"
    sent = []
    def fake_post(form, delay, retries=4):
        sent.append(form)
        return 200, json.dumps(EVENT if form["mode"] == "event" else CATALOGUE).encode()
    S.post = fake_post
    S.main(["--delay", "0", "--session", "s1", "search"])
    cand = list(csv.DictReader(open(f"{tmp}/config/events_candidates.csv", encoding="utf-8")))
    assert [c["event_id"] for c in cand] == ["20041023175600"], "box filter should drop the Tohoku quake"
    shutil.copy(f"{tmp}/config/events_candidates.csv", f"{tmp}/config/events.csv")
    S.main(["--delay", "0", "--session", "s1", "events"])
    S.main(["--delay", "0", "--session", "s1", "events"])            # second run must skip, not re-download
    assert sum(f["mode"] == "event" for f in sent) == 1
    meta = json.load(open(f"{tmp}/data/raw/s1/event_20041023175600.meta.json"))
    assert meta["http_status"] == 200 and len(meta["sha256"]) == 64
    S.main(["build"])
    rows = list(csv.DictReader(open(f"{tmp}/data/processed/intensities.csv", encoding="utf-8")))
    assert len(rows) == 4
    r7 = rows[0]
    assert (r7["intensity"], float(r7["instr_lower"]), float(r7["instr_upper"])) == ("7", 6.5, 7.0)
    assert rows[2]["intensity"] == "5-" and float(rows[2]["instr_mid"]) == 4.75
    hyp = list(csv.DictReader(open(f"{tmp}/data/processed/hypocentres.csv", encoding="utf-8")))
    assert hyp[0]["depth_km"] == "13" and hyp[0]["n_stations"] == "4"
    log = list(csv.reader(open(f"{tmp}/data/raw/scrape_log.csv", encoding="utf-8")))
    assert len(log) == 3                                              # header + catalogue + 1 event
    shutil.rmtree(tmp)
    print("all scraper tests passed")


if __name__ == "__main__":
    run()
