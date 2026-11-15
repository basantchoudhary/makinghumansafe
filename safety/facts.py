"""The fact store: one place for every checked fact, with its source, period and how it was checked.

A fact is one measured statement about a place and topic, for example
  place=bengaluru topic=road dimension=when metric=deaths_share_6pm_2am value=43 unit=% period=2023
  statement="43% of road deaths happened between 6 pm and 2 am."  quote=<word-for-word sentence from the source>

Dimensions (the branches of every story's mind map):
  how_many  when  who  where  why  action  trend  caveat
Facts come from adapters (official tables, our incident lists) and from the document reader (AI proposes, code checks).
Storage: DuckDB file data/facts.duckdb (kept on this machine; built from sources, so it can always be rebuilt).
"""
import datetime, hashlib, json, pathlib

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


def fid(f):
    return hashlib.sha1("|".join(str(f.get(k, "")) for k in ("place", "topic", "metric", "period", "source_id", "value")).encode()).hexdigest()[:16]


def upsert(facts):
    """Insert or replace facts (by id). Returns how many were written."""
    con = connect()
    n = 0
    for f in facts:
        f = {**f, "id": fid(f), "checked": f.get("checked") or datetime.date.today().isoformat(),
             "time_window": json.dumps(f["window"]) if isinstance(f.get("window"), (dict, list)) else f.get("window")}
        con.execute("DELETE FROM facts WHERE id = ?", [f["id"]])
        cols = ["id", "place", "topic", "dimension", "metric", "value", "unit", "period", "statement", "quote", "time_window",
                "source_id", "source_name", "source_url", "source_page", "method", "checked", "status"]
        con.execute(f"INSERT INTO facts ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})", [f.get(c) for c in cols])
        n += 1
    con.close()
    return n


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
                          FROM facts WHERE place = ? AND topic = ? AND status = 'checked'
                          GROUP BY metric, period HAVING count(DISTINCT value) > 1""", [place, topic]).fetchall()
    con.close()
    return [{"metric": m, "period": p, "figures": f} for m, p, f in rows]
