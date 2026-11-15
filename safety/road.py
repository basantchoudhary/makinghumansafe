"""Road-safety block for city pages: official totals, black spots, checked incidents, route briefs, what to do.

Built by fixed rules from official statistics, official black spot lists and checked incidents (no AI).
"""
import collections, datetime, html, json, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
e = html.escape
CORPUS = ROOT / "data" / "_corpus" / "food_liquor_road_incidents.json"
VEH = {"two_wheeler": "two-wheeler", "car": "car", "bus": "bus", "truck": "truck", "tempo_traveller": "tempo traveller",
       "auto": "auto-rickshaw", "pedestrian": "pedestrian"}


def incidents_for(cfg):
    if not CORPUS.exists():
        return []
    keys = [k.lower() for k in cfg.get("road_corpus_spots", [])]
    dists = {d.lower() for d in cfg.get("road_districts", cfg.get("districts", []))}
    out = []
    for r in json.loads(CORPUS.read_text())["incidents"]:
        if r.get("activity") != "road" or r.get("evidence") != "checked":
            continue
        text = " ".join(str(r.get(k) or "") for k in ("spot", "district", "what_happened")).lower()
        if (r.get("district") or "").lower() in dists or (keys and any(k in text for k in keys)):
            out.append(r)
    return sorted(out, key=lambda r: r["date"], reverse=True)


def city_map(spots, w=900, h=460):
    """Hand-drawn dot map of black spots (no base map: just the shape of where they are)."""
    from safety.doodles import WOBBLE, p, t
    lats, lons = [s["lat"] for s in spots], [s["lon"] for s in spots]
    la0, la1, lo0, lo1 = min(lats), max(lats), min(lons), max(lons)
    sc = min((w - 120) / (lo1 - lo0), (h - 100) / (la1 - la0))
    X = lambda lon: 60 + (lon - lo0) * sc
    Y = lambda lat: h - 50 - (lat - la0) * sc
    inner = p(f"M{X(lo0) - 20},{Y(la0) + 20} Q{X((lo0 + lo1) / 2)},{Y(la0) + 40} {X(lo1) + 20},{Y(la0) + 10} "
              f"Q{X(lo1) + 40},{Y((la0 + la1) / 2)} {X(lo1) + 10},{Y(la1) - 20} Q{X((lo0 + lo1) / 2)},{Y(la1) - 40} {X(lo0) - 10},{Y(la1) - 10} "
              f"Q{X(lo0) - 40},{Y((la0 + la1) / 2)} {X(lo0) - 20},{Y(la0) + 20} Z", fill="#f6f7f9", w=1.6, stroke="#9aa0a6")
    txt = ""
    for s in spots:
        inner += f'<circle cx="{X(s["lon"]):.1f}" cy="{Y(s["lat"]):.1f}" r="6" fill="#e34948" stroke="#1d2129" stroke-width="1.4"/>'
    txt += t(20, 30, f"{len(spots)} official accident black spots", 22, 700) + t(20, h - 14, "each red dot: a 500 m stretch with repeated deaths or serious injuries", 16)
    return (f'<svg class="doodle" viewBox="0 0 {w} {h}" role="img" aria-label="Map of {len(spots)} official accident black spots across the city, '
            f'shown as red dots.">{WOBBLE}<g filter="url(#wob)">{inner}</g>{txt}</svg>')


def block(key, cfg):
    from safety import routes
    from safety.insights import bars
    out = []
    st_p = ROOT / cfg["road_stats"] if cfg.get("road_stats") else None
    bs_p = ROOT / cfg["blackspots"] if cfg.get("blackspots") else None
    stats = json.loads(st_p.read_text()) if st_p and st_p.exists() else None
    bs = json.loads(bs_p.read_text()) if bs_p and bs_p.exists() else None
    incs = incidents_for(cfg)
    name = cfg["name"]

    # 1. Summary from official numbers
    s = []
    if stats:
        ys = [y for y in stats["years"] if y["killed"]]
        cur, prev = ys[-1], ys[-2]
        full = [y for y in ys[:-1]][-5:]
        most = max(full, key=lambda y: y["killed"])
        s.append(f"<b>{e(name)} roads:</b> {cur['killed']} people killed from January to October {cur['year']}, "
                 f"about {round(cur['killed'] / (10 * 30.4))} a day."
                 + (f" That is already more than any full year since {full[0]['year']} (highest: {most['killed']} in {most['year']})." if cur["killed"] > most["killed"] else ""))
    if bs:
        s.append(f"The traffic police list {len(bs['spots'])} accident black spots in the city.")
    vehs = collections.Counter(r.get("vehicle") for r in incs if r.get("vehicle"))
    if incs:
        s.append(f"Our checked news records here: {len(incs)} road incident{'s' if len(incs) != 1 else ''}"
                 + (f", mostly {VEH.get(vehs.most_common(1)[0][0], vehs.most_common(1)[0][0])} riders" if vehs else "") + ".")
    s.append("Wear a helmet (rider and pillion), never use the phone while driving, and slow down in rain: potholes hide under water.")
    out.append(f'<div class="summary"><p>{" ".join(s)}</p><p class="hand" style="font-size:1.35rem;margin:6px 0 0">Someone is waiting for you.</p></div>')

    # 2. Trend chart
    if stats:
        ys = [y for y in stats["years"] if y["killed"]][-10:]
        out.append('<h2 id="road-trend">Deaths on the roads, by year</h2>'
                   + bars([y["killed"] for y in ys], [y["year"][2:] if y is not ys[-1] else y["year"][2:] + "*" for y in ys],
                          "People killed in road accidents", highlight=(len(ys) - 1,))
                   + f'<p class="src">* {e(stats["note"])} Source: <a href="{e(stats["source_url"])}">{e(stats["source"])}</a>, checked {e(stats["checked"])}.</p>')

    # 3. Black spots
    if bs:
        by_div = collections.defaultdict(list)
        for b in bs["spots"]:
            by_div[b["division"]].append(b)
        out.append('<h2 id="blackspots">Accident black spots</h2>' + city_map(bs["spots"])
                   + '<p class="note"><b>What is a black spot?</b> A stretch of road of about 500 m where, over three years, there were at least 5 crashes in which someone died '
                   "or was badly injured, or at least 10 deaths (the road ministry's rule). The list shows where crashes already happened often; other roads are not proven safe.</p>"
                   + "".join(f"<details><summary><b>{e(d)}</b> ({len(v)})</summary><ul>" + "".join(f'<li>{e(b["location"])} <span class="src">({e(b["station"])})</span></li>' for b in v) + "</ul></details>"
                             for d, v in sorted(by_div.items()))
                   + f'<p class="src">Source: <a href="{e(bs["source_url"])}">{e(bs["source"])}</a>, checked {e(bs["checked"])}.</p>')

    # 4. Route briefs starting or ending here
    rs = [(slug, r) for slug, r in routes.load_routes().items() if r.get("city") == key]
    if rs:
        out.append('<h2 id="routes">Long-drive briefs</h2><ul>' + "".join(
            f'<li><a href="/routes/{slug}/">{e(r["from_name"])} to {e(r["to_name"])}</a>: black spots on the way, hospitals and police along the route</li>' for slug, r in rs) + "</ul>")

    # 5. Checked incidents
    out.append('<h2 id="road-incidents">Road incidents in our checked records</h2>')
    if incs:
        out.append('<div class="tbl"><table><tr><th>Date</th><th>Where</th><th>What happened</th><th>Vehicle</th><th>Deaths</th><th>Source</th></tr>' + "".join(
            f'<tr><td style="white-space:nowrap">{e(r["date"])}</td><td><b>{e(r.get("spot") or "")}</b></td><td>{e(r["what_happened"])}</td>'
            f'<td>{e(VEH.get(r.get("vehicle"), r.get("vehicle") or ""))}</td><td>{r.get("deaths") if r.get("deaths") is not None else "missing"}</td>'
            f'<td><a href="{e(r["source_url"])}">{e(r.get("source_name") or "source")}</a></td></tr>' for r in incs) + "</table></div>"
            '<p class="src">A small, checked sample from news (each linked article contains the quoted sentence). Official totals above cover all reported crashes.</p>')
    else:
        out.append('<p class="muted">No checked road incidents in our records yet. Official totals above cover all reported crashes.</p>')

    # 6. What to do
    out.append("<h2 id='road-what-to-do'>What to do</h2><ul>"
               "<li><b>Two-wheelers:</b> a helmet for rider and pillion, buckled. In rain, slow down: potholes fill with water and look like flat road.</li>"
               "<li><b>Phone:</b> never while driving. A co-pilot or a dashboard mount with voice directions only.</li>"
               "<li><b>Night:</b> dip high beams, watch for unlit parked vehicles, and don't drive tired.</li>"
               "<li><b>Junctions and exits:</b> expect late lane changes and two-wheelers filtering between lanes.</li>"
               "<li><b>Crash ahead?</b> Park well off the road with hazard lights, call 112, and don't move an injured person unless there is fire or traffic danger.</li></ul>")
    return "\n".join(out)
