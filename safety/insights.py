"""Insight pages: one question, hand-drawn charts, plain answers, open data. Built only from checked records."""
import collections, csv, html, io, json, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
e = html.escape
MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()


def bars(counts, labels, title, color="#2a78d6", w=900, h=300, highlight=()):
    """A hand-drawn bar chart (wobbly ink, handwritten labels)."""
    from safety.doodles import WOBBLE, p, t
    mx = max(counts) or 1
    bw = (w - 80) / len(counts)
    inner = p(f"M50,{h - 50} L{w - 20},{h - 50} M50,{h - 50} L50,40", w=2)
    txt = t(60, 30, e(title), 22, 700)
    for i, (c, lab) in enumerate(zip(counts, labels)):
        x = 60 + i * bw
        bh = (h - 110) * c / mx
        inner += p(f"M{x + 6},{h - 50} L{x + 6},{h - 50 - bh} L{x + bw - 6},{h - 50 - bh} L{x + bw - 6},{h - 50}",
                   fill="#e34948" if i in highlight else color, w=1.8)
        txt += t(x + bw / 2, h - 28, e(lab), 18, 400, "middle") + t(x + bw / 2, h - 58 - bh, str(c), 18, 700, "middle")
    return (f'<svg class="doodle" viewBox="0 0 {w} {h}" role="img" aria-label="{e(title)}: '
            + e(", ".join(f"{l} {c}" for l, c in zip(labels, counts))) + f'">{WOBBLE}<g filter="url(#wob)">{inner}</g>{txt}</svg>')


def drowning_india():
    rows = [r for r in json.loads((ROOT / "data/_corpus/water_incidents.json").read_text())["incidents"]
            if r["country"] == "India" and r.get("evidence") == "checked"]
    deaths = sum(r.get("deaths") or 0 for r in rows)
    by_month = collections.Counter(r["month"] for r in rows)
    m = [by_month.get(i, 0) for i in range(1, 13)]
    by_type = collections.Counter(r.get("water_body") for r in rows)
    tlabel = {"sea_beach": "Sea beach", "river": "River", "waterfall": "Waterfall", "sea_boat": "Boat at sea",
              "backwater": "Backwater", "lake": "Lake", "dam": "Dam", "reservoir": "Reservoir"}
    types = by_type.most_common()
    dist = collections.Counter(f'{r.get("district") or r["state"]}, {r["state"]}' for r in rows).most_common(8)
    warn = sum(r.get("warning_ignored") is True for r in rows)
    lifeguard = sum(r.get("lifeguard_present") is True for r in rows)
    bt = json.loads((ROOT / "data/_research/wave_backtest.json").read_text())["summary"] if (ROOT / "data/_research/wave_backtest.json").exists() else None
    first, last = min(r["date"] for r in rows), max(r["date"] for r in rows)

    body = [f"<h1>Where and when people drown in India</h1>",
            f'<p class="muted">From {len(rows)} water incidents we checked one by one ({first[:4]} to {last[:4]}), {deaths} deaths. '
            "Each record links to a news report, and we confirmed the quoted sentence is really in it. "
            "This is not every drowning in India (official figures run to tens of thousands a year); it is a careful sample that shows patterns.</p>",
            "<h2>When: May and June are the worst months</h2>",
            bars(m, MONTHS, "Water incidents by month", highlight=(4, 5)),
            "<p>Summer holidays bring crowds to beaches and waterfalls, and pre-monsoon and monsoon swells make the sea rough. "
            "Waterfalls and rivers are most dangerous in the monsoon (June to September), when water can rise within minutes.</p>",
            "<h2>Where: the type of water</h2>",
            bars([c for _, c in types], [tlabel.get(k, k or "other") for k, _ in types], "Water incidents by type of water", color="#17795a"),
            "<h2>Where: places with the most incidents</h2><ol>" + "".join(f"<li>{e(d)}: {c}</li>" for d, c in dist) + "</ol>",
            "<h2>A calm sea is not a safe sea</h2>"]
    if bt:
        body.append(f'<p>We checked the waves on the day of {bt["incidents_tested"]} beach drownings: those days were no rougher than the three months around them '
                    f'(average 51st percentile; only {round(bt["share_top_quarter_wave"] * 100)}% among the roughest quarter of days, against 25% by chance). '
                    "People drown on ordinary-looking days, pulled by rip currents or a sudden wave. A calm forecast is not a reason to swim.</p>")
    body += ["<h2>Who, and why</h2><ul>",
             "<li>Most victims were groups of young friends, students or colleagues on a trip. Often several people were swept away together, and some drowned trying to rescue a friend.</li>",
             f"<li>In {warn} incidents the report says people went in despite a red flag, a barrier, a ban or a lifeguard's warning.</li>",
             f"<li>A lifeguard is mentioned as present in {lifeguard} incidents: lifeguards save lives, but only where people swim near them.</li></ul>",
             "<h2>What to do</h2><p>Swim only near lifeguards and between their flags; never after drinking or in the evening; stay off wet rocks; "
             "if caught in a rip current, swim sideways, not back; if a friend is pulled out, shout for help and throw something that floats instead of swimming after them. "
             '<a href="/pictures/">See the pictures</a>.</p>',
             '<h2>Open data</h2><p><a href="/insights/drowning-india/water-incidents-india.csv" download>Download the table (CSV)</a>: date, place, type of water, deaths and the source link for every incident. '
             "Free to use with credit to Making Human Safe. The death counts are as first reported; some tolls rose later.</p>"]
    # CSV (no quotes from articles, only facts and links)
    buf = io.StringIO()
    wr = csv.writer(buf)
    wr.writerow(["date", "state", "district", "spot", "water_type", "incident_type", "deaths", "warning_ignored", "source_name", "source_url"])
    for r in sorted(rows, key=lambda r: r["date"]):
        wr.writerow([r["date"], r["state"], r.get("district"), r.get("spot"), r.get("water_body"), r.get("incident_type"),
                     r.get("deaths"), r.get("warning_ignored"), r.get("source_name"), r["source_url"]])
    return "\n".join(body), buf.getvalue()
