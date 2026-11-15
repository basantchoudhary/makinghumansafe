"""Simple pictures chosen automatically from the shape of the facts (one idea per picture, one plain line on top).

Patterns borrowed from good data storytellers:
  - Isotype pictographs (little people instead of percentages): shares of a whole, e.g. who dies.
  - Clock and week charts: 'when' facts with hours or days.
  - 'N of 100' behaviour pictures: helmet, seat-belt, child-seat use.
  - Annotated trend bars (one label on the bar that matters): yearly totals.
Every picture is built from checked facts; nothing is drawn by hand per city.
"""
import html, json, math, re

from safety.doodles import WOBBLE, p, t

e = html.escape
INK, RED, BLUE, GREEN, AMBER, GREY = "#1d2129", "#e34948", "#2a78d6", "#17795a", "#f0a52b", "#c9ced6"


def _svg(w, h, label, inner, txt=""):
    return (f'<svg class="doodle" viewBox="0 0 {w} {h}" role="img" aria-label="{e(label)}">{WOBBLE}'
            f'<g filter="url(#wob)">{inner}</g>{txt}</svg>')


# --- tiny icons (hand-drawn style) ---
def rider(x, y, fill):
    return (p(f"M{x - 13},{y + 18} a7,7 0 1,0 0.1,0 M{x + 13},{y + 18} a7,7 0 1,0 0.1,0", w=2) +
            p(f"M{x - 13},{y + 18} L{x - 2},{y + 6} L{x + 13},{y + 18} M{x - 2},{y + 6} L{x + 4},{y - 6}", w=2.2) +
            f'<circle cx="{x + 4}" cy="{y - 14}" r="6" fill="{fill}" stroke="{INK}" stroke-width="2"/>')


def walker(x, y, fill):
    return (f'<circle cx="{x}" cy="{y - 14}" r="6" fill="{fill}" stroke="{INK}" stroke-width="2"/>' +
            p(f"M{x},{y - 8} L{x},{y + 10} M{x},{y - 2} L{x - 8},{y + 6} M{x},{y - 2} L{x + 8},{y + 4} M{x},{y + 10} L{x - 7},{y + 24} M{x},{y + 10} L{x + 8},{y + 24}", w=2.2))


def other(x, y, fill):
    return p(f"M{x - 16},{y + 14} v-10 q4,-12 14,-12 h6 q10,0 12,12 v10 z", fill=fill, w=2) + \
        p(f"M{x - 9},{y + 18} a4,4 0 1,0 0.1,0 M{x + 9},{y + 18} a4,4 0 1,0 0.1,0", w=2)


GROUPS = [("motorcycl|two_wheel|biker|rider", "on two-wheelers", rider, BLUE),
          ("pedestrian|walk", "walking", walker, AMBER),
          ("car|occupant|cyclist|other", "others", other, GREY)]


def who_pictograph(fs):
    """Shares of deaths by road-user group become 10 little people."""
    shares = []
    for rx, label, icon, col in GROUPS[:2]:
        f = next((f for f in fs if f["dimension"] == "who" and (f.get("unit") or "") == "%" and f.get("value")
                  and re.search(rx, (f["metric"] or "") + " " + (f["statement"] or ""), re.I) and "death" in ((f["metric"] or "") + (f["statement"] or "")).lower()
                  or (f["dimension"] == "who" and (f.get("unit") or "") == "%" and re.search(rx, f["metric"] or "", re.I) and "fatalit" in (f["statement"] or "").lower())), None)
        if f:
            shares.append((label, icon, col, float(f["value"]), f))
    if not shares or sum(s[3] for s in shares) > 100:
        return None
    counts = [round(s[3] / 10) for s in shares]
    rest = 10 - sum(counts)
    icons = [(s[1], s[2]) for s, n in zip(shares, counts) for _ in range(n)] + [(other, GREY)] * max(rest, 0)
    inner = "".join(f'<g transform="translate({40 + i * 84},20) scale(1.6)">' + ic(20, 30, col) + "</g>" for i, (ic, col) in enumerate(icons[:10]))
    parts = [f"{n} {s[0]}" for s, n in zip(shares, counts)] + ([f"{rest} others"] if rest > 0 else [])
    head = "Of every 10 people killed: " + ", ".join(parts) + "."
    legend = t(40, 160, "blue: on two-wheelers   orange: walking   grey: others", 16)
    return {"title": head, "svg": _svg(880, 175, head, inner, legend), "facts": [s[4] for s in shares]}


def clock(f):
    """A 24-hour clock with the dangerous hours shaded."""
    w = json.loads(f["time_window"]) if f.get("time_window") else {}
    if not w.get("hours"):
        return None
    ranges = hour_ranges(f["statement"]) or [tuple(int(h) % 24 for h in w["hours"][:2])]
    cx, cy, r = 160, 150, 100
    ang = lambda h: math.radians(h / 24 * 360 - 90)
    inner = ""
    for a, b in ranges:  # shade every range the statement names (e.g. 6-10 pm and 12-2 am)
        span = (b - a) % 24 or 24
        x1, y1 = cx + r * math.cos(ang(a)), cy + r * math.sin(ang(a))
        x2, y2 = cx + r * math.cos(ang(a + span)), cy + r * math.sin(ang(a + span))
        inner += p(f"M{cx},{cy} L{x1:.1f},{y1:.1f} A{r},{r} 0 {1 if span > 12 else 0},1 {x2:.1f},{y2:.1f} Z", fill="#f6b7b6", w=0)
    inner += f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{INK}" stroke-width="2.4"/>'
    txt = ""
    for h, lab in ((0, "midnight"), (6, "6 am"), (12, "noon"), (18, "6 pm")):
        txt += t(cx + (r + 24) * math.cos(ang(h)), cy + (r + 24) * math.sin(ang(h)) + 5, lab, 17, 400, "middle", hand=False)
    big = f"{int(f['value'])}%" if f.get("value") is not None else ""
    txt += t(cx, cy + 10, big, 34, 700, "middle", RED)
    head = f["statement"]
    return {"title": head, "svg": _svg(320, 300, head, inner, txt), "facts": [f]}


def hour_ranges(text):
    """'between 6pm and 10pm, and 12am to 2am' -> [(18, 22), (0, 2)] (fixed rules, read from the fact's own words)."""
    def hh(n, ap):
        n = int(n) % 12
        return n + 12 if ap.lower().startswith("p") else n
    pat = r"(\d{1,2})(?::\d\d)?\s*(am|pm|a\.m\.|p\.m\.)\s*(?:to|and|-|–|until)\s*(\d{1,2})(?::\d\d)?\s*(am|pm|a\.m\.|p\.m\.)"
    return [(hh(a, x), hh(b, y)) for a, x, b, y in re.findall(pat, text or "", re.I)]


def _h(h):
    return "midnight" if h == 0 else "noon" if h == 12 else f"{h} am" if h < 12 else f"{h - 12} pm"


def week(f):
    w = json.loads(f["time_window"]) if f.get("time_window") else {}
    if not w.get("days"):
        return None
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    hot = {d[:3].title() for d in w["days"]}
    inner, txt = "", ""
    for i, d in enumerate(days):
        x = 20 + i * 64
        inner += p(f"M{x},30 h54 v54 h-54 z", fill="#f6b7b6" if d in hot else "#ffffff", w=2)
        txt += t(x + 27, 64, d, 22, 700 if d in hot else 400, "middle", hand=False)
    big = f"{int(f['value'])}% of deaths" if f.get("value") is not None else "Deaths peak"
    head = f"{big}: {', '.join(d for d in days if d in hot)}." if f.get("value") is not None else f"Deaths peak on {', '.join(d for d in days if d in hot)}."
    return {"title": head, "svg": _svg(470, 100, head, inner, txt), "facts": [f]}


BEHAVIOUR = [("helmet", "riders wear a helmet correctly", "helmet"), ("rear.*belt|belt.*rear", "people in the back seat wear a seat belt", "belt"),
             ("child.*restraint|restraint.*child|child_seat", "young children travel in a child seat", "child"),
             ("seat.?belt|seatbelt", "people in cars wear a seat belt", "belt")]


def behaviour(fs):
    """'N of 100' pictures for safety-equipment use (fewer filled icons = bigger gap)."""
    out = []
    used = set()
    for rx, label, kind in BEHAVIOUR:
        f = next((f for f in fs if (f.get("unit") or "") == "%" and f.get("value") is not None and re.search(rx, f["metric"] or "", re.I)
                  and f["metric"] not in used), None)
        if not f:
            continue
        used.add(f["metric"])
        v = float(f["value"])
        inner = ""
        for i in range(10):
            fill = GREEN if i < round(v / 10) else "#ffffff"
            inner += f'<circle cx="{25 + i * 34}" cy="30" r="13" fill="{fill}" stroke="{INK}" stroke-width="2"/>'
        head = f"Only {int(v) if v.is_integer() else v} in 100 {label}."
        out.append({"title": head, "svg": _svg(360, 60, head, inner), "facts": [f]})
        if len(out) == 3:
            break
    return out


def trend(fs):
    """Yearly totals as bars, with one label on the bar that matters."""
    from safety.insights import bars
    from safety.story import period_key
    rows = sorted([f for f in fs if f["metric"] == "deaths_total" and f.get("value") and re.search("police|official|government", f.get("source_name") or "", re.I)],
                  key=lambda f: period_key(f["period"]))
    seen, ys = set(), []
    for f in rows:
        y = re.findall(r"(?:19|20)\d\d", f["period"])[-1]
        if y not in seen:
            seen.add(y); ys.append((y, int(f["value"]), f["period"]))
    ys = ys[-10:]
    if len(ys) < 3:
        return None
    rec = next((f for f in fs if f["metric"] == "deaths_record"), None)
    head = rec["statement"] if rec else f"Road deaths, {ys[0][0]} to {ys[-1][0]}."
    labels = [y[2:] + ("*" if " " in per else "") for y, _, per in ys]
    return {"title": head, "svg": bars([v for _, v, _ in ys], labels, "People killed on the roads each year", highlight=(len(ys) - 1,)),
            "facts": [rec] if rec else []}


def by_question(fs, place, topic):
    """Pictures grouped by the question they answer."""
    out = {}
    tr = trend(fs)
    if tr:
        out.setdefault("how_bad", []).append(tr)
    who = who_pictograph(fs)
    if who:
        out.setdefault("who", []).append(who)
    hours = [f for f in fs if f["dimension"] == "when" and f.get("time_window") and '"hours"' in f["time_window"] and f.get("value") is not None
             and re.search("death|fatalit", (f["statement"] or "") + (f["metric"] or ""), re.I)]
    if hours and clock(hours[0]):
        out.setdefault("when", []).append(clock(hours[0]))
    days = next((f for f in fs if f["dimension"] == "when" and f.get("time_window") and '"days"' in f["time_window"] and f.get("value") is not None), None)
    if days and week(days):
        out.setdefault("when", []).append(week(days))
    bh = behaviour(fs)
    if bh:
        out.setdefault("why", []).extend(bh)
    return out


def gallery(fs):
    """Pick the pictures this place's facts can support, in story order."""
    pics = []
    tr = trend(fs)
    if tr:
        pics.append(tr)
    who = who_pictograph(fs)
    if who:
        pics.append(who)
    hours = next((f for f in fs if f["dimension"] == "when" and f.get("time_window") and '"hours"' in f["time_window"] and "death" in (f["statement"] or "").lower() + (f["metric"] or "")
                  or (f["dimension"] == "when" and f.get("time_window") and '"hours"' in f["time_window"] and "fatalit" in (f["statement"] or "").lower())), None)
    if hours and clock(hours):
        pics.append(clock(hours))
    days = next((f for f in fs if f["dimension"] == "when" and f.get("time_window") and '"days"' in f["time_window"] and f.get("value") is not None), None)
    if days and week(days):
        pics.append(week(days))
    pics += behaviour(fs)
    return pics
