"""Check every spot's map point against Wikidata's coordinates for the same landmark.

Run: python3 -m safety.spotcheck [place ...]
Overture points are matched by name, and names can point at the wrong thing (a hotel called "Amber Fort",
a village with the same name as a waterfall). Wikidata gives an independent coordinate. A spot more than
MAX_KM away is marked "far" in data/<place>/spot_check.json, and the help-nearby fetcher then uses the Wikidata
point instead (checked by hand on 13 Nov: in all 13 disagreements Overture had matched a shop or hotel named after
the landmark). "no reference" spots keep the Overture point. No AI involved.
"""
import json, math, sys, time, tomllib, urllib.parse, urllib.request

from safety.fetch import DATA, ROOT, get

MAX_KM = 1.5
LONG_FEATURES = ("beach", "valley", "pass", "lake", "tunnel", "hill", "falls", "road", "bazaar")  # stretch for km


def max_km_for(name):
    return 3.0 if any(w in name.lower() for w in LONG_FEATURES) else MAX_KM


def km(a, b):
    """Great-circle distance in km between (lat, lon) pairs."""
    la1, lo1, la2, lo2 = map(math.radians, (*a, *b))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(h))


def api(params):
    url = "https://www.wikidata.org/w/api.php?" + urllib.parse.urlencode({**params, "format": "json"})
    out = json.loads(get(url))
    time.sleep(1.5)
    return out


def reference(label, place_name, near):
    """Wikidata coordinate for the best-matching item with a coordinate within 50 km of the place; None if none."""
    hits = api({"action": "wbsearchentities", "search": label.split(",")[0], "language": "en", "limit": 7, "type": "item"}).get("search", [])
    if not hits:
        return None
    ents = api({"action": "wbgetentities", "ids": "|".join(h["id"] for h in hits), "props": "claims|labels"})["entities"]
    for h in hits:  # search order = relevance
        c = ents.get(h["id"], {}).get("claims", {}).get("P625")
        if not c:
            continue
        v = c[0]["mainsnak"].get("datavalue", {}).get("value")
        if v and km((v["latitude"], v["longitude"]), near) < 50:
            return {"qid": h["id"], "label": h.get("label"), "lat": v["latitude"], "lon": v["longitude"]}
    return None


def verdict(spot_latlon, ref, max_km=MAX_KM):
    """'ok', 'far' or 'no reference' plus the distance (None if no reference)."""
    if ref is None:
        return "no reference", None
    d = round(km(spot_latlon, (ref["lat"], ref["lon"])), 2)
    return ("ok" if d <= max_km else "far"), d


def run(place):
    cfg = tomllib.loads((ROOT / "places.toml").read_text())[place]
    w, s, e, n = cfg["bbox"]
    centre = ((s + n) / 2, (w + e) / 2)
    f = DATA / place / "help.json"
    j = json.loads(f.read_text())
    checks = {}
    for name, pt in j["data"]["spots"].items():
        ref = reference(name, cfg["name"], centre)
        v, d = verdict((pt["y"], pt["x"]), ref, max_km_for(name))
        checks[name] = {"verdict": v, "km": d, "wikidata": ref and ref["qid"],
                        **({"lat": ref["lat"], "lon": ref["lon"]} if ref else {})}
        print(f"  {place:10} {name:32} {v:12} {d if d is not None else ''}")
    (DATA / place / "spot_check.json").write_text(json.dumps(checks, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    places = sys.argv[1:] or list(tomllib.loads((ROOT / "places.toml").read_text()))
    for p in places:
        run(p)
