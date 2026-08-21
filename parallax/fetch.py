"""Fetch and normalize headlines from outlet RSS feeds."""

import time
from dataclasses import dataclass, asdict
from typing import Iterable

import feedparser

from .feeds import FEEDS


@dataclass
class Headline:
    outlet: str
    owner: str
    title: str
    summary: str
    link: str
    published: str  # ISO 8601 where available, else empty

    def to_dict(self) -> dict:
        return asdict(self)


def _parse_time(entry) -> str:
    for key in ("published_parsed", "updated_parsed"):
        t = entry.get(key)
        if t:
            return time.strftime("%Y-%m-%dT%H:%M:%SZ", t)
    return ""


def fetch_all(feeds: dict | None = None, per_outlet_limit: int = 40) -> list[Headline]:
    """Fetch every configured feed. Failures are skipped, not fatal."""
    feeds = feeds or FEEDS
    headlines: list[Headline] = []
    for outlet, cfg in feeds.items():
        try:
            parsed = feedparser.parse(cfg["url"])
            for entry in parsed.entries[:per_outlet_limit]:
                title = (entry.get("title") or "").strip()
                if not title:
                    continue
                headlines.append(
                    Headline(
                        outlet=outlet,
                        owner=cfg.get("owner", "unknown"),
                        title=title,
                        summary=(entry.get("summary") or "")[:500],
                        link=entry.get("link", ""),
                        published=_parse_time(entry),
                    )
                )
        except Exception as exc:  # network hiccups shouldn't kill the run
            print(f"[warn] {outlet}: {exc}")
    return headlines


def from_records(records: Iterable[dict]) -> list[Headline]:
    """Build Headline objects from stored/fixture records (offline mode)."""
    return [Headline(**r) for r in records]
