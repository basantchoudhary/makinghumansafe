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


def risk_today(cfg, incs, alerts, today=None):
    """Risk level v1 (published rules). Returns (level, css class, reasons)."""
    today = today or datetime.date.today()
    reasons, level = [], 0
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


def block(key, cfg, alerts, helpd):
    from safety import doodles
    incs = incidents_for(cfg)
    al = live_alerts(alerts)
    level, cls, reasons = risk_today(cfg, incs, al)
    name = cfg["name"]
    hosp = nearest(helpd, "hospital")
    deaths = sum(r.get("deaths") or 0 for r in incs)

    # 1. Summary: plain sentences built only from the facts above.
    s = [f"<b>{e(name)}, water safety today:</b> {level.lower()}."]
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
               '<p class="src">How this is decided: Danger if an official sea warning is in force; High in the monsoon or with a weather warning; '
               'Take care if there are past incidents here or in May; otherwise Low. We never say "safe".</p>')

    # 3. Live alerts
    out.append('<h2 id="live">Live now</h2>')
    if al:
        out.append("".join(f'<div class="alert"><b>{e(a.get("title", ""))}</b> <span class="src">{e(a.get("date") or "")}</span><br>{e(a.get("description", ""))}</div>' for a in al[:4]))
    else:
        out.append('<div class="ok">No official sea or weather warning mentions this area right now.</div>')
    checked = ((alerts or {}).get("fetched") or "")[:16].replace("T", " ")
    out.append(f'<p class="src">Source: NDMA SACHET, India\'s official alert feed (includes IMD weather and INCOIS ocean warnings){", checked " + e(checked) if checked else ""}. Refreshed 4 times a day.</p>')

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
.lenses{display:flex;flex-wrap:wrap;gap:8px;margin:8px 0}
.lenses button{border:1.5px solid var(--ink);border-radius:999px;padding:5px 14px;background:#fff;font:inherit;font-weight:600;cursor:pointer}
.lenses button.on{background:var(--ink);color:#fff}
@media (max-width:640px){.risk{flex-direction:column;gap:4px}}
"""
