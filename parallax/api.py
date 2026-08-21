"""Parallax API + static frontend server.

Run:  python -m parallax serve            (default :8000)
      uvicorn parallax.api:app            (production style)
"""

import json
import os
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from .db import (
    ConsequenceRow, CoverageRow, FactRow, NumericRow, StoryRow, get_engine,
)
from .feedback import append as append_feedback, validate as validate_feedback
from .framing import LOADED_LEXICON

WEB_DIR = Path(__file__).resolve().parent.parent / "web"
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
QUERY_MAX_LEN = 100
FEED_PAGE_MAX = 100

limiter = Limiter(key_func=get_remote_address, default_limits=["120/minute"])
app = FastAPI(title="Parallax", version="0.9")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS: read-only public API, safe to open widely. Restrict via env if the
# frontend is ever split onto its own domain.
# Default CORS origins cover both the canonical domain and www.
# Override via CORS_ORIGINS env var (comma-separated) for custom setups.
_DEFAULT_ORIGINS = [
    "https://useparallax.net",
    "https://www.useparallax.net",
    "http://localhost:8000",   # local dev
    "http://127.0.0.1:8000",
]
_env = os.environ.get("CORS_ORIGINS", "")
_origins = [o.strip() for o in _env.split(",") if o.strip()] or _DEFAULT_ORIGINS
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

_engine = None
_start_time = time.time()


def engine():
    global _engine
    if _engine is None:
        _engine = get_engine()
    return _engine


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


def _clean_query(q: str) -> str:
    q = (q or "").strip()
    if len(q) > QUERY_MAX_LEN:
        q = q[:QUERY_MAX_LEN]
    return q


@app.get("/api/health")
def health():
    """Liveness + basic readiness: DB reachable, data not stale."""
    try:
        with Session(engine()) as s:
            count = s.query(func.count(StoryRow.id)).scalar()
            latest = s.query(func.max(StoryRow.last_updated)).scalar()
    except Exception as exc:
        return JSONResponse(
            status_code=503,
            content={"status": "error", "db_ok": False, "detail": str(exc)},
        )
    return {
        "status": "ok",
        "db_ok": True,
        "stories_tracked": count,
        "latest_run": latest,
        "uptime_seconds": round(time.time() - _start_time),
    }


@app.get("/api/meta")
@limiter.limit("60/minute")
def meta(request: Request):
    return {
        "categories": sorted(LOADED_LEXICON),
        "tiers": ["corroborated", "reported", "single-source"],
        "caveat": (
            "Corroboration is a weight, not truth: outlets may share one "
            "wire source. Every claim traces to who published it and when."
        ),
    }


@app.get("/api/stories")
@limiter.limit("60/minute")
def stories(request: Request, q: str = "", limit: int = 50, offset: int = 0):
    q = _clean_query(q)
    limit = max(1, min(limit, FEED_PAGE_MAX))
    offset = max(0, offset)
    with Session(engine()) as s:
        query = s.query(StoryRow)
        if q:
            query = query.filter(StoryRow.label.ilike(f"%{q}%"))
        total = query.count()
        rows = (
            query.order_by(desc(StoryRow.last_updated))
            .offset(offset).limit(limit).all()
        )
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
        return {"total": total, "limit": limit, "offset": offset, "stories": out}


@app.get("/api/stories/{story_id}")
@limiter.limit("60/minute")
def story_detail(request: Request, story_id: str):
    story_id = story_id[:16]
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
                    "outlet": c.outlet, "owner": c.owner,
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
@limiter.limit("30/minute")
def query(request: Request, q: str):
    from .query import run_query
    q = _clean_query(q)
    if not q:
        raise HTTPException(400, "empty query")
    return run_query(q, engine())


@app.post("/api/feedback")
@limiter.limit("10/minute")
def submit_feedback(request: Request, payload: dict):
    try:
        fb = validate_feedback(
            payload.get("category", ""),
            payload.get("message", ""),
            payload.get("story_id", ""),
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    append_feedback(DATA_DIR / "feedback.jsonl", fb)
    return {"status": "received"}


@app.get("/")
def index():
    return FileResponse(WEB_DIR / "index.html")


app.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")
