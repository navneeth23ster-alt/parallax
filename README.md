# Parallax

One event, every headline, side by side.

Parallax pulls headlines from major outlets' RSS feeds, groups the ones covering the same underlying event, and diffs the language: which evaluative words each outlet chose, how the same actors are labeled ("migrants" vs "illegal aliens", "government" vs "regime", "protesters" vs "rioters"), and whether headlines attribute actions or bury them in passive voice. The goal is to let a reader see the factual core of an event by comparing framings, rather than trusting any single one.

## What it measures — and what it can't

Parallax reports **text-observable signals only**:

- **Loaded-term usage** per outlet, categorized (alarmist, delegitimizing, sympathetic, minimizing, militarized) against a curated, editable lexicon in `parallax/framing.py`.
- **Entity-label divergence**: when different outlets pick different terms from a known contested pair for the same story.
- **Voice**: agentless passive constructions in headlines ("three died in clashes" vs "forces killed three").
- **Reaction vocabulary and coverage momentum**: whether words like protest/boycott/backlash enter coverage, and how many outlets keep covering a story across daily runs (`data/runs.jsonl`).
- **Consensus record**: fact atoms extracted from neutralized text (loaded terms stripped and marked with "…", contested labels mapped to neutral canonicals), tiered by corroboration — `corroborated` (2+ outlets from 2+ distinct ownership clusters), `reported` (2+ outlets within one ownership cluster), `single-source`. Numeric claims are cross-checked across outlets and disagreements are surfaced as `discrepancy`, never averaged. Corroboration is a weight, not truth: outlets often share one wire source, so even "corroborated" means independently published, not independently verified.
- **Timeline + consequence log** (`data/timeline.jsonl`): stories are fingerprinted (frequency-weighted vocabulary, cosine-matched across runs) so the same event accumulates a record over days. Each run appends newly corroborated facts with first-seen times, and consequence events — did a protest, boycott, strike, march, petition, or walkout start, when was it first reported, and by whom. A consequence entry means exactly that outlets reported it happened; nothing about who arranged it.

It deliberately does **not** infer intent, funding, or coordination behind any story or reaction. Coverage velocity and reaction vocabulary are proxies for public salience — leads for human investigation, never conclusions. Claims about who organized or paid for something require financial records and on-the-ground reporting; no headline statistic can establish them, and a tool that pretended otherwise would be producing exactly the kind of unearned opinion it exists to expose.

Outlets carry `owner` fields in `parallax/feeds.py` — ownership clusters as checkable public facts, used only to require independent confirmation for the `corroborated` tier (see `DESIGN.md`). The tool never scores outlets politically — it only compares their text. For the preserved global list (`feeds_global.py`), AllSides-derived lean tags are retained as display-only context since audited trackers exist for those outlets.

## Live at useparallax.net

Domain: `https://useparallax.net` (Cloudflare-managed)
Deployment: Render (Docker, auto-deploy on push to `main`)
Data: GitHub Actions runs every 6h, commits fresh `timeline.jsonl` + reports

CORS is open to `https://useparallax.net`, `https://www.useparallax.net`, and localhost for dev.
Override via `CORS_ORIGINS` env var (comma-separated) if needed.

## v1 region: Indian subcontinent

Default feeds (`parallax/feeds.py`) now target India, Pakistan, and Bangladesh — 22 outlets spanning establishment broadsheets, business press, independent/investigative digital-native outlets (Scroll.in, The Wire, The News Minute), regional English press, and international coverage of the region (BBC India desk, Al Jazeera). The original global feed list is preserved in `parallax/feeds_global.py` if you want to switch back or run both.

**Outlets carry ownership clusters, not political-lean labels.** See `DESIGN.md` (the independence-cluster model): corroboration measures independence of confirmation, and independence is an ownership fact, not a politics judgment. Each feed's `owner` field is a checkable public fact ("HT Media (Birla family)", "Network18 / Reliance Industries", "Foundation for Independent Journalism (nonprofit)"), and `corroborated` now requires confirmations from distinct ownership clusters — so sister publications (Hindustan Times + LiveMint, News18 + Moneycontrol, The Hindu + Business Line) correctly collapse to one voice. No political-lean ratings are assigned to Indian outlets, because no audited public tracker comparable to AllSides/Ad Fontes exists for Indian media; dated ownership facts (e.g. NDTV's Dec 2022 acquisition by Adani Group) are recorded in display-only `note` fields and readers weigh them themselves.

**Reaction vocabulary extended** (`parallax/reactions.py`) with subcontinent-specific protest terms not captured by the original English set: *bandh* (general strike/shutdown call), *hartal* (coordinated closure protest), *dharna* (sit-in protest), *gherao* (surround-and-blockade protest), *rasta roko* (road-blockade protest).

## Production hardening (v0.6)

- **Rate limiting** — per-IP limits on every endpoint (query 30/min, story/feed reads 60/min, feedback 10/min) via `slowapi`. Exceeding it returns `429`.
- **`/api/health`** — DB reachability, tracked story count, latest run timestamp, uptime. Point your host's health check here.
- **`/api/feedback`** (POST) — "report an issue" from any story page. Validated, length-capped, sanitized, append-only to `data/feedback.jsonl` (gitignored — a human reviews it; nothing auto-applies). No accounts required.
- **Security headers** — `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy` on every response. CORS open by default for the public read-only API; set `CORS_ORIGINS` to restrict if the frontend ever moves to its own domain.
- **Pagination** — `/api/stories` takes `limit`/`offset` (capped at 100) and returns `{total, limit, offset, stories}`.
- **Input validation** — query strings capped at 100 chars server-side; story IDs sanitized before DB lookup.

## Velocity — observable timing of reactions

```bash
python -m parallax velocity "border"
```

For each tracked story: reaction latency (hours between first coverage and the first sighting of each consequence), simultaneity (outlets carrying the reaction within 24h of first sighting, plus first-to-last spread), and burst days (headline count ≥ 2× the story's median daily volume, minimum 3). These are timing facts about coverage, not findings about actors: fast, wide reactions are consistent with organic virality, wire propagation, and organization alike. Velocity flags are leads for human investigation — never conclusions about coordination, and never evidence about any person or organization. Also exposed as `velocity` on `/api/stories/{id}` and rendered on the story page.

## Web app

```bash
python -m parallax run     # populate the database
python -m parallax serve   # http://127.0.0.1:8000
```

FastAPI backend (`parallax/api.py`) + static frontend (`web/`). The story page shows every outlet's headline with evaluative language marked in place (category-colored), contested-label diff pills, the corroboration-tiered factual record with numeric cross-checks, and the consequence log. Coverage accumulates per story across runs, so a story page is its history, not just today's snapshot.

Storage is SQLite by default (`data/parallax.db`), rebuilt idempotently from `data/timeline.jsonl` each run. Set `DATABASE_URL` (e.g. `postgresql+psycopg://...`) to use Postgres — no code changes. Deploy with the included `Dockerfile` (Fly.io, Render, Railway all work: the container refreshes data on start, then serves).

## Topic queries — past + present in one view

```bash
python -m parallax query "border"        # CLI digest
# or press Enter in the web app's search box
```

A query matches everything tracked so far — story labels, headlines, facts, consequence descriptions — and aggregates across all matched stories and runs: a chronological record merging tiered facts with consequence events (what transpired, in order, each item sourced), coverage volume per day, unresolved numeric discrepancies, per-outlet framing profiles with denominators (observed word-choice counts in the matched sample under the public lexicon — a description of language use, not a rating of any outlet), and contested-label choices by outlet. Backed by `/api/query?q=`.

## Quick start

```bash
pip install -r requirements.txt
python -m parallax run                # live fetch + report
python -m parallax run --fixture tests/fixture_headlines.json   # offline demo
python -m parallax momentum "border"  # coverage-over-time for a story
python -m parallax timeline "border"  # factual record + what started
pytest                                  # run tests
```

Outputs land in `reports/`: `index.html` (browsable comparison), `report.md`, and `report.json` (machine-readable). Each run appends a fingerprint to `data/runs.jsonl` so momentum is comparable across days.

## Scheduled runs

`.github/workflows/aggregate.yml` runs the aggregator every 6 hours on GitHub Actions and commits the refreshed reports back to the repo. Enable GitHub Pages on the `reports/` folder to get a public, always-current comparison page.

## Extending

- Add outlets in `parallax/feeds.py` (any RSS feed works).
- Add loaded terms or contested-label groups in `parallax/framing.py`. Keep entries defensible — every term should be one whose presence a reasonable editor would recognize as evaluative.
- Tune clustering in `parallax/cluster.py` (`similarity_threshold`, default 0.15; raise it if unrelated stories merge, lower it if the same event splits).

## License

MIT
