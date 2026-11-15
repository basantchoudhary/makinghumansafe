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


MON = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}
WIDER = re.compile(r"\b(karnataka|india|indian|state|national|nationally|country|countrywide|nationwide)\b", re.I)


def period_key(p):
    """'2026 Jan-Oct' sorts after '2026 Jan-Sep' and before '2027' (real dates, not text)."""
    y = re.findall(r"(?:19|20)\d\d", str(p or ""))
    ms = [MON[m] for m in re.findall(r"[a-z]{3}", str(p or "").lower()) if m in MON]
    return (int(y[-1]) if y else 0, max(ms) if ms else 12)


def about_place(f, place_name):
    """A fact about a wider area (the state, the country) is context, not this place's story."""
    st = f.get("statement") or ""
    return not (WIDER.search(st) and place_name.lower() not in st.lower())


OFFICIAL = re.compile(r"police|government|ministry|ncrb|morth|official", re.I)


def score(f):
    s = 0
    s += 4 if f.get("value") is not None else 0
    s += 3 if re.search("death|fatal|killed", (f.get("metric") or "") + " " + (f.get("statement") or ""), re.I) else 0
    s += 1 if (f.get("unit") or "") == "%" else 0
    s += 2 if OFFICIAL.search(f.get("source_name") or "") else 0
    return (s, period_key(f.get("period")))


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
        if re.search(r"(?<!the )\b(most|majority of)\s+(crash|death|fatalit|accident|people|victim|of the)", sent, re.I) or re.search(r"\bmostly\b", sent, re.I):
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


def synthesis(fs, place_name, topic):
    """Summary (one sentence) + 3 insights that connect several facts. AI proposes; code checks each insight
    cites at least 2 real facts and uses only numbers from the facts it cites."""
    menu = [f for f in fs if f["dimension"] in ("how_many", "trend", "when", "who", "where", "why", "action") and f["metric"] != "deaths_total"]
    menu = sorted(menu, key=score, reverse=True)[:40]
    ids = {f"F{i}": f for i, f in enumerate(menu, 1)}
    inputs = [f["statement"] for f in menu]

    def make():
        prompt = (f"You are given checked {topic}-safety facts about {place_name}, each with an id.\n"
                  "1) 'summary': ONE plain sentence (max 30 words): the single most important message for a family.\n"
                  "2) 'insights': exactly 3 insights. Each CONNECTS at least 2 facts into something no single fact says "
                  "(e.g. who + when + why together), max 45 words, plain words, and lists the ids it uses in 'facts'.\n"
                  "Use ONLY numbers from the facts you cite, written as digits exactly as in the facts. Never say 'most' or 'majority' for a share under 50%.\n"
                  'Return JSON {"summary": "...", "summary_facts": ["F1", ...], "insights": [{"text": "...", "facts": ["F2","F5"]}, ...]}\n'
                  "Facts:\n" + "\n".join(f"{k}: {f['statement']}" for k, f in ids.items()))
        feedback = ""
        for _ in range(3):
            r = llm.json_call(prompt + feedback) or {}
            probs, ok = [], []
            def allowed_for(keys):
                fsel = [ids[k] for k in keys if k in ids]
                a = {float(f["value"]) for f in fsel if f.get("value") is not None}
                return a | {float(x) for f in fsel for x in re.findall(r"\d+(?:\.\d+)?", (f["statement"] or "") + " " + (f["period"] or ""))}, fsel
            sa, sf = allowed_for(r.get("summary_facts") or [])
            sp = draft_problems(r.get("summary") or "", sa, " ".join(f["statement"] for f in sf).lower())
            if sp:
                probs.append("summary: " + "; ".join(sp))
            for ins in (r.get("insights") or [])[:3]:
                keys = [k for k in ins.get("facts") or [] if k in ids]
                if len(keys) < 2:
                    probs.append(f"insight '{(ins.get('text') or '')[:40]}' cites fewer than 2 facts"); continue
                a, fsel = allowed_for(keys)
                ip = draft_problems(ins.get("text") or "", a, " ".join(f["statement"] for f in fsel).lower())
                if ip:
                    probs.append(f"insight '{(ins.get('text') or '')[:40]}': " + "; ".join(ip)); continue
                ok.append({"text": ins["text"], "sources": sorted({(f["source_name"], f["source_url"]) for f in fsel})})
            if not sp and len(ok) == 3:
                return {"ok": True, "summary": r["summary"], "insights": ok}
            feedback = "\nYour previous answer was rejected: " + " | ".join(probs) + ". Fix exactly these points."
        return {"ok": False, "summary": "", "insights": ok}
    return cached("synthesis", [place_name, topic] + inputs, make)


QUESTIONS = [("how_bad", "How bad is it?", ("how_many", "trend")), ("who", "Who is dying?", ("who",)), ("when", "When?", ("when",)),
             ("where", "Where?", ("where",)), ("why", "Why?", ("why",)), ("do", "So what do I do?", ("action", "why", "when", "who"))]


def question_chain(fs, place_name, topic):
    """The human mind map: six questions, each with a six-word answer and one plain sentence, from that question's
    own checked facts. AI proposes; code checks numbers per question (and 'do' answers may not contain numbers)."""
    groups = {}
    for key, _, dims in QUESTIONS:
        pool = sorted([f for f in fs if f["dimension"] in dims and f["metric"] != "deaths_total"], key=score, reverse=True)[:8]
        if key == "how_bad":  # the newest official record leads 'how bad'
            rec = [f for f in fs if f["metric"] in ("deaths_record", "deaths_per_day")]
            pool = rec + [f for f in pool if f not in rec][:6]
        groups[key] = {f"{key}{i}": f for i, f in enumerate(pool, 1)}
    inputs = {k: [f["statement"] for f in v.values()] for k, v in groups.items()}

    def make():
        prompt = (f"Turn checked {topic}-safety facts about {place_name} into the mind map a family will remember.\n"
                  "For each question key, write 'short' (max 6 words, like a label on a mind map) and 'answer' (one plain sentence, max 25 words), "
                  "using ONLY that question's facts and ONLY their numbers, as digits. For 'do', give practical advice with NO numbers. "
                  "Never say 'most' or 'majority' for a share under 50%.\n"
                  'Return JSON {"how_bad": {"short": "...", "answer": "..."}, "who": {...}, "when": {...}, "where": {...}, "why": {...}, "do": {...}}\n'
                  + "\n".join(f"Question {k}:\n" + "\n".join(f"- {st}" for st in v) for k, v in inputs.items() if v))
        feedback, good, last_probs = "", {}, []
        for _ in range(3):
            r = llm.json_call(prompt + feedback) or {}
            probs, out = [], {}
            for key, _, _ in QUESTIONS:
                if not groups[key]:
                    continue
                item = r.get(key) or {}
                fsel = list(groups[key].values())
                allowed = {float(f["value"]) for f in fsel if f.get("value") is not None}
                allowed |= {float(x) for f in fsel for x in re.findall(r"\d+(?:\.\d+)?", (f["statement"] or "") + " " + (f["period"] or ""))}
                src = " ".join(f["statement"] for f in fsel).lower()
                for part in ("short", "answer"):
                    txt = item.get(part) or ""
                    pr = draft_problems(txt, allowed if key != "do" else set(), src)
                    if part == "short" and len(txt.split()) > 7:
                        pr.append("short must be at most 6 words")
                    from safety.visuals import hour_ranges
                    for f in fsel:  # a number used with its time window must keep ALL the ranges that fact names
                        rs = hour_ranges(f["statement"])
                        if f.get("value") is not None and len(rs) > 1 and re.search(rf"\b{int(f['value'])}\s*%", txt) and len(hour_ranges(txt)) < len(rs):
                            pr.append(f"keep all time ranges of the fact '{f['statement']}'")
                    if part == "short" and key != "do" and not grounded_short(txt, fsel):
                        pr.append("short must use words from ONE fact only (do not combine two facts)")
                    if pr:
                        probs.append(f"{key}.{part}: " + "; ".join(pr))
                out[key] = {**item, "sources": sorted({(f["source_name"], f["source_url"]) for f in fsel})[:3]}
            rec = next((f for f in fs if f["metric"] == "deaths_record"), None)
            pdy = next((f for f in fs if f["metric"] == "deaths_per_day" and rec and f["period"] == rec["period"]), None)
            if rec:  # 'how bad' is written by code from the official record, never by the AI
                since = re.search(r"highest (since \d{4}|on record)", rec["statement"])
                out["how_bad"] = {"short": ("Highest " + since.group(1)) if since else f"{int(rec['value'])} killed",
                                  "answer": rec["statement"] + (" " + pdy["statement"] if pdy else ""),
                                  "sources": [(rec["source_name"], rec["source_url"])]}
                probs = [x for x in probs if not x.startswith("how_bad")]
            failed = {x.split(".")[0] for x in probs}
            for key in list(out):
                if key not in failed:
                    good[key] = out[key]  # keep every answer that passed, across attempts
            if all(k in good for k, _, _ in QUESTIONS if groups[k]):
                return {"ok": True, "chain": good}
            last_probs = probs
            feedback = "\nYour previous answer was rejected: " + " | ".join(probs) + ". Fix exactly these points."
        # Answers that never passed fall back to the plain checked fact (no AI wording); their mind-map box is left out.
        for key, _, _ in QUESTIONS:
            if groups[key] and key not in good:
                best = list(groups[key].values())[0]
                good[key] = {"short": code_short(key, list(groups[key].values())), "answer": best["statement"],
                             "sources": [(best["source_name"], best["source_url"])], "fallback": True}
        print("  chain: kept fallbacks for", [k for k in good if good[k].get("fallback")], "| last problems:", last_probs[:4])
        return {"ok": True, "chain": good}
    return cached("chain", [place_name, topic, inputs], make)


STOP = set("the and for with from that this are was were have has into over under near only very more less than their there about after before during when where while who what why your you can".split())


def grounded_short(short, fsel):
    """Every content word of a mind-map label must come from ONE fact (no stitching two unrelated facts)."""
    words = [w for w in re.findall(r"[a-z]{4,}", short.lower()) if w not in STOP]
    if not words:
        return True
    def stem(w):
        return w[:5]
    return any(all(stem(w) in " ".join(x[:5] for x in re.findall(r"[a-z]{4,}", (f["statement"] or "").lower())) for w in words) for f in fsel)


def code_short(key, fsel):
    """A mind-map label written by code when the AI's wording fails the checks (only for time, which code can read)."""
    if key != "when":
        return ""
    from safety.visuals import hour_ranges
    parts = []
    hrs = [h for f in fsel for r in hour_ranges(f["statement"]) for h in r]
    if any(h >= 18 for h in hrs):
        parts.append("Evenings")
    if any(h <= 4 for h in hrs):
        parts.append("late nights")
    days = " ".join((f.get("time_window") or "") for f in fsel)
    if "Sat" in days or "Sun" in days:
        parts.append("weekends")
    return (", ".join(parts[:-1]) + " and " + parts[-1] if len(parts) > 1 else (parts[0] if parts else "")).capitalize()


def chain_map(place_name, topic, chain, w=1000, h=420):
    """The mind map picture: the place in the centre, six questions around it, each with its six-word answer."""
    from safety.doodles import WOBBLE, p, t
    cx, cy = w / 2, h / 2
    inner = p(f"M{cx - 110},{cy - 34} h220 v68 h-220 z", fill="#fdecec", w=2.6)
    txt = t(cx, cy + 9, f"{place_name} {topic}s" if topic == "road" else f"{place_name} {topic}", 26, 700, "middle", hand=True)
    pos = [(170, 70), (w / 2, 40), (w - 170, 70), (170, h - 60), (w / 2, h - 30), (w - 170, h - 60)]
    order = ["how_bad", "who", "when", "where", "why", "do"]
    labels = dict((k, q) for k, q, _ in QUESTIONS)
    fills = ["#fde2e2", "#fff4e5", "#e8f0fc", "#e4f3ed", "#f3e8fd", "#e4f3ed"]
    for (x, y), key, fill in zip(pos, order, fills):
        if key not in chain or not chain[key].get("short"):
            continue
        bw = 290
        inner += p(f"M{cx + (-110 if x < cx else 110 if x > cx else 0)},{cy + (-34 if y < cy else 34)} L{x},{y + (22 if y < cy else -22)}", w=1.8)
        inner += p(f"M{x - bw / 2},{y - 26} h{bw} v52 h-{bw} z", fill=fill, w=2.2)
        txt += t(x, y - 6, labels[key].upper(), 15, 700, "middle", hand=False)
        txt += t(x, y + 16, e(chain[key].get("short", "")), 19, 700, "middle", hand=False)
    lab = "Mind map: " + "; ".join(f"{labels[k]} {chain[k].get('short', '')}" for k in order if k in chain)
    return f'<svg class="doodle" viewBox="0 0 {w} {h}" role="img" aria-label="{e(lab)}">{WOBBLE}<g filter="url(#wob)">{inner}</g>{txt}</svg>'


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
    from safety import visuals
    allfs = dedupe(facts.for_story(place, topic))
    if not allfs:
        return ""
    fs = [f for f in allfs if about_place(f, place_name)]
    rec = [f for f in fs if f["metric"] == "deaths_record"]
    tot = sorted([f for f in fs if f["metric"] == "deaths_total" and f.get("value")], key=lambda f: (bool(OFFICIAL.search(f.get("source_name") or "")), period_key(f["period"])))
    centre = rec[-1] if rec else (tot[-1] if tot else None)
    out = [f'<h2 id="{topic}-story">{e(place_name)} {e(topic)} safety, simply</h2>']

    # 1. The mind map a person keeps: six questions with six-word answers (AI from each question's facts; code checks)
    qc = question_chain(fs, place_name, topic).get("chain") or {}
    syn = synthesis(fs, place_name, topic)
    # The one-line summary is composed by code from the checked mind-map answers (no new AI wording to drift).
    if qc:
        parts = []
        if qc.get("how_bad", {}).get("short"):
            parts.append(f"{place_name}'s roads: {qc['how_bad']['short'].lower()}")
        if qc.get("who", {}).get("short"):
            parts.append(f"who dies: {qc['who']['short'].lower()}")
        if qc.get("when", {}).get("short"):
            parts.append(f"worst: {qc['when']['short'].lower()}")
        line = ". ".join(p_[0].upper() + p_[1:] for p_ in parts) + "."
        if qc.get("do", {}).get("short"):
            line += f" {qc['do']['short']}."
        out.append(f'<p class="headline">{e(line)}</p>')
    if qc:
        out.append(chain_map(place_name, topic, qc))
    # 2. The story, one question at a time: a plain answer and one picture that proves it
    pics = visuals.by_question(fs, place, topic)
    for key, question, _ in QUESTIONS:
        if key not in qc and key not in pics:
            continue
        a = qc.get(key, {})
        out.append(f'<section class="step"><h3><span class="qnum">{[k for k, _, _ in QUESTIONS].index(key) + 1}</span>{e(question)}</h3>'
                   + (f'<p class="ans">{e(a.get("answer", ""))}</p>' if a.get("answer") else "")
                   + "".join(f'<figure class="pic1"><figcaption>{e(pc["title"])}</figcaption>{pc["svg"]}</figure>' for pc in pics.get(key, []))
                   + (f'<p class="src">From: ' + "; ".join(f'<a href="{e(u)}">{e(n)}</a>' for n, u in a.get("sources", [])) + "</p>" if a.get("sources") else "")
                   + "</section>")
    # Theme sections (potholes, pedestrians, helmets...): every checked fact and incident on each subject
    from safety import themes, road as road_mod, store as _st
    import tomllib, pathlib as _pl
    cfgs = tomllib.loads((_pl.Path(__file__).resolve().parent.parent / "places.toml").read_text())
    incs = road_mod.incidents_for(cfgs[place]) if topic == "road" and place in cfgs else []
    out.append(themes.render(place, topic, fs, incs, score))
    if syn.get("insights"):
        out.append('<details><summary><b>Connections across the findings</b> (3 insights)</summary><div class="insights">' + "".join(
            f'<div class="insight"><span class="num">{i}</span><p>{e(x["text"])}</p><p class="src">From: '
            + "; ".join(f'<a href="{e(u)}">{e(n)}</a>' for n, u in x["sources"]) + "</p></div>" for i, x in enumerate(syn["insights"], 1)) + "</div></details>")

    # Right now (from the visitor's own clock)
    rules = now_rules(fs)
    if rules:
        out.append('<div id="now-line" class="alert" hidden></div><script>(function(){const R=' + json.dumps(rules).replace("</", "<\\/") +
                   ';const d=new Date(),h=d.getHours(),wd=d.getDay(),m=[];for(const r of R){if(r.type==="hours"&&(r.a<=r.b?(h>=r.a&&h<r.b):(h>=r.a||h<r.b)))m.push("<b>Right now:</b> "+r.text);'
                   'if(r.type==="days"&&r.d.includes(wd))m.push("<b>Today:</b> "+r.text);}if(m.length){const el=document.getElementById("now-line");el.innerHTML=m.join("<br>");el.hidden=false;}})();</script>')

    # 4. Narration (read or listen) and advice
    selected = [f for dim, _, _ in BRANCHES for f in pick(fs, dim)]
    if centre:
        text, how = narration(selected, centre)
        tip = advice(topic, [f for dim in ("when", "who", "why") for f in pick(fs, dim)])
        out.append(f'<details class="narr"><summary><b>Read the story</b> (40 seconds)</summary><p>{e(text)}</p><p class="src">{e(how)}.</p></details>')
        if tip:
            out.append(f'<div class="ok"><b>What you can do:</b> {e(tip)}</div>')

    # Numbers differ, and 5. all findings (folded)
    cf = facts.conflicts(place, topic)
    if cf:
        out.append('<details><summary><b>Why numbers differ between sources</b></summary><p class="small">Agencies count differently (city limits, '
                   'when a death is counted, date of update). ' + " ".join(
                       f"{e(c['metric'].replace('_', ' '))}, {e(c['period'])}: " + "; ".join(f"{int(x['v']) if float(x['v']).is_integer() else x['v']} ({e(x['s'])})" for x in c["figures"]) + "."
                       for c in cf) + "</p></details>")
    out.append(f'<details><summary><b>All {len(fs)} checked findings</b>, with sources</summary><ul>' + "".join(
        f'<li><b>{e(f["dimension"].replace("_", " ").title())}:</b> {e(f["statement"])} <span class="src">({e(f["period"])}; '
        f'<a href="{e(f["source_url"])}">{e(f["source_name"])}</a>{", " + e(f["source_page"]) if f.get("source_page") else ""})</span></li>'
        for f in sorted(fs, key=lambda f: (facts.DIMENSIONS.index(f["dimension"]), f["metric"])) if f["metric"] != "deaths_total") + "</ul>"
        '<p class="src">Every finding passed code checks: AI-read findings quote their source word for word, and every number appears in that quote.</p></details>')
    return "\n".join(out)


CSS = """
.headline{font-size:1.45rem;line-height:1.35;font-weight:700;margin:6px 0 14px}
.insights{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:12px;margin:8px 0 18px}
.insight{border:2px solid var(--ink);border-radius:14px;padding:12px 14px;background:#fff;box-shadow:3px 3px 0 var(--ink)}
.insight .num{display:inline-block;background:var(--ink);color:#fff;border-radius:999px;width:26px;height:26px;text-align:center;font-weight:700;line-height:26px}
.insight p{margin:6px 0 0}
.pics{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:14px}
.pic1{margin:0;border:1px solid var(--line);border-radius:14px;padding:10px 14px}
.pic1 figcaption{font-weight:700;font-size:1.05rem;margin-bottom:4px}
.narr{margin:12px 0}
.step{border-top:2px solid var(--ink);margin-top:22px;padding-top:8px}
.step h3{font-size:1.35rem;margin:6px 0}
.qnum{display:inline-block;background:var(--red);color:#fff;border-radius:999px;width:30px;height:30px;text-align:center;line-height:30px;margin-right:10px;font-size:1rem}
.ans{font-size:1.15rem;margin:4px 0 8px}
.step .pic1{max-width:760px}
"""
