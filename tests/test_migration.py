"""Reproduces the production failure from Actions run #22:
legacy timeline.jsonl entries (pre-v0.8 'placement' format, written by
runs #1-21) crashed db.sync with KeyError: 'owner'."""
import json
from pathlib import Path

from parallax.db import get_engine, sync, StoryRow, CoverageRow
from parallax.timeline import TimelineStore
from sqlalchemy.orm import Session

LEGACY_ENTRY = {
    # exactly what pre-v0.8 runs wrote: placement in coverage, placements
    # in facts, and (for the very oldest) no accumulated-coverage keys
    "id": "abc123def456",
    "label": "Old story from the US-feed era",
    "fingerprint": {"old": 3, "story": 2, "era": 1},
    "tracked_since": "2026-08-18T13:00:00+00:00",
    "last_updated": "2026-08-18T19:00:00+00:00",
    "outlet_count_latest": 2,
    "coverage": [
        {"outlet": "AP", "placement": "center",
         "title": "Something happened", "link": "", "published": "2026-08-18T12:00:00Z",
         "loaded_terms": {}, "labels_used": [], "passive_voice": False},
    ],
    "divergence": 0.4,
    "divergent_labels": [],
    "facts": [
        {"text": "something happened", "tier": "corroborated",
         "outlets": ["AP", "BBC"], "placements": ["center"],
         "first_seen": "2026-08-18T12:00:00Z", "logged_at": "2026-08-18T13:00:00+00:00"},
    ],
    "numeric": [],
    "consequences": [],
}

MINIMAL_ANCIENT_ENTRY = {
    # oldest possible shape: no coverage/divergence/numeric keys at all
    "id": "999888777666",
    "label": "Ancient minimal story",
    "fingerprint": {"ancient": 2, "minimal": 1},
    "tracked_since": "2026-08-18T13:00:00+00:00",
    "last_updated": "2026-08-18T13:00:00+00:00",
    "outlet_count_latest": 2,
    "facts": [],
    "consequences": [],
}


def _write_store(tmp_path: Path) -> Path:
    p = tmp_path / "timeline.jsonl"
    with p.open("w") as f:
        f.write(json.dumps(LEGACY_ENTRY) + "\n")
        f.write(json.dumps(MINIMAL_ANCIENT_ENTRY) + "\n")
    return p


def test_legacy_store_loads_normalized(tmp_path):
    store = TimelineStore(_write_store(tmp_path))
    assert len(store.entries) == 2
    legacy = store.entries[0]
    assert legacy["coverage"][0]["owner"] == "center"      # migrated key
    assert "placement" not in legacy["coverage"][0]
    assert legacy["facts"][0]["owners"] == ["center"]
    ancient = store.entries[1]
    assert ancient["coverage"] == [] and ancient["numeric"] == []


def test_legacy_store_syncs_without_keyerror(tmp_path):
    """The exact production crash: sync() over legacy entries."""
    store = TimelineStore(_write_store(tmp_path))
    engine = get_engine(f"sqlite:///{tmp_path}/t.db")
    n = sync(store.entries, engine=engine)
    assert n == 2
    with Session(engine) as s:
        cov = s.query(CoverageRow).one()
        assert cov.owner == "center"
        assert s.query(StoryRow).count() == 2


def test_raw_legacy_dict_direct_to_sync_is_also_safe(tmp_path):
    """Even unmigrated dicts can't crash sync (defense in depth)."""
    engine = get_engine(f"sqlite:///{tmp_path}/t2.db")
    n = sync([json.loads(json.dumps(LEGACY_ENTRY))], engine=engine)
    assert n == 1
