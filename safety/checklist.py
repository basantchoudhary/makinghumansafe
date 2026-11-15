"""Category checklist: India's standard breakdown of road crashes (as in MoRTH 'Road Accidents in India' and iRAD),
filled for each place from checked facts and checked incidents, with honest gaps and who holds the missing data.
Defined once per topic, so every city gets the same checklist."""
import html, re

e = html.escape

CATEGORIES = {"road": [
    ("Severity", "fatal, grievous, minor, no injury", r"injur|grievous|fatal crash|killed|deaths? total|fatalities total", "how_many", "Traffic police (yearly statistics); MoRTH"),
    ("Who died (road user)", "walking, cycling, two-wheeler, car, auto, bus, truck", r"pedestrian|motorcycl|two-wheel|cyclist|car occupant|auto", "who", "Traffic police; MoRTH annexures"),
    ("Who hit whom", "which vehicle hit which road user", r"collision with|collisions with|hit by|who hit whom|impacting|rammed|knocked down", None, "Traffic police (crash reports, iRAD)"),
    ("Type of collision", "rear-end, head-on, side, hit pedestrian, ran off road, fixed object, overturned", r"rear|head-on|from behind|side impact|overturn|fixed object|single vehicle|skid|veered", None, "Traffic police (iRAD)"),
    ("Cause (traffic offence)", "speeding, drink-driving, wrong side, red light, phone", r"speed|drunk|drink|wrong side|red light|signal jump|mobile|phone|overtak", "why", "Traffic police; MoRTH"),
    ("Safety gear", "helmet, seat belt, child seat", r"helmet|seat ?belt|restraint", None, "Traffic police; road-safety observation studies"),
    ("Road and feature", "highway, city road, junction, flyover, curve, pothole", r"highway|expressway|junction|flyover|underpass|pothole|corridor|black ?spot|road\b", "where", "Traffic police; city corporation; NHAI"),
    ("Weather and light", "clear, rain, fog; day or night", r"fog|wet road|visibility|street ?light|unlit|night|after dark|rain\w*[^.]{0,60}(?:crash|accident|skid|fatalit)", None, "Traffic police (iRAD)"),
    ("Time", "hour, day of week, month", r"\bpm\b|\bam\b|hour|weekend|sunday|monday|month|night", "when", "Traffic police; NCRB (time of day)"),
    ("Place within the city", "division, police station, ward, road", r"division|police station|ward|zone|road\b|junction", "where", "Traffic police (station-wise data)"),
    ("Age and sex of victims", "age groups, men and women", r"aged|age group|years old|\bmen\b|women|male|female", None, "Traffic police; NCRB"),
    ("Licence and vehicle", "licence status, vehicle age and fitness", r"licen[cs]e|unlicensed|vehicle age|fitness certificate|insurance", None, "Transport department (RTO); traffic police"),
]}

INCIDENT_HINTS = {"Who died (road user)": "vehicle", "Who hit whom": "what_happened", "Type of collision": "what_happened",
                  "Cause (traffic offence)": "what_happened", "Road and feature": "spot", "Time": "date", "Place within the city": "spot"}


OFFICIAL_DOMAINS = re.compile(r"https?://(?:[a-z0-9-]+\.)*(?:gov\.in|nic\.in|gov\b)", re.I)


def is_official(f):
    """Official = published on a government website (by its address), never judged from a title's wording."""
    return bool(OFFICIAL_DOMAINS.match(f.get("source_url") or ""))


def render(place, topic, fs, incidents):
    rows = []
    covered = 0
    for name, groups, rx, dim, holder in CATEGORIES.get(topic, []):
        hits = [f for f in fs if re.search(rx, (f.get("statement") or "") + " " + (f.get("metric") or ""), re.I)
                and (dim is None or f["dimension"] == dim or name in ("Safety gear", "Weather and light", "Age and sex of victims", "Who hit whom", "Type of collision", "Licence and vehicle"))]
        official = [f for f in hits if is_official(f)]
        inc_field = INCIDENT_HINTS.get(name)
        inc_n = sum(1 for r in incidents if inc_field and r.get(inc_field) and re.search(rx, str(r.get(inc_field)), re.I)) if inc_field not in ("vehicle", "date", "spot") \
            else (sum(1 for r in incidents if r.get(inc_field)) if inc_field else 0)
        if official:
            status, cls = "Covered (official)", "yes"
        elif hits or inc_n:
            status, cls = "Partly (news and our checked crashes)", "maybe"
        else:
            status, cls = "No public data yet", "no"
        covered += cls != "no"
        best = sorted(official or hits, key=lambda f: (f.get("value") is not None, (f.get("unit") or "") == "%", str(f.get("period") or "")), reverse=True)[:1]
        know = (f'{e(best[0]["statement"])} <span class="src">({e(str(best[0]["period"]))}; <a href="{e(best[0]["source_url"])}">{e(best[0]["source_name"])}</a>)</span>'
                if best else "")
        if inc_n and cls != "yes":
            know += f'<br><span class="small">{inc_n} of our {len(incidents)} checked crashes describe this.</span>'
        rows.append(f'<tr><td><b>{e(name)}</b><br><span class="small muted">{e(groups)}</span></td><td><span class="badge {cls}">{e(status)}</span></td>'
                    f'<td>{know or "<span class=muted>Not published for this city.</span>"}</td>'
                    f'<td class="small">{e(holder) if cls != "yes" else ""}</td></tr>')
    n = len(CATEGORIES.get(topic, []))
    return (f'<h2 id="checklist">The full picture: {covered} of {n} standard categories</h2>'
            "<p class=\"muted\">India's road ministry splits every crash the same way. Here is what is publicly known for this city in each category, "
            "and who holds the data where it is missing (a Right to Information request can ask them).</p>"
            '<div class="tbl"><table><tr><th>Category</th><th>Status</th><th>What we know here</th><th>Who holds the missing data</th></tr>'
            + "".join(rows) + "</table></div>")
