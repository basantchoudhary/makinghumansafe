import pytest

from safety.verify import check

INC = {"place": "Baga beach", "incident_type": "drowning"}


@pytest.mark.parametrize("name, inc, page, want", [
    ("place and type present", INC, "a tourist drowned at baga on sunday", "checked"),
    ("page not loaded", INC, None, "unreachable"),
    ("wrong place", INC, "a tourist drowned at colva on sunday", "mismatch"),
    ("place present but not the event", INC, "baga beach was crowded on sunday", "mismatch"),
    ("generic words like 'beach' don't count as the place", {"place": "Baga beach", "incident_type": "drowning"},
     "a man drowned at a beach", "mismatch"),
    ("taxi overcharging", {"place": "Calangute", "incident_type": "overcharging"},
     "tourists at calangute were overcharged by taxi drivers", "checked"),
])
def test_check(name, inc, page, want):
    assert check(inc, page)[0] == want, name
