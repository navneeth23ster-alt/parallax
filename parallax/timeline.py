"""Persistent timeline: what transpired, and did anything start.

Stories are fingerprinted so the same event matches across daily runs.
Each run appends:
  - fact atoms newly reaching "corroborated"/"reported" tier, and
  - consequence events: a reaction (protest, boycott, strike, rally,
    petition, walkout, march...) newly appearing in the story's
    coverage — answering "did anything start, and what was it",
    with first-seen time and which outlets reported it.

No inference is made about who started anything or why. A consequence
entry means exactly: outlets began reporting that this happened.
"""

import hashlib
import json
import re
from collections import Counter
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from .cluster import Story
from .consensus import ConsensusRecord, _STOP, _tokens, neutralize
from .reactions import REACTION_RE as _REACTION_RE
_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")


def fingerprint(story: Story) -> dict[str, int]:
    """Frequency-weighted content vocabulary from titles AND summaries.
    Frequency matters: an event's core words (the place, the policy, the
    actors) repeat across every outlet's coverage, so they dominate the
    vector even as day-to-day wording shifts."""
    counts: Counter = Counter()
    for h in story.headlines:
        counts.update(
            t for t in _tokens(neutralize(f"{h.title}. {h.summary}"))
            if t not in _STOP and len(t) > 2
        )
    return dict(counts.most_common(60))


def _cosine(a: dict[str, int], b: dict[str, int]) -> float:
    shared = set(a) & set(b)
    if not shared:
        return 0.0
    dot = sum(a[t] * b[t] for t in shared)
    na = sum(v * v for v in a.values()) ** 0.5
    nb = sum(v * v for v in b.values()) ** 0.5
    return dot / (na * nb) if na and nb else 0.0


# Cross-run match threshold. Tradeoff: lower -> follow-up coverage of the
# same event merges reliably, but two distinct incidents of the same TYPE
# (e.g. two separate shootings) risk merging. Raise if that happens.
MATCH_THRESHOLD = 0.22


def _match(fp: dict[str, int], stored: dict[str, int]) -> bool:
    return _cosine(fp, stored) >= MATCH_THRESHOLD


def extract_consequences(story: Story) -> list[dict]:
    """Reaction events visible in this story's coverage right now."""
    events: dict[str, dict] = {}
    for h in story.headlines:
        for sent in _SENT_SPLIT.split(f"{h.title}. {h.summary}"):
            m = _REACTION_RE.search(sent)
            if not m:
                continue
            kind = m.group(0).lower().rstrip("s")
            desc = neutralize(sent, mark_elisions=True)[:160]
            ev = events.setdefault(
                kind,
                {"type": kind, "description": desc, "outlets": [],
                 "outlet_times": {}, "first_seen": h.published or ""},
            )
            if h.outlet not in ev["outlets"]:
                ev["outlets"].append(h.outlet)
            if h.published:
                ot = ev["outlet_times"]
                if h.outlet not in ot or h.published < ot[h.outlet]:
                    ot[h.outlet] = h.published
            if h.published and (not ev["first_seen"] or h.published < ev["first_seen"]):
                ev["first_seen"] = h.published
                ev["description"] = desc
    return list(events.values())


class TimelineStore:
    """JSONL store: one document per tracked story, rewritten per run."""

    def __init__(self, path: Path):
        self.path = path
        self.entries: list[dict] = []
        if path.exists():
            self.entries = [
                json.loads(line)
                for line in path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]

    def _find(self, fp: set[str]) -> dict | None:
        for e in self.entries:
            if _match(fp, e["fingerprint"]):
                return e
        return None

    def update(
        self,
        story: Story,
        record: ConsensusRecord,
        coverage: list[dict] | None = None,
        divergence: float = 0.0,
        divergent_labels: list | None = None,
    ) -> dict:
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        fp = fingerprint(story)
        entry = self._find(fp)
        if entry is None:
            entry = {
                "id": hashlib.sha1(
                    f"{record.label}|{now}".encode()
                ).hexdigest()[:12],
                "label": record.label,
                "fingerprint": dict(fp),
                "tracked_since": now,
                "facts": [],
                "consequences": [],
                "numeric": [],
                "coverage": [],
                "divergence": 0.0,
                "divergent_labels": [],
            }
            self.entries.append(entry)
        merged = Counter(entry["fingerprint"]) + Counter(fp)
        entry["fingerprint"] = dict(merged.most_common(60))
        entry["last_updated"] = now
        entry["outlet_count_latest"] = len(story.outlets)

        # coverage accumulates across runs (a story page shows its history)
        entry.setdefault("coverage", [])
        seen = {(c["outlet"], c["title"]) for c in entry["coverage"]}
        for c in coverage or []:
            if (c["outlet"], c["title"]) not in seen:
                entry["coverage"].append(c)
        # divergence: keep the peak observed; label groups: union
        entry["divergence"] = max(entry.get("divergence", 0.0), divergence)
        groups = {frozenset(g) for g in entry.get("divergent_labels", [])}
        for g in divergent_labels or []:
            groups.add(frozenset(g))
        entry["divergent_labels"] = [sorted(g) for g in groups]

        known_facts = {f["text"] for f in entry["facts"]}
        for atom in record.facts:
            if atom.tier == "single-source" or atom.text in known_facts:
                continue
            d = asdict(atom)
            d["logged_at"] = now
            entry["facts"].append(d)

        # latest cross-checked numeric claims; disagreements matter most
        entry["numeric"] = [
            {"context": n.context, "values": n.values, "agreement": n.agreement}
            for n in record.numeric_claims
            if len(n.values) >= 2
        ]

        existing = {c["type"]: c for c in entry["consequences"]}
        started = []
        for ev in extract_consequences(story):
            cur = existing.get(ev["type"])
            if cur is None:
                ev["logged_at"] = now
                entry["consequences"].append(ev)
                started.append(ev)
                continue
            # merge: outlets accumulate, per-outlet times keep the earliest
            for o in ev["outlets"]:
                if o not in cur["outlets"]:
                    cur["outlets"].append(o)
            ot = cur.setdefault("outlet_times", {})
            for o, t in ev.get("outlet_times", {}).items():
                if t and (o not in ot or t < ot[o]):
                    ot[o] = t
            if ev["first_seen"] and (
                not cur["first_seen"] or ev["first_seen"] < cur["first_seen"]
            ):
                cur["first_seen"] = ev["first_seen"]
                cur["description"] = ev["description"]
        entry["_newly_started"] = started  # transient, for this run's report
        return entry

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as f:
            for e in self.entries:
                e = {k: v for k, v in e.items() if not k.startswith("_")}
                f.write(json.dumps(e) + "\n")

    def show(self, query: str) -> list[dict]:
        q = query.lower()
        return [e for e in self.entries if q in e["label"].lower()]
