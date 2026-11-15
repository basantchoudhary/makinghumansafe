"""Lessons from incidents: each checked incident is tagged with risk factors from a fixed list, every tag backed by
words in the incident record or its article (an evidence snippet is kept). Repeating factors become ranked lessons,
each with what a person can do and what the city should fix. Rules first; no AI guessing.
"""
import collections, hashlib, html, pathlib, re

ROOT = pathlib.Path(__file__).resolve().parent.parent
e = html.escape

# (key, label, evidence pattern, what you can do, what the city should fix)
FACTORS = {"road": [
    ("pothole", "Pothole or bad road", r"pothole|crater|damaged road|bad road|uneven road|open drain|drainage pit|loose stones",
     "Slow down in rain, when potholes hide under water; never swerve suddenly.", "Fix potholes fast and publish repair times; pay victims as the High Court ordered."),
    ("hitrun", "Hit-and-run", r"hit-and-run|hit and run|fled|sped away|escaped from the spot|absconding|did not stop",
     "Note the vehicle number if you can, call 112 at once, and help the injured reach hospital.", "Cameras at junctions and faster tracing of fleeing drivers."),
    ("nohelmet", "No helmet", r"without (?:a )?helmet|not wearing (?:a )?helmet|no helmet|helmet(?:-less|less)",
     "Clasp your helmet, and make the pillion rider wear one too.", "Steady helmet enforcement, including pillion riders."),
    ("speed", "Speeding or loss of control", r"speeding|high speed|over-?speed(?:ing)?|lost control|at great speed|sped\b",
     "Slow down, most of all at night and on empty roads.", "Speed cameras and traffic calming on fast stretches."),
    ("night", "Night or early hours", r"\bnight\b|late hours|early hours|midnight|\b(?:1[0-2]|[1-5])(?:\.\d\d)? ?(?:am|a\.m\.)\b|after dark",
     "Take extra care after dark: dip high beams, watch for people walking and parked vehicles.", "Street lighting and night enforcement."),
    ("heavy", "Lorry, tipper, bus or truck", r"lorry|tipper|truck|container|\bbus\b|bmtc|ksrtc|tanker",
     "Stay out of heavy vehicles' blind spots; never overtake them on the left near junctions.", "Time and lane rules for heavy vehicles; trained, rested drivers."),
    ("crossing", "Person walking or crossing", r"pedestrian|crossing the road|was walking|while walking|footpath|zebra|skywalk",
     "Cross at signals or skywalks; be seen at night.", "Safe crossings, continuous footpaths and refuge islands."),
    ("wrongside", "Wrong-side driving", r"wrong side|wrong direction|wrong-side",
     "Expect wrong-side riders on service roads and near medians.", "Close illegal median gaps; enforce on service roads."),
    ("drink", "Drink-driving", r"drunk(?:en)?[- ]driv|drunk driver|driv\w*\s+(?:while\s+)?drunk|driving under the influence|(?:driver|rider|motorist)\s+(?:was|were)\s+(?:drunk|inebriated)|driven by a drunk",
     "Never drive after drinking; take a cab.", "Drink-driving checkpoints, especially on weekend nights."),
    ("flyover", "Flyover or underpass", r"flyover|underpass|overpass|elevated",
     "Slow down on flyover bends and slopes; keep a gap.", "Crash barriers, signs and speed control on flyovers."),
    ("rain", "Rain or wet road", r"\brain\b|rainy|wet road|waterlogg|slippery",
     "Slow down and brake early on wet roads.", "Drainage and quick pothole repair after rain."),
]}


def article_text(url, quote=""):
    """The article body around our checked quote (from the page cached when we checked it). Only ~1,500 characters
    either side of the quote are searched, so sidebars and other stories on the page never create tags."""
    f = ROOT / "data" / "_pages" / (hashlib.sha1(url.encode()).hexdigest()[:16] + ".txt")
    if not f.exists():
        return ""
    t = f.read_text()
    q = re.sub(r"\s+", " ", (quote or "").lower()).strip()[:60]
    i = t.find(q) if q else -1
    return t[max(0, i - 1500): i + 1500] if i >= 0 else ""


UNCERTAIN = re.compile(r"\bwhether\b|ascertain|to determine|probe if|probing if|if he was|if she was|yet to be confirmed|suspected|suspect|allegedly not|denied", re.I)


def sentences(text):
    return [x.strip() for x in re.split(r"(?<=[.!?])\s+|\n+", text or "") if len(x.strip()) > 15]


def tag(r, topic="road"):
    """Return [(factor key, label, evidence sentence)] for one incident. A factor counts only if a whole sentence
    in the record or the article body says it, and that sentence is not uncertain ('whether', 'to determine'...)."""
    own = " ".join(str(r.get(k) or "") for k in ("what_happened", "cause", "incident_type", "quote", "spot"))
    art = article_text(r.get("source_url") or "", r.get("quote") or "")
    out = []
    for key, label, rx, _, _ in FACTORS.get(topic, []):
        ev = next((sn for sn in sentences(own) + sentences(art) if re.search(rx, sn, re.I) and not UNCERTAIN.search(sn)), None)
        if ev:
            out.append((key, label, ev[:220] + ("…" if len(ev) > 220 else "")))
    return out


def summary(incidents, topic="road"):
    """Ranked lessons across incidents: factor, crashes, deaths, actions, one example."""
    rows = collections.defaultdict(list)
    for r in incidents:
        for key, label, ev in tag(r, topic):
            rows[key].append((r, ev))
    out = []
    for key, label, _, you, city in FACTORS.get(topic, []):
        if rows.get(key):
            rs = rows[key]
            out.append({"key": key, "label": label, "crashes": len(rs), "deaths": sum(r.get("deaths") or 0 for r, _ in rs),
                        "you": you, "city": city, "example": rs[0]})
    return sorted(out, key=lambda x: (-x["crashes"], -x["deaths"]))


def tags_html(r, topic="road"):
    return " ".join(f'<span class="tag" title="{e(ev)}">{e(label)}</span>' for _, label, ev in tag(r, topic))


def render(incidents, topic="road"):
    ls = summary(incidents, topic)
    if not ls:
        return ""
    n = len(incidents)
    rows = "".join(
        f'<tr><td><b>{e(x["label"])}</b></td><td>{x["crashes"]} of {n}</td><td>{x["deaths"]}</td><td>{e(x["you"])}</td><td>{e(x["city"])}</td>'
        f'<td class="small">{e(x["example"][0]["date"])}, {e(x["example"][0].get("spot") or "")}: <i>{e(x["example"][1])}</i> '
        f'(<a href="{e(x["example"][0]["source_url"])}">source</a>)</td></tr>' for x in ls)
    return (f'<h2 id="lessons">Lessons from {n} checked crashes</h2>'
            f'<p class="muted">Each crash is tagged with risk factors only when its report says so (hover a tag to see the words). '
            'A crash can have several factors. These are patterns in reported crashes, not official causes.</p>'
            '<div class="tbl"><table><tr><th>What keeps happening</th><th>Crashes</th><th>Deaths</th><th>What you can do</th><th>What the city should fix</th><th>Example</th></tr>'
            + rows + "</table></div>")


CSS = """
.tag{display:inline-block;border:1px solid var(--ink);border-radius:999px;padding:0 8px;font-size:.75rem;margin:2px 3px 0 0;background:var(--amber-soft);cursor:help}
"""
