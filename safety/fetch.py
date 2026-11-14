"""Fetchers, one per source. Each saves raw results under data/ with the date fetched.

Run: <venv>/bin/python -m safety.fetch goa
Sources used here (licences checked 13 Nov 2026, see the design page):
- Wikivoyage (CC BY-SA 4.0): known dangers and scams, quoted with credit, share-alike.
- NDMA SACHET RSS: official disaster and weather alerts for India.
- Overture Maps places (CDLA-Permissive-2.0): spot locations, hospitals, police stations.
- GDELT DOC API (free, commercial use allowed): recent news article links. Rate-limited, so slow.
"""
import datetime, html, json, pathlib, re, sys, time, tomllib, urllib.parse, urllib.request
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
UA = {"User-Agent": "SafetyIntelligence/0.1 (open-data research prototype)"}
OVERTURE = "s3://overturemaps-us-west-2/release/2026-10-21.0/theme=places/type=place/*"


def get(url, timeout=60):
    """GET with polite retries: on 429 (rate limited) wait 15s, 30s, 60s, then give up."""
    for wait in (15, 30, 60, None):
        try:
            req = urllib.request.Request(url, headers=UA)
            out = urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8", "replace")
            if "wikivoyage.org" in url:
                time.sleep(2)  # Wikimedia asks bots to go slowly
            return out
        except urllib.error.HTTPError as ex:
            if ex.code != 429 or wait is None:
                raise
            time.sleep(wait)


def save(place, name, payload):
    d = DATA / place
    d.mkdir(parents=True, exist_ok=True)
    out = {"fetched": datetime.datetime.now().isoformat(timespec="minutes"), "data": payload}
    (d / f"{name}.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    return payload


# ---------- Wikivoyage ----------

def clean_html(s):
    s = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", s, flags=re.S)
    s = re.sub(r'<sup class="reference.*?</sup>', "", s, flags=re.S)
    s = re.sub(r'<span class="mw-editsection.*?</span></span>', "", s, flags=re.S)
    paras = re.findall(r"<(p|li)[^>]*>(.*?)</\1>", s, flags=re.S)
    out = []
    for _, p in paras:
        t = html.unescape(re.sub(r"<[^>]+>", "", p)).strip()
        t = re.sub(r"\s+", " ", t)
        if len(t) > 25:
            out.append(t)
    return out


def wikivoyage(place, cfg):
    page = cfg["wikivoyage_page"]
    meta = json.loads(get("https://en.wikivoyage.org/w/api.php?" + urllib.parse.urlencode(
        {"action": "parse", "page": page, "prop": "sections|revid", "format": "json"})))["parse"]
    want = {s.lower() for s in cfg["wikivoyage_sections"]}
    sections = {}
    for s in meta["sections"]:
        name = html.unescape(s["line"])
        if name.lower() in want and name not in sections:
            body = json.loads(get("https://en.wikivoyage.org/w/api.php?" + urllib.parse.urlencode(
                {"action": "parse", "page": page, "section": s["index"], "prop": "text", "format": "json"})))
            sections[name] = clean_html(body["parse"]["text"]["*"])
    return save(place, "wikivoyage", {"page": page, "revid": meta.get("revid"),
                                       "url": f"https://en.wikivoyage.org/wiki/{page}", "sections": sections})


# ---------- NDMA SACHET alerts ----------

def sachet(place, cfg):
    root = ET.fromstring(get("https://sachet.ndma.gov.in/cap_public_website/rss/rss_india.xml"))
    items = []
    for it in root.iter("item"):
        title = (it.findtext("title") or "").strip()
        desc = (it.findtext("description") or "").strip()
        text = f"{title} {desc}".lower()
        if any(k in text for k in cfg["alert_keywords"]):
            items.append({"title": title, "description": html.unescape(re.sub(r"<[^>]+>", "", desc))[:400],
                          "link": it.findtext("link"), "date": it.findtext("pubDate")})
    return save(place, "alerts", items[:20])


# ---------- Overture: spots and help nearby ----------

# Overture has spam and mis-tagged listings (a Delhi "hospital" with a Pakistani phone, a gurdwara tagged as a
# hospital). A wrong "nearest hospital" is worse than none, so every listing must pass these plain rules.
DIAL = {"IN": "+91", "GB": "+44", "AU": "+61", "US": "+1"}
NAME_MUST = {"hospital": ("hospital", "medical", "medicare", "health", "aiims", "nursing", "emergency", "trauma",
                          "phc", "chc", "dispensary", "institute of medical", "medical college", "primary health"),
             "police": ("police", "thana", "chowki", "outpost", "station"),
             "pharmacy": ("pharma", "chemist", "medical", "drug", "medicine", "apollo", "medplus", "jan aushadhi", "dawa")}
NAME_NOT = ("gurdwara", "temple", "mandir", "masjid", "mosque", "church", "school", "hotel", "restaurant", "shop",
            "veterinary", "pet ", "dental", "dentist", "homoeo", "homeo", "ayur", "skin", "hair", "eye ", "physio", "lab ")
NAME_NOT_BY_LABEL = {"hospital": ("pharmacy", "chemist", "pharma ", "medical store", "medicals")}


def plausible(label, name, phone, country="IN"):
    n = (name or "").lower()
    if not n or any(ord(ch) > 0x2FF and not 0x900 <= ord(ch) <= 0xDFF for ch in n):  # Latin or Indian scripts only
        return False
    if phone and DIAL.get(country) and not phone.replace(" ", "").startswith(DIAL[country]):
        return False
    if any(w in n for w in NAME_NOT + NAME_NOT_BY_LABEL.get(label, ())):
        return False
    return any(w in n for w in NAME_MUST[label])

def help_nearby(place, cfg):
    import duckdb
    con = duckdb.connect()
    con.sql("LOAD httpfs; LOAD spatial; SET s3_region='us-west-2'; SET memory_limit='2GB'; SET threads=4;"
            "SET enable_progress_bar=false; SET geometry_always_xy=true")
    w, s, e, n = cfg["bbox"]
    # spot_alias maps the label we show to the exact Overture name, picked by a human from the candidates list.
    lookup = {sp: cfg.get("spot_alias", {}).get(sp, sp) for sp in cfg["spots"]}
    con.execute(f"""CREATE TABLE p AS SELECT names.primary AS name, basic_category AS cat, taxonomy.primary AS tax,
                    confidence AS conf, ST_X(geometry) AS x, ST_Y(geometry) AS y,
                    phones[1] AS phone, websites[1] AS web
                    FROM read_parquet('{OVERTURE}')
                    WHERE bbox.xmin BETWEEN {w} AND {e} AND bbox.ymin BETWEEN {s} AND {n}
                      AND (basic_category IN ('hospital','emergency_or_urgent_care_facility','police_station','pharmacy_and_drug_store','fire_station')
                           OR regexp_matches(lower(names.primary), '{"|".join(re.escape(x.lower()).replace("'", "''") for x in lookup.values())}'))""")
    spots = {}
    for name in cfg["spots"]:
        # Skip placeholder points with rounded coordinates (e.g. 15.4, 73.8): they are vague geocodes, not the place.
        r = con.execute("""SELECT x, y FROM p WHERE lower(name) = lower(?)
                           AND NOT (round(x, 2) = x AND round(y, 2) = y)
                           ORDER BY conf DESC LIMIT 1""", [lookup[name]]).fetchone()
        if r:
            spots[name] = {"x": r[0], "y": r[1]}
    # Spots whose Overture point disagreed with Wikidata (safety.spotcheck) use the Wikidata point instead.
    fix_p = DATA / place / "spot_check.json"
    for name, c in (json.loads(fix_p.read_text()) if fix_p.exists() else {}).items():
        if c.get("verdict") == "far" and "lat" in c and name in lookup:
            spots[name] = {"x": c["lon"], "y": c["lat"], "located_by": f"Wikidata {c['wikidata']}"}
    # For spots with no exact match, list close names so a human can fix places.toml (never auto-picked).
    candidates = {name: con.execute("""SELECT DISTINCT name FROM p WHERE contains(lower(name), lower(?)) AND name IS NOT NULL
                                       ORDER BY length(name) LIMIT 6""", [lookup[name]]).fetchall()
                  for name in cfg["spots"] if name not in spots}
    near = {}
    for name, pt in spots.items():
        near[name] = {}
        for label, cats, minc in (("hospital", ("hospital", "emergency_or_urgent_care_facility"), 0.6),
                                  ("police", ("police_station",), 0.5),
                                  ("pharmacy", ("pharmacy_and_drug_store",), 0.6)):
            rows = con.execute(f"""SELECT name, phone, round(ST_Distance_Spheroid(ST_Point(x, y), ST_Point(?, ?)) / 1000, 1) km
                                   FROM p WHERE cat IN ({",".join("'" + c + "'" for c in cats)}) AND conf >= {minc}
                                   AND name IS NOT NULL
                                   AND NOT regexp_matches(lower(name), 'homoeo|homeo|ayur|dental|dent |skin|hair|eye care|physio|veterinary|pet |clinic$')
                                   ORDER BY km LIMIT 15""", [pt["x"], pt["y"]]).fetchall()
            near[name][label] = [{"name": r[0], "phone": r[1], "km": r[2]} for r in rows
                                 if plausible(label, r[0], r[1], cfg.get("country", "IN"))][:2]
    counts = dict(con.execute("SELECT cat, count(*) FROM p WHERE conf >= 0.5 GROUP BY 1").fetchall())
    return save(place, "help", {"spots": spots, "near": near, "counts": counts,
                                "missing_spots": [s for s in cfg["spots"] if s not in spots],
                                "candidates": {k: [r[0] for r in v] for k, v in candidates.items()}})


# ---------- News: one growing file per place, fed by local RSS and GDELT ----------

def add_articles(place, new, log):
    """Merge articles into data/<place>/news.json by URL. Never drops old ones: feeds only show the latest items."""
    p = DATA / place / "news.json"
    old = json.loads(p.read_text())["data"] if p.exists() else {"articles": [], "log": []}
    arts = {a["url"]: a for a in old["articles"]}
    added = 0
    for a in new:
        if a["url"] not in arts:
            arts[a["url"]] = a
            added += 1
    log = (old.get("log", []) + [f"{datetime.date.today()} {x}" for x in log])[-60:]
    save(place, "news", {"articles": sorted(arts.values(), key=lambda a: a["date"], reverse=True), "log": log})
    return added


# A feed item is kept only if it contains one of these word stems (a place can override with news_keywords).
DEFAULT_KEYWORDS = ["drown", "tourist", "taxi", "cab", "auto", "scam", "cheat", "fleec", "overcharg", "tout", "molest",
                    "harass", "rape", "assault", "theft", "stolen", "robb", "snatch", "accident", "crash", "killed",
                    "died", "dead", "injur", "rescue", "lifeguard", "beach", "waterfall", "ghat", "boat", "rafting",
                    "paraglid", "trek", "coracle", "stampede", "landslide", "flood", "fire", "drug", "fraud", "attack"]


def relevant(text, keywords, require=()):
    """Keep an item if it has a safety word, and (for wide-area feeds) also names the place."""
    t = text.lower()
    return any(k in t for k in keywords) and (not require or any(r in t for r in require))


def rss_date(s):
    """RSS pubDate (RFC 822) or ISO date -> YYYYMMDD; '' if unreadable."""
    import email.utils
    s = (s or "").strip()
    if re.match(r"\d{4}-\d{2}-\d{2}", s):
        return s[:10].replace("-", "")
    try:
        return email.utils.parsedate_to_datetime(s).strftime("%Y%m%d")
    except Exception:
        return ""


def local_news(place, cfg):
    new, log = [], []
    for source, url in cfg.get("news_feeds", []):
        try:
            root = ET.fromstring(get(url).lstrip())
        except Exception as ex:
            log.append(f"{source}: FAILED ({ex})")
            continue
        n = 0
        for it in root.iter("item"):
            title = html.unescape((it.findtext("title") or "").strip())
            desc = html.unescape(re.sub(r"<[^>]+>", " ", it.findtext("description") or ""))
            link = (it.findtext("link") or "").strip()
            if link and relevant(f"{title} {desc}", cfg.get("news_keywords", DEFAULT_KEYWORDS), cfg.get("news_require", ())):
                new.append({"title": title, "url": link, "domain": source, "date": rss_date(it.findtext("pubDate")),
                            "query": "feed"})
                n += 1
        log.append(f"{source}: {n} relevant")
    return {"added": add_articles(place, new, log), "log": log}


def news(place, cfg):
    """GDELT: 12 months of history. Heavily rate-limited, so run it in the background."""
    arts, log = {}, []
    for q in cfg["news_queries"]:
        url = "https://api.gdeltproject.org/api/v2/doc/doc?" + urllib.parse.urlencode(
            {"query": q + " sourcecountry:india", "mode": "artlist", "maxrecords": 75, "format": "json", "timespan": "12m"})
        got = None
        for attempt in range(4):
            try:
                raw = get(url)
                if raw.startswith("Please limit"):
                    raise RuntimeError("rate limited")
                got = json.loads(raw).get("articles", []) if raw.strip() else []
                break
            except Exception as ex:
                log.append(f"{q}: attempt {attempt + 1} failed ({ex})")
                time.sleep(90 * (attempt + 1))
        for a in got or []:
            arts[a["url"]] = {"title": a.get("title"), "url": a["url"], "domain": a.get("domain"),
                              "date": a.get("seendate", "")[:8], "query": q}
        log.append(f"gdelt {q}: {len(got) if got is not None else 'FAILED'}")
        time.sleep(30)
    return {"added": add_articles(place, list(arts.values()), log), "log": log}


FETCHERS = {"wikivoyage": wikivoyage, "alerts": sachet, "help": help_nearby, "feeds": local_news, "news": news}

if __name__ == "__main__":
    place = sys.argv[1]
    only = sys.argv[2:] or list(FETCHERS)
    cfg = tomllib.loads((ROOT / "places.toml").read_text())[place]
    for name in only:
        t = time.time()
        try:
            out = FETCHERS[name](place, cfg)
            size = len(out) if isinstance(out, (list, dict)) else 1
            print(f"{name}: ok ({size} items, {time.time() - t:.0f}s)")
        except Exception as ex:
            print(f"{name}: FAILED {ex}")
