"""Load incoming incidents (from research or AI extraction) into the store: normalise, validate, de-duplicate.

Usage: python -m safety.ingest goa path/to/incoming.json [news|official|crowd]
Then run: python -m safety.verify goa   (checks every incident against its source)
"""
import json, sys

from safety.store import load, merge, normalise, save


def main(place, path, source_type="news"):
    incoming = json.loads(open(path).read())
    data = load(place)
    # Every incoming record must quote its source; a missing quote becomes "" so verify fails it.
    new = [normalise({**r, "quote": r.get("quote") or ""}, source_type) for r in incoming.get("incidents", [])]
    data["incidents"], rejected = merge(data["incidents"], new)
    for k in ("aggregates", "rules"):
        seen = {json.dumps(x, sort_keys=True) for x in data.get(k, [])}
        data[k] = data.get(k, []) + [x for x in incoming.get(k, []) if json.dumps(x, sort_keys=True) not in seen and x.get("source_url")]
    save(place, data)
    print(f"{len(new) - len(rejected)} accepted, {len(rejected)} rejected; store now has {len(data['incidents'])} incidents")
    for inc, why in rejected:
        print("  rejected:", inc.get("place"), inc.get("date"), why)


if __name__ == "__main__":
    main(*sys.argv[1:])
