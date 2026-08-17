"""Velocity: observable timing of coverage and reactions.

Three measurements, all computed from published timestamps:

  1. Reaction latency — hours between a story's first coverage and the
     first sighting of each consequence (protest, boycott, strike...).
  2. Simultaneity — how many outlets carried the reaction within 24h of
     its first sighting, and the spread (hours between the first and
     last outlet to carry it).
  3. Bursts — days whose headline count is anomalously high relative to
     the story's own median daily volume.

Epistemics, stated once and attached to every output: these are timing
facts about COVERAGE, not findings about actors. A fast, wide reaction
is consistent with organic virality, with wire-service propagation,
with organization, and with mixtures of all three. Velocity flags are
leads for human investigation — never conclusions about coordination,
and never evidence about any person or organization. Determining who
arranged anything requires platform-internal or financial evidence
that headline timestamps cannot contain.
"""

from datetime import datetime
from statistics import median

VELOCITY_NOTE = (
    "Timing facts about coverage, not findings about actors. Fast, wide "
    "reactions are consistent with organic virality, wire propagation, "
    "and organization alike — flags are leads for human investigation, "
    "never conclusions about coordination."
)

BURST_MIN_HEADLINES = 3      # a burst day needs at least this many
BURST_FACTOR = 2.0           # ...and >= factor x median of other days


def _parse(ts: str) -> datetime | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None


def _hours(a: datetime, b: datetime) -> float:
    return round((b - a).total_seconds() / 3600, 1)


def compute_velocity(coverage: list[dict], consequences: list[dict]) -> dict:
    """coverage: [{outlet, published, ...}]
    consequences: [{type, first_seen, outlets, outlet_times?, ...}]"""
    times = sorted(
        t for c in coverage if (t := _parse(c.get("published", "")))
    )
    first = times[0] if times else None

    reactions = []
    for c in consequences:
        fs = _parse(c.get("first_seen", ""))
        outlet_times = {
            o: t for o, raw in (c.get("outlet_times") or {}).items()
            if (t := _parse(raw))
        }
        within_24h = (
            sum(1 for t in outlet_times.values() if fs and _hours(fs, t) <= 24)
            if fs else 0
        )
        spread = (
            _hours(min(outlet_times.values()), max(outlet_times.values()))
            if len(outlet_times) >= 2 else 0.0
        )
        reactions.append({
            "type": c.get("type", ""),
            "first_seen": c.get("first_seen", ""),
            "latency_hours": _hours(first, fs) if first and fs else None,
            "outlets": c.get("outlets", []),
            "outlets_within_24h": within_24h,
            "spread_hours": spread,
        })
    reactions.sort(key=lambda r: (r["latency_hours"] is None,
                                  r["latency_hours"] or 0))

    by_day: dict[str, int] = {}
    for t in times:
        d = t.date().isoformat()
        by_day[d] = by_day.get(d, 0) + 1
    daily = [{"date": d, "headlines": n} for d, n in sorted(by_day.items())]

    bursts = []
    if len(daily) >= 2:
        for day in daily:
            others = [x["headlines"] for x in daily if x is not day]
            base = median(others)
            if (day["headlines"] >= BURST_MIN_HEADLINES
                    and base > 0
                    and day["headlines"] >= BURST_FACTOR * base):
                bursts.append({
                    "date": day["date"],
                    "headlines": day["headlines"],
                    "median_other_days": base,
                })

    return {
        "first_coverage": times[0].isoformat() if times else "",
        "reactions": reactions,
        "daily_volume": daily,
        "bursts": bursts,
        "note": VELOCITY_NOTE,
    }
