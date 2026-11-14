import pytest

from safety.extract import article_body, clean_json
from safety.fetch import relevant, rss_date
from safety.verify import check, quote_in

PAGE = ("goa news. tourist swept away while filming at arambol beach. a 24-year-old tourist from pune was swept "
        "away by strong waves while filming a video at arambol beach on tuesday evening, police said.")


@pytest.mark.parametrize("name, quote, want", [
    ("exact sentence", "A 24-year-old tourist from Pune was swept away by strong waves", True),
    ("punctuation and case ignored", "swept away by strong waves, while filming a video!", True),
    ("words changed by the model", "a tourist from Pune drowned in strong waves at Arambol", False),
    ("too short to prove anything", "arambol beach", False),
    ("empty quote", "", False),
])
def test_quote_in(name, quote, want):
    assert quote_in(quote, PAGE) == want, name


INC = {"place": "Arambol beach", "incident_type": "drowning"}


@pytest.mark.parametrize("name, inc, want", [
    ("hand-researched record without a quote: place and type words are enough",
     {**INC, "incident_type": "rescue", "quote": None}, "mismatch"),  # 'rescue' word not on page
    ("quote matches but no word for the claimed event (death) on the page", {**INC, "incident_type": "death", "quote": "was swept away by strong waves while filming a video"}, "mismatch"),
    ("AI record with a missing quote fails", {**INC, "incident_type": "other", "quote": ""}, "mismatch"),
    ("AI record with a good quote and matching type passes",
     {**INC, "incident_type": "other", "quote": "was swept away by strong waves while filming a video"}, "checked"),
])
def test_check_with_quote(name, inc, want):
    assert check(inc, PAGE)[0] == want, name


@pytest.mark.parametrize("name, reply, want", [
    ("plain JSON", '{"incidents": [{"place": "Baga"}]}', [{"place": "Baga"}]),
    ("think block and fences", '<think>hmm {"x":1}</think>```json\n{"incidents": []}\n```', []),
    ("not JSON", "sorry, no incidents", []),
    ("broken JSON", '{"incidents": [', []),
    ("wrong shape", '{"incidents": "none"}', []),
])
def test_clean_json(name, reply, want):
    assert clean_json(reply)["incidents"] == want, name


@pytest.mark.parametrize("name, text, want", [
    ("drowning headline", "Tourist drowns off Baga", True),
    ("taxi scam", "Cab driver fleeces tourists", True),
    ("politics", "Council rejects land proposal", False),
])
def test_relevant(name, text, want):
    assert relevant(text, ["drown", "cab", "fleec", "tourist"]) == want, name


@pytest.mark.parametrize("name, raw, want", [
    ("RFC 822", "Fri, 13 Nov 2026 06:10:00 +0530", "20261113"),
    ("ISO", "2026-11-12T23:30:00+05:30", "20261112"),
    ("missing", None, ""),
    ("junk", "yesterday", ""),
])
def test_rss_date(name, raw, want):
    assert rss_date(raw) == want, name


def test_article_body_starts_at_title():
    assert article_body("menu menu tourist swept away at arambol. body", "Tourist swept away at Arambol").startswith("tourist swept")


@pytest.mark.parametrize("name, inc, want", [
    ("same state", {"state": "Goa"}, True),
    ("case and spaces ignored", {"state": " goa "}, True),
    ("Goa-bound bus crash in Maharashtra", {"state": "Maharashtra"}, False),
    ("model left state out", {}, False),
])
def test_in_state(name, inc, want):
    from safety.extract import in_state
    assert in_state(inc, "Goa") == want, name


@pytest.mark.parametrize("name, inc, want", [
    ("right state and district", {"state": "Uttar Pradesh", "district": "Varanasi"}, True),
    ("district written differently", {"state": "uttar pradesh", "district": "Varanasi district"}, True),
    ("same state, other district (wide city feed)", {"state": "Uttar Pradesh", "district": "Ghazipur"}, False),
    ("district missing", {"state": "Uttar Pradesh"}, False),
])
def test_in_state_with_districts(name, inc, want):
    from safety.extract import in_state
    assert in_state(inc, "Uttar Pradesh", ["Varanasi"]) == want, name


@pytest.mark.parametrize("name, spot, ref, max_km, want", [
    ("same point", (26.9855, 75.8513), {"lat": 26.9855, "lon": 75.8513}, 1.5, "ok"),
    ("hotel named after the fort, 8 km away", (26.9134, 75.7983), {"lat": 26.9855, "lon": 75.8513}, 1.5, "far"),
    ("long beach, 1.6 km between points", (15.5439, 73.7553), {"lat": 15.5300, "lon": 73.7600}, 3.0, "ok"),
    ("no Wikidata item", (15.0, 74.0), None, 1.5, "no reference"),
])
def test_spot_verdict(name, spot, ref, max_km, want):
    from safety.spotcheck import verdict
    assert verdict(spot, ref, max_km)[0] == want, name


@pytest.mark.parametrize("name, label, place, phone, want", [
    ("real hospital", "hospital", "Lok Nayak Hospital", "+911123232400", True),
    ("Pakistani phone number on a Delhi 'hospital'", "hospital", "Dr Fida Painless & General Hospital", "+923439111645", False),
    ("Arabic-script listing", "hospital", "مستشفى فورتيس الهند - Fortis Hospital India", "+917795888413", False),
    ("gurdwara tagged as hospital", "hospital", "Gurdwara Sis Ganj Sahib", "+911123285117", False),
    ("pharmacy tagged as hospital", "hospital", "Guradian Pharmacy", None, False),
    ("Hindi name is fine", "hospital", "सरकारी अस्पताल Government Hospital", None, True),
    ("police station", "police", "Kotwali Police Station", None, True),
    ("chemist as pharmacy", "pharmacy", "Gupta Chemist", "+919811111111", True),
    ("dental clinic is not a hospital", "hospital", "Smile Dental Clinic", None, False),
])
def test_plausible(name, label, place, phone, want):
    from safety.fetch import plausible
    assert plausible(label, place, phone) == want, name


def test_specialist_clinic_is_not_an_emergency_hospital():
    from safety.fetch import plausible
    assert not plausible("hospital", "Dr Richa's Child Clinic & Endocrine Centre", None)
