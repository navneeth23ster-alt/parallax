import json
from pathlib import Path

from parallax.cluster import cluster_headlines
from parallax.consensus import build_consensus
from parallax.fetch import from_records
from parallax.timeline import TimelineStore
from parallax.velocity import compute_velocity

FIX = Path(__file__).parent


def test_latency_and_simultaneity_math():
    coverage = [{"outlet": "A", "published": "2026-01-01T06:00:00Z"},
                {"outlet": "B", "published": "2026-01-01T08:00:00Z"}]
    conseq = [{"type": "protest", "first_seen": "2026-01-01T09:00:00Z",
               "outlets": ["B", "C"],
               "outlet_times": {"B": "2026-01-01T09:00:00Z",
                                "C": "2026-01-01T15:30:00Z"}}]
    v = compute_velocity(coverage, conseq)
    r = v["reactions"][0]
    assert r["latency_hours"] == 3.0
    assert r["outlets_within_24h"] == 2
    assert r["spread_hours"] == 6.5


def test_burst_requires_min_and_factor():
    cov = ([{"outlet": "A", "published": f"2026-01-01T0{i}:00:00Z"} for i in range(1, 7)]
           + [{"outlet": "A", "published": "2026-01-02T01:00:00Z"},
              {"outlet": "A", "published": "2026-01-02T02:00:00Z"}])
    v = compute_velocity(cov, [])
    assert len(v["bursts"]) == 1 and v["bursts"][0]["date"] == "2026-01-01"
    # two quiet days: no burst
    v2 = compute_velocity(cov[-2:] + cov[-2:], [])
    assert v2["bursts"] == []


def test_no_actor_claims_in_output():
    v = compute_velocity([], [])
    assert "leads for human investigation" in v["note"]
    assert "coordination" in v["note"]  # explicitly disclaimed


def test_two_day_simulation_end_to_end(tmp_path):
    store = TimelineStore(tmp_path / "tl.jsonl")
    for fx in ("fixture_headlines.json", "fixture_day2.json"):
        hs = from_records(json.loads((FIX / fx).read_text()))
        for story in cluster_headlines(hs):
            cov = [{"outlet": h.outlet, "owner": h.owner,
                    "title": h.title, "link": "", "published": h.published,
                    "loaded_terms": {}, "labels_used": [],
                    "passive_voice": False} for h in story.headlines]
            store.update(story, build_consensus(story), coverage=cov)
    store.save()
    border = [e for e in store.entries if "border" in e["label"].lower()][0]
    v = compute_velocity(border["coverage"], border["consequences"])
    protest = next(r for r in v["reactions"] if r["type"] == "protest")
    assert protest["latency_hours"] == 1.5
    assert len(protest["outlets"]) == 2  # merged across days
