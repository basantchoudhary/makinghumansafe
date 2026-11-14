"""Backtest: were beach drownings on rougher-than-usual sea days?

For each checked Indian sea-beach incident: locate the spot (OpenStreetMap Nominatim, else the district), take the
nearest sea grid cell (Open-Meteo Marine, research use), and rank the incident day's max wave height and swell period
against the 91 days around it (45 before, 45 after). If waves drove drownings, incident days would sit high in that
ranking (well above the 50th percentile on average, and far more than 25% of them in the top quarter).

Run: python3 scripts/wave_backtest.py   -> data/_research/wave_backtest.json
"""
import datetime as dt, json, pathlib, statistics, time, urllib.parse, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
UA = {"User-Agent": "MakingHumanSafe/0.1 (open-data safety research)"}
EAST = {"Odisha", "Andhra Pradesh", "Tamil Nadu", "West Bengal", "Puducherry"}


def getj(url):
    for wait in (5, 20, 60, None):
        try:
            return json.load(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60))
        except Exception:
            if wait is None:
                raise
            time.sleep(wait)


def locate(r):
    for q in (f'{r["spot"].split("(")[0].strip()}, {r.get("district") or ""}, {r["state"]}, India', f'{r.get("district") or r["state"]}, {r["state"]}, India'):
        res = getj("https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode({"q": q, "format": "json", "limit": 1}))
        time.sleep(1.2)
        if res:
            return float(res[0]["lat"]), float(res[0]["lon"]), q
    return None


def waves(lat, lon, day):
    d0, d1 = day - dt.timedelta(days=45), min(day + dt.timedelta(days=45), dt.date.today())
    for shift in (0, 0.08, 0.16, 0.3):
        q = {"latitude": lat, "longitude": lon + shift, "daily": "wave_height_max,swell_wave_period_max",
             "start_date": d0.isoformat(), "end_date": d1.isoformat(), "timezone": "Asia/Kolkata"}
        d = getj("https://marine-api.open-meteo.com/v1/marine?" + urllib.parse.urlencode(q)).get("daily")
        if d and any(v is not None for v in d["wave_height_max"]):
            return d, shift
    return None, None


def pct(values, x):
    vals = [v for v in values if v is not None]
    return round(100 * sum(v < x for v in vals) / len(vals)) if vals and x is not None else None


def main():
    inc = [r for r in json.loads((ROOT / "data/_corpus/water_incidents.json").read_text())["incidents"]
           if r["country"] == "India" and r.get("water_body") == "sea_beach" and r.get("evidence") == "checked"]
    rows = []
    for r in inc:
        loc = locate(r)
        if not loc:
            continue
        lat, lon, how = loc
        sign = 1 if r["state"] in EAST else -1  # move offshore: west coast to the west, east coast to the east
        day = dt.date.fromisoformat(r["date"])
        d, shift = waves(lat, lon + sign * 0.02, day)
        if not d:
            continue
        i = d["time"].index(r["date"])
        h, p = d["wave_height_max"][i], d["swell_wave_period_max"][i]
        rows.append({"date": r["date"], "spot": r["spot"], "state": r["state"], "month": day.month, "deaths": r.get("deaths"),
                     "wave_max_m": h, "wave_pct": pct(d["wave_height_max"], h), "period_s": p, "period_pct": pct(d["swell_wave_period_max"], p),
                     "median_wave_m": statistics.median(v for v in d["wave_height_max"] if v is not None), "located_by": how})
        print(rows[-1]["date"], rows[-1]["spot"][:30], h, rows[-1]["wave_pct"], p, rows[-1]["period_pct"], flush=True)
    wp = [x["wave_pct"] for x in rows if x["wave_pct"] is not None]
    pp = [x["period_pct"] for x in rows if x["period_pct"] is not None]
    summary = {"incidents_tested": len(rows), "of": len(inc),
               "mean_wave_percentile": round(statistics.mean(wp), 1), "share_top_quarter_wave": round(sum(v >= 75 for v in wp) / len(wp), 2),
               "mean_period_percentile": round(statistics.mean(pp), 1), "share_top_quarter_period": round(sum(v >= 75 for v in pp) / len(pp), 2),
               "expected_if_random": {"mean_percentile": 50, "share_top_quarter": 0.25},
               "monsoon_share": round(sum(x["month"] in (6, 7, 8, 9) for x in rows) / len(rows), 2)}
    out = ROOT / "data/_research/wave_backtest.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({"run": dt.date.today().isoformat(), "method": __doc__, "summary": summary, "rows": rows}, indent=1))
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
