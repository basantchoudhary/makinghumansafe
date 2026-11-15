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
    """Checked road incidents for a place from EVERY incident list in data/_corpus (deduplicated by date and spot)."""
    import glob
    files = sorted(glob.glob(str(ROOT / "data" / "_corpus" / "*.json")))
    if not files:
        return []
    keys = [k.lower() for k in cfg.get("road_corpus_spots", [])]
    dists = {d.lower() for d in cfg.get("road_districts", cfg.get("districts", []))}
    out, seen = [], set()
    rows = [r for f in files for r in json.loads(pathlib.Path(f).read_text()).get("incidents", [])]
    for r in rows:
        if r.get("activity") != "road" or r.get("evidence") != "checked":
            continue
        k = (r["date"], (r.get("spot") or "").lower()[:20])
        if k in seen:
            continue
        seen.add(k)
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
    if False:  # the story's narration replaces this short summary
        out.append(f'<div class="summary"><p>{" ".join(s)}</p><p class="hand" style="font-size:1.35rem;margin:6px 0 0">Someone is waiting for you.</p></div>')

    # 1b. The story: mind map, narration, right-now line (from an official report's findings)
    from safety import story as story_gen
    generated = story_gen.render(key, "road", name)
    if generated:
        out.append(generated)  # produced by the machine from the fact store
    elif cfg.get("road_findings"):
        out.append(story(cfg, stats))  # older hand-made path, kept only as a fallback

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
        nb_p = ROOT / cfg.get("blackspots_new", "")
        if cfg.get("blackspots_new") and nb_p.exists():
            nb = json.loads(nb_p.read_text())
            out.append('<div class="alert"><b>Newer list reported:</b> the traffic police\'s 2023 to 2025 list adds six black spots (East division is now the worst): '
                       + "; ".join(e(x["location"]) for x in nb["spots"]) + f'. <span class="src">{e(nb["note"])} <a href="{e(nb["source_url"])}">{e(nb["source"])}</a>.</span></div>')

    # 4. Route briefs starting or ending here
    rs = [(slug, r) for slug, r in routes.load_routes().items() if r.get("city") == key]
    if rs:
        out.append('<h2 id="routes">Long-drive briefs</h2><ul>' + "".join(
            f'<li><a href="/routes/{slug}/">{e(r["from_name"])} to {e(r["to_name"])}</a>: black spots on the way, hospitals and police along the route</li>' for slug, r in rs) + "</ul>")

    # 5. Checked incidents
    total = None
    if stats:
        ys = [y for y in stats["years"] if y.get("killed")]
        total = ys[-1]["killed"] if ys else None
    out.append('<h2 id="road-incidents">Examples we checked, one by one</h2>'
               f'<p class="muted">These are individual crashes we read and checked against their news report. They are examples, not a count'
               + (f': the official total is {total} deaths this year.' if total else '.') +
               " The list grows as our news reader checks every reported crash, four times a day.</p>")
    if incs:
        head = '<div class="tbl"><table><tr><th>Date</th><th>Where</th><th>What happened</th><th>Vehicle</th><th>Deaths</th><th>Source</th></tr>'
        from safety import lessons
        out.append(lessons.render(incs, "road"))
        row = lambda r: (f'<tr><td style="white-space:nowrap">{e(r["date"])}</td><td><b>{e(r.get("spot") or "")}</b></td><td>{e(r["what_happened"])}<br>{lessons.tags_html(r)}</td>'
                         f'<td>{e(VEH.get(r.get("vehicle"), r.get("vehicle") or ""))}</td><td>{r.get("deaths") if r.get("deaths") is not None else "missing"}</td>'
                         f'<td><a href="{e(r["source_url"])}">{e(r.get("source_name") or "source")}</a></td></tr>')
        out.append(head + "".join(row(r) for r in incs[:15]) + "</table></div>")
        if len(incs) > 15:
            out.append(f'<details><summary>All {len(incs)} checked crashes</summary>' + head + "".join(row(r) for r in incs[15:]) + "</table></div></details>")
        out.append('<p class="src">Each linked article contains the quoted sentence, checked by our code. Official totals above cover all reported crashes.</p>')
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


def mind_map(F, cur, w=980, h=620):
    """Hand-drawn mind map: one centre fact, five branches, each with 2-3 short facts from the official report."""
    from safety.doodles import WOBBLE, p, t, person, palm
    cx, cy = w / 2, h / 2
    inner = p(f"M{cx - 150},{cy - 48} h300 v96 h-300 z", fill="#fdecec", w=2.6)
    txt = t(cx, cy - 8, f"{cur} killed, Jan to Oct 2026", 30, 700, "middle") + t(cx, cy + 26, "about 3 every day in Bengaluru", 22, 400, "middle")
    branches = [
        ("WHEN", 170, 95, "#e8f0fc", [f"{F['night_6pm_2am_pct']}% of deaths: 6 pm to 2 am", f"worst day: {F['peak_day']}", "weekends peak"]),
        ("WHO", w - 170, 95, "#fff4e5", [f"{F['motorcyclist_pct']}% two-wheeler riders", f"{F['pedestrian_pct']}% people walking", f"over {F['men_pct_over']}% men; {F['age_20_29_pct']}% aged 20 to 29"]),
        ("WHERE", 150, h - 150, "#e4f3ed", ["North: over one-third of deaths", "Yelahanka, Devanahalli, Kengeri,", "Whitefield, K R Puram"]),
        ("WHY", w - 160, h - 150, "#f3e8fd", [f"{F['speeding_pct']}% of vehicles over the limit", f"only {F['helmet_correct_pct']}% helmets worn right", f"{F['hit_and_run_pct']}% hit-and-run"]),
        ("YOU CAN", cx, h - 40, "#ffffff", [f"clasp the helmet; rear seat belts ({F['seatbelt_rear_pct']}% wear them)", "", ""]),
    ]
    for name, x, y, fill, lines in branches:
        if name == "YOU CAN":
            inner += p(f"M{cx},{cy + 48} L{cx},{y - 52}", w=2.2)
            inner += p(f"M{x - 340},{y - 50} h680 v44 h-680 z", fill="#e4f3ed", w=2.2)
            txt += t(x, y - 20, f"YOU CAN: clasp your helmet, belt up in the back seat ({F['seatbelt_rear_pct']}% do), slow down at night", 18, 700, "middle")
            continue
        inner += p(f"M{cx + (-150 if x < cx else 150)},{cy + (-30 if y < cy else 30)} Q{(cx + x) / 2},{(cy + y) / 2 + (-30 if y < cy else 30)} {x + (110 if x < cx else -110)},{y}", w=2.2)
        inner += p(f"M{x - 135},{y - 62} h270 v124 h-270 z", fill=fill, w=2.2)
        txt += t(x, y - 34, name, 24, 700, "middle")
        for k, ln in enumerate(lines):
            txt += t(x, y - 6 + k * 24, ln, 17, 400, "middle")
    return (f'<svg class="doodle" viewBox="0 0 {w} {h}" role="img" aria-label="Mind map of road deaths in Bengaluru: {cur} killed January to October 2026. '
            f'When: {F["night_6pm_2am_pct"]}% between 6 pm and 2 am, worst on Sundays. Who: {F["motorcyclist_pct"]}% two-wheeler riders, {F["pedestrian_pct"]}% pedestrians, mostly young men. '
            f'Where: North division, Yelahanka, Devanahalli, Kengeri, Whitefield, K R Puram. Why: speeding, helmets not worn correctly, hit-and-run. '
            f'You can: clasp your helmet, belt up in the back, slow down at night.">{WOBBLE}<g filter="url(#wob)">{inner}</g>{txt}</svg>')


def story(cfg, stats):
    """'A day on the roads': mind map, narration and a 'right now' line, from an official report's findings."""
    fp = ROOT / cfg["road_findings"]
    if not fp.exists():
        return ""
    src = json.loads(fp.read_text()); F = src["findings"]
    cur = [y for y in stats["years"] if y["killed"]][-1]["killed"] if stats else F["deaths_2023"]
    full = [y for y in stats["years"] if y["killed"] and y is not [y for y in stats["years"] if y["killed"]][-1]] if stats else []
    prev_hi = next((y for y in reversed(full) if y["killed"] >= cur), None)
    record = (f"the highest since {prev_hi['year']} ({prev_hi['killed']} that year), with two months still to go" if prev_hi else "the highest on record")
    nar = (f"Every day, about three people die on Bengaluru's roads. This year, {cur} people were killed by October, {record}. "
           f"Most were riding a two-wheeler ({F['motorcyclist_pct']} in every 100) or walking ({F['pedestrian_pct']} in every 100), and most were young men. "
           f"Danger peaks after dark: {F['night_6pm_2am_pct']} of every 100 deaths happen between 6 in the evening and 2 at night, and Sunday is the worst day. "
           f"Three things kill most: speed (about a third of vehicles drive over the limit), helmets that are not clasped (only {F['helmet_correct_pct']} in 100 riders wear one correctly), "
           f"and drivers who flee: {F['hit_and_run_pct']} in every 100 deaths are hit-and-run. "
           f"In cars, almost nobody in the back wears a seat belt: {F['seatbelt_rear_pct']} in 100. Clasp your helmet, belt up in every seat, and slow down at night.")
    out = ['<h2 id="road-story">A day on Bengaluru\'s roads</h2>', mind_map(F, cur),
           f'<div class="summary"><p>{e(nar)}</p><p class="hand" style="font-size:1.35rem;margin:6px 0 0">Someone is waiting for you.</p></div>',
           # "Right now": chosen in the browser from the visitor's local time (nothing is sent anywhere)
           '<div id="now-line" class="alert" hidden></div>'
           f"""<script>(function(){{const d=new Date(),h=d.getHours(),wd=d.getDay(),el=document.getElementById('now-line'),m=[];
if(h>=18||h<2)m.push('<b>Right now is the most dangerous time.</b> {F["night_6pm_2am_pct"]}% of Bengaluru\\'s road deaths happen between 6 pm and 2 am. Slow down, dip high beams, watch for people walking.');
if(wd===0||wd===6)m.push('<b>It\\'s the weekend.</b> Road deaths peak on weekends, especially Sunday.');
if(h>=14&&h<16)m.push('<b>Afternoon:</b> the hours when the fewest riders wear their helmet correctly ({F["helmet_2_4pm_pct"]}%). Clasp it.');
if(m.length){{el.innerHTML=m.join('<br>');el.hidden=false;}}}})();</script>""",
           (f'<p class="src"><b>Note:</b> {e(F["record_note"]["text"])} (<a href="{e(F["record_note"]["url"])}">{e(F["record_note"]["source"])}</a>)</p>' if F.get("record_note") else "")
           + ('<details><summary><b>Why numbers differ between sources</b></summary><p class="small">Different agencies count differently (city limits, when a death is counted, date of update). '
              + " ".join(f"For {n['year']}: " + "; ".join(f"{e(a)} {b}" for a, b in n["figures"]) + "." for n in F.get("numbers_differ", []))
              + " We use the traffic police's own yearly table for totals.</p></details>" if F.get("numbers_differ") else ""),
           '<h3>What the official report found</h3><ul>'
           f"<li><b>When:</b> {F['night_6pm_2am_pct']}% of deaths between 6 pm and 2 am; weekends peak, especially Sunday.</li>"
           f"<li><b>Who:</b> {F['motorcyclist_pct']}% two-wheeler riders, {F['pedestrian_pct']}% pedestrians; over {F['men_pct_over']}% men; {F['age_20_29_pct']}% aged 20 to 29.</li>"
           f"<li><b>Where:</b> North division has over a third of deaths. Most deaths around Yelahanka, Devanahalli, Kengeri, Whitefield and K R Puram. "
           f"Highest-risk spots: {e(', '.join(F['top_locations']))}.</li>"
           f"<li><b>Why:</b> {F['speeding_pct']}% of vehicles over the speed limit ({F['expressway_speeding_pct']}% on expressways); only {F['helmet_correct_pct']}% wear helmets correctly; "
           f"seat belts {F['seatbelt_all_pct']}% overall and {F['seatbelt_rear_pct']}% in the back; child seats {F['child_restraint_pct']}%; {F['hit_and_run_pct']}% of deaths hit-and-run; "
           f"{F['single_vehicle_deaths']} deaths with no other vehicle involved, mostly two-wheelers hitting a fixed object.</li>"
           f"<li><b>Attitudes:</b> only {F['know_speed_limit_pct']}% of drivers knew the city's speed limits, and {F['comfortable_speeding_pct']}% felt comfortable speeding.</li></ul>"
           f'<p class="src">Source: <a href="{e(src["source_url"])}">{e(src["source"])}</a>, {e(src["page"])}; figures are for {src["year"]}. '
           f"The 2026 total is from Bengaluru Traffic Police's yearly statistics. Checked {e(src['checked'])}.</p>"]
    return "\n".join(out)
