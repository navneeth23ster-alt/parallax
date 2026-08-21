"""Framing analysis for a clustered story.

Everything here is observable-text-only. The tool flags:
  1. Loaded / evaluative terms (vs. neutral descriptors) per outlet
  2. Entity-label divergence: the same actor named differently
     (e.g. "regime" vs "government", "migrants" vs "illegal aliens")
  3. Voice: active attribution vs. agentless passive ("X killed Y"
     vs "Y died in clashes")

It deliberately does NOT infer intent, funding, or coordination —
those are claims text statistics cannot support.
"""

import re
from collections import Counter
from dataclasses import dataclass, field

from .cluster import Story

# Evaluative/loaded terms grouped by the effect they carry.
# Curated from media-linguistics literature (Fairclough, van Dijk) and
# style-guide debates (AP vs. house styles). Extend freely in lexicon terms.
LOADED_LEXICON = {
    "delegitimizing": [
        "regime", "junta", "cronies", "propaganda", "puppet", "so-called",
        "self-styled", "notorious", "disgraced", "embattled",
    ],
    "alarmist": [
        "chaos", "crisis", "catastrophe", "bloodbath", "onslaught", "surge",
        "flood", "invasion", "explosive", "bombshell", "shocking", "slams",
        "blasts", "erupts", "spirals",
    ],
    "sympathetic": [
        "heroic", "brave", "landmark", "historic", "long-awaited",
        "hard-won", "beleaguered", "defiant",
    ],
    "minimizing": [
        "merely", "just", "only", "so-called", "alleged", "claims",
        "supposed", "disputed",
    ],
    "militarized": [
        "war", "battle", "assault", "siege", "crusade", "showdown",
        "clash", "standoff",
    ],
}

# Common entity-label pairs where the choice itself encodes a stance.
CONTESTED_LABELS = [
    {"migrants", "immigrants", "illegal aliens", "asylum seekers", "illegals"},
    {"regime", "government", "administration"},
    {"protesters", "rioters", "demonstrators", "mob", "activists"},
    {"militants", "terrorists", "fighters", "rebels", "insurgents", "gunmen"},
    {"pro-life", "anti-abortion"},
    {"pro-choice", "abortion rights"},
    {"gun control", "gun safety", "gun rights"},
    {"climate change", "climate crisis", "global warming"},
    {"attack", "operation", "raid"},  # NB: no "strike" — labor strikes collide
    {"occupied", "disputed", "contested"},
]

PASSIVE_RE = re.compile(
    r"\b(was|were|is|are|been|being)\s+\w+ed\b|\b(dies?|died|killed)\s+in\b",
    re.IGNORECASE,
)


@dataclass
class OutletFraming:
    outlet: str
    owner: str
    title: str
    link: str = ""
    published: str = ""
    loaded_terms: dict = field(default_factory=dict)  # category -> [terms]
    labels_used: list = field(default_factory=list)
    passive_voice: bool = False


@dataclass
class StoryAnalysis:
    label: str
    outlets: list
    per_outlet: list  # list[OutletFraming]
    divergent_labels: list  # groups of contested labels seen across outlets
    loaded_term_counts: Counter

    def divergence_score(self) -> float:
        """0..1-ish heuristic: how differently is this event framed?"""
        n = max(len(self.per_outlet), 1)
        loaded_share = sum(
            1 for o in self.per_outlet if any(o.loaded_terms.values())
        ) / n
        label_signal = min(len(self.divergent_labels) * 0.35, 0.6)
        return round(min(loaded_share * 0.6 + label_signal, 1.0), 2)


def _find_terms(text: str, terms: list[str]) -> list[str]:
    low = f" {text.lower()} "
    return [t for t in terms if re.search(rf"\b{re.escape(t)}\b", low)]


def analyze_story(story: Story) -> StoryAnalysis:
    per_outlet: list[OutletFraming] = []
    all_labels_seen: dict[int, set] = {}
    counts: Counter = Counter()

    for h in story.headlines:
        text = f"{h.title} {h.summary}"
        loaded = {}
        for category, terms in LOADED_LEXICON.items():
            hits = _find_terms(text, terms)
            if hits:
                loaded[category] = hits
                counts.update(hits)

        labels = []
        for gi, group in enumerate(CONTESTED_LABELS):
            hits = _find_terms(text, sorted(group))
            if hits:
                labels.extend(hits)
                all_labels_seen.setdefault(gi, set()).update(hits)

        per_outlet.append(
            OutletFraming(
                outlet=h.outlet,
                owner=h.owner,
                title=h.title,
                link=h.link,
                published=h.published,
                loaded_terms=loaded,
                labels_used=labels,
                passive_voice=bool(PASSIVE_RE.search(h.title)),
            )
        )

    # A label group only shows *divergence* if outlets picked different terms
    divergent = [sorted(s) for s in all_labels_seen.values() if len(s) > 1]

    return StoryAnalysis(
        label=story.label,
        outlets=story.outlets,
        per_outlet=per_outlet,
        divergent_labels=divergent,
        loaded_term_counts=counts,
    )
