"""The incident store: one JSON file per place (data/<place>/incidents.json), validated and de-duplicated.

Every incident must carry a source URL. Nothing is stored without one.
"""
import json, pathlib, re
from collections import Counter

ROOT = pathlib.Path(__file__).resolve().parent.parent

ACTIVITIES = {"swimming", "water sports", "parasailing", "waterfall", "trek", "scooter/road",
              "nightlife", "crime", "scam", "other"}
TYPES = {"drowning", "near-drowning", "rescue", "injury", "death", "theft", "assault", "harassment",
         "overcharging", "fraud", "fire", "accident", "missing", "other"}
# Design categories (safety-intelligence.html, "The data model").
CATEGORIES = {"crime", "road", "health", "activity", "nature", "scam"}
SOURCE_TYPES = {"news", "official", "crowd"}
CONFIDENCE = {"high", "medium", "low"}
REQUIRED = ("date", "place", "activity", "incident_type", "what_happened", "source_url")

# Full incident record, as in the design. Optional fields default to None.
FIELDS = ("date", "place", "place_code", "lat", "lon", "area", "category", "activity", "incident_type",
          "severity", "what_happened", "people_affected", "deaths", "visitor_type", "cause",
          "source_name", "source_url", "source_date", "source_type", "confidence", "quote")

_CATEGORY_OF = {"crime": "crime", "scam": "scam", "scooter/road": "road", "nightlife": "crime"}


def severity(inc: dict) -> str:
    """Derived, never typed in: death > injury or drowning > the rest."""
    if (inc.get("deaths") or 0) > 0 or inc.get("incident_type") in ("death", "drowning"):
        return "fatal"
    if inc.get("incident_type") in ("injury", "assault", "near-drowning", "fire", "accident", "missing"):
        return "serious"
    return "minor"


def normalise(raw: dict, source_type: str = "news") -> dict:
    """Map any incoming record into the full design record."""
    inc = {f: raw.get(f) for f in FIELDS}
    inc["category"] = raw.get("category") or _CATEGORY_OF.get(raw.get("activity"), "activity")
    inc["source_type"] = raw.get("source_type") or source_type
    inc["confidence"] = raw.get("confidence") or ("high" if inc["source_type"] == "official" else "medium")
    inc["severity"] = severity(inc)
    return inc


def problems(inc: dict) -> list[str]:
    """Reasons an incident can't be stored. Empty list means it's fine."""
    out = [f"missing {f}" for f in REQUIRED if not inc.get(f)]
    if inc.get("activity") and inc["activity"] not in ACTIVITIES:
        out.append(f"unknown activity {inc['activity']!r}")
    if inc.get("incident_type") and inc["incident_type"] not in TYPES:
        out.append(f"unknown type {inc['incident_type']!r}")
    if inc.get("date") and not re.fullmatch(r"\d{4}(-\d{2}(-\d{2})?)?", inc["date"]):
        out.append(f"bad date {inc['date']!r}")
    if inc.get("source_url") and not inc["source_url"].startswith(("http://", "https://")):
        out.append("source_url is not a link")
    for f, allowed in (("category", CATEGORIES), ("source_type", SOURCE_TYPES), ("confidence", CONFIDENCE)):
        if inc.get(f) and inc[f] not in allowed:
            out.append(f"unknown {f} {inc[f]!r}")
    return out


def key(inc: dict) -> tuple:
    """Same place, month, activity and type counts as one incident (several papers, one event)."""
    place = re.sub(r"[^a-z]", "", (inc.get("place") or "").lower())
    return (inc.get("date", "")[:7], place, inc.get("activity"), inc.get("incident_type"))


def merge(existing: list[dict], new: list[dict]) -> tuple[list[dict], list[tuple[dict, list[str]]]]:
    """Add valid, not-yet-seen incidents. Returns (all incidents, rejected with reasons)."""
    seen = {key(i) for i in existing}
    out, rejected = list(existing), []
    for inc in new:
        why = problems(inc)
        if why:
            rejected.append((inc, why))
        elif key(inc) not in seen:
            seen.add(key(inc))
            out.append(inc)
    out.sort(key=lambda i: i["date"], reverse=True)
    return out, rejected


def summarise(incidents: list[dict], activity: str) -> dict:
    rows = [i for i in incidents if i["activity"] == activity]
    return {
        "count": len(rows),
        "deaths": sum(i.get("deaths") or 0 for i in rows),
        "last": rows[0]["date"] if rows else None,
        "since": min((i["date"][:4] for i in rows), default=None),
        "types": Counter(i["incident_type"] for i in rows).most_common(3),
        "places": Counter(i["place"] for i in rows).most_common(3),
        "causes": [c for c, _ in Counter(i["cause"] for i in rows if i.get("cause")).most_common(3)],
    }


def path(place: str) -> pathlib.Path:
    return ROOT / "data" / place / "incidents.json"


def load(place: str) -> dict:
    p = path(place)
    return json.loads(p.read_text()) if p.exists() else {"incidents": [], "aggregates": [], "rules": []}


def save(place: str, data: dict) -> None:
    p = path(place)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=1))
