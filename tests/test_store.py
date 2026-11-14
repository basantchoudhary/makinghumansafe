import pytest

from safety.store import merge, problems, summarise

GOOD = {"date": "2025-12-02", "place": "Baga beach", "activity": "swimming", "incident_type": "drowning",
        "what_happened": "A tourist drowned while swimming at night.", "source_url": "https://example.com/a", "deaths": 1}


@pytest.mark.parametrize("name, change, want", [
    ("valid incident", {}, []),
    ("no source", {"source_url": None}, ["missing source_url"]),
    ("source not a link", {"source_url": "Times of India"}, ["source_url is not a link"]),
    ("unknown activity", {"activity": "skydiving"}, ["unknown activity 'skydiving'"]),
    ("unknown type", {"incident_type": "mystery"}, ["unknown type 'mystery'"]),
    ("month-only date is fine", {"date": "2025-12"}, []),
    ("bad date", {"date": "Dec 2025"}, ["bad date 'Dec 2025'"]),
    ("missing place", {"place": ""}, ["missing place"]),
])
def test_problems(name, change, want):
    assert problems({**GOOD, **change}) == want, name


@pytest.mark.parametrize("name, new, want_count, want_rejected", [
    ("adds a new incident", [{**GOOD, "date": "2025-11-01", "place": "Calangute"}], 2, 0),
    ("same event from another paper counts once", [{**GOOD, "source_url": "https://other.com/b", "date": "2025-12-03"}], 1, 0),
    ("place spelling differences still match", [{**GOOD, "place": "baga Beach!"}], 1, 0),
    ("invalid incident is rejected, not stored", [{**GOOD, "source_url": None, "place": "Anjuna"}], 1, 1),
])
def test_merge(name, new, want_count, want_rejected):
    out, rejected = merge([GOOD], new)
    assert (len(out), len(rejected)) == (want_count, want_rejected), name


@pytest.mark.parametrize("name, raw, want", [
    ("drowning is fatal, activity category, news, medium",
     {**GOOD}, ("fatal", "activity", "news", "medium")),
    ("scooter crash with injury is serious and road",
     {**GOOD, "activity": "scooter/road", "incident_type": "accident", "deaths": 0}, ("serious", "road", "news", "medium")),
    ("taxi overcharging is minor and scam",
     {**GOOD, "activity": "scam", "incident_type": "overcharging", "deaths": None}, ("minor", "scam", "news", "medium")),
    ("official source gets high confidence",
     {**GOOD, "source_type": "official"}, ("fatal", "activity", "official", "high")),
])
def test_normalise(name, raw, want):
    from safety.store import normalise
    inc = normalise(raw)
    assert (inc["severity"], inc["category"], inc["source_type"], inc["confidence"]) == want, name
    assert problems(inc) == [], name


def test_summarise():
    incs = [GOOD, {**GOOD, "date": "2024-05-01", "place": "Calangute", "deaths": 2, "cause": "rip current"},
            {**GOOD, "activity": "scam", "incident_type": "overcharging", "deaths": None}]
    s = summarise(sorted(incs, key=lambda i: i["date"], reverse=True), "swimming")
    assert (s["count"], s["deaths"], s["last"], s["since"], s["causes"]) == (2, 3, "2025-12-02", "2024", ["rip current"])
