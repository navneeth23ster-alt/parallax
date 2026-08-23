"""Read-optimized database view of the pipeline's output.

The timeline store (data/timeline.jsonl) remains the durable source of
truth; each run rebuilds the DB view from it plus the latest payload's
coverage. That keeps sync idempotent and trivially correct.

SQLite by default. Set DATABASE_URL (e.g. postgresql+psycopg://...)
to use Postgres — no code changes needed.
"""

import json
import os

from sqlalchemy import Column, Float, ForeignKey, Integer, String, Text, create_engine
from sqlalchemy.orm import Session, declarative_base, relationship

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///data/parallax.db")

Base = declarative_base()


class StoryRow(Base):
    __tablename__ = "stories"
    id = Column(String(16), primary_key=True)
    label = Column(Text, nullable=False)
    divergence = Column(Float, default=0.0)
    outlet_count = Column(Integer, default=0)
    tracked_since = Column(String(32))
    last_updated = Column(String(32))
    divergent_labels = Column(Text, default="[]")   # JSON
    caveat = Column(Text, default="")
    coverage = relationship("CoverageRow", cascade="all, delete-orphan")
    facts = relationship("FactRow", cascade="all, delete-orphan")
    numeric = relationship("NumericRow", cascade="all, delete-orphan")
    consequences = relationship("ConsequenceRow", cascade="all, delete-orphan")


class CoverageRow(Base):
    __tablename__ = "coverage"
    id = Column(Integer, primary_key=True)
    story_id = Column(String(16), ForeignKey("stories.id"))
    outlet = Column(String(64))
    owner = Column(String(32))
    title = Column(Text)
    link = Column(Text, default="")
    published = Column(String(32), default="")
    loaded_terms = Column(Text, default="{}")       # JSON: category -> [terms]
    labels_used = Column(Text, default="[]")        # JSON
    passive_voice = Column(Integer, default=0)


class FactRow(Base):
    __tablename__ = "facts"
    id = Column(Integer, primary_key=True)
    story_id = Column(String(16), ForeignKey("stories.id"))
    text = Column(Text)
    tier = Column(String(16))
    outlets = Column(Text, default="[]")            # JSON
    first_seen = Column(String(32), default="")


class NumericRow(Base):
    __tablename__ = "numeric_claims"
    id = Column(Integer, primary_key=True)
    story_id = Column(String(16), ForeignKey("stories.id"))
    context = Column(Text)
    values_json = Column(Text, default="{}")        # JSON: outlet -> value
    agreement = Column(Integer, default=1)


class ConsequenceRow(Base):
    __tablename__ = "consequences"
    id = Column(Integer, primary_key=True)
    story_id = Column(String(16), ForeignKey("stories.id"))
    kind = Column(String(32))
    description = Column(Text)
    outlets = Column(Text, default="[]")            # JSON
    outlet_times = Column(Text, default="{}")       # JSON: outlet -> ISO time
    first_seen = Column(String(32), default="")


def get_engine(url: str | None = None):
    url = url or DATABASE_URL
    if url.startswith("sqlite:///"):
        os.makedirs(os.path.dirname(url.removeprefix("sqlite:///")) or ".", exist_ok=True)
    engine = create_engine(url, future=True)
    Base.metadata.create_all(engine)
    return engine


CAVEAT = (
    "Corroboration is a weight, not truth: outlets may share one wire "
    "source. Every claim traces to who published it and when."
)


def sync(timeline_entries: list[dict], payload: list[dict] | None = None,
         engine=None) -> int:
    """Rebuild the DB view from timeline entries (coverage, divergence and
    label groups accumulate on the entries themselves)."""
    engine = engine or get_engine()
    # DB is a rebuildable view: recreate tables so schema changes apply
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        for e in timeline_entries:
            row = StoryRow(
                id=e["id"],
                label=e["label"],
                divergence=e.get("divergence", 0.0),
                outlet_count=e.get("outlet_count_latest", 0),
                tracked_since=e.get("tracked_since", ""),
                last_updated=e.get("last_updated", ""),
                divergent_labels=json.dumps(e.get("divergent_labels", [])),
                caveat=CAVEAT,
            )
            s.add(row)
            for c in e.get("coverage", []):
                s.add(CoverageRow(
                    story_id=e["id"], outlet=c.get("outlet", "unknown"),
                    # legacy entries (pre-v0.8) used "placement"
                    owner=c.get("owner", c.get("placement", "unknown")),
                    title=c.get("title", ""),
                    link=c.get("link", ""), published=c.get("published", ""),
                    loaded_terms=json.dumps(c.get("loaded_terms", {})),
                    labels_used=json.dumps(c.get("labels_used", [])),
                    passive_voice=int(c.get("passive_voice", False)),
                ))
            for f in e.get("facts", []):
                s.add(FactRow(
                    story_id=e["id"], text=f["text"], tier=f["tier"],
                    outlets=json.dumps(f["outlets"]),
                    first_seen=f.get("first_seen", ""),
                ))
            for n in e.get("numeric", []):
                s.add(NumericRow(
                    story_id=e["id"], context=n["context"],
                    values_json=json.dumps(n["values"]),
                    agreement=int(n["agreement"]),
                ))
            for c in e.get("consequences", []):
                s.add(ConsequenceRow(
                    story_id=e["id"], kind=c["type"],
                    description=c["description"],
                    outlets=json.dumps(c["outlets"]),
                    outlet_times=json.dumps(c.get("outlet_times", {})),
                    first_seen=c.get("first_seen") or c.get("logged_at", ""),
                ))
        s.commit()
        return s.query(StoryRow).count()
