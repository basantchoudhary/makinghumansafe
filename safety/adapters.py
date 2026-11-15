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
    label = partial_label or cur["year"]
    prev_hi = next((y for y in reversed(full) if y["killed"] >= cur["killed"]), None)
    out.append({**base, "dimension": "trend", "metric": "deaths_record", "value": cur["killed"], "unit": "deaths", "period": cur["year"],
                "statement": (f"{cur['killed']} killed in {label}: the highest since {prev_hi['year']} ({prev_hi['killed']} that year)."
                              if prev_hi else f"{cur['killed']} killed in {label}: the highest on record.")})
    days = 304 if partial_label else 365
    out.append({**base, "dimension": "how_many", "metric": "deaths_per_day", "value": round(cur["killed"] / days, 1), "unit": "deaths a day",
                "period": cur["year"], "statement": f"About {round(cur['killed'] / days)} people die on the roads every day."})
    return out


def run():
    places = tomllib.loads((ROOT / "places.toml").read_text())
    n = 0
    for key, cfg in places.items():
        if cfg.get("road_stats") and (ROOT / cfg["road_stats"]).exists():
            n += facts.upsert(yearly_deaths(key, "road", cfg["road_stats"], cfg.get("road_stats_partial")))
    print(f"adapters: {n} facts written")


if __name__ == "__main__":
    run()
