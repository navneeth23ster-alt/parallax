import json
from pathlib import Path

from parallax.cluster import cluster_headlines
from parallax.fetch import from_records
from parallax.framing import analyze_story
from parallax.reactions import reaction_signal

FIXTURE = Path(__file__).parent / "fixture_headlines.json"


def _headlines():
    return from_records(json.loads(FIXTURE.read_text(encoding="utf-8")))


def test_clusters_same_event_across_outlets():
    stories = cluster_headlines(_headlines())
    assert len(stories) >= 2
    border = next(s for s in stories if "border" in s.label.lower())
    assert {"AP", "Fox News"}.issubset(set(border.outlets))


def test_single_outlet_stories_dropped():
    stories = cluster_headlines(_headlines())
    assert all(len(s.outlets) >= 2 for s in stories)


def test_detects_contested_entity_labels():
    stories = cluster_headlines(_headlines())
    border = next(s for s in stories if "border" in s.label.lower())
    analysis = analyze_story(border)
    flat = {t for group in analysis.divergent_labels for t in group}
    assert "migrants" in flat and "illegal aliens" in flat


def test_flags_loaded_terms_by_category():
    stories = cluster_headlines(_headlines())
    border = next(s for s in stories if "border" in s.label.lower())
    analysis = analyze_story(border)
    fox = next(o for o in analysis.per_outlet if o.outlet == "Fox News")
    assert "alarmist" in fox.loaded_terms
    ap = next(o for o in analysis.per_outlet if o.outlet == "AP")
    assert not ap.loaded_terms


def test_reaction_signal_counts_terms():
    sig = reaction_signal(["Groups announced a protest and a boycott"])
    assert sig["mentions"] == 2
    assert "protest" in sig["reaction_terms"]


def test_divergence_score_bounded():
    for story in cluster_headlines(_headlines()):
        assert 0.0 <= analyze_story(story).divergence_score() <= 1.0


# --- consensus + timeline ---------------------------------------------
from parallax.consensus import build_consensus, neutralize
from parallax.timeline import TimelineStore, extract_consequences

DAY2 = Path(__file__).parent / "fixture_day2.json"


def _day2():
    return from_records(json.loads(DAY2.read_text(encoding="utf-8")))


def test_neutralize_maps_labels_and_strips_loaded():
    out = neutralize("Regime slams illegal aliens amid chaos")
    assert "government" in out and "migrants" in out
    assert "regime" not in out and "chaos" not in out and "slams" not in out


def test_consensus_tiers_require_placement_diversity():
    stories = cluster_headlines(_day2())
    border = next(s for s in stories if "border" in s.label.lower())
    rec = build_consensus(border)
    corroborated = [f for f in rec.facts if f.tier == "corroborated"]
    assert corroborated
    for f in corroborated:
        assert len(set(f.placements)) >= 2


def test_numeric_discrepancy_surfaced_not_averaged():
    stories = cluster_headlines(_day2())
    demo = next(s for s in stories if "toll" in s.label.lower())
    rec = build_consensus(demo)
    disputed = [n for n in rec.numeric_claims if len(n.values) >= 2]
    assert any(not n.agreement for n in disputed)


def test_consequences_report_what_started_only():
    stories = cluster_headlines(_day2())
    border = next(s for s in stories if "border" in s.label.lower())
    kinds = {e["type"] for e in extract_consequences(border)}
    assert "march" in kinds or "protest" in kinds
    # every event carries only observables: what, when, who reported
    for e in extract_consequences(border):
        assert set(e) == {"type", "description", "outlets", "first_seen"}


def test_protesters_noun_does_not_log_protest_event():
    hs = from_records([{
        "outlet": "X", "placement": "center",
        "title": "Protesters killed in clashes",
        "summary": "Several protesters were killed.",
        "link": "", "published": "2026-07-29T00:00:00Z",
    }])
    from parallax.cluster import Story
    assert extract_consequences(Story(headlines=hs)) == []


def test_timeline_merges_same_event_across_runs(tmp_path):
    store = TimelineStore(tmp_path / "tl.jsonl")
    day1 = cluster_headlines(_headlines())
    day2 = cluster_headlines(_day2())
    for s in day1:
        store.update(s, build_consensus(s))
    store.save()
    store2 = TimelineStore(tmp_path / "tl.jsonl")
    for s in day2:
        store2.update(s, build_consensus(s))
    store2.save()
    entries = TimelineStore(tmp_path / "tl.jsonl").entries
    border = [e for e in entries if "border" in e["label"].lower()]
    assert len(border) == 1          # merged, not duplicated
    assert border[0]["consequences"] # something started, and it's recorded
