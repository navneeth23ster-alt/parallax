"""Track follow-on coverage momentum for a story across runs.

What this measures: how many outlets keep covering an event on
subsequent days, and whether reaction-type words (protest, boycott,
petition, backlash, walkout) enter the coverage — an observable signal
that a story has become a mobilizing event.

What this does NOT measure: who organized anything, whether reactions
were funded, or whether coordination occurred. Coverage velocity is a
proxy for public salience, nothing more. Treat spikes as leads for
human investigation, never as conclusions.
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path

REACTION_TERMS = [
    "protest", "boycott", "petition", "backlash", "walkout", "strike",
    "rally", "march", "campaign", "calls for resignation", "demands",
]

# suffixes limited to plural/verb forms: "protests" yes, "protesters" no
REACTION_RE = _REACTION_RE = re.compile(
    "|".join(rf"\b{re.escape(t)}(?:s|es|ed|ing)?\b" for t in REACTION_TERMS),
    re.IGNORECASE,
)


def reaction_signal(texts: list[str]) -> dict:
    hits = []
    for t in texts:
        hits.extend(m.group(0).lower() for m in _REACTION_RE.finditer(t))
    return {"reaction_terms": sorted(set(hits)), "mentions": len(hits)}


def append_run_log(store: Path, stories: list[dict]) -> None:
    """Append this run's story fingerprints so momentum is comparable
    across days. One JSON line per run."""
    store.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "stories": [
            {
                "label": s["label"],
                "outlet_count": len(s["outlets"]),
                "reaction": s.get("reaction", {}),
            }
            for s in stories
        ],
    }
    with store.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


def momentum(store: Path, label_query: str) -> list[dict]:
    """Coverage count over time for stories whose label matches query."""
    if not store.exists():
        return []
    points = []
    q = label_query.lower()
    for line in store.read_text(encoding="utf-8").splitlines():
        run = json.loads(line)
        for s in run["stories"]:
            if q in s["label"].lower():
                points.append(
                    {
                        "run_at": run["run_at"],
                        "outlet_count": s["outlet_count"],
                        "reaction_mentions": s.get("reaction", {}).get("mentions", 0),
                    }
                )
    return points
