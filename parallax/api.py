"""Parallax API + static frontend server.

Run:  python -m parallax serve            (default :8000)
      uvicorn parallax.api:app            (production style)
"""

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import desc
from sqlalchemy.orm import Session

from .db import (
    ConsequenceRow, CoverageRow, FactRow, NumericRow, StoryRow, get_engine,
)
from .framing import LOADED_LEXICON

WEB_DIR = Path(__file__).resolve().parent.parent / "web"

app = FastAPI(title="Parallax", version="0.3")
_engine = None


def engine():
    global _engine
    if _engine is None:
        _engine = get_engine()
    return _engine


@app.get("/api/meta")
def meta():
    return {
        "categories": sorted(LOADED_LEXICON),
        "tiers": ["corroborated", "reported", "single-source"],
        "caveat": (
            "Corroboration is a weight, not truth: outlets may share one "
            "wire source. Every claim traces to who published it and when."
        ),
    }


@app.get("/api/stories")
def stories(q: str = ""):
    with Session(engine()) as s:
        query = s.query(StoryRow)
        if q:
            query = query.filter(StoryRow.label.ilike(f"%{q}%"))
        rows = query.order_by(desc(StoryRow.last_updated)).all()
        out = []
        for r in rows:
            n_disc = (
                s.query(NumericRow)
                .filter(NumericRow.story_id == r.id, NumericRow.agreement == 0)
                .count()
            )
            kinds = [
                c.kind for c in s.query(ConsequenceRow)
                .filter(ConsequenceRow.story_id == r.id).all()
            ]
            out.append({
                "id": r.id,
                "label": r.label,
                "divergence": r.divergence,
                "outlet_count": r.outlet_count,
                "last_updated": r.last_updated,
                "tracked_since": r.tracked_since,
                "discrepancies": n_disc,
                "consequence_kinds": sorted(set(kinds)),
            })
        return out


@app.get("/api/stories/{story_id}")
def story_detail(story_id: str):
    with Session(engine()) as s:
        r = s.get(StoryRow, story_id)
        if r is None:
            raise HTTPException(404, "story not found")
        from .velocity import compute_velocity
        out = {
            "id": r.id,
            "label": r.label,
            "divergence": r.divergence,
            "outlet_count": r.outlet_count,
            "tracked_since": r.tracked_since,
            "last_updated": r.last_updated,
            "divergent_labels": json.loads(r.divergent_labels),
            "caveat": r.caveat,
            "coverage": [
                {
                    "outlet": c.outlet, "placement": c.placement,
                    "title": c.title, "link": c.link,
                    "published": c.published,
                    "loaded_terms": json.loads(c.loaded_terms),
                    "labels_used": json.loads(c.labels_used),
                    "passive_voice": bool(c.passive_voice),
                }
                for c in s.query(CoverageRow)
                .filter(CoverageRow.story_id == r.id)
                .order_by(CoverageRow.published)
            ],
            "facts": [
                {
                    "text": f.text, "tier": f.tier,
                    "outlets": json.loads(f.outlets),
                    "first_seen": f.first_seen,
                }
                for f in s.query(FactRow)
                .filter(FactRow.story_id == r.id)
                .order_by(FactRow.first_seen)
            ],
            "numeric_claims": [
                {
                    "context": n.context,
                    "values": json.loads(n.values_json),
                    "agreement": bool(n.agreement),
                }
                for n in s.query(NumericRow)
                .filter(NumericRow.story_id == r.id)
            ],
            "consequences": [
                {
                    "type": c.kind, "description": c.description,
                    "outlets": json.loads(c.outlets),
                    "outlet_times": json.loads(c.outlet_times or "{}"),
                    "first_seen": c.first_seen,
                }
                for c in s.query(ConsequenceRow)
                .filter(ConsequenceRow.story_id == r.id)
                .order_by(ConsequenceRow.first_seen)
            ],
        }
        out["velocity"] = compute_velocity(out["coverage"], out["consequences"])
        return out


@app.get("/api/query")
def query(q: str):
    from .query import run_query
    if not q.strip():
        raise HTTPException(400, "empty query")
    return run_query(q.strip(), engine())


@app.get("/")
def index():
    return FileResponse(WEB_DIR / "index.html")


app.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")
