import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import parallax.api as api_mod
from parallax.cluster import cluster_headlines
from parallax.consensus import build_consensus
from parallax.db import get_engine, sync
from parallax.fetch import from_records
from parallax.timeline import TimelineStore

FIX = Path(__file__).parent


@pytest.fixture()
def client(tmp_path, monkeypatch):
    engine = get_engine(f"sqlite:///{tmp_path}/t.db")
    store = TimelineStore(tmp_path / "tl.jsonl")
    for fixture in ("fixture_headlines.json", "fixture_day2.json"):
        hs = from_records(json.loads((FIX / fixture).read_text()))
        for story in cluster_headlines(hs):
            rec = build_consensus(story)
            cov = [
                {"outlet": h.outlet, "owner": h.owner,
                 "title": h.title, "link": h.link, "published": h.published,
                 "loaded_terms": {}, "labels_used": [], "passive_voice": False}
                for h in story.headlines
            ]
            store.update(story, rec, coverage=cov, divergence=0.5,
                         divergent_labels=[["migrants", "illegal aliens"]])
    store.save()
    sync(store.entries, engine=engine)
    monkeypatch.setattr(api_mod, "_engine", engine)
    return TestClient(api_mod.app)


def test_feed_lists_stories_with_signals(client):
    data = client.get("/api/stories").json()
    assert data["total"] == 2
    border = next(s for s in data["stories"] if "border" in s["label"].lower())
    assert border["outlet_count"] >= 2
    assert "boycott" in border["consequence_kinds"]


def test_feed_search_filters(client):
    data = client.get("/api/stories", params={"q": "border"}).json()
    assert data["total"] == 1 and len(data["stories"]) == 1


def test_feed_pagination(client):
    page1 = client.get("/api/stories", params={"limit": 1, "offset": 0}).json()
    page2 = client.get("/api/stories", params={"limit": 1, "offset": 1}).json()
    assert len(page1["stories"]) == 1 and len(page2["stories"]) == 1
    assert page1["stories"][0]["id"] != page2["stories"][0]["id"]
    assert page1["total"] == 2


def test_feed_limit_is_capped(client):
    data = client.get("/api/stories", params={"limit": 99999}).json()
    assert data["limit"] <= 100


def test_health_reports_story_count(client):
    h = client.get("/api/health").json()
    assert h["status"] == "ok" and h["stories_tracked"] == 2


def test_security_headers_present(client):
    r = client.get("/api/health")
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["x-frame-options"] == "DENY"


def test_feedback_accepts_valid_submission(client):
    r = client.post("/api/feedback", json={
        "category": "wrong-loaded-term", "message": "the word X isn't loaded",
        "story_id": "abc123",
    })
    assert r.status_code == 200 and r.json()["status"] == "received"


def test_feedback_rejects_empty_message(client):
    r = client.post("/api/feedback", json={"category": "other", "message": "  "})
    assert r.status_code == 400


def test_feedback_sanitizes_unknown_category(client):
    from parallax.feedback import validate
    fb = validate("nonsense-category", "a real issue description")
    assert fb.category == "other"


def test_query_length_is_capped(client):
    long_q = "a" * 500
    r = client.get("/api/query", params={"q": long_q})
    assert r.status_code == 200  # doesn't error, just truncates server-side


def test_detail_carries_full_evidence(client):
    sid = client.get("/api/stories").json()["stories"][0]["id"]
    d = client.get(f"/api/stories/{sid}").json()
    assert d["coverage"] and d["caveat"]
    for f in d["facts"]:
        assert f["tier"] in {"corroborated", "reported", "single-source"}


def test_coverage_accumulates_across_runs(client):
    data = client.get("/api/stories").json()["stories"]
    border = next(s for s in data if "border" in s["label"].lower())
    d = client.get(f"/api/stories/{border['id']}").json()
    published = {c["published"][:10] for c in d["coverage"]}
    assert len(published) == 2  # both simulated days present


def test_detail_404(client):
    assert client.get("/api/stories/nope").status_code == 404


def test_meta_exposes_lexicon_categories(client):
    m = client.get("/api/meta").json()
    assert "alarmist" in m["categories"]


def test_query_aggregates_across_history(client):
    r = client.get("/api/query", params={"q": "border"}).json()
    assert r["stories"]
    kinds = {i["kind"] for i in r["record"]}
    assert kinds == {"fact", "consequence"}
    whens = [i["when"] for i in r["record"] if i["when"]]
    assert whens == sorted(whens)                 # chronological
    assert len({v["date"] for v in r["volume"]}) == 2  # both days
    for o in r["outlets"]:
        assert o["headlines"] >= 1                # denominators present
    assert "not a rating" in r["note"]


def test_query_no_match_is_empty_not_error(client):
    r = client.get("/api/query", params={"q": "zzzunmatched"}).json()
    assert r["stories"] == [] and r["record"] == []


def test_query_empty_string_rejected(client):
    assert client.get("/api/query", params={"q": "  "}).status_code == 400
