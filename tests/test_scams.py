"""Deterministic guard against made-up scam records: every quoted source_text must appear,
word for word, in the fetched Wikivoyage text (unless the record cites a different source)."""
import json, pathlib, re, tomllib

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent


def norm(s):
    return re.sub(r"\s+", " ", s.replace("☏ ", "")).strip()


def records():
    for f in sorted((ROOT / "scams").glob("*.toml")):
        place = f.stem
        wv = ROOT / "data" / place / "wikivoyage.json"
        if not wv.exists():
            continue
        text = norm(" ".join(p for sec in json.loads(wv.read_text())["data"]["sections"].values() for p in sec))
        data = tomllib.loads(f.read_text())
        for kind in ("scam", "rule", "helpline"):
            for r in data.get(kind, []):
                if r.get("source", data["source_default"]) == data["source_default"]:
                    yield pytest.param(text, r["source_text"], id=f"{place}:{kind}:{r.get('name') or r.get('number') or r.get('rule', '')[:30]}")


@pytest.mark.parametrize("source, quote", list(records()))
def test_quote_is_in_source(source, quote):
    assert norm(quote) in source
