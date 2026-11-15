"""Theme sections: subjects that cut across the six questions (potholes, pedestrians, helmets...).
Defined once per topic, so every place gets them; filled from checked facts and checked incidents by keyword rules."""
import html, re

e = html.escape

THEMES = {"road": [
    ("potholes", "Potholes and bad roads", r"pothole|civic negligence|civic agenc|road condition|crater|bad roads?\b|road repair"),
    ("pedestrians", "People walking", r"pedestrian|walking|footpath|crossing|skywalk|zebra"),
    ("helmets", "Helmets, seat belts and child seats", r"helmet|seat ?belt|child restraint|child seat"),
    ("speed", "Speed and night driving", r"speed|night|late hours|after dark"),
    ("drink", "Drink-driving", r"drunk|drink|alcohol"),
    ("hitrun", "Hit-and-run", r"hit-and-run|hit and run|fled|absconded"),
    ("spots", "Black spots, corridors and junctions", r"black ?spot|corridor|junction|stretch"),
    ("children", "Children and schools", r"child|school|students?"),
    ("heavy", "Lorries, buses and heavy vehicles", r"lorr|truck|tipper|heavy vehicle|bus\b|buses"),
]}


def render(place, topic, fs, incidents, score):
    out = []
    for key, title, rx in THEMES.get(topic, []):
        tf = sorted([f for f in fs if re.search(rx, (f.get("statement") or "") + " " + (f.get("metric") or ""), re.I)], key=score, reverse=True)
        ti = [r for r in incidents if re.search(rx, " ".join(str(r.get(k) or "") for k in ("incident_type", "what_happened", "cause")), re.I)]
        if not tf and not ti:
            continue
        seen, top = set(), []
        for f in tf:
            k = (f.get("value"), f.get("unit"), f.get("period"))
            if f.get("value") is None or k not in seen:
                seen.add(k); top.append(f)
        body = "".join(f'<li>{e(f["statement"])} <span class="src">({e(str(f["period"]))}; <a href="{e(f["source_url"])}">{e(f["source_name"])}</a>)</span></li>' for f in top[:6])
        inc = "".join(f'<li>{e(r["date"])}, <b>{e(r.get("spot") or "")}</b>: {e(r["what_happened"])} '
                      f'<span class="src">(<a href="{e(r["source_url"])}">{e(r.get("source_name") or "source")}</a>)</span></li>' for r in ti[:5])
        out.append(f'<details class="theme" {"open" if key == "potholes" else ""}><summary><b>{e(title)}</b> '
                   f'<span class="muted small">{len(top)} finding{"s" if len(top) != 1 else ""}'
                   f'{f", {len(ti)} checked incident" + ("s" if len(ti) != 1 else "") if ti else ""}</span></summary>'
                   + (f"<ul>{body}</ul>" if body else "") + (f'<p class="small"><b>Checked incidents</b></p><ul class="small">{inc}</ul>' if inc else "")
                   + "</details>")
    if not out:
        return ""
    return '<h2 id="themes">More on each subject</h2>' + "".join(out)


CSS = """
.theme{border:1px solid var(--line);border-radius:12px;padding:8px 14px;margin:8px 0;background:#fff}
.theme summary{cursor:pointer;font-size:1.08rem}
.theme ul{margin:8px 0}
"""
