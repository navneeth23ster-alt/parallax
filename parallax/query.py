"""Topic queries across everything Parallax has tracked.

A query matches stories by label, headline, fact text, or consequence
description, then aggregates across ALL matched stories and runs:

  - chronological record: corroborated/reported facts and consequence
    events merged into one timeline — what transpired, in order,
    each item traceable to who published it and when;
  - coverage volume per day (salience over time);
  - per-outlet framing profile: loaded-term category counts WITH
    denominators (headlines analyzed). These are observed counts in the
    matched sample under a public lexicon — an empirical description
    of word choice, not a bias rating of the outlet;
  - contested-label usage: which outlets chose which label.

The same epistemics apply as everywhere else: aggregation widens the
sample but cannot verify claims or infer intent.
"""

import json
from collections import Counter, defaultdict

from sqlalchemy import or_
from sqlalchemy.orm import Session

from .db import ConsequenceRow, CoverageRow, FactRow, NumericRow, StoryRow


def run_query(q: str, engine) -> dict:
    like = f"%{q}%"
    with Session(engine) as s:
        ids: set[str] = set()
        ids |= {r.id for r in s.query(StoryRow)
                .filter(StoryRow.label.ilike(like))}
        ids |= {r.story_id for r in s.query(CoverageRow)
                .filter(CoverageRow.title.ilike(like))}
        ids |= {r.story_id for r in s.query(FactRow)
                .filter(FactRow.text.ilike(like))}
        ids |= {r.story_id for r in s.query(ConsequenceRow)
                .filter(or_(ConsequenceRow.description.ilike(like),
                            ConsequenceRow.kind.ilike(like)))}
        if not ids:
            return {"query": q, "stories": [], "record": [], "volume": [],
                    "outlets": [], "labels": [], "discrepancies": []}

        stories = s.query(StoryRow).filter(StoryRow.id.in_(ids)).all()
        coverage = s.query(CoverageRow).filter(CoverageRow.story_id.in_(ids)).all()
        facts = s.query(FactRow).filter(FactRow.story_id.in_(ids)).all()
        conseq = s.query(ConsequenceRow).filter(ConsequenceRow.story_id.in_(ids)).all()
        numeric = s.query(NumericRow).filter(
            NumericRow.story_id.in_(ids), NumericRow.agreement == 0).all()
        label_of = {r.id: r.label for r in stories}

        # --- merged chronological record: facts + consequences
        record = []
        for f in facts:
            record.append({
                "kind": "fact", "tier": f.tier, "text": f.text,
                "when": f.first_seen, "outlets": json.loads(f.outlets),
                "story": label_of.get(f.story_id, ""),
            })
        for c in conseq:
            record.append({
                "kind": "consequence", "tier": c.kind, "text": c.description,
                "when": c.first_seen, "outlets": json.loads(c.outlets),
                "story": label_of.get(c.story_id, ""),
            })
        record.sort(key=lambda r: r["when"] or "9999")

        # --- coverage volume per day
        by_day: Counter = Counter()
        for c in coverage:
            if c.published:
                by_day[c.published[:10]] += 1
        volume = [{"date": d, "headlines": n} for d, n in sorted(by_day.items())]

        # --- per-outlet framing profile with denominators
        prof: dict[str, dict] = defaultdict(
            lambda: {"headlines": 0, "loaded": Counter(), "passive": 0,
                     "placement": ""})
        label_use: dict[str, set] = defaultdict(set)
        for c in coverage:
            p = prof[c.outlet]
            p["headlines"] += 1
            p["placement"] = c.placement
            p["passive"] += int(c.passive_voice)
            for cat, terms in json.loads(c.loaded_terms).items():
                p["loaded"][cat] += len(terms)
            for term in json.loads(c.labels_used):
                label_use[term].add(c.outlet)
        outlets = [
            {"outlet": o, "placement": p["placement"],
             "headlines": p["headlines"],
             "loaded": dict(p["loaded"]),
             "loaded_total": sum(p["loaded"].values()),
             "passive": p["passive"]}
            for o, p in prof.items()
        ]
        outlets.sort(key=lambda x: -x["headlines"])

        return {
            "query": q,
            "note": (
                "Counts are observed word choices in the matched sample "
                "under a public lexicon — a description of language use, "
                "not a rating of any outlet. Aggregation widens the sample; "
                "it does not verify claims or reveal intent."
            ),
            "stories": [
                {"id": r.id, "label": r.label,
                 "tracked_since": r.tracked_since,
                 "last_updated": r.last_updated,
                 "divergence": r.divergence}
                for r in sorted(stories, key=lambda r: r.tracked_since)
            ],
            "record": record,
            "volume": volume,
            "outlets": outlets,
            "labels": [
                {"term": t, "outlets": sorted(v)}
                for t, v in sorted(label_use.items())
            ],
            "discrepancies": [
                {"context": n.context, "values": json.loads(n.values_json),
                 "story": label_of.get(n.story_id, "")}
                for n in numeric
            ],
        }
