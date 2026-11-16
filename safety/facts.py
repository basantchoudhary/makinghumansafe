"""The fact store: one place for every checked fact, with its source, period and how it was checked.

A fact is one measured statement about a place and topic, for example
  place=bengaluru topic=road dimension=when metric=deaths_share_6pm_2am value=43 unit=% period=2023
  statement="43% of road deaths happened between 6 pm and 2 am."  quote=<word-for-word sentence from the source>

Dimensions (the branches of every story's mind map):
  how_many  when  who  where  why  action  trend  caveat
Facts come from adapters (official tables, our incident lists) and from the document reader (AI proposes, code checks).
Storage: DuckDB file data/facts.duckdb (kept on this machine; built from sources, so it can always be rebuilt).
"""
import datetime, hashlib, json, pathlib, re

import duckdb

ROOT = pathlib.Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "facts.duckdb"
DIMENSIONS = ("how_many", "when", "who", "where", "why", "action", "trend", "caveat")

SCHEMA = """
CREATE TABLE IF NOT EXISTS facts (
  id VARCHAR PRIMARY KEY,           -- hash of place, topic, metric, period, source
  place VARCHAR, topic VARCHAR, dimension VARCHAR,
  metric VARCHAR,                   -- short snake_case name, e.g. deaths_share_motorcyclists
  value DOUBLE, unit VARCHAR,       -- e.g. 59, '%' ; 933, 'deaths'
  period VARCHAR,                   -- e.g. '2023', '2026-01..2026-10'
  statement VARCHAR,                -- one plain sentence for people
  quote VARCHAR,                    -- word-for-word from the source (empty for table adapters)
  time_window VARCHAR,                  -- JSON for 'right now' rules, e.g. {"hours":[18,2]} or {"days":["Sun"]}
  source_id VARCHAR, source_name VARCHAR, source_url VARCHAR, source_page VARCHAR,
  method VARCHAR,                   -- 'table adapter' | 'document reader (AI) + quote check' | 'computed from incidents'
  checked DATE, status VARCHAR      -- 'checked' | 'rejected: <reason>'
);
"""


def connect():
    DB.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(DB))
    con.execute(SCHEMA)
    return con


MONTHS = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]


def canonical_metric(f):
    """Standard names for core measures, so the same measure from different sources can be compared (fixed rules)."""
    m, u = (f.get("metric") or "").lower(), (f.get("unit") or "").lower()
    if u in ("%", "percent") or re.search(r"share|rate|per_|record|increase|decrease|change|average|_day", m):  # derived measures keep their names
        return f.get("metric")
    if re.search(r"child|school|near|within|zone|junction|spot|corridor|night|day|age|male|female|men|women|helmet|hit_and_run|single|"
                 r"weekend|month|hour|division|station|ward|road_|highway|expressway|ring|drunk|speed", m):
        return f.get("metric")  # a qualified measure (a group, place or time) is never merged with a citywide total
    if re.search(r"child|school|near |within|junction|black spot|corridor|aged |students|elderly|occupant|every day|per day|daily|each day|"
                 r"seat ?belt|helmet|two-wheeler|four-wheeler|three-wheeler|cars?\b|bikers?|riders?|males?|females?|women|men\b|"
                 r"pothole|negligence|civic|drunk|drink|hit-and-run|speed|night|weekend",
                 (f.get("statement") or "").lower()):
        q = re.search(r"pothole|negligence|civic|drunk|drink|hit-and-run|speed|night|weekend|occupant|every day|per day|daily|child|school|"
                      r"two-wheeler|four-wheeler|three-wheeler|pedestrian|helmet|seat ?belt|women|men\b|males?|aged", (f.get("statement") or "").lower())
        m0 = f.get("metric") or ""
        if q and re.fullmatch(r"(?:\w+_)?(?:deaths|injuries|fatal_crashes)_total", m0):
            return m0 + "_" + re.sub(r"\W+", "_", q.group(0)).strip("_")  # a qualified count is never a citywide total
        return m0  # the qualifier is in the sentence, not the name
    who = "pedestrian" if "pedestrian" in m else "motorcyclist" if re.search("motorcycl|two_wheel|biker|rider", m) else ""
    if re.search("injur", m):
        return f"{who + '_' if who else ''}injuries_total"
    if re.search("fatal_crash|fatal_accident", m):
        return "fatal_crashes_total"
    if re.search("death|fatalit|killed|died", m) and ("death" in u or u in ("", "people", "persons", "deaths", "fatalities")):
        return f"{who + '_' if who else ''}deaths_total"
    return f.get("metric")


def canonical_period(f):
    """'2026' plus months named in the statement or quote ('between January and September') becomes '2026 Jan-Sep'."""
    p = str(f.get("period") or "")
    yr = re.findall(r"(?:19|20)\d\d", p)
    txt = (f.get("statement") or "").lower()  # month ranges only from the statement, and only when written as a range
    rng = re.search(r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+(?:to|and|-|–|through|till|until)\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*", txt)
    ms = [MONTHS.index(rng.group(1)), MONTHS.index(rng.group(2))] if rng else []
    if re.search(r"first (?:nine|six|three) months", txt):
        ms = [0, {"nine": 8, "six": 5, "three": 2}[re.search(r"first (nine|six|three)", txt).group(1)]]
    if len(yr) == 1 and len(ms) >= 2:
        return f"{yr[0]} {MONTHS[min(ms)].title()}-{MONTHS[max(ms)].title()}"
    return p


def fid(f):
    return hashlib.sha1("|".join(str(f.get(k, "")) for k in ("place", "topic", "metric", "period", "source_id", "value")).encode()).hexdigest()[:16]


def upsert(facts):
    """Insert or replace facts (by id). Returns how many were written."""
    con = connect()
    n = 0
    for f in facts:
        f = {**f, "metric": canonical_metric(f), "period": canonical_period(f)}
        f = {**f, "id": fid(f), "checked": f.get("checked") or datetime.date.today().isoformat(),
             "time_window": json.dumps(f["window"]) if isinstance(f.get("window"), (dict, list)) else f.get("window")}
        con.execute("DELETE FROM facts WHERE id = ?", [f["id"]])
        cols = ["id", "place", "topic", "dimension", "metric", "value", "unit", "period", "statement", "quote", "time_window",
                "source_id", "source_name", "source_url", "source_page", "method", "checked", "status"]
        con.execute(f"INSERT INTO facts ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})", [f.get(c) for c in cols])
        n += 1
    con.close()
    return n


def replace_source(source_id, place, topic, new):
    """Re-reading a source replaces all its earlier facts for this place and topic (no stale facts pile up)."""
    con = connect()
    con.execute("DELETE FROM facts WHERE source_id = ? AND place = ? AND topic = ?", [source_id, place, topic])
    con.close()
    return upsert(new)


def for_story(place, topic):
    """Checked facts for one place and topic, newest period first."""
    con = connect()
    cur = con.execute("""SELECT * FROM facts WHERE place = ? AND topic = ? AND status = 'checked'
                          ORDER BY period DESC, dimension, metric""", [place, topic])
    cols = [c[0] for c in cur.description]
    rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    con.close()
    return rows


def conflicts(place, topic):
    """Same metric and period, different values from different sources: shown as 'numbers differ'."""
    con = connect()
    rows = con.execute("""SELECT metric, period, list(DISTINCT struct_pack(v := value, s := source_name, u := source_url)) AS figures
                          FROM facts WHERE place = ? AND topic = ? AND status = 'checked' AND value IS NOT NULL
                          GROUP BY metric, period HAVING count(DISTINCT value) > 1""", [place, topic]).fetchall()
    con.close()
    return [{"metric": m, "period": p, "figures": f} for m, p, f in rows]
