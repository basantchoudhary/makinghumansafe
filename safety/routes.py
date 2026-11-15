"""Long-drive briefs: a route, the black spots on it, help along it, and a pre-drive checklist.

Route line: OSRM (OpenStreetMap routing, research/demo server; to be self-hosted or replaced before heavy use).
Black spots: official lists (e.g. Bengaluru Traffic Police) within 300 m of the route line.
Help: hospitals and police from OpenStreetMap within 3 km of the route, with the distance along the route.
Everything is computed by fixed rules; nothing is guessed.
"""
import html, json, math, pathlib, tomllib, urllib.parse, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
e = html.escape
UA = {"User-Agent": "MakingHumanSafe/0.1 (open-data safety research)"}


def km(a, b):
    (lat1, lon1), (lat2, lon2) = a, b
    p = math.pi / 180
    h = math.sin((lat2 - lat1) * p / 2) ** 2 + math.cos(lat1 * p) * math.cos(lat2 * p) * math.sin((lon2 - lon1) * p / 2) ** 2
    return 12742 * math.asin(math.sqrt(h))


def along(line, pt):
    """(distance from route in km, km from start of the nearest route point)."""
    best, acc, at = 1e9, 0.0, 0.0
    for i, q in enumerate(line):
        if i:
            acc += km(line[i - 1], q)
        d = km(q, pt)
        if d < best:
            best, at = d, acc
    return best, at


def emergency_capable(name):
    """Hospitals that can plausibly treat a road-crash victim: general and government hospitals, health centres.
    Excludes eye, dental, ayurveda, maternity, clinics and shops (fixed word rules, published)."""
    import re
    n = name.lower()
    if re.search(r"dental|dent |implant|ayur|homoeo|homeo|eye|nethralaya|netra|vision|medical shop|pharma|first aid|maternity|cradle|"
                 r"fertility|ivf|skin|derma|physio|naturo|wellness|diagnostic|lab$|scan|clinic$|clinic and|health care$", n):
        return False
    return bool(re.search(r"hospital|health cent|phc|chc|government|medical college|trauma|emergency", n))


def fetch(slug, r):
    d = ROOT / "data" / "_road"
    d.mkdir(parents=True, exist_ok=True)
    pts = ";".join(f"{lon},{lat}" for lat, lon in [r["from"]] + r.get("via", []) + [r["to"]])
    raw = json.load(urllib.request.urlopen(urllib.request.Request(
        f"https://router.project-osrm.org/route/v1/driving/{pts}?overview=full&geometries=geojson&steps=true", headers=UA), timeout=60))
    route = raw["routes"][0]
    line = [(lat, lon) for lon, lat in route["geometry"]["coordinates"]]
    roads = []
    for leg in route["legs"]:
        for s in leg["steps"]:
            n = s.get("name") or s.get("ref") or ""
            if n and (not roads or roads[-1][0] != n):
                roads.append([n, 0.0])
            if roads:
                roads[-1][1] += s["distance"] / 1000
    lats, lons = [p[0] for p in line], [p[1] for p in line]
    s_, n_, w_, e_ = min(lats) - 0.03, max(lats) + 0.03, min(lons) - 0.03, max(lons) + 0.03
    q = f'[out:json][timeout:60];(nwr["amenity"~"^(hospital|police)$"]({s_},{w_},{n_},{e_}););out center tags;'
    osm = json.load(urllib.request.urlopen(urllib.request.Request(
        "https://overpass-api.de/api/interpreter?" + urllib.parse.urlencode({"data": q}), headers=UA), timeout=90))
    help_ = []
    for el in osm["elements"]:
        tg = el.get("tags", {})
        lat = el.get("lat") or el.get("center", {}).get("lat")
        lon = el.get("lon") or el.get("center", {}).get("lon")
        name = tg.get("name:en") or tg.get("name") or ("Police station (name not on map)" if tg.get("amenity") == "police" else None)
        if not (lat and lon and name):
            continue
        if tg["amenity"] == "hospital" and not emergency_capable(name):
            continue
        off, at = along(line, (lat, lon))
        if off <= 3:
            help_.append({"kind": tg["amenity"], "name": name, "off_km": round(off, 1), "at_km": round(at, 1),
                          "phone": tg.get("phone") or tg.get("contact:phone"), "src": f"OpenStreetMap {el['type']}/{el['id']}"})
    spots = []
    for f in r.get("blackspot_files", []):
        bs = json.loads((ROOT / f).read_text())
        for b in bs["spots"]:
            off, at = along(line, (b["lat"], b["lon"]))
            if off <= 0.3:
                spots.append({**b, "at_km": round(at, 1), "source": bs["source"], "source_url": bs["source_url"]})
    out = {"km": round(route["distance"] / 1000, 1), "minutes": round(route["duration"] / 60), "line": line,
           "roads": [(n, round(k, 1)) for n, k in roads if k > 0.3], "help": sorted(help_, key=lambda h: h["at_km"]),
           "blackspots": spots, "blackspots_checked": sum(len(json.loads((ROOT / f).read_text())["spots"]) for f in r.get("blackspot_files", []))}
    (d / f"route_{slug}.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
    return out


def map_svg(r, data, w=900, h=420):
    """Hand-drawn route map: the line, start and end, hospitals (+), police (P), black spots (!)."""
    from safety.doodles import WOBBLE, p, t
    line = data["line"]
    lats, lons = [q[0] for q in line], [q[1] for q in line]
    la0, la1, lo0, lo1 = min(lats), max(lats), min(lons), max(lons)
    sc = min((w - 120) / max(lo1 - lo0, 1e-6), (h - 120) / max(la1 - la0, 1e-6))
    X = lambda lon: 60 + (lon - lo0) * sc
    Y = lambda lat: h - 60 - (lat - la0) * sc
    d = "M" + " L".join(f"{X(lon):.1f},{Y(lat):.1f}" for lat, lon in line[::2] + [line[-1]])
    inner = p(d, w=5, stroke="#9cc3f5") + p(d, w=2)
    txt = ""
    for hp in data["help"]:
        if hp["off_km"] <= 1.5:
            # place the marker on the route at its km mark
            acc, pos = 0, line[0]
            for i in range(1, len(line)):
                acc += km(line[i - 1], line[i])
                if acc >= hp["at_km"]:
                    pos = line[i]
                    break
            x, y = X(pos[1]), Y(pos[0]) - 16
            if hp["kind"] == "hospital":
                inner += p(f"M{x - 7},{y} h14 M{x},{y - 7} v14", w=3, stroke="#e34948")
            else:
                txt += t(x, y + 6, "P", 18, 700, "middle", "#2a78d6")
    for b in data["blackspots"]:
        txt += t(X(b["lon"]), Y(b["lat"]) + 26, "!", 28, 700, "middle", "#e34948")
    (sl, so), (el, eo) = line[0], line[-1]
    inner += f'<circle cx="{X(so):.1f}" cy="{Y(sl):.1f}" r="8" fill="#17795a"/><circle cx="{X(eo):.1f}" cy="{Y(el):.1f}" r="8" fill="#e34948"/>'
    txt += t(X(so) - 10, Y(sl) + 30, e(r["from_name"]), 20, 700, "end" if X(so) > w / 2 else "start")
    txt += t(X(eo) + 12, Y(el) + 30, e(r["to_name"]), 20, 700)
    txt += t(20, 30, f'{data["km"]} km, about {data["minutes"]} min without traffic', 20, 700)
    txt += t(20, h - 12, "+ hospital near the road   P police   ! official black spot", 16)
    return (f'<svg class="doodle" viewBox="0 0 {w} {h}" role="img" aria-label="Map of the route from {e(r["from_name"])} to {e(r["to_name"])}, '
            f'{data["km"]} km, with hospitals, police stations and black spots marked.">{WOBBLE}<g filter="url(#wob)">{inner}</g>{txt}</svg>')


def page_body(slug, r, data):
    from safety import doodles
    hosp = [h for h in data["help"] if h["kind"] == "hospital"]
    pol = [h for h in data["help"] if h["kind"] == "police"]
    roads = ", ".join(f"{e(n)} ({k} km)" for n, k in data["roads"])
    out = [f'<h1>Long-drive brief: {e(r["from_name"])} to {e(r["to_name"])}</h1>',
           f'<p class="muted">{data["km"]} km by {roads}. Checked against official black spots and mapped hospitals and police along the way.</p>',
           map_svg(r, data)]
    s = []
    s.append(f"<b>Black spots:</b> {len(data['blackspots'])} of the {data['blackspots_checked']} official Bengaluru black spots lie on this route."
             + (" " if data["blackspots"] else " That list covers city roads; it does not cover NICE Road, so this is not proof the road is safe."))
    if hosp:
        s.append(f"<b>Hospitals:</b> {len(hosp)} within 3 km of the road; first at km {hosp[0]['at_km']} ({e(hosp[0]['name'])}), last at km {hosp[-1]['at_km']} ({e(hosp[-1]['name'])}).")
    gaps = [(a["at_km"], b["at_km"]) for a, b in zip([{"at_km": 0}] + hosp, hosp + [{"at_km": data["km"]}]) if b["at_km"] - a["at_km"] >= 8]
    if gaps:
        s.append("<b>Longest stretch without a hospital close to the road:</b> " + "; ".join(f"km {a} to km {b}" for a, b in gaps) + ". Know where you would go.")
    out.append('<div class="summary"><p>' + "</p><p>".join(s) + '</p><p class="hand" style="font-size:1.35rem;margin:6px 0 0">Someone is waiting for you.</p></div>')
    if data["blackspots"]:
        out.append("<h2>Official black spots on the way</h2>"
                   '<p class="note"><b>What is a black spot?</b> A stretch of road of about 500 m where, over three years, there were at least 5 crashes '
                   "in which someone died or was badly injured, or at least 10 deaths (the road ministry's rule). Slow down, stay in your lane and watch for "
                   "vehicles merging or crossing. The list only shows where crashes already happened often; a road without black spots is not proven safe.</p><ul>" + "".join(
            f'<li>km {b["at_km"]}: <b>{e(b["location"])}</b> ({e(b["station"])})</li>' for b in data["blackspots"]) + "</ul>")
    out.append("<h2>Before you leave</h2><ul>"
               "<li><b>Pick a co-pilot.</b> The driver never touches the phone; the co-pilot navigates and reports hazards in Google Maps.</li>"
               "<li><b>Tyres:</b> check pressure and look for cracks; tyre age is the 4-digit code on the side (week and year).</li>"
               "<li><b>Lights:</b> dip your high beam for oncoming traffic and when following a car. If you are dazzled, look at the left edge of the road and slow down.</li>"
               "<li><b>Speed and lanes:</b> keep left except to overtake, leave a long gap, and expect two-wheelers and late lane changes near exits.</li>"
               "<li><b>At night:</b> watch for unlit parked vehicles on the shoulder. Sleepy? Stop. A 20-minute nap beats an accident.</li>"
               "<li><b>Seat belts for everyone</b>, front and back, and a helmet on every two-wheeler rider and pillion.</li></ul>")
    out.append(doodles.co_pilot())
    out.append("<h2>Help along the route</h2>")
    shown, seen = [], {}
    for h in sorted(data["help"], key=lambda h: (h["at_km"], h["off_km"])):  # nearest 2 of each kind per 3 km of road
        k = (h["kind"], int(h["at_km"] // 3))
        if seen.get(k, 0) < 2 and h["name"] not in {x["name"] for x in shown}:
            shown.append(h); seen[k] = seen.get(k, 0) + 1
    rows = "".join(f'<tr><td>km {h["at_km"]}</td><td>{"Hospital" if h["kind"] == "hospital" else "Police"}</td><td>{e(h["name"])}</td><td>{h["off_km"]} km off the road</td>'
                   f'<td>{e(h["phone"] or "")}</td></tr>' for h in shown)
    out.append(f'<div class="tbl"><table><tr><th>Where</th><th>What</th><th>Name</th><th>Distance from road</th><th>Phone</th></tr>{rows}</table></div>'
               '<p class="src">Sources: route from OpenStreetMap routing (OSRM); hospitals and police from OpenStreetMap; black spots from '
               '<a href="https://btp.karnataka.gov.in/216/black-spots/en">Bengaluru Traffic Police</a> (2021 to 2023). In an emergency call 112.</p>')
    return "\n".join(out)


def load_routes():
    p = ROOT / "routes.toml"
    return tomllib.loads(p.read_text()) if p.exists() else {}
