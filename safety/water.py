"""Water-safety block for place pages: summary, risk today, live alerts, who's going, incidents, what to do, help.

Everything here is assembled by fixed rules from checked facts (no AI). The risk level rules are published on the
page so anyone can see why a level was given. We never say "safe"; "Low" means no known warning signs today.
"""
import datetime, html, json, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
e = html.escape
CORPUS = ROOT / "data" / "_corpus" / "water_incidents.json"
SEA_WORDS = ("sea", "wave", "swell", "surge", "cyclone", "coast", "rough", "fishermen", "current", "tide")
RAIN_WORDS = ("rain", "flood", "thunder", "storm", "landslide")
MONSOON = range(6, 10)  # June to September on India's west coast

# General water-safety advice per person (reviewed 14 Nov 2026). Facts about this place are added at run time.
LENS_TIPS = {
    "family": ("Family with children", [
        "Children only in knee-deep water, with an adult within arm's reach the whole time.",
        "A life jacket for anyone who can't swim well, even in shallow water.",
        "Stay away from rocks, river mouths and the calm-looking gaps between waves (rip currents)."]),
    "friends": ("Group of friends", [
        "Most drownings in our records are groups of young friends. One person stays out of the water and watches.",
        "No swimming after drinking, and never at dusk or night.",
        "If a friend is pulled out, don't swim after them: shout for help, call 112, throw anything that floats."]),
    "solo": ("Solo traveller", [
        "Swim only where other people are around, in daylight.",
        "Tell someone where you are going and when you'll be back.",
        "Isolated coves and rocks are where help is furthest away."]),
    "elderly": ("Older person", [
        "Waves can knock you over even in knee-deep water: stay at the edge.",
        "Wet rocks and steps are slippery: wear grippy footwear and use a hand to steady yourself.",
        "Carry your medicines and an emergency contact card."]),
}


def in_season(season, today=None):
    """'1st of October to 31st of May' style; True if today is inside (seasons can wrap the year end)."""
    import re
    today = today or datetime.date.today()
    m = re.findall(r"(\d{1,2})(?:st|nd|rd|th)?(?: of)? ([A-Z][a-z]+)", season)
    if len(m) != 2:
        return None
    md = [(datetime.datetime.strptime(mon[:3], "%b").month, int(day)) for day, mon in m]
    t = (today.month, today.day)
    return md[0] <= t <= md[1] if md[0] <= md[1] else (t >= md[0] or t <= md[1])


def blue_flags_near(cfg, km=60):
    import math
    p = ROOT / "data" / "_global" / f"blueflag_{cfg.get('country', 'IN')}.json"
    if not p.exists():
        return []
    w, s, e_, n = cfg["bbox"]; lat0, lon0 = (s + n) / 2, (w + e_) / 2
    out = []
    for b in json.loads(p.read_text())["data"]:
        d = 6371 * 2 * math.asin(math.sqrt(math.sin(math.radians(b["lat"] - lat0) / 2) ** 2 + math.cos(math.radians(lat0)) * math.cos(math.radians(b["lat"])) * math.sin(math.radians(b["lon"] - lon0) / 2) ** 2))
        if d <= km:
            out.append({**b, "km": round(d)})
    return sorted(out, key=lambda b: b["km"])


def incidents_for(cfg):
    """Checked water incidents for this place from the researched list."""
    if not CORPUS.exists():
        return []
    keys = [k.lower() for k in cfg.get("corpus_spots", [])]
    dists = {d.lower() for d in cfg.get("districts", [])}
    out = []
    for r in json.loads(CORPUS.read_text())["incidents"]:
        if r.get("evidence") != "checked":
            continue
        text = " ".join(str(r.get(k) or "") for k in ("spot", "district", "what_happened")).lower()
        if (keys and any(k in text for k in keys)) or (not keys and (r.get("district") or "").lower() in dists):
            out.append(r)
    return sorted(out, key=lambda r: r["date"], reverse=True)


def live_alerts(alerts):
    """Current official alerts relevant to water, newest first."""
    rows = (alerts or {}).get("data") or []
    keep = []
    for a in rows:
        txt = (a.get("title", "") + " " + a.get("description", "")).lower()
        if any(w in txt for w in SEA_WORDS + RAIN_WORDS):
            keep.append(a)
    return keep


def notice_status(n, today=None):
    today = (today or datetime.date.today()).isoformat()
    f, u = n.get("in_force_from"), n.get("in_force_until")
    if f and u:
        return ("in force", "alert") if f <= today <= u else (("ended " + u, "muted-box") if u < today else ("starts " + f, "note"))
    return ("no end date given", "note") if f else ("advisory", "muted-box")


def risk_today(cfg, incs, alerts, today=None, ocean=(), notices=()):
    """Risk level v1 (published rules). Returns (level, css class, reasons)."""
    today = today or datetime.date.today()
    reasons, level = [], 0
    for n in notices:
        if notice_status(n, today)[0] == "in force":
            level = max(level, 2); reasons.append(f"Official ban in force until {e(n['in_force_until'])}: {e(n['title'])}.")
    for a in ocean:  # INCOIS: red Warning = Danger, orange Alert = High, yellow Watch = Take care
        lv = {"red": 3, "orange": 2, "yellow": 1}.get((a.get("color") or "").lower(), 1)
        level = max(level, lv)
        reasons.append(f"INCOIS {e(a['alert'].title())} for this coast (issued {e(a['date'])}): {e(a['description'].split('. It advised')[0])}.")
    sea = [a for a in alerts if any(w in (a.get("title", "") + a.get("description", "")).lower() for w in SEA_WORDS)]
    rain = [a for a in alerts if a not in sea]
    if sea:
        level = 3; reasons.append(f"Official sea warning in force ({e(sea[0].get('title', ''))}).")
    if rain:
        level = max(level, 2); reasons.append(f"Official weather warning in force ({e(rain[0].get('title', ''))}).")
    if today.month in MONSOON:
        level = max(level, 2)
        reasons.append("Monsoon season (June to September): big swells and rip currents; most drownings in our records happen in May and June."
                       if cfg.get("coastal", True) else "Monsoon season (June to September): rivers and waterfalls can rise within minutes.")
    if today.month == 5:
        level = max(level, 1); reasons.append("May: pre-monsoon swells and holiday crowds; the second most dangerous month in our records.")
    deaths = sum(r.get("deaths") or 0 for r in incs)
    if incs:
        level = max(level, 1)
        reasons.append(f"{len(incs)} water incident{'s' if len(incs) != 1 else ''} here since {min(r['date'][:4] for r in incs)}"
                       + (f", {deaths} death{'s' if deaths != 1 else ''}" if deaths else "") + " in our checked records.")
    if not reasons:
        reasons.append("No official warning and no incidents in our records. That is not proof of safety.")
    names = [("Low", "lvl-low"), ("Take care", "lvl-care"), ("High", "lvl-high"), ("Danger", "lvl-danger")]
    return names[level][0], names[level][1], reasons


def nearest(helpd, kind):
    near = ((helpd or {}).get("data") or {}).get("near") or {}
    best = None
    beaches = {k: v for k, v in near.items() if any(w in k.lower() for w in ("beach", "island", "falls", "river", "ghat"))}
    for spot, n in (beaches or near).items():
        for h in n.get(kind) or []:
            if not best or h["km"] < best[1]["km"]:
                best = (spot, h)
    return best


def block(key, cfg, alerts, helpd, incois=None, notices=None):
    from safety import doodles
    incs = incidents_for(cfg)
    al = live_alerts(alerts)
    ocean = (incois or {}).get("data") or []
    nts = (notices or {}).get("data") or []
    level, cls, reasons = risk_today(cfg, incs, al, ocean=ocean, notices=nts)
    name = cfg["name"]
    hosp = nearest(helpd, "hospital")
    deaths = sum(r.get("deaths") or 0 for r in incs)

    # 1. Summary: plain sentences built only from the facts above.
    s = [f"<b>{e(name)}, water safety today:</b> {level.lower()}."]
    if ocean:
        s.append(f"Official ocean alert now: {e(ocean[0]['alert'].title())} (INCOIS).")
    if al:
        s.append(f"An official warning is in force: {e(al[0].get('title', ''))}.")
    if incs:
        last = incs[0]
        s.append(f"Our checked records show {len(incs)} water incident{'s' if len(incs) != 1 else ''} here since {min(r['date'][:4] for r in incs)}"
                 + (f" with {deaths} death{'s' if deaths != 1 else ''}" if deaths else "") + ". "
                 f"Most recent: {e(datetime.date.fromisoformat(last['date']).strftime('%-d %b %Y'))} at {e(last.get('spot') or name)}.")
    if hosp:
        s.append(f"Nearest hospital from {e(hosp[0])}: {e(hosp[1]['name'])}, {hosp[1]['km']} km.")
    s.append("Swim only in daylight, never after drinking, and stay out of the sea when flags are red.")
    out = [f'<div class="summary"><p>{" ".join(s)}</p><p class="hand" style="font-size:1.35rem;margin:6px 0 0">Someone is waiting for you.</p></div>']

    # 2. Risk today with reasons
    out.append(f'<h2 id="risk">Risk today</h2><div class="risk {cls}"><span class="lvl">{level}</span><ul>'
               + "".join(f"<li>{r}</li>" for r in reasons) + "</ul></div>"
               '<p class="src">How this is decided: Danger if an official sea warning or an INCOIS red warning is in force; High in the monsoon, with a weather warning or an INCOIS orange alert; High also when an official swimming ban is in force; Take care with an INCOIS yellow watch, '
               'past incidents here, or in May; otherwise Low. We never say "safe".</p>')

    # 2b. The calm-sea trap (from our wave backtest)
    bt = ROOT / "data" / "_research" / "wave_backtest.json"
    if bt.exists() and cfg.get("coastal", True):
        sm = json.loads(bt.read_text())["summary"]
        out.append(f'<div class="note"><b>A calm sea is not a safe sea.</b> We checked the waves on the day of {sm["incidents_tested"]} beach drownings in India: '
                   f'those days were no rougher than usual (only {round(sm["share_top_quarter_wave"] * 100)}% were among the roughest days). '
                   'Most people drowned on ordinary-looking days, pulled by rip currents or a sudden wave. '
                   '<a href="https://github.com/basantchoudhary/makinghumansafe/blob/main/data/_research/wave_backtest.json">How we checked</a></div>')

    # 3. Live alerts
    out.append('<h2 id="live">Live now</h2>')
    colors = {"red": "alert", "orange": "alert", "yellow": "note"}
    out.append("".join(f'<div class="{colors.get((a.get("color") or "").lower(), "note")}"><b>{e(a["title"])}</b> <span class="src">INCOIS, issued {e(a["date"])}</span><br>{e(a["description"])}</div>' for a in ocean[:4]))
    if al:
        out.append("".join(f'<div class="alert"><b>{e(a.get("title", ""))}</b> <span class="src">{e(a.get("date") or "")}</span><br>{e(a.get("description", ""))}</div>' for a in al[:4]))
    elif not ocean:
        out.append('<div class="ok">No official sea or weather warning mentions this area right now.</div>')
    checked = ((alerts or {}).get("fetched") or "")[:16].replace("T", " ")
    out.append(f'<p class="src">Source: NDMA SACHET, India\'s official alert feed (includes IMD weather and INCOIS ocean warnings){", checked " + e(checked) if checked else ""}. Ocean alerts: INCOIS (Indian National Centre for Ocean Information Services). Refreshed 4 times a day.</p>')

    # 3b. Official notices: bans, closures, advisories (with the period each one is in force)
    if nts:
        out.append('<h3>Official notices</h3>' + "".join(
            f'<div class="{notice_status(n)[1]}"><b>{e(n["title"])}</b> <span class="badge">{e(notice_status(n)[0])}</span> '
            f'<span class="src">{e(n["date"])}, <a href="{e(n["link"])}">{e(n["source"])}</a></span><br><span class="small">{e(n["text"][:300])}</span></div>'
            for n in nts[:5]))

    # 3b2. Lifeguarded beaches (hand-collected lists, e.g. Drishti in Goa)
    lg_p = ROOT / "lifeguards" / f"{key}.json"
    if lg_p.exists():
        lg = json.loads(lg_p.read_text())
        names = lg.get("north_goa", []) + lg.get("south_goa", []) + lg.get("beaches", [])
        spots = (((helpd or {}).get("data") or {}).get("near") or {}).keys()
        mark = [(sp, any(n.lower().split()[0] in sp.lower().replace(",", " ").split() for n in names)) for sp in spots if any(w in sp.lower() for w in ("beach", "falls"))]
        out.append(f'<h3>Lifeguards</h3><p>{len(names)} beaches and waterfalls here have lifesavers ({e(lg["source"].split(",")[0])}). '
                   f'Swim only near them, between their flags. Lifesaver helpline: <b>{e(lg.get("helpline", ""))}</b>.</p>'
                   + ("<ul>" + "".join(f'<li>{e(sp)}: ' + ("<b>lifesavers present</b>" if ok else "not on the lifesaver list") + "</li>" for sp, ok in mark) + "</ul>" if mark else "")
                   + f'<details><summary>All {len(names)} lifeguarded places</summary><p class="small">{e(", ".join(names))}</p></details>'
                   f'<p class="src">Source: <a href="{e(lg["source_url"])}">{e(lg["source"])}</a>, checked {e(lg["checked"])}. {e(lg["note"])}</p>')

    # 3c. Certified beaches nearby (Blue Flag: lifeguards and safety signs in season)
    bfs = blue_flags_near(cfg) if cfg.get("coastal", True) else []
    if bfs:
        out.append('<h3>Want a beach with lifeguards?</h3><p>Blue Flag beaches are certified for safety: lifeguards, warning signs and first aid during their season.</p><ul>'
                   + "".join(f'<li><b>{e(b["name"])}</b>, about {b["km"]} km away. Season {e(b["season"])}: '
                             + ("<b>in season now</b>" if in_season(b["season"]) else "out of season now (no lifeguard guarantee)")
                             + f'. <a href="{e(b["url"])}">Blue Flag page</a></li>' for b in bfs[:3])
                   + '</ul><p class="src">Source: Foundation for Environmental Education (Blue Flag) site map. Lifeguards are not guaranteed outside the season.</p>')

    # 4. Who's going (filters advice in the browser; nothing is sent anywhere)
    chips = "".join(f'<button type="button" data-lens="{k}">{e(v[0])}</button>' for k, v in LENS_TIPS.items())
    lists = "".join(f'<ul class="lens-tips" data-for="{k}" hidden>' + "".join(f"<li>{e(t)}</li>" for t in v[1])
                    + (f"<li>Nearest hospital: {e(hosp[1]['name'])}, {hosp[1]['km']} km from {e(hosp[0])}.</li>" if hosp and k in ("family", "elderly") else "")
                    + "</ul>" for k, v in LENS_TIPS.items())
    out.append(f'<h2 id="who">Who\'s going?</h2><div class="lenses">{chips}</div>{lists}'
               '<p class="src">Your choice stays in your browser.</p>'
               """<script>(function(){const b=document.querySelectorAll('.lenses button'),l=document.querySelectorAll('.lens-tips');
function pick(k){b.forEach(x=>x.classList.toggle('on',x.dataset.lens===k));l.forEach(x=>x.hidden=x.dataset.for!==k);try{localStorage.setItem('mhs-lens',k)}catch(_){}}
b.forEach(x=>x.addEventListener('click',()=>pick(x.dataset.lens)));let s=null;try{s=localStorage.getItem('mhs-lens')}catch(_){}pick(s||'family');})();</script>""")

    # 5. What has happened here
    out.append('<h2 id="water-incidents">What has happened here</h2>')
    if incs:
        out.append('<p class="src">Each incident was checked: the linked article contains the quoted sentence word for word. No names are shown.</p>'
                   '<div class="tbl"><table><tr><th>Date</th><th>Where</th><th>What happened</th><th>Deaths</th><th>Source</th></tr>' + "".join(
                       f'<tr><td style="white-space:nowrap">{e(r["date"])}</td><td><b>{e(r.get("spot") or "")}</b></td><td>{e(r["what_happened"])}'
                       + (' <span class="badge">warning ignored</span>' if r.get("warning_ignored") else "") + f'</td><td>{r.get("deaths") if r.get("deaths") is not None else "missing"}</td>'
                       f'<td><a href="{e(r["source_url"])}">{e(r.get("source_name") or "source")}</a></td></tr>' for r in incs) + "</table></div>")
    else:
        out.append('<p class="muted">No checked water incidents in our records for this place yet. That does not mean none happened.</p>')

    # 6. What to do: the pictures that teach it
    acts = cfg.get("activities", [])
    pics = [doodles.rip_current()] if "swimming" in acts else []
    if cfg.get("coastal", True) and "swimming" in acts:
        pics.append(doodles.monsoon_sea())
    if "waterfall" in acts:
        pics.append(doodles.waterfall_rise())
    if "water_sports" in acts:
        pics.append(doodles.boat_jackets())
    out.append('<h2 id="what-to-do">What to do</h2>' + "".join(f'<div class="pic">{p}</div>' for p in pics))
    return "\n".join(out)


CSS = """
.summary{border:2px solid var(--ink);border-radius:14px;padding:14px 16px;box-shadow:3px 3px 0 var(--ink);background:#fff;margin:10px 0 6px}
.summary p{margin:0}
.risk{display:flex;gap:16px;align-items:flex-start;border-radius:14px;padding:12px 16px;border:2px solid var(--ink)}
.risk .lvl{font-family:var(--hand);font-size:2.2rem;font-weight:700;white-space:nowrap;line-height:1.1}
.risk ul{margin:4px 0 0;padding-left:18px}
.lvl-low{background:var(--green-soft)}.lvl-care{background:var(--amber-soft)}.lvl-high{background:#ffe1c2}.lvl-danger{background:var(--red-soft)}
.lvl-danger .lvl{color:var(--red)}
.muted-box{background:var(--soft);border:1px solid var(--line);border-radius:10px;padding:10px 14px;margin:10px 0;color:var(--muted)}
.lenses{display:flex;flex-wrap:wrap;gap:8px;margin:8px 0}
.lenses button{border:1.5px solid var(--ink);border-radius:999px;padding:5px 14px;background:#fff;font:inherit;font-weight:600;cursor:pointer}
.lenses button.on{background:var(--ink);color:#fff}
@media (max-width:640px){.risk{flex-direction:column;gap:4px}}
"""
