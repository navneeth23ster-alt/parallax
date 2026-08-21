"""Feedback storage: 'report an issue' submissions from the public site.

Public trust in Parallax depends on visible correction paths — a wrong
loaded-term flag or a bad cluster merge needs somewhere to go. This is
intentionally simple: append-only, no accounts, rate-limited at the API
layer. A human reviews the file; nothing here auto-applies a correction.
"""

import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

MAX_LEN = 2000
VALID_CATEGORIES = {
    "wrong-loaded-term", "bad-cluster", "wrong-tier",
    "broken-link", "other",
}


@dataclass
class Feedback:
    category: str
    message: str
    story_id: str = ""
    submitted_at: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def validate(category: str, message: str, story_id: str = "") -> Feedback:
    category = (category or "other").strip().lower()
    if category not in VALID_CATEGORIES:
        category = "other"
    message = (message or "").strip()
    if not message:
        raise ValueError("message is required")
    if len(message) > MAX_LEN:
        message = message[:MAX_LEN]
    # strip control characters; keep it plain text
    message = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", message)
    story_id = re.sub(r"[^a-zA-Z0-9]", "", (story_id or ""))[:16]
    return Feedback(
        category=category,
        message=message,
        story_id=story_id,
        submitted_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )


def append(store: Path, fb: Feedback) -> None:
    store.parent.mkdir(parents=True, exist_ok=True)
    with store.open("a", encoding="utf-8") as f:
        f.write(json.dumps(fb.to_dict()) + "\n")
