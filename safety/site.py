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


CSS = """
:root{--ink:#1d2129;--muted:#5d6470;--line:#e3e6ea;--soft:#f6f7f9;--blue:#2a78d6;--amber:#a15c00;--amber-soft:#fff4e5;--green:#17795a;--green-soft:#e4f3ed}
*{box-sizing:border-box}body{margin:0;background:#fff;color:var(--ink);font:16px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
.wrap{max-width:920px;margin:0 auto;padding:24px 16px 70px}
header.top{display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid var(--line);padding-bottom:12px;margin-bottom:22px}
header.top a{color:var(--ink);text-decoration:none;font-weight:700}
h1{font-size:2rem;margin:0 0 4px}h2{font-size:1.35rem;margin:40px 0 8px}h3{margin:18px 0 6px;font-size:1.05rem}
.muted{color:var(--muted)}.small{font-size:.85rem}
.note{background:var(--amber-soft);border:1px solid #f3d9b1;border-radius:10px;padding:10px 14px;margin:14px 0}
.ok{background:var(--green-soft);border:1px solid #bfe3d4;border-radius:10px;padding:10px 14px;margin:14px 0}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:10px}
.card{border:1px solid var(--line);border-radius:10px;padding:12px 14px}.card h3{margin:0 0 6px}
.tbl{overflow-x:auto;border:1px solid var(--line);border-radius:10px;margin:10px 0}
table{border-collapse:collapse;width:100%;min-width:560px;font-size:.93rem}
th,td{text-align:left;padding:8px 11px;border-bottom:1px solid var(--line);vertical-align:top}
th{background:var(--soft);font-size:.72rem;text-transform:uppercase;letter-spacing:.05em;color:var(--muted)}
.src{font-size:.8rem;color:var(--muted)} a{color:var(--blue)}
ul li{margin:4px 0}
.badge{display:inline-block;border-radius:999px;padding:1px 9px;font-size:.75rem;font-weight:600;background:var(--soft);color:var(--muted)}
.btn{display:inline-block;background:var(--ink);color:#fff;border-radius:8px;padding:8px 14px;text-decoration:none;font-weight:600}
footer{margin-top:50px;border-top:1px solid var(--line);padding-top:12px;font-size:.82rem;color:var(--muted)}
"""


def page(title, body, desc):
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>{e(title)}</title>
<meta name="description" content="{e(desc)}"><style>{CSS}</style></head><body><div class="wrap">
<header class="top"><a href="../index.html">Safety Intelligence</a><span class="small muted">Is it safe, and what should I watch out for?</span></header>
{body}
<footer>Information and precautions from open sources, not a guarantee of safety. In an emergency call 112.
Built {datetime.date.today():%-d %b %Y}. Sources and licences are listed on each page.</footer>
</div></body></html>"""


def place_page(key, cfg):
    wv, alerts, helpd, news = (load(key, n) for n in ("wikivoyage", "alerts", "help", "news"))
    fares_p = ROOT / "fares" / f"{key}.toml"
    fares = tomllib.loads(fares_p.read_text()) if fares_p.exists() else None
    name = cfg["name"]
    out = [f"<h1>{e(name)}: safety, scams and fair fares</h1>",
           f'<p class="muted">What to watch out for, what taxis should cost, and where help is, with a source for every fact.</p>',
           '<div class="note"><b>Coverage:</b> built from open sources (travel guides, news, official alerts, open maps). '
           'Many incidents go unreported, so an absence of reports is not proof of safety.</div>']

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
    out.append('<h2 id="activities">Activities: what has happened, and what to do</h2>')
    out.append(f'<p class="src">Incidents are counted only when the source article was opened and found to name the place and the event '
               f'({len(checked)} of {len(store["incidents"])} stored incidents passed this check). Many incidents are never reported.</p>')
    out.append('<div class="cards">')
    for akey, act in ACTIVITIES.items():
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
                   f'<p class="src">General advice; review {e(act["reviewed"])}.</p></div>')
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
                return "<br>".join(f'{e(i["name"])} <b>{i["km"]} km</b>' + (f'<br><span class="src">{e(i["phone"])}</span>' if i.get("phone") else "")
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
    if arts:
        out.append(f'<p class="src">Safety-related headlines from local papers ({e(", ".join(f[0] for f in cfg.get("news_feeds", [])))}) and GDELT. Links only; read the original for details. '
                   'Not every article is about safety, and many incidents are never reported.</p><ul>'
                   + "".join(f'<li>{e(a["title"] or a["url"])} <span class="src">({e(a["domain"])}, {e(a["date"][:4])}-{e(a["date"][4:6])}-{e(a["date"][6:8])}) '
                             f'<a href="{e(a["url"])}">read</a></span></li>' for a in arts[:15]) + "</ul>")
    else:
        out.append('<p class="muted">News reading for this place is still being set up.</p>')

    # Lenses
    out.append('<h2 id="lenses">If you are travelling with…</h2><div class="cards">')
    for lens, tips in LENSES.items():
        out.append(f'<div class="card"><h3>{e(lens)}</h3><ul>' + "".join(f"<li>{e(t)}</li>" for t in tips) + "</ul></div>")
    out.append("</div>")

    # Helplines and report
    out.append('<h2 id="helplines">Helplines (India)</h2><div class="tbl"><table><tr><th>Number</th><th>For</th></tr>'
               + "".join(f"<tr><td><b>{n}</b></td><td>{e(d)}</td></tr>" for n, d in HELPLINES) + "</table></div>")
    out.append('<h2 id="report">Report a fare or a scam</h2><p>Paid a taxi fare, met a scam, or found something here out of date? '
               'Tell us in 30 seconds: <b>where</b>, <b>what happened or what you paid</b>, and <b>when</b>. No names, please.</p>'
               '<p><span class="badge">Report form coming soon</span></p>')
    out.append('<h2>Sources and licences</h2><ul class="small">'
               '<li>Wikivoyage, CC BY-SA 4.0 (quoted sections are share-alike)</li>'
               '<li>Overture Maps places, CDLA-Permissive-2.0</li>'
               '<li>NDMA SACHET alert feed</li>'
               f'<li>News links: {e(", ".join(f[0] for f in cfg.get("news_feeds", [])))} RSS feeds, GDELT Project</li>'
               '<li>Fare figures: the news and government sources linked in the fares table</li></ul>')
    return page(f"{name}: safety, scams and fair fares", "\n".join(out),
                f"Is {name} safe? Known scams, fair taxi fares, nearest hospitals and police, official alerts, with sources.")


def index_page(places):
    cards = "".join(f'<div class="card"><h3><a href="{k}/index.html">{e(c["name"])}</a></h3><p class="muted">Scams, fair fares, help nearby, alerts</p></div>'
                    for k, c in places.items())
    body = ("<h1>Is it safe, and what should I watch out for?</h1>"
            "<p>Known scams, fair prices, past incidents, official alerts and the nearest help for places people travel to, "
            "with a source for every fact.</p>"
            f'<h2>Places</h2><div class="cards">{cards}</div>'
            '<div class="note">This is an early version covering a few places. More are being added.</div>')
    return page("Safety Intelligence", body, "Travel safety, scams and fair fares with sources").replace('href="../index.html"', 'href="index.html"')


def main():
    places = tomllib.loads((ROOT / "places.toml").read_text())
    SITE.mkdir(exist_ok=True)
    for key, cfg in places.items():
        (SITE / key).mkdir(exist_ok=True)
        (SITE / key / "index.html").write_text(place_page(key, cfg))
    (SITE / "index.html").write_text(index_page(places))
    print(f"built {len(places)} place page(s) into {SITE}")


if __name__ == "__main__":
    main()
