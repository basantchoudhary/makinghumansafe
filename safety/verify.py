"""Deterministic evidence check: does the source article actually say what the incident claims?

For each incident we fetch source_url, strip it to plain text, and require:
  1. the page loads, and
  2. the place name (or its main word) appears in the text, and
  3. at least one word for the incident type or activity appears in the text.
Passing incidents get evidence = "checked"; anything else goes to a review list and is NOT published.
No AI is involved. Results are cached per URL so reruns are cheap.
"""
import hashlib, html, json, pathlib, re, sys, time, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
CACHE = ROOT / "data" / "_pages"
UA = {"User-Agent": "Mozilla/5.0 (SafetyIntelligence evidence check; open-data research)"}

# Words that must appear for each incident type (any one is enough).
TYPE_WORDS = {
    "drowning": ["drown"], "near-drowning": ["drown", "rescued", "rescue"], "rescue": ["rescue"],
    "injury": ["injur", "hurt", "wound"], "death": ["death", "died", "dead", "killed"],
    "theft": ["theft", "stole", "stolen", "robbed", "snatch"], "assault": ["assault", "attack", "beat"],
    "harassment": ["harass", "molest", "misbehav"], "overcharging": ["overcharg", "fleec", "charged", "fare"],
    "fraud": ["fraud", "cheat", "scam", "dupe"], "fire": ["fire", "blaze"], "accident": ["accident", "crash", "collision", "collided", "rammed"],
    "missing": ["missing", "swept away", "search"],
    "other": [""],
}
# Words too common to prove the place: generic place words plus every covered place and state name
# (an Agra paper says "Agra" everywhere, so "Taj Mahal, Agra" must match on "taj" or "mahal").
STOP = {"beach", "goa", "the", "near", "north", "south", "east", "west", "village", "road", "falls", "area", "ghat",
        "temple", "fort", "market", "station", "railway", "junction", "airport", "palace", "hill", "valley", "river",
        "lake", "city", "district", "new", "old", "bazaar", "mall"}
try:
    import tomllib as _t
    for _c in _t.loads((ROOT / "places.toml").read_text()).values():
        STOP |= set(re.findall(r"[a-z]+", (_c["name"] + " " + _c.get("state", "")).lower()))
except FileNotFoundError:
    pass


def text_of(url: str) -> str | None:
    CACHE.mkdir(parents=True, exist_ok=True)
    f = CACHE / (hashlib.sha1(url.encode()).hexdigest()[:16] + ".txt")
    if f.exists():
        t = f.read_text()
        return t or None
    try:
        raw = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30).read().decode("utf-8", "replace")
        raw = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", raw, flags=re.S | re.I)
        t = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", raw))).lower()
    except Exception:
        t = ""
    f.write_text(t)
    time.sleep(1)
    return t or None


def place_words(place: str) -> list[str]:
    words = [w for w in re.findall(r"[a-z]+", place.lower()) if w not in STOP and len(w) > 2]
    return words or [place.lower()]


def check(inc: dict, page: str | None) -> tuple[str, str]:
    """Return (evidence, reason). evidence is 'checked', 'unreachable' or 'mismatch'."""
    if page is None:
        return "unreachable", "source page could not be loaded"
    if not any(w in page for w in place_words(inc["place"])):
        return "mismatch", f"place {inc['place']!r} not found in source"
    words = TYPE_WORDS.get(inc["incident_type"], [""])
    if not any(w in page for w in words):
        return "mismatch", f"no word for {inc['incident_type']!r} in source"
    if inc.get("quote") is not None and not quote_in(inc["quote"], page):
        return "mismatch", "quote not found word for word in source"
    return "checked", "place and incident type found in source" + (", quote matches" if inc.get("quote") else "")


def _words(s: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", html.unescape(s).lower()))


def quote_in(quote: str, page: str) -> bool:
    """AI-extracted incidents carry a quote. It must appear in the page, ignoring case, punctuation and spacing.
    Quotes under 6 words prove nothing, so they fail."""
    q = _words(quote)
    return len(q.split()) >= 6 and q in _words(page)


def run(place: str) -> None:
    from safety.store import load, save
    data = load(place)
    review = []
    for inc in data["incidents"]:
        inc["evidence"], inc["evidence_reason"] = check(inc, text_of(inc["source_url"]))
        if inc["evidence"] != "checked":
            review.append({"place": inc["place"], "date": inc["date"], "url": inc["source_url"], "reason": inc["evidence_reason"]})
    save(place, data)
    (ROOT / "data" / place / "review.json").write_text(json.dumps(review, indent=1, ensure_ascii=False))
    n = len(data["incidents"])
    print(f"{n - len(review)} of {n} incidents checked against their source; {len(review)} sent to review")


if __name__ == "__main__":
    run(sys.argv[1])
