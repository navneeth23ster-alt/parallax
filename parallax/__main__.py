"""Parallax CLI.

  python -m parallax run                 # live fetch + full report
  python -m parallax run --fixture F     # analyze stored headlines (offline)
  python -m parallax momentum "query"    # coverage-over-time for a story
"""

import argparse
import json
from pathlib import Path

from .cluster import cluster_headlines
from .consensus import build_consensus
from .fetch import fetch_all, from_records
from .framing import analyze_story
from .reactions import append_run_log, momentum, reaction_signal
from .report import to_json, write_html, write_json, write_markdown
from .timeline import TimelineStore

DATA = Path("data")
REPORTS = Path("reports")


def cmd_run(args) -> None:
    if args.fixture:
        records = json.loads(Path(args.fixture).read_text(encoding="utf-8"))
        headlines = from_records(records)
        print(f"Loaded {len(headlines)} fixture headlines")
    else:
        headlines = fetch_all()
        print(f"Fetched {len(headlines)} headlines")
        (DATA / "raw").mkdir(parents=True, exist_ok=True)
        raw_path = DATA / "raw" / "latest.json"
        raw_path.write_text(
            json.dumps([h.to_dict() for h in headlines], indent=2),
            encoding="utf-8",
        )

    stories = cluster_headlines(headlines, min_outlets=args.min_outlets)
    print(f"Clustered into {len(stories)} multi-outlet stories")

    analyses = [analyze_story(s) for s in stories]
    reactions = [
        reaction_signal([f"{h.title} {h.summary}" for h in s.headlines])
        for s in stories
    ]
    payload = to_json(analyses, reactions)
    for p, r in zip(payload, reactions):
        p["reaction"] = r

    store = TimelineStore(DATA / "timeline.jsonl")
    for p, s in zip(payload, stories):
        record = build_consensus(s)
        p["consensus"] = {
            "caveat": record.caveat,
            "facts": [
                {"text": f.text, "tier": f.tier, "outlets": f.outlets,
                 "first_seen": f.first_seen}
                for f in record.facts
            ],
            "numeric_claims": [
                {"context": n.context, "values": n.values,
                 "agreement": n.agreement}
                for n in record.numeric_claims
            ],
        }
        entry = store.update(
            s, record,
            coverage=p["coverage"],
            divergence=p["divergence_score"],
            divergent_labels=p["divergent_labels"],
        )
        p["story_id"] = entry["id"]
        p["consequences_started"] = entry.get("_newly_started", [])
        p["consequences_all"] = entry["consequences"]
    store.save()

    from .db import sync
    n = sync(store.entries, payload)
    print(f"Synced {n} stories to database")

    REPORTS.mkdir(exist_ok=True)
    write_json(payload, REPORTS / "report.json")
    write_markdown(payload, REPORTS / "report.md")
    write_html(payload, REPORTS / "index.html")
    append_run_log(DATA / "runs.jsonl", payload)
    print(f"Wrote {REPORTS}/report.json, report.md, index.html")


def cmd_query(args) -> None:
    from .db import get_engine
    from .query import run_query
    r = run_query(args.query, get_engine())
    if not r["stories"]:
        print("No tracked coverage matches that query.")
        return
    span = (f'{r["volume"][0]["date"]} to {r["volume"][-1]["date"]}'
            if r["volume"] else "n/a")
    print(f'"{r["query"]}" — {len(r["stories"])} stories, '
          f'{sum(v["headlines"] for v in r["volume"])} headlines, {span}\n')
    print("Chronological record (facts + consequences, as reported):")
    for item in r["record"]:
        when = (item["when"] or "?")[:16]
        print(f'  [{item["tier"]:<12}] {when}  {item["text"][:90]}'
              f'  ({", ".join(item["outlets"])})')
    if r["discrepancies"]:
        print("\nUnresolved numeric discrepancies:")
        for d in r["discrepancies"]:
            vals = ", ".join(f"{o}: {v}" for o, v in d["values"].items())
            print(f'  “…{d["context"]}” — {vals}')
    print("\nFraming profile (observed counts / headlines analyzed):")
    for o in r["outlets"]:
        cats = ", ".join(f"{c}:{n}" for c, n in sorted(o["loaded"].items())) or "none"
        print(f'  {o["outlet"]:<18} {o["headlines"]} headlines · loaded terms: {cats}')
    print(f'\nNote: {r["note"]}')


def cmd_serve(args) -> None:
    import uvicorn
    uvicorn.run("parallax.api:app", host=args.host, port=args.port)


def cmd_timeline(args) -> None:
    store = TimelineStore(DATA / "timeline.jsonl")
    entries = store.show(args.query)
    if not entries:
        print("No tracked story matches that query.")
        return
    for e in entries:
        print(f"== {e['label']}")
        print(f"   tracked since {e['tracked_since']}, "
              f"last seen at {e['outlet_count_latest']} outlets")
        print("   -- factual record (corroboration-tiered, not verified truth):")
        for f in e["facts"]:
            when = f["first_seen"][:16] or "?"
            print(f"   [{f['tier']:<12}] {when}  {f['text']}"
                  f"  ({', '.join(f['outlets'])})")
        for n in e.get("numeric", []):
            tag = "agree" if n["agreement"] else "DISCREPANCY"
            vals = ", ".join(f"{o}: {v}" for o, v in n["values"].items())
            print(f"   [{tag:<12}] number near “…{n['context']}” — {vals}")
        if e["consequences"]:
            print("   -- consequences that started (as reported):")
            for c in e["consequences"]:
                when = (c["first_seen"] or c["logged_at"])[:16]
                print(f"   [{c['type']:<10}] {when}  {c['description']}"
                      f"  ({', '.join(c['outlets'])})")
        else:
            print("   -- no reported consequence events yet")
        print()


def cmd_momentum(args) -> None:
    points = momentum(DATA / "runs.jsonl", args.query)
    if not points:
        print("No matching stories in run log yet.")
        return
    for p in points:
        bar = "#" * p["outlet_count"]
        print(
            f"{p['run_at'][:16]}  outlets={p['outlet_count']:<3} "
            f"reaction-mentions={p['reaction_mentions']:<3} {bar}"
        )


def main() -> None:
    ap = argparse.ArgumentParser(prog="parallax")
    sub = ap.add_subparsers(dest="cmd", required=True)

    run = sub.add_parser("run", help="fetch, cluster, analyze, report")
    run.add_argument("--fixture", help="path to stored headlines JSON")
    run.add_argument("--min-outlets", type=int, default=2)
    run.set_defaults(fn=cmd_run)

    mom = sub.add_parser("momentum", help="coverage volume over time")
    mom.add_argument("query")
    mom.set_defaults(fn=cmd_momentum)

    tl = sub.add_parser("timeline", help="factual record + consequences for a story")
    tl.add_argument("query")
    tl.set_defaults(fn=cmd_timeline)

    qy = sub.add_parser("query", help="aggregate past+present analysis for a topic")
    qy.add_argument("query")
    qy.set_defaults(fn=cmd_query)

    srv = sub.add_parser("serve", help="start the web app")
    srv.add_argument("--host", default="127.0.0.1")
    srv.add_argument("--port", type=int, default=8000)
    srv.set_defaults(fn=cmd_serve)

    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
