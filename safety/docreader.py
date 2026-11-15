"""Document reader: turn a report (PDF or web page) into checked facts for any place and topic.

Run: .venv/bin/python -m safety.docreader <doc_id>      (documents are listed in docs.toml)

1. Fetch the document once into data/_docs/ (not committed; the source keeps its own rights).
2. Split the text into chunks of a few pages, keeping page numbers.
3. The AI proposes findings a member of the public should know, each with dimension, metric, number, unit,
   period, a plain statement and a WORD-FOR-WORD quote.
4. Code checks every finding (no AI): the quote is in the chunk; the number is in the quote; every number in the
   plain statement is in the quote; the dimension is valid; a 'right now' window uses hours or days named in the quote.
5. Passing findings go into the fact store as 'checked'; failures are kept with the reason, never shown.
"""
import json, pathlib, re, subprocess, sys, tomllib, urllib.request

from safety import facts, llm

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOCS = ROOT / "data" / "_docs"
UA = {"User-Agent": "Mozilla/5.0 (MakingHumanSafe document reader; open-data safety research)"}

PROMPT = """You read part of an official or expert report about {topic} safety in {place_name}.
List the findings an ordinary person should know to stay safe: how many are hurt or killed, when (hours, days,
months), who (road users, ages, sexes), where (roads, junctions, areas), why (causes, behaviours), what helps (actions),
trends (rising or falling) and caveats (data limits). Skip methods, budgets, acknowledgements and institutional plans.
Return JSON only: {{"findings": [ ... ]}} with at most 12 findings. Each finding:
  "dimension": one of how_many, when, who, where, why, action, trend, caveat
  "metric": short snake_case name, e.g. deaths_share_motorcyclists, deaths_total, helmet_correct_use_share
  "value": the main number (e.g. 59), or null if the finding has no number
  "unit": "%", "deaths", "crashes", "km/h", "per km" ... or ""
  "period": the year or period the number is for, e.g. "2023"
  "statement": one short plain sentence a member of the public understands; use ONLY numbers that appear in the quote
  "quote": one sentence copied WORD FOR WORD from the text below that contains the number
  "window": only for 'when' findings that name hours or days: {{"hours": [start_hour_24, end_hour_24]}} or {{"days": ["Sun", ...]}}; else null
Text (pages {pages}):
{text}"""


def norm(s):
    s = (s or "").lower().replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    s = s.replace("–", "-").replace("—", "-").replace(" ", " ")
    return re.sub(r"\s+", " ", s).strip()


def numbers(s):
    return {float(x.replace(",", "")) for x in re.findall(r"\d[\d,]*\.?\d*", s or "") if x.replace(",", "").replace(".", "", 1).isdigit()}


HOURS = {"12 am": 0, "midnight": 0, "noon": 12, "12 pm": 12}


WORDNUM = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
           "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17,
           "eighteen": 18, "nineteen": 19, "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70,
           "eighty": 80, "ninety": 90, "hundred": 100}


def quote_numbers(q):
    """Numbers in a quote, counting number words ('Eleven' = 11) as well as digits."""
    return numbers(q) | {float(v) for w, v in WORDNUM.items() if re.search(rf"\b{w}\b", (q or "").lower())}


def check(f, chunk):
    """Return '' if the finding passes every rule, else the reason it fails."""
    if f.get("dimension") not in facts.DIMENSIONS:
        return f"bad dimension {f.get('dimension')}"
    q = norm(f.get("quote"))
    if len(q) < 20 or q not in norm(chunk):
        return "quote not found word for word"
    qn = quote_numbers(f.get("quote"))
    years = {float(y) for y in re.findall(r"(?:19|20)\d\d", str(f.get("period") or ""))}
    if f.get("value") is not None:
        try:
            v = float(f["value"])
        except (TypeError, ValueError):
            return "value is not a number"
        if not any(abs(v - x) < 1e-6 for x in qn):
            return f"value {f['value']} not in quote"
    extra = {x for x in numbers(f.get("statement")) if not any(abs(x - y) < 1e-6 for y in qn) and x not in years}  # the fact's own year is allowed
    if extra:
        return f"statement has numbers not in quote: {sorted(extra)}"
    w = f.get("window")
    if isinstance(w, dict) and w.get("hours"):
        hs = [int(h) % 24 for h in w["hours"]]
        named = {int(x) % 12 for x in re.findall(r"(\d{1,2})(?::\d\d)?\s*(?:am|pm|a\.m|p\.m)", q)}
        if not all((h % 12) in named or (h in (0, 12) and ("midnight" in q or "noon" in q)) for h in hs):
            return "window hours not named in quote"
    return ""


def fetch(doc_id, d):
    DOCS.mkdir(parents=True, exist_ok=True)
    raw = DOCS / f"{doc_id}.{d['type']}"
    if not raw.exists():
        raw.write_bytes(urllib.request.urlopen(urllib.request.Request(d["url"], headers=UA), timeout=300).read())
    if d["type"] == "pdf":
        from pypdf import PdfReader
        return [(i + 1, p.extract_text() or "") for i, p in enumerate(PdfReader(str(raw)).pages)]
    if d["type"] == "html":
        dom = subprocess.run(["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "--headless", "--disable-gpu",
                              "--virtual-time-budget=8000", "--dump-dom", d["url"]], capture_output=True, text=True, timeout=90).stdout
        txt = re.sub(r"<[^>]+>", " ", re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", dom, flags=re.S))
        return [(1, txt)]
    raise ValueError(d["type"])


def chunks(pages, size=7000):
    cur, first, out = "", None, []
    for n, t in pages:
        if first is None:
            first = n
        cur += f"\n[page {n}]\n{t}"
        if len(cur) > size:
            out.append((f"{first}-{n}", cur)); cur, first = "", None
    if cur.strip():
        out.append((f"{first}-{pages[-1][0]}", cur))
    return out


def run(doc_id):
    reg = tomllib.loads((ROOT / "docs.toml").read_text())
    d = reg[doc_id]
    pages = fetch(doc_id, d)
    ok, bad = [], []
    cache_p = DOCS / f"{doc_id}.proposals.json"  # AI proposals are cached: re-checking never re-pays for AI calls
    cache = json.loads(cache_p.read_text()) if cache_p.exists() else {}
    for pr, text in chunks(pages):
        if pr not in cache:
            cache[pr] = llm.json_call(PROMPT.format(topic=d["topic"], place_name=d["place_name"], pages=pr, text=text)).get("findings") or []
            cache_p.write_text(json.dumps(cache, indent=1))
        got = cache[pr]
        for f in got:
            why = check(f, text)
            rec = {**{k: f.get(k) for k in ("dimension", "metric", "value", "unit", "period", "statement", "quote", "window")},
                   "place": d["place"], "topic": d["topic"], "period": str(f.get("period") or d.get("period", "")),
                   "source_id": doc_id, "source_name": d["title"], "source_url": d["url"], "source_page": f"pages {pr}",
                   "method": "document reader (AI proposes) + code checks (quote, numbers, window)",
                   "status": "checked" if not why else f"rejected: {why}"}
            (ok if not why else bad).append(rec)
        print(f"  pages {pr}: {len(got)} proposed, {sum(1 for f in got if not check(f, text))} passed", flush=True)
    facts.upsert(ok + bad)
    print(f"{doc_id}: {len(ok)} checked facts, {len(bad)} rejected")
    for b in bad[:8]:
        print("   rejected:", b["status"], "|", (b.get("statement") or "")[:80])


if __name__ == "__main__":
    run(sys.argv[1])
