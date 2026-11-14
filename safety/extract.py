"""AI extraction: read news articles and pull out safety incidents as structured records.

Run: python3 -m safety.extract goa [max_articles]
Then: python3 -m safety.verify goa

The AI only proposes. Every incident must carry a word-for-word quote from the article; verify.py
checks that quote (and the place and event words) against the page with plain rules, and anything that
fails is not published. Articles already read are remembered in data/<place>/extracted.json.

Extractor is a port: GroqExtractor (free tier, open-weight model) or NoExtractor (skip AI).
"""
import json, os, pathlib, re, sys, time, urllib.request

from safety.store import ACTIVITIES, TYPES, load, merge, normalise, save
from safety.verify import text_of

ROOT = pathlib.Path(__file__).resolve().parent.parent
MODEL = os.environ.get("SAFETY_MODEL", "qwen/qwen3.8-27b")

PROMPT = """You read one Indian news article and list the safety incidents it reports in or near {place}.
Only events that happened INSIDE {place} itself: skip events elsewhere even if the people were going to or from {place}.
Only incidents that tell a visitor or a person out in public something about risk: public-place crime, scams,
road crashes, drownings, activity accidents, fires or collapses in public places, disasters. SKIP targeted gang
killings, family or property disputes, police encounters, crimes inside homes, and household accidents.
Only real events that happened (not plans, policies, statistics, court hearings about old cases or opinion).
Return JSON only: {{"incidents": [ ... ]}} — an empty list if there are none.
Each incident:
  "date": "YYYY-MM-DD" of the event (or "YYYY-MM" if the day is unclear); use the article date {article_date} if it says "today"/"on Sunday" etc.
  "district": the district where it happened (e.g. "North Goa", "Varanasi", "Dehradun")
  "state": the Indian state or territory where it happened, as written in the article
  "place": the most specific named spot (beach, village, town) in {place}; never a person's name
  "activity": one of {activities}
  "incident_type": one of {types}; use "drowning" or "death" only if the article says the person died, "missing" if they are still being searched for
  "what_happened": one plain sentence, no names of people
  "people_affected": number or null, "deaths": number or null
  "visitor_type": "tourist" | "local" | "unknown"
  "cause": short phrase or null (e.g. "rip current", "drunk driving")
  "quote": one sentence copied WORD FOR WORD from the article that shows the incident happened
If the article is not about {place}, return an empty list.

Title: {title}
Article text:
{text}"""


def clean_json(s: str) -> dict:
    """Pull the JSON object out of a model reply (drops <think> blocks and ``` fences)."""
    s = re.sub(r"<think>.*?</think>", "", s, flags=re.S)
    m = re.search(r"\{.*\}", s, flags=re.S)
    if not m:
        return {"incidents": []}
    try:
        out = json.loads(m.group(0))
    except json.JSONDecodeError:
        return {"incidents": []}
    return out if isinstance(out.get("incidents"), list) else {"incidents": []}


def in_state(inc: dict, state: str, districts=()) -> bool:
    """Deterministic geography gate: the model must name the state (and district, if the place lists districts),
    and they must be ours. Wide feeds (a city paper covering a whole region) make this necessary."""
    norm = lambda x: re.sub(r"[^a-z]", "", (x or "").lower())
    if norm(inc.get("state")) != norm(state):
        return False
    return not districts or any(norm(d) in norm(inc.get("district")) for d in districts) and bool(norm(inc.get("district")))


def article_body(page: str, title: str) -> str:
    """Rough cut of the article from the page text: start at the title, keep ~6000 chars."""
    t = page
    i = t.find(title.lower()[:40]) if title else -1
    if i > 0:
        t = t[i:]
    return t[:6000]


class NoExtractor:
    def extract(self, place, article, text):
        return []


class GroqExtractor:
    URL = "https://api.groq.com/openai/v1/chat/completions"

    def __init__(self, key, model=MODEL):
        self.key, self.model = key, model

    def extract(self, place, article, text):
        d = article.get("date", "")
        prompt = PROMPT.format(place=place, article_date=f"{d[:4]}-{d[4:6]}-{d[6:8]}" if len(d) == 8 else "unknown",
                               activities=sorted(ACTIVITIES), types=sorted(TYPES), title=article["title"], text=text)
        body = json.dumps({"model": self.model, "temperature": 0, "response_format": {"type": "json_object"},
                           "messages": [{"role": "user", "content": prompt}]}).encode()
        for attempt in range(4):
            req = urllib.request.Request(self.URL, data=body, headers={
                "Authorization": f"Bearer {self.key}", "Content-Type": "application/json", "User-Agent": "safety-intelligence/0.1"})
            try:
                reply = json.loads(urllib.request.urlopen(req, timeout=90).read())["choices"][0]["message"]["content"]
                return clean_json(reply)["incidents"]
            except urllib.error.HTTPError as ex:
                if ex.code == 429:
                    time.sleep(20 * (attempt + 1))
                    continue
                raise
        return []


def extractor():
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"'))
    key = os.environ.get("GROQ_API_KEY")
    return GroqExtractor(key) if key else NoExtractor()


def run(place_key: str, limit: int = 40) -> None:
    import tomllib
    cfg = tomllib.loads((ROOT / "places.toml").read_text())[place_key]
    place, state, districts = cfg["name"], cfg.get("state", cfg["name"]), cfg.get("districts", ())
    news = json.loads((ROOT / "data" / place_key / "news.json").read_text())["data"]["articles"]
    done_p = ROOT / "data" / place_key / "extracted.json"
    done = json.loads(done_p.read_text()) if done_p.exists() else {}
    ex = extractor()
    if isinstance(ex, NoExtractor):
        print("No GROQ_API_KEY: nothing extracted.")
        return
    todo = [a for a in news if a["url"] not in done][:limit]
    found = []
    for a in todo:
        page = text_of(a["url"])
        if not page:
            done[a["url"]] = {"status": "unreachable"}
            continue
        try:
            incs = ex.extract(place, a, article_body(page, a["title"]))
        except Exception as err:
            print("  failed:", a["url"], err)
            continue
        incs = [i for i in incs if in_state(i, state, districts)]
        for i in incs:
            # A missing quote becomes "" so verify fails it (None would mean "hand-researched, no quote").
            i.update(source_url=a["url"], source_name=a["domain"], source_date=a["date"], quote=i.get("quote") or "")
        done[a["url"]] = {"status": "read", "incidents": len(incs)}
        found += incs
        print(f"  {len(incs)} from: {a['title'][:80]}")
        time.sleep(2)
    done_p.write_text(json.dumps(done, indent=1))
    data = load(place_key)
    new = [normalise(r, "news") for r in found]
    data["incidents"], rejected = merge(data["incidents"], new)
    save(place_key, data)
    print(f"read {len(todo)} articles; {len(found)} incidents proposed, {len(rejected)} rejected; "
          f"store has {len(data['incidents'])}. Now run: python3 -m safety.verify {place_key}")


if __name__ == "__main__":
    run(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 40)
