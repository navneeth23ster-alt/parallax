"""Build a corroboration-tiered factual record for a clustered story.

Method:
  1. Neutralize each outlet's text: strip loaded terms, map contested
     entity labels to a neutral canonical.
  2. Extract fact atoms two ways:
     - shared phrases: longest common word runs (>=3 content tokens)
       between outlet pairs, grouped and counted;
     - numeric claims: numbers with their local context, cross-checked
       across outlets so disagreements are surfaced, never averaged.
  3. Tier every atom by corroboration breadth AND outlet diversity:
       corroborated   2+ outlets spanning 2+ placement groups
       reported       2+ outlets, single placement group
       single-source  1 outlet
  4. Order atoms by earliest supporting timestamp -> story timeline.

Honesty note baked into every output: corroboration is a weight, not
truth. Outlets frequently share one wire source (AP/Reuters/AFP), so
even "corroborated" means "independently published", not
"independently verified". The record is a probable-fact ledger with
its evidence attached, so a reader can always trace an atom back to
who said it and when.
"""

import re
from collections import defaultdict
from dataclasses import dataclass, field
from difflib import SequenceMatcher

from .cluster import Story
from .framing import CONTESTED_LABELS, LOADED_LEXICON

# Neutral canonical for each contested-label group (index-aligned with
# CONTESTED_LABELS in framing.py).
NEUTRAL_CANONICAL = [
    "migrants",
    "government",
    "demonstrators",
    "armed group members",
    "abortion opponents",
    "abortion-rights supporters",
    "gun policy",
    "climate change",
    "military action",  # attack/operation/raid group
    "disputed territory",
]

_ALL_LOADED = sorted(
    {t for terms in LOADED_LEXICON.values() for t in terms},
    key=len,
    reverse=True,
)

_STOP = set(
    """a an the of in on at to for with by from as is are was were be been
    and or but that this these those it its his her their our your new said
    says say after amid over under about""".split()
)

_NUM_RE = re.compile(r"\b(\d[\d,.]*)\b")


def neutralize(text: str, mark_elisions: bool = False) -> str:
    """Map contested labels to neutral canonicals; strip loaded terms.
    With mark_elisions=True, stripped terms leave a visible "…" so a
    reader can tell evaluative language was removed, not silently lost."""
    low = text.lower()
    for gi, group in enumerate(CONTESTED_LABELS):
        canon = NEUTRAL_CANONICAL[gi]
        for term in sorted(group, key=len, reverse=True):
            low = re.sub(rf"\b{re.escape(term)}\b", canon, low)
    gap = " … " if mark_elisions else " "
    for term in _ALL_LOADED:
        low = re.sub(rf"\b{re.escape(term)}\b", gap, low)
    low = re.sub(r"(?:\s*…\s*)+", " … ", low)
    return re.sub(r"[ \t]+", " ", low).strip()


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9][a-z0-9'-]*", text)


def _content_count(tokens: list[str]) -> int:
    return sum(1 for t in tokens if t not in _STOP)


@dataclass
class FactAtom:
    text: str
    outlets: list[str]
    placements: list[str]
    first_seen: str  # earliest published timestamp among supporters
    tier: str = "single-source"

    def retier(self) -> None:
        if len(self.outlets) >= 2 and len(set(self.placements)) >= 2:
            self.tier = "corroborated"
        elif len(self.outlets) >= 2:
            self.tier = "reported"
        else:
            self.tier = "single-source"


@dataclass
class NumericClaim:
    context: str                 # e.g. "killed", "policy takes effect"
    values: dict = field(default_factory=dict)  # outlet -> value string

    @property
    def agreement(self) -> bool:
        return len(set(self.values.values())) == 1


@dataclass
class ConsensusRecord:
    label: str
    facts: list[FactAtom]
    numeric_claims: list[NumericClaim]
    caveat: str = (
        "Corroboration is a weight, not truth: outlets may share one "
        "wire source. Every atom links back to who published it and when."
    )


def _shared_runs(a: list[str], b: list[str], min_content: int = 3) -> list[str]:
    """Longest common word runs between two token lists."""
    out = []
    for m in SequenceMatcher(None, a, b, autojunk=False).get_matching_blocks():
        if m.size >= min_content:
            run = a[m.a : m.a + m.size]
            if _content_count(run) >= min_content:
                out.append(" ".join(run))
    return out


def _dedupe_subsumed(phrases: list[str]) -> list[str]:
    keep = []
    for p in sorted(phrases, key=len, reverse=True):
        if not any(p in longer for longer in keep):
            keep.append(p)
    return keep


def build_consensus(story: Story) -> ConsensusRecord:
    per_outlet = []
    for h in story.headlines:
        per_outlet.append(
            {
                "outlet": h.outlet,
                "placement": h.placement,
                "published": h.published,
                "tokens": _tokens(neutralize(f"{h.title}. {h.summary}")),
            }
        )

    # --- shared phrases across outlet pairs -> fact atoms
    support: dict[str, set[tuple[str, str, str]]] = defaultdict(set)
    for i in range(len(per_outlet)):
        for j in range(i + 1, len(per_outlet)):
            oi, oj = per_outlet[i], per_outlet[j]
            if oi["outlet"] == oj["outlet"]:
                continue
            for phrase in _shared_runs(oi["tokens"], oj["tokens"]):
                for o in (oi, oj):
                    support[phrase].add(
                        (o["outlet"], o["placement"], o["published"])
                    )

    atoms: list[FactAtom] = []
    for phrase in _dedupe_subsumed(list(support)):
        sup = support[phrase]
        # fold in support recorded only under longer/shorter variants
        for other, osup in support.items():
            if phrase != other and phrase in other:
                sup = sup | osup
        outlets = sorted({s[0] for s in sup})
        placements = sorted({s[1] for s in sup})
        stamps = sorted(s[2] for s in sup if s[2])
        atom = FactAtom(
            text=phrase,
            outlets=outlets,
            placements=placements,
            first_seen=stamps[0] if stamps else "",
        )
        atom.retier()
        atoms.append(atom)

    # single-source numeric or headline-only material stays out of the
    # phrase atoms by construction; the numeric pass below catches the
    # numbers so lone claims are still visible, just tiered honestly.

    # --- numeric claims, cross-checked
    numeric: dict[str, NumericClaim] = {}
    for o, h in zip(per_outlet, story.headlines):
        text = neutralize(f"{h.title}. {h.summary}")
        toks = _tokens(text)
        for idx, tok in enumerate(toks):
            if _NUM_RE.fullmatch(tok):
                ctx = " ".join(
                    t for t in toks[idx + 1 : idx + 4] if t not in _STOP
                )[:40]
                if not ctx:
                    continue
                claim = numeric.setdefault(ctx, NumericClaim(context=ctx))
                claim.values[o["outlet"]] = tok

    atoms.sort(key=lambda a: (a.first_seen or "9999", -len(a.outlets)))
    return ConsensusRecord(
        label=story.label,
        facts=atoms,
        numeric_claims=list(numeric.values()),
    )
