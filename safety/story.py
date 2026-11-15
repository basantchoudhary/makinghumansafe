"""Story generator: checked facts for any place and topic become a mind map, a narration, 'right now' lines,
a 'numbers differ' note and the list of findings with sources. Nothing here is written by hand per city.

Selection (fixed rules): the centre is the newest official total; each branch (when, who, where, why, action) gets up to
three checked facts, preferring the newest period, facts with numbers, and death-related measures.
Narration: the AI writes it from the selected facts only; code rejects it if it contains any number not in those facts
(then a plain template version is used).
"""
import hashlib, html, json, pathlib, re

from safety import facts, llm

CACHE = pathlib.Path(__file__).resolve().parent.parent / "data" / "_stories"


def cached(kind, inputs, make):
    """AI text is made once per set of facts and reused until the facts change (stable pages, few AI calls).
    Only accepted outputs are cached; a rejected or failed draft is retried next build."""
    CACHE.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha1(json.dumps([kind, inputs], sort_keys=True, default=str).encode()).hexdigest()[:16]
    f = CACHE / f"{kind}_{key}.json"
    if f.exists():
        return json.loads(f.read_text())
    out = make()
    if out and out.get("ok"):
        f.write_text(json.dumps(out))
    return out

e = html.escape
BRANCHES = [("when", "WHEN", "#e8f0fc"), ("who", "WHO", "#fff4e5"), ("where", "WHERE", "#e4f3ed"), ("why", "WHY", "#f3e8fd")]
DAYS = {"Sun": 0, "Mon": 1, "Tue": 2, "Wed": 3, "Thu": 4, "Fri": 5, "Sat": 6}


def score(f):
    s = 0
    s += 3 if f.get("value") is not None else 0
    s += 2 if "death" in (f.get("metric") or "") or "fatal" in (f.get("metric") or "") else 0
    s += 1 if (f.get("unit") or "") == "%" else 0
    return (str(f.get("period") or ""), s)


def same(f):
    """Two facts are the same finding if value, unit and period match (names from the AI vary)."""
    return (f.get("value"), (f.get("unit") or "").strip(), f.get("period")) if f.get("value") is not None else (f["metric"], f["period"])


def dedupe(fs):
    seen, out = set(), []
    for f in sorted(fs, key=score, reverse=True):
        k = (f["dimension"],) + tuple(same(f))
        if k not in seen:
            seen.add(k); out.append(f)
    return out


def pick(fs, dim, n=3):
    seen, out = set(), []
    for f in sorted([f for f in fs if f["dimension"] == dim], key=score, reverse=True):
        key = same(f)
        if key not in seen:
            seen.add(key); out.append(f)
        if len(out) == n:
            break
    return out


def short(s, n=46):
    s = re.sub(r"\s+", " ", s or "").strip().rstrip(".")
    return s if len(s) <= n else s[: n - 1].rsplit(" ", 1)[0] + "…"


def wrap(s, n=40, lines=2):
    words, out, cur = re.sub(r"\s+", " ", s or "").strip().rstrip(".").split(" "), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > n:
            out.append(cur); cur = w
            if len(out) == lines:
                out[-1] = out[-1] + " …"; return out
        else:
            cur = (cur + " " + w).strip()
    return out + ([cur] if cur else [])


def mind_map(centre_big, centre_small, branches, action, w=1000, h=700):
    from safety.doodles import WOBBLE, p, t
    cx, cy = w / 2, h / 2 - 10
    inner = p(f"M{cx - 170},{cy - 50} h340 v100 h-340 z", fill="#fdecec", w=2.6)
    txt = t(cx, cy - 8, e(centre_big), 28, 700, "middle") + t(cx, cy + 26, e(centre_small), 20, 400, "middle")
    pos = [(185, 110), (w - 185, 110), (185, h - 215), (w - 185, h - 215)]
    for (label, fill, lines), (x, y) in zip(branches, pos):
        inner += p(f"M{cx + (-170 if x < cx else 170)},{cy + (-30 if y < cy else 30)} Q{(cx + x) / 2},{(cy + y) / 2} {x + (140 if x < cx else -140)},{y}", w=2.2)
        rows = [r for ln in lines for r in wrap(ln) + [""]][:-1]
        inner += p(f"M{x - 175},{y - 80} h350 v{44 + 21 * max(1, len(rows))} h-350 z", fill=fill, w=2.2)
        txt += t(x, y - 52, label, 24, 700, "middle")
        for k, ln in enumerate(rows):
            txt += t(x, y - 26 + k * 21, e(ln), 16, 400, "middle")
    if action:
        inner += p(f"M{cx},{cy + 50} L{cx},{h - 70}", w=2.2) + p(f"M{cx - 440},{h - 70} h880 v48 h-880 z", fill="#e4f3ed", w=2.2)
        txt += t(cx, h - 38, e("YOU CAN: " + short(action, 110)), 17, 700, "middle")
    label = f"Mind map. Centre: {centre_big}, {centre_small}. " + " ".join(f"{b[0]}: {'; '.join(b[2])}." for b in branches)
    return f'<svg class="doodle" viewBox="0 0 {w} {h}" role="img" aria-label="{e(label)}">{WOBBLE}<g filter="url(#wob)">{inner}</g>{txt}</svg>'


def narration(selected, centre):
    r = cached("narration", [f["statement"] for f in [centre] + selected], lambda: _narration(selected, centre))
    return r["text"], r["how"]


def _narration(selected, centre):
    allowed = {float(f["value"]) for f in selected if f.get("value") is not None} | {float(centre["value"])}
    allowed |= {float(x) for f in selected + [centre] for x in re.findall(r"\d+(?:\.\d+)?", (f.get("statement") or "") + " " + (f.get("period") or ""))}
    plain = " ".join(f["statement"] for f in [centre] + selected)
    prompt = ("Write a short, warm, plain-English paragraph (at most 110 words) for families, telling the story of these road-safety facts "
              "in this order: how many, when, who, where, why, what to do. Use ONLY these facts and ONLY their numbers; no new numbers, "
              "no names of people. Keep every percentage with its own fact; never say 'most' or 'majority' for a share under 50%. "
              "Return JSON {\"text\": \"...\"}.\nFacts:\n" + "\n".join(f"- {f['statement']}" for f in [centre] + selected))
    source_text = " ".join(f.get("statement") or "" for f in [centre] + selected).lower()
    feedback = ""
    for attempt in range(3):  # retry with the exact reason the previous draft failed
        out = (llm.json_call(prompt + feedback) or {}).get("text") or ""
        problems = draft_problems(out, allowed, source_text)
        if out and not problems:
            return {"ok": True, "text": out, "how": "AI-written from the facts below; every number and claim checked against them"}
        feedback = "\nYour previous draft was rejected: " + "; ".join(problems) + ". Write it again, fixing exactly these points."
    return {"ok": False, "text": plain, "how": "assembled from the facts below (AI draft rejected or unavailable)"}


NUMBER_WORDS = r"\b(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand|lakh|crore|half|third|quarter|dozen)\b"


def draft_problems(out, allowed, source_text):
    """Code checks on an AI draft: digits must be in the facts; number words must appear in the facts' own words;
    no 'most ...' claims for shares under 50%."""
    if not out:
        return ["empty"]
    p = []
    nums = {float(x) for x in re.findall(r"\d+(?:\.\d+)?", out.replace(",", ""))}
    if nums - allowed:
        p.append(f"it used numbers not in the facts: {sorted(nums - allowed)}")
    words = {w.lower() for w in re.findall(NUMBER_WORDS, out, re.I)} - set(re.findall(NUMBER_WORDS, source_text, re.I))
    if words:
        p.append(f"write numbers as digits exactly as in the facts, not as words ({sorted(words)})")
    if overclaims(out):
        p.append("it said 'most' for a share under 50%; give the percentage instead")
    return p


def overclaims(text):
    """Reject 'most crashes/deaths ...' style claims unless that sentence carries a share of 50% or more.
    ('the most pedestrian deaths', meaning the highest, is allowed.)"""
    for sent in re.split(r"(?<=[.!?])\s+", text):
        if re.search(r"(?<!the )\b(most|majority of)\s+(crash|death|fatalit|accident|people|victim|of the)", sent, re.I):
            if not any(float(x) >= 50 for x in re.findall(r"(\d+(?:\.\d+)?)\s*%", sent)):
                return True
    return False


ADVICE = {"road": "Clasp your helmet, belt up in every seat, and slow down at night and on weekends.",
          "water": "Swim only near lifeguards, never after drinking, and stay out when the sea or river is rough."}


def advice(topic, selected):
    r = cached("advice", [topic] + [f["statement"] for f in selected], lambda: _advice(topic, selected))
    return r["text"]


def _advice(topic, selected):
    """One sentence of advice from the facts (AI), rejected if it contains any number; else the topic's default."""
    prompt = ("From these safety facts, write ONE short sentence of practical advice for an ordinary person (max 20 words), "
              "no numbers, no statistics. Return JSON {\"text\": \"...\"}.\nFacts:\n" + "\n".join(f"- {f['statement']}" for f in selected))
    out = ((llm.json_call(prompt) or {}).get("text") or "").strip()
    ok = bool(out) and not re.search(r"\d", out) and len(out) < 140
    return {"ok": ok, "text": out if ok else ADVICE.get(topic, "")}


def now_rules(fs):
    rules = []
    for f in fs:
        w = json.loads(f["time_window"]) if f.get("time_window") else None
        if not w:
            continue
        if w.get("hours") and len(w["hours"]) == 2:
            a, b = int(w["hours"][0]) % 24, int(w["hours"][1]) % 24
            rules.append({"type": "hours", "a": a, "b": b, "text": f["statement"]})
        if w.get("days"):
            rules.append({"type": "days", "d": [DAYS[d[:3].title()] for d in w["days"] if d[:3].title() in DAYS], "text": f["statement"]})
    return rules


def render(place, topic, place_name):
    fs = dedupe(facts.for_story(place, topic))
    if not fs:
        return ""
    totals = sorted([f for f in fs if f["metric"] == "deaths_record"] or [f for f in fs if f["metric"] == "deaths_total"], key=lambda f: f["period"])
    centre = totals[-1] if totals else None
    per_day = next((f for f in fs if f["metric"] == "deaths_per_day"), None)
    branches = [(label, fill, [f["statement"] for f in pick(fs, dim)]) for dim, label, fill in BRANCHES]
    branches = [b for b in branches if b[2]]
    actions = pick(fs, "action", 2)
    selected = [f for dim, _, _ in BRANCHES for f in pick(fs, dim)] + actions
    out = [f'<h2 id="{topic}-story">The story in one picture</h2>']
    if centre:
        tip = advice(topic, [f for dim in ("when", "who", "why") for f in pick(fs, dim)])
        out.append(mind_map(f"{int(centre['value'])} killed, {centre['period']}", per_day["statement"] if per_day else place_name, branches, tip))
        text, how = narration(selected, centre)
        out.append(f'<div class="summary"><p>{e(text)}</p><p class="hand" style="font-size:1.35rem;margin:6px 0 0">Someone is waiting for you.</p>'
                   f'<p class="src">{e(how)}.</p></div>')
    rules = now_rules(fs)
    if rules:
        out.append('<div id="now-line" class="alert" hidden></div><script>(function(){const R=' + json.dumps(rules).replace("</", "<\\/") +
                   ';const d=new Date(),h=d.getHours(),wd=d.getDay(),m=[];for(const r of R){if(r.type==="hours"&&(r.a<=r.b?(h>=r.a&&h<r.b):(h>=r.a||h<r.b)))m.push("<b>Right now:</b> "+r.text);'
                   'if(r.type==="days"&&r.d.includes(wd))m.push("<b>Today:</b> "+r.text);}if(m.length){const el=document.getElementById("now-line");el.innerHTML=m.join("<br>");el.hidden=false;}})();</script>')
    cf = facts.conflicts(place, topic)
    if cf:
        out.append('<details><summary><b>Why numbers differ between sources</b></summary><p class="small">Agencies count differently (city limits, '
                   'when a death is counted, date of update). ' + " ".join(
                       f"{e(c['metric'].replace('_', ' '))}, {e(c['period'])}: " + "; ".join(f"{int(x['v']) if float(x['v']).is_integer() else x['v']} ({e(x['s'])})" for x in c["figures"]) + "."
                       for c in cf) + "</p></details>")
    out.append("<h3>All checked findings</h3><ul>" + "".join(
        f'<li><b>{e(f["dimension"].replace("_", " ").title())}:</b> {e(f["statement"])} <span class="src">({e(f["period"])}; '
        f'<a href="{e(f["source_url"])}">{e(f["source_name"])}</a>{", " + e(f["source_page"]) if f.get("source_page") else ""})</span></li>'
        for f in sorted(fs, key=lambda f: (facts.DIMENSIONS.index(f["dimension"]), f["metric"])) if f["metric"] not in ("deaths_total",)) + "</ul>"
               '<p class="src">Every finding above passed code checks: AI-read findings must quote their source word for word, and every number must appear in that quote.</p>')
    return "\n".join(out)
