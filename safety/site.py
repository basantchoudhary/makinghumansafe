"""Build the static website into site/ from data/, fares/ and places.toml.

Run: python3 -m safety.site
Every fact on a page carries its source. Nothing is invented: if a source has no data, the page says so.
"""
import datetime, html, json, pathlib, tomllib

ROOT = pathlib.Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
e = html.escape

LENSES_CFG = tomllib.loads((ROOT / "lenses.toml").read_text())
HELPLINES = [(h["number"], h["what"]) for h in LENSES_CFG["helpline"]]
LENSES = {v["label"]: v["tips"] for v in LENSES_CFG["lens"].values()}
ACTIVITIES = tomllib.loads((ROOT / "activities.toml").read_text())


def load(place, name):
    p = ROOT / "data" / place / f"{name}.json"
    return json.loads(p.read_text()) if p.exists() else None


FONT = '<link rel="preconnect" href="https://fonts.googleapis.com"><link href="https://fonts.googleapis.com/css2?family=Caveat:wght@400;700&display=swap" rel="stylesheet">'
SITE_URL = "https://makinghumansafe.com"
CSS = """
:root{--ink:#1d2129;--muted:#5d6470;--line:#e3e6ea;--soft:#f6f7f9;--blue:#2a78d6;--blue-soft:#e8f0fc;--red:#e34948;--red-soft:#fdecec;
--amber:#a15c00;--amber-soft:#fff4e5;--green:#17795a;--green-soft:#e4f3ed;--hand:Caveat,"Comic Sans MS",cursive}
*{box-sizing:border-box}html{-webkit-text-size-adjust:100%}
body{margin:0;background:#fff;color:var(--ink);font:16.5px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
.wrap{max-width:980px;margin:0 auto;padding:0 16px 40px}
header.top{display:flex;flex-wrap:wrap;gap:10px 18px;align-items:center;padding:12px 0;border-bottom:1px solid var(--line);margin-bottom:22px}
.brand{display:flex;align-items:center;gap:8px;color:var(--ink);text-decoration:none;font-family:var(--hand);font-size:1.7rem;font-weight:700;line-height:1}
header nav{display:flex;flex-wrap:wrap;gap:4px 16px;flex:1}
header nav a{color:var(--ink);text-decoration:none;font-weight:600;font-size:.95rem}
header nav a:hover{color:var(--blue)}
.mus{background:var(--red);color:#fff!important;border-radius:999px;padding:7px 16px;text-decoration:none;font-weight:700;white-space:nowrap}
h1{font-size:2.1rem;line-height:1.2;margin:6px 0 6px}h2{font-size:1.4rem;margin:42px 0 8px}h3{margin:18px 0 6px;font-size:1.08rem}
.hand{font-family:var(--hand)}
.muted{color:var(--muted)}.small{font-size:.86rem}
.note{background:var(--amber-soft);border:1px solid #f3d9b1;border-radius:10px;padding:10px 14px;margin:14px 0}
.ok{background:var(--green-soft);border:1px solid #bfe3d4;border-radius:10px;padding:10px 14px;margin:14px 0}
.alert{background:var(--red-soft);border:1px solid #f5c2c2;border-radius:10px;padding:10px 14px;margin:14px 0}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:12px}
.card{border:1.5px solid var(--ink);border-radius:14px;padding:12px 14px;background:#fff;box-shadow:3px 3px 0 var(--ink)}
.card h3{margin:0 0 4px;font-family:var(--hand);font-size:1.6rem}.card h3 a{color:var(--ink);text-decoration:none}
.tbl{overflow-x:auto;border:1px solid var(--line);border-radius:10px;margin:10px 0}
table{border-collapse:collapse;width:100%;min-width:560px;font-size:.93rem}
th,td{text-align:left;padding:8px 11px;border-bottom:1px solid var(--line);vertical-align:top}
th{background:var(--soft);font-size:.72rem;text-transform:uppercase;letter-spacing:.05em;color:var(--muted)}
.src{font-size:.8rem;color:var(--muted)} a{color:var(--blue)}
ul li{margin:4px 0}
.badge{display:inline-block;border-radius:999px;padding:1px 9px;font-size:.75rem;font-weight:600;background:var(--soft);color:var(--muted)}
.btn{display:inline-block;background:var(--ink);color:#fff;border-radius:8px;padding:8px 14px;text-decoration:none;font-weight:600}
svg.doodle{width:100%;height:auto;display:block;margin:8px 0;font-family:var(--hand)}
.search{display:flex;border:2px solid var(--ink);border-radius:999px;padding:4px 6px 4px 18px;background:#fff;box-shadow:3px 3px 0 var(--ink);max-width:680px}
.search input{flex:1;border:0;outline:0;font:inherit;font-size:1.08rem;min-width:0;background:transparent}
.search button{border:0;background:var(--ink);color:#fff;border-radius:999px;padding:8px 18px;font:inherit;font-weight:700;cursor:pointer}
.chips{display:flex;flex-wrap:wrap;gap:8px;margin:12px 0 4px}
.chips a{border:1.5px solid var(--ink);border-radius:999px;padding:3px 12px;text-decoration:none;color:var(--ink);background:var(--blue-soft);font-family:var(--hand);font-size:1.2rem}
#results a{display:block;padding:6px 2px;border-bottom:1px solid var(--line);text-decoration:none;font-weight:600}
.pic{border:1px solid var(--line);border-radius:14px;padding:6px 14px 12px;margin:18px 0}
.pic p{margin:4px 0 0}
footer{margin-top:56px;border-top:2px solid var(--ink);padding-top:14px;font-size:.88rem;color:var(--muted)}
footer .sos{font-size:1rem;color:var(--ink)}
footer a{color:var(--muted)}
""" + __import__("safety.water", fromlist=["CSS"]).CSS + """
@media (max-width:640px){h1{font-size:1.7rem}.brand{font-size:1.45rem}header nav{order:3;flex-basis:100%}}
"""

EMERGENCY = "112 India and Europe \u00b7 911 US and Canada \u00b7 000 Australia \u00b7 999 UK \u00b7 1906 LPG gas leak (India)"


def page(title, body, desc, path="/"):
    from safety import doodles
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>{e(title)}</title>
<meta name="description" content="{e(desc)}"><link rel="canonical" href="{SITE_URL}{path}">
<meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(desc)}"><meta property="og:url" content="{SITE_URL}{path}">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">{FONT}<style>{CSS}</style></head><body><div class="wrap">
<header class="top"><a class="brand" href="/">{doodles.logo(38)}Making Human Safe</a>
<nav><a href="/#places">Places</a><a href="/insights/drowning-india/">Insights</a><a href="/pictures/">Stay safe, in pictures</a><a href="/about/">About</a></nav>
<a class="mus" href="/make-us-safe/">MakeUsSafe</a></header>
{body}
<footer><p class="sos"><b>In danger? Call your emergency number.</b> {EMERGENCY}</p>
<p>We are not an emergency service. We show what is known, with sources; a place with no reports is not proven safe.
<a href="/about/#disclaimer">Disclaimer</a> \u00b7 <a href="/about/#privacy">Privacy</a> \u00b7 <a href="/about/#sources">Sources</a> \u00b7
<a href="https://github.com/basantchoudhary/makinghumansafe">Open code</a> \u00b7 Built {datetime.date.today():%-d %b %Y}.</p>
<p class="hand" style="font-size:1.3rem;color:var(--ink)">Someone is waiting for you.</p></footer>
</div></body></html>"""


def place_page(key, cfg):
    wv, alerts, helpd, news = (load(key, n) for n in ("wikivoyage", "alerts", "help", "news"))
    fares_p = ROOT / "fares" / f"{key}.toml"
    fares = tomllib.loads(fares_p.read_text()) if fares_p.exists() else None
    name = cfg["name"]
    water = any(a in cfg.get("activities", []) for a in ("swimming", "waterfall"))
    roadcity = bool(cfg.get("road_stats") or cfg.get("blackspots"))
    out = [f"<h1>{e(name)}: {'water safety, incidents and help' if water else ('road safety, black spots and help' if roadcity else 'safety, scams and fair fares')}</h1>",
           f'<p class="muted">{"What has happened in the water here, what is happening now, and what to do, with a source for every fact." if water else ("How many people die on the roads here, where the black spots are, and what to do, with a source for every fact." if roadcity else "What to watch out for, what taxis should cost, and where help is, with a source for every fact.")}</p>',
           '<div class="note"><b>Coverage:</b> built from open sources (travel guides, news, official alerts, open maps). '
           'Many incidents go unreported, so an absence of reports is not proof of safety.</div>']
    if cfg.get("road_stats") or cfg.get("blackspots"):
        from safety import road
        out.append(road.block(key, cfg))
        out.append('<h2 id="more">More about ' + e(name) + ': help nearby, scams and fares</h2>')
    if water:
        from safety import water as wmod
        out.append(wmod.block(key, cfg, alerts, helpd, load(key, "incois"), load(key, "notices")))
        out.append('<h2 id="more">More about ' + e(name) + ': help nearby, scams and fares</h2>')

    # Before you go
    out.append('<h2 id="quick">Before you go</h2><div class="cards">')
    if fares:
        out.append(f'<div class="card"><h3>Taxis</h3><p>{e(fares["summary"])}</p><a href="#fares">Fare facts</a></div>')
    if wv and wv["data"]["sections"].get("Stay safe"):
        out.append('<div class="card"><h3>Known dangers</h3><p>What the travel guide warns about: scams, touts and risks for visitors.</p><a href="#activities">Read them</a></div>')
    out.append('<div class="card"><h3>Help nearby</h3><p>Nearest hospital, police station and pharmacy for popular spots, with distances.</p><a href="#help">See distances</a></div>')
    out.append('<div class="card"><h3>Helplines</h3><p>' + "<br>".join(f"<b>{n}</b> {e(d)}" for n, d in HELPLINES[:3]) + '</p><a href="#helplines">All helplines</a></div>')
    out.append("</div>")

    # Activities: incidents from the store (only those checked against their source) + precautions
    from safety.store import load as load_store, summarise
    store = load_store(key)
    checked = [i for i in store["incidents"] if i.get("evidence") == "checked"]
    if not roadcity:
        out.append('<h2 id="activities">Activities: what has happened, and what to do</h2>')
        out.append(f'<p class="src">Incidents are counted only when the source article was opened and found to name the place and the event '
                   f'({len(checked)} of {len(store["incidents"])} stored incidents passed this check). Many incidents are never reported.</p>')
        out.append('<div class="cards">')
    for akey, act in (ACTIVITIES.items() if not roadcity else []):
        if akey not in cfg.get("activities", ACTIVITIES):
            continue
        rows = [i for i in checked if i["activity"] in act["incident_activities"]]
        rows.sort(key=lambda i: i["date"], reverse=True)
        if rows:
            s = {"count": len(rows), "deaths": sum(i.get("deaths") or 0 for i in rows), "last": rows[0]["date"],
                 "since": min(i["date"][:4] for i in rows)}
            places = sorted({i["place"] for i in rows})[:4]
            facts = (f'<p><b>{s["count"]}</b> reported incident{"s" if s["count"] != 1 else ""} since {s["since"]}'
                     + (f', <b>{s["deaths"]}</b> death{"s" if s["deaths"] != 1 else ""}' if s["deaths"] else "")
                     + f'. Latest: {e(s["last"])}.</p><p class="src">Where: {e(", ".join(places))}</p>')
        else:
            facts = '<p class="muted">No checked incidents in our records yet.</p>'
        tips = "".join(f"<li>{e(t)}</li>" for t in act["precautions"])
        out.append(f'<div class="card"><h3>{e(act["label"])}</h3>{facts}<ul class="small">{tips}</ul>'
                   '<p class="src">General advice.</p></div>')
    if not roadcity:
        out.append("</div>")

    # Scam patterns (structured, each quoting its source)
    scams_p = ROOT / "scams" / f"{key}.toml"
    if scams_p.exists():
        sc = tomllib.loads(scams_p.read_text())
        out.append('<h2 id="scams">Known scams</h2><div class="tbl"><table><tr><th>Scam</th><th>How it works</th><th>How to avoid it</th><th>Source</th></tr>')
        for r in sc.get("scam", []):
            src_name, src_url = r.get("source", sc["source_default"]), r.get("source_url", sc["source_url_default"])
            where = f'<br><span class="src">Where: {e(", ".join(r["places"]))}</span>' if r.get("places") else ""
            out.append(f'<tr><td><b>{e(r["name"])}</b>{where}</td><td>{e(r["how_it_works"])}</td><td>{e(r["how_to_avoid"])}</td>'
                       f'<td><span class="badge">From travel guide</span><br><a href="{e(src_url)}" title="{e(r["source_text"])}">{e(src_name)}</a></td></tr>')
        out.append("</table></div>")
        if sc.get("rule"):
            out.append('<h3>Local rules visitors break without knowing</h3><ul>' + "".join(
                f'<li>{e(r["rule"])} <span class="src">({e(sc["source_default"])})</span></li>' for r in sc["rule"]) + "</ul>")
    if store.get("rules"):
        out.append('<h3>Official rules and bans</h3><ul>' + "".join(
            f'<li>{e(r["rule"])} <span class="src">(<a href="{e(r["source_url"])}">{e(r.get("source_name") or "source")}</a>{", " + e(r["date"]) if r.get("date") else ""})</span></li>'
            for r in store["rules"]) + "</ul>")
    if store.get("aggregates"):
        out.append('<h3>Official figures</h3><ul>' + "".join(
            f'<li>{e(a["fact"])} <span class="src">(<a href="{e(a["source_url"])}">{e(a.get("source_name") or "source")}</a>)</span></li>'
            for a in store["aggregates"]) + "</ul>")

    # Past incidents table
    if checked:
        out.append('<h2 id="incidents">Past incidents</h2><p class="src">Each row links to its source. No names are shown.</p>'
                   '<div class="tbl"><table><tr><th>Date</th><th>Where</th><th>Activity</th><th>What happened</th><th>Source</th></tr>' + "".join(
            f'<tr><td>{e(i["date"])}</td><td>{e(i["place"])}</td><td>{e(i["activity"])}</td><td>{e(i["what_happened"])}</td>'
            f'<td><span class="badge">From news · checked</span><br><a href="{e(i["source_url"])}">{e(i.get("source_name") or "source")}</a></td></tr>'
            for i in checked[:60]) + "</table></div>")

    # The travel guide's own words (Wikivoyage, CC BY-SA)
    if wv:
        d = wv["data"]
        out.append('<details><summary><b>Read the travel guide\'s full safety section</b></summary>')
        out.append(f'<p class="src">From the Wikivoyage guide to {e(d["page"])}, written by travellers. '
                   f'Quoted under <a href="https://creativecommons.org/licenses/by-sa/4.0/">CC BY-SA 4.0</a>; '
                   f'source: <a href="{e(d["url"])}">{e(d["url"])}</a>, fetched {e(wv["fetched"][:10])}.</p>')
        for sec in d["sections"]:
            paras = d["sections"].get(sec)
            if paras:
                out.append(f"<h3>{e(sec)}</h3><ul>" + "".join(f"<li>{e(p)}</li>" for p in paras) + "</ul>")
        out.append("</details>")

    # Fares
    if fares:
        out.append('<h2 id="fares">Taxi fares: what the rules say</h2>')
        out.append(f'<p>{e(fares["summary"])}</p>')
        out.append('<div class="tbl"><table><tr><th>Figure</th><th>What it is</th><th>Source</th><th>Date</th></tr>' + "".join(
            f'<tr><td><b>{e(r["figure"])}</b></td><td>{e(r["what"])}</td><td><a href="{e(r["url"])}">{e(r["source"])}</a></td><td>{e(r["date"])}</td></tr>'
            for r in fares.get("rule", [])) + "</table></div>")
        out.append("<ul>" + "".join(f'<li>{e(f["text"])} <span class="src">(<a href="{e(f["url"])}">{e(f["source"])}</a>)</span></li>'
                                    for f in fares.get("fact", [])) + "</ul>")
        out.append(f'<p class="src">Collected by hand from the sources linked; checked {e(fares["checked"])}. '
                   'Official figures conflict, so all are shown. <b>Paid a fare recently?</b> <a href="#report">Tell us what you paid.</a></p>')

    # Help nearby
    if helpd:
        h = helpd["data"]
        out.append('<h2 id="help">Help nearby</h2>')
        out.append('<p class="src">Nearest places by straight-line distance, from Overture Maps open data (CDLA-Permissive-2.0), '
                   f'fetched {e(helpd["fetched"][:10])}. Map data can be out of date: call ahead where you can.</p>')
        rows = []
        chk = load(key, "spot_check") or {}
        hidden = []
        for spot, near in h["near"].items():
            if spot in hidden:
                continue
            def cell(items):
                return "<br>".join(f'{e(i["name"])} <b>{i["km"]} km</b>' + (' <span class="badge">listing not confirmed</span>' if i.get("confirmed") is False else "")
                                   + (f'<br><span class="src">{e(i["phone"])}</span>' if i.get("phone") else "")
                                   for i in items[:1]) or '<span class="muted">none found</span>'
            rows.append(f'<tr><td><b>{e(spot)}</b></td><td>{cell(near["hospital"])}</td><td>{cell(near["police"])}</td><td>{cell(near["pharmacy"])}</td></tr>')
        out.append('<div class="tbl"><table><tr><th>Spot</th><th>Nearest hospital</th><th>Nearest police</th><th>Nearest pharmacy</th></tr>'
                   + "".join(rows) + "</table></div>")
        if chk:
            ok = sum(c["verdict"] == "ok" for c in chk.values())
            fixed = [sp for sp, c in chk.items() if c["verdict"] == "far"]
            out.append(f'<p class="src">Spot locations were checked against Wikidata: {ok} of {len(chk)} agree'
                       + (f'; {len(fixed)} map points were wrong and use Wikidata\'s location instead ({e(", ".join(fixed))})' if fixed else "") + '.</p>')
        far = [(s, n["hospital"][0]["km"]) for s, n in h["near"].items() if s not in hidden and n["hospital"] and n["hospital"][0]["km"] >= 10]
        if far:
            out.append('<div class="note"><b>Far from a hospital:</b> ' + "; ".join(f"{e(s)} ({k} km)" for s, k in far)
                       + ". Plan for this, especially with children, older people or risky activities.</div>")

    # Alerts
    out.append('<h2 id="alerts">Official alerts</h2>')
    if alerts and alerts["data"]:
        out.append("<ul>" + "".join(f'<li><b>{e(a["title"])}</b> <span class="src">{e(a.get("date") or "")}</span><br>{e(a["description"])}</li>'
                                    for a in alerts["data"][:8]) + "</ul>")
    else:
        out.append('<div class="ok">No active official disaster or weather alerts mention this place right now.</div>')
    out.append('<p class="src">Source: NDMA SACHET alert feed (India\'s official disaster alerts)'
               + (f', checked {e(alerts["fetched"][:16].replace("T", " "))}' if alerts else "") + ".</p>")

    # News
    out.append('<h2 id="news">Recent news</h2>')
    arts = (news or {}).get("data", {}).get("articles", []) if news else []
    if roadcity:
        RW = ("accident", "crash", "pothole", "collid", "rammed", "run over", "hit-and-run", "skid", "toppled", "road", "traffic", "bike", "lorry", "bus")
        arts = [a for a in arts if any(w in (a.get("title") or "").lower() for w in RW)]
    if arts:
        out.append(f'<p class="src">Safety-related headlines from local papers ({e(", ".join(f[0] for f in cfg.get("news_feeds", [])))}) and GDELT. Links only; read the original for details. '
                   'Not every article is about safety, and many incidents are never reported.</p><ul>'
                   + "".join(f'<li>{e(a["title"] or a["url"])} <span class="src">({e(a["domain"])}, {e(a["date"][:4])}-{e(a["date"][4:6])}-{e(a["date"][6:8])}) '
                             f'<a href="{e(a["url"])}">read</a></span></li>' for a in arts[:15]) + "</ul>")
    else:
        out.append('<p class="muted">News reading for this place is still being set up.</p>')

    # Lenses
    if not roadcity:
        out.append('<h2 id="lenses">If you are travelling with…</h2><div class="cards">')
        for lens, tips in LENSES.items():
            out.append(f'<div class="card"><h3>{e(lens)}</h3><ul>' + "".join(f"<li>{e(t)}</li>" for t in tips) + "</ul></div>")
        out.append("</div>")

    # Helplines and report
    out.append('<h2 id="helplines">Helplines (India)</h2><div class="tbl"><table><tr><th>Number</th><th>For</th></tr>'
               + "".join(f"<tr><td><b>{n}</b></td><td>{e(d)}</td></tr>" for n, d in HELPLINES) + "</table></div>")
    out.append('<h2 id="report">Report a fare or a scam</h2><p>Paid a taxi fare, met a scam, or found something here out of date? '
               'Tell us in 30 seconds: <b>where</b>, <b>what happened or what you paid</b>, and <b>when</b>. No names, please.</p>'
               '<p>For now, report it as an issue on <a href="https://github.com/basantchoudhary/makinghumansafe/issues">GitHub</a>; a simple form is being built.</p>')
    out.append('<h2>Sources and licences</h2><ul class="small">'
               '<li>Wikivoyage, CC BY-SA 4.0 (quoted sections are share-alike)</li>'
               '<li>Overture Maps places, CDLA-Permissive-2.0</li>'
               '<li>NDMA SACHET alert feed</li>'
               f'<li>News links: {e(", ".join(f[0] for f in cfg.get("news_feeds", [])))} RSS feeds, GDELT Project</li>'
               '<li>Fare figures: the news and government sources linked in the fares table</li></ul>')
    return page(f"Is {name} safe to swim? Incidents, sea alerts and help nearby" if water else f"{name}: safety, scams and fair fares", "\n".join(out),
                f"Is {name} safe? Known scams, fair taxi fares, nearest hospitals and police, official alerts, with sources.", path=f"/{key}/")


ALIASES = {"goa": ["calangute", "baga", "anjuna", "palolem", "colva", "arambol", "dudhsagar", "panaji", "north goa", "south goa"],
           "rishikesh": ["ganga rafting", "laxman jhula", "uttarakhand"], "manali": ["solang", "kullu", "himachal", "atal tunnel"],
           "hogenakkal": ["cauvery", "dharmapuri"], "gokarna": ["om beach", "kudle", "half moon", "paradise beach", "kumta"],
           "murudeshwar": ["murdeshwar", "netrani", "bhatkal"], "udupi": ["malpe", "st mary", "kaup", "delta beach", "manipal"],
           "lonavala": ["bhushi", "devkund", "tamhini", "pawna", "malshej", "khandala", "pune"], "alappuzha": ["alleppey", "houseboat", "vembanad", "marari", "kuttanad"],
           "kozhikode": ["calicut", "pathankayam", "kappad", "thikkodi"], "varkala": ["kovalam", "trivandrum", "thiruvananthapuram", "papanasam", "kappil"], "hampi": ["vijayanagara"], "varanasi": ["banaras", "kashi", "ghats"],
           "agra": ["taj mahal"], "bengaluru": ["bangalore", "blr", "nice road", "silk board", "hebbal", "electronic city", "whitefield", "koramangala", "outer ring road"], "delhi": ["new delhi", "paharganj", "connaught place"], "jaipur": ["amer", "pink city"]}


def index_page(places):
    from safety import doodles
    n = len(places)
    cards = "".join(f'<div class="card"><h3><a href="/{k}/">{e(c["name"])}</a></h3><p class="muted small">Scams, fair fares, help nearby, alerts, incidents</p></div>'
                    for k, c in places.items())
    index = json.dumps([{"k": k, "n": c["name"], "a": ALIASES.get(k, [])} for k, c in places.items()])
    chips = "".join(f'<a href="/{k}/">{e(label)}</a>' for k, label in
                    [("routes/bengaluru-nice-road-art-of-living", "Long drive: NICE Road to Art of Living"), ("bengaluru", "Bengaluru roads"), ("gokarna", "Gokarna beaches"), ("goa", "Goa beaches"), ("lonavala", "Lonavala waterfalls"), ("alappuzha", "Alappuzha houseboats"), ("varkala", "Varkala cliffs and beach"), ("rishikesh", "Rafting, Rishikesh")])
    body = (doodles.hero_wait() +
            '<h1>Search a place. See what affects your safety there.</h1>'
            '<p class="muted">Past incidents, live alerts, help nearby, precautions and fair prices, with a source and a date for every fact.</p>'
            '<form class="search" onsubmit="go();return false"><input id="q" placeholder="Where are you going?" autocomplete="off" aria-label="Search a place">'
            '<button>Search</button></form><div id="results"></div>'
            f'<div class="chips">{chips}</div>'
            f'<div class="note"><b>Early preview.</b> We are starting with India and with water safety first: beaches, waterfalls, rivers and boats. {n} places now; more every week. '
            'Every country is coming. <a href="/about/">How we check facts</a>.</div>'
            f'<h2 id="places">Places</h2><div class="cards">{cards}</div>'
            '<h2>Stay safe, in pictures</h2><p>One picture, a thousand words. <a href="/pictures/">See all</a>.</p>' + doodles.rip_current() +
            f"""<script>const P={index};
function match(q){{q=q.trim().toLowerCase();if(q.length<2)return[];return P.filter(p=>p.n.toLowerCase().includes(q)||p.k.includes(q)||p.a.some(a=>a.includes(q)||q.includes(a)))}}
function show(){{const r=match(document.getElementById('q').value);document.getElementById('results').innerHTML=r.map(p=>`<a href="/${{p.k}}/">${{p.n}}</a>`).join('')||(document.getElementById('q').value.trim().length>1?'<p class="muted">Not covered yet. We are adding places every week; tell us where you are going on the <a href="/about/#contact">About page</a>.</p>':'')}}
function go(){{const r=match(document.getElementById('q').value);if(r.length)location.href='/'+r[0].k+'/';else show()}}
document.getElementById('q').addEventListener('input',show);</script>""")
    return page("Making Human Safe: search a place, see what affects your safety", body,
                "Search a place and see what affects your safety there: past incidents, live alerts, help nearby, precautions and fair prices, with sources. Someone is waiting for you.", "/")


def pictures_page():
    from safety import doodles
    import re
    items = []
    for name, fn in doodles.ALL:
        if name in ("hero-wait", "make-us-safe"):
            continue
        s = fn()
        label = re.search(r'aria-label="([^"]+)"', s).group(1)
        items.append(f'<div class="pic" id="{name}">{s}<p>{e(label)}</p></div>')
    body = ('<h1>Stay safe, in pictures</h1><p class="muted">Each picture teaches one thing. Share the one that matters for your next trip or your home.</p>'
            + "".join(items))
    return page("Stay safe, in pictures | Making Human Safe", body,
                "Simple drawings that teach safety: rip currents, monsoon seas, waterfalls, boats and life jackets, gas leaks, falls at home, taxi scams, co-pilot reporting.", "/pictures/")


def about_page():
    body = """<h1>About Making Human Safe</h1>
<p><b>Purpose:</b> before you go anywhere or do anything, at home, on the street, at the beach or abroad, see what has actually happened there,
what is happening now, and what keeps you and your family safe. Every fact has a date and a source.</p>
<h2 id="method">How we check facts</h2>
<ol><li><b>Collect</b> public information: official alerts and statistics, news reports, and reports from people.</li>
<li><b>Check</b> every fact. Each incident keeps its source link and a sentence copied word for word from it. Plain code confirms that sentence is really in the source before anything is published. AI may help read news; it never decides what is true.</li>
<li><b>Connect</b> facts to places, spots, causes, seasons and the people they affect.</li>
<li><b>Show only what affects you</b>, with the date it was last checked.</li></ol>
<p>We never name victims. We never call a place "safe"; we say what is known. When we get something wrong, we correct it openly.</p>
<h2 id="disclaimer">Disclaimer</h2>
<p>Making Human Safe gathers public information (official alerts and statistics, news reports and reports from visitors) and shows it with its source and the date it was last checked.
It may be incomplete, out of date or wrong, and conditions can change in minutes. <b>The absence of incidents or alerts does not mean a place or activity is safe.</b>
Always follow official warnings, lifeguards, flags and local authorities. This site does not give medical, legal or emergency advice. Reports from visitors are labelled as reports until confirmed.
We are not an emergency service: in danger, call your local emergency number.</p>
<h2 id="privacy">Privacy</h2>
<p>We do not use tracking cookies or advertising trackers. MakeUsSafe (coming soon) will work inside your browser, so we will not see your family details.
We will store contact details only if you ask for alerts, and you will be able to delete them anytime.</p>
<h2 id="sources">Sources and credits</h2>
<p>Each source keeps its own licence and is credited on the pages that use it. Examples: Wikivoyage (CC BY-SA 4.0), Overture Maps and OpenStreetMap (map data),
NDMA SACHET (India's official disaster alerts), and news publishers (short quotes with links). The code is open: <a href="https://github.com/basantchoudhary/makinghumansafe">github.com/basantchoudhary/makinghumansafe</a>.</p>
<h2 id="contact">Contact and corrections</h2>
<p>Found a mistake, or want a place covered? Open an issue on <a href="https://github.com/basantchoudhary/makinghumansafe/issues">GitHub</a>. An email address is coming soon.</p>"""
    return page("About, method and disclaimer | Making Human Safe", body,
                "How Making Human Safe checks every fact, our disclaimer, privacy and sources.", "/about/")


def mus_page():
    from safety import doodles
    body = ('<h1>MakeUsSafe</h1><p>Tell us who is going, where and when, and what you will do. You will get a safety brief just for your family: '
            'the top risks for your people at that place and time, live alerts, help nearby and a checklist.</p>'
            + doodles.make_us_safe_steps() +
            '<div class="note"><b>Coming soon.</b> Until then, search your destination on the <a href="/">home page</a>. '
            'It will work inside your browser; your family details will never be sent to us.</div>')
    return page("MakeUsSafe: a safety brief for your family | Making Human Safe", body,
                "Tell us who is going, where, when and what you will do; get a safety brief for your family. Coming soon.", "/make-us-safe/")


def favicon():
    from safety import doodles
    s = doodles.logo(64)
    return s.replace('<svg class="logo"', '<svg xmlns="http://www.w3.org/2000/svg"', 1)


def main():
    places = tomllib.loads((ROOT / "places.toml").read_text())
    SITE.mkdir(exist_ok=True)
    for key, cfg in places.items():
        (SITE / key).mkdir(exist_ok=True)
        (SITE / key / "index.html").write_text(place_page(key, cfg))
    (SITE / "index.html").write_text(index_page(places))
    for path, fn in (("pictures", pictures_page), ("about", about_page), ("make-us-safe", mus_page)):
        (SITE / path).mkdir(exist_ok=True)
        (SITE / path / "index.html").write_text(fn())
    (SITE / "favicon.svg").write_text(favicon())
    from safety import insights
    body, csv_text = insights.drowning_india()
    d = SITE / "insights" / "drowning-india"
    d.mkdir(parents=True, exist_ok=True)
    (d / "index.html").write_text(page("Where and when people drown in India: checked incidents, months, places | Making Human Safe", body,
        "When and where people drown in India, from checked incidents: May and June are worst, most victims are groups of young friends, and most drownings happen on calm days. Open data.",
        "/insights/drowning-india/"))
    (d / "water-incidents-india.csv").write_text(csv_text)
    from safety import routes
    for slug, r in routes.load_routes().items():
        f = ROOT / "data" / "_road" / f"route_{slug}.json"
        if f.exists():
            rd = SITE / "routes" / slug
            rd.mkdir(parents=True, exist_ok=True)
            data = json.loads(f.read_text())
            (rd / "index.html").write_text(page(f"{r['from_name']} to {r['to_name']}: long-drive safety brief | Making Human Safe", routes.page_body(slug, r, data),
                f"Driving from {r['from_name']} to {r['to_name']} ({data['km']} km): official black spots on the route, hospitals and police along the way, and a pre-drive checklist.",
                f"/routes/{slug}/"))
    print(f"built {len(places)} place page(s) into {SITE}")


if __name__ == "__main__":
    main()
