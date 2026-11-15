"""Table adapters: official tables become facts by fixed code (no AI). One function per kind of table.

Run: .venv/bin/python -m safety.adapters
"""
import json, pathlib, tomllib

from safety import facts

ROOT = pathlib.Path(__file__).resolve().parent.parent


def yearly_deaths(place, topic, path, partial_label=None):
    """A yearly table of deaths (e.g. traffic police statistics) becomes how_many and trend facts,
    including 'highest since <year>' computed from the table itself."""
    t = json.loads((ROOT / path).read_text())
    ys = [y for y in t["years"] if y.get("killed")]
    base = {"place": place, "topic": topic, "source_id": pathlib.Path(path).stem, "source_name": t["source"],
            "source_url": t["source_url"], "source_page": "yearly table", "method": "table adapter (no AI)", "status": "checked", "quote": ""}
    out = []
    for y in ys:
        out.append({**base, "dimension": "how_many", "metric": "deaths_total", "value": y["killed"], "unit": "deaths",
                    "period": y["year"], "statement": f"{y['killed']} people were killed on the roads in {y['year']}."})
    cur, full = ys[-1], ys[:-1]
    # A partial current year is labelled with its months (e.g. '2026 Jan-Oct') so it is never compared with a full year.
    import re as _re
    mo = _re.findall(r"(January|February|March|April|May|June|July|August|September|October|November|December)", t.get("note", ""))
    if len(mo) >= 2:
        for f in out:
            if f["period"] == cur["year"]:
                f["period"] = f"{cur['year']} {mo[0][:3]}-{mo[-1][:3]}"
    label = partial_label or cur["year"]
    prev_hi = next((y for y in reversed(full) if y["killed"] >= cur["killed"]), None)
    cur_period = next((f["period"] for f in out if f["value"] == cur["killed"]), cur["year"])
    out.append({**base, "dimension": "trend", "metric": "deaths_record", "value": cur["killed"], "unit": "deaths", "period": cur_period,
                "statement": (f"{cur['killed']} killed in {label}: the highest since {prev_hi['year']} ({prev_hi['killed']} that year)."
                              if prev_hi else f"{cur['killed']} killed in {label}: the highest on record.")})
    MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    days = 365 if len(mo) < 2 else round(30.4 * (MON.index(mo[-1][:3]) - MON.index(mo[0][:3]) + 1))
    out.append({**base, "dimension": "how_many", "metric": "deaths_per_day", "value": round(cur["killed"] / days, 1), "unit": "deaths a day",
                "period": cur_period, "statement": f"About {round(cur['killed'] / days)} people die on the roads every day."})
    return out


def checked_incidents(place, topic, cfg):
    """Our checked incident lists become summary facts per incident type (count, years, places, deaths)."""
    import collections
    from safety import road
    rows = road.incidents_for(cfg) if topic == "road" else []
    out = []
    by = collections.defaultdict(list)
    for r in rows:
        by[r.get("incident_type") or "other"].append(r)
    names = {"pothole": "pothole crashes", "night_driving": "night-time crashes", "two_wheeler": "two-wheeler crashes",
             "drunk_driving": "drink-driving crashes", "bus_crash": "bus crashes", "crash_black_spot": "crashes at black spots",
             "crash_ghat_road": "ghat-road crashes", "pedestrian": "pedestrian deaths", "other": "other road incidents"}
    for typ, rs in by.items():
        deaths = sum(r.get("deaths") or 0 for r in rs)
        yrs = sorted({r["date"][:4] for r in rs})
        spots = ", ".join(sorted({r.get("spot") or "" for r in rs})[:5])
        out.append({"place": place, "topic": topic, "dimension": "where", "metric": f"checked_incidents_{typ}", "value": len(rs),
                    "unit": "incidents", "period": f"{yrs[0]}-{yrs[-1]}" if len(yrs) > 1 else yrs[0],
                    "statement": f"Our checked news records hold {len(rs)} {names.get(typ, typ.replace('_', ' '))} here ({yrs[0]} to {yrs[-1]}), "
                                 f"{deaths} deaths, at {spots}.",
                    "quote": "", "source_id": "mhs-incidents", "source_name": "Making Human Safe checked incident list",
                    "source_url": "https://github.com/basantchoudhary/makinghumansafe/tree/main/data/_corpus",
                    "source_page": "each record links to its news source", "method": "computed from checked incidents (no AI)", "status": "checked"})
    return out


def run():
    places = tomllib.loads((ROOT / "places.toml").read_text())
    n = 0
    for key, cfg in places.items():
        if cfg.get("road_stats") and (ROOT / cfg["road_stats"]).exists():
            n += facts.upsert(yearly_deaths(key, "road", cfg["road_stats"], cfg.get("road_stats_partial")))
        if cfg.get("road_stats") or cfg.get("blackspots"):
            n += facts.upsert(checked_incidents(key, "road", cfg))
    print(f"adapters: {n} facts written")


if __name__ == "__main__":
    run()
