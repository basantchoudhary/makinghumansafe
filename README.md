# Making Human Safe

**Someone is waiting for you.** Search any place and see what affects your safety there:
past incidents, live alerts, help nearby, precautions and fair prices, with a source and a date for every fact.

Website: https://makinghumansafe.com (early preview; the full design is being built).

> **Not an emergency service.** In danger, call your local emergency number (112 in India and Europe,
> 911 in the US, 000 in Australia). We show what is known, with sources; a place with no reports is not proven safe.

## How it works

1. **Collect** public information: official alerts, statistics, news and visitor reports.
2. **Check** every fact: each incident keeps its source link and a word-for-word quote, and plain code
   confirms the quote is in the source before anything is published. AI may propose; code decides.
3. **Connect** facts to places, spots, causes, seasons and people.
4. **Serve** only what affects you, on static pages that load fast anywhere.

## Run

```bash
python3 -m venv .venv && .venv/bin/pip install duckdb   # duckdb is needed for help-nearby (Overture maps)
.venv/bin/python -m safety.fetch goa          # wikivoyage, alerts, help, feeds, news (news = GDELT history, slow)
python3 -m safety.fetch goa feeds             # local paper RSS only (fast; run daily, history accumulates)
python3 -m safety.extract goa                 # AI (Groq; put GROQ_API_KEY in .env) proposes incidents, each with a quote
python3 -m safety.verify goa                  # plain-rule check: place, event word and quote must be in the source
python3 -m safety.site                        # builds site/ (static pages)
open site/goa/index.html
```

## Layout

- `places.toml`: places, their spots, Wikivoyage page, alert keywords, news queries
- `fares/<place>.toml`: hand-collected fare facts, each with a source link and date
- `safety/fetch.py`: one fetcher per source, raw results in `data/<place>/`
- `safety/extract.py`: news article to incident records (AI proposes; must name the state and quote the article)
- `safety/verify.py`: deterministic evidence check; only `checked` incidents are published
- `safety/spotcheck.py`: checks every spot's map point against Wikidata; disagreements use the Wikidata point
- `safety/ingest.py`: loads researched incidents (`data/_incoming/<place>.json`, each with a quote) into the store
- `data/_corpus/`: researched incident lists (e.g. water incidents), each record with source and quote
- `scripts/refresh.sh` + launchd plist: feeds, extraction, verify and site build 4 times a day
- `safety/site.py`: static site generator into `site/`

## Rules

Source and date on every fact. Nothing invented: no data means the page says so.
Never a "safe" score. No victims' names. Placeholder map points with rounded coordinates are skipped.
Full article copies are never stored in the repo (only short quotes with links).

## Data and credits

Each source keeps its own licence. Examples: Wikivoyage text (CC BY-SA 4.0, credited per page),
Overture Maps places (CDLA Permissive 2.0 / ODbL parts), OpenStreetMap (ODbL), NDMA SACHET alerts,
news reports (short quotes with links to the publisher). Found a mistake? Open an issue and we will correct it openly.
