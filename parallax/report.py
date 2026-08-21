"""Render analysis into markdown, JSON, and a static HTML page."""

import html
import json
from datetime import datetime, timezone
from pathlib import Path

from .framing import StoryAnalysis


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def to_json(analyses: list[StoryAnalysis], reactions: list[dict]) -> list[dict]:
    out = []
    for a, r in zip(analyses, reactions):
        out.append(
            {
                "label": a.label,
                "outlets": a.outlets,
                "divergence_score": a.divergence_score(),
                "divergent_labels": a.divergent_labels,
                "reaction": r,
                "coverage": [
                    {
                        "outlet": o.outlet,
                        "owner": o.owner,
                        "title": o.title,
                        "link": o.link,
                        "published": o.published,
                        "loaded_terms": o.loaded_terms,
                        "labels_used": o.labels_used,
                        "passive_voice": o.passive_voice,
                    }
                    for o in a.per_outlet
                ],
            }
        )
    return out


def write_markdown(stories: list[dict], path: Path) -> None:
    lines = [
        "# Parallax daily report",
        f"_Generated {_now()}. Text-observable signals only — no intent or",
        "coordination claims can be drawn from headline statistics._",
        "",
    ]
    for s in stories:
        lines.append(f"## {s['label']}")
        lines.append(
            f"Covered by {len(s['outlets'])} outlets · "
            f"framing divergence {s['divergence_score']}"
        )
        if s["divergent_labels"]:
            for group in s["divergent_labels"]:
                lines.append(f"- Same actors, different labels: {', '.join(group)}")
        if s["reaction"]["reaction_terms"]:
            lines.append(
                "- Reaction vocabulary present: "
                + ", ".join(s["reaction"]["reaction_terms"])
            )
        cons = s.get("consensus")
        if cons and cons["facts"]:
            lines.append("")
            lines.append("**Factual record** (corroboration-tiered — "
                         "agreement is a weight, not verified truth):")
            for f in cons["facts"]:
                when = f["first_seen"][:16] or "?"
                lines.append(f"- `{f['tier']}` {when} — {f['text']} "
                             f"_({', '.join(f['outlets'])})_")
            for n in cons.get("numeric_claims", []):
                if not n["agreement"]:
                    vals = ", ".join(f"{o}: {v}" for o, v in n["values"].items())
                    lines.append(f"- `discrepancy` “…{n['context']}” — {vals}")
        started = s.get("consequences_started") or []
        allcons = s.get("consequences_all") or []
        if allcons:
            lines.append("")
            lines.append("**Consequences (as reported — what started, not who arranged it):**")
            for c in allcons:
                new = " · NEW this run" if c in started else ""
                when = (c["first_seen"] or c.get("logged_at", ""))[:16]
                lines.append(f"- {c['type']} — first seen {when}, reported by "
                             f"{', '.join(c['outlets'])}{new}")
        lines.append("")
        lines.append("| Outlet | Owner | Headline | Loaded terms |")
        lines.append("|---|---|---|---|")
        for c in s["coverage"]:
            loaded = "; ".join(
                f"{cat}: {', '.join(t)}" for cat, t in c["loaded_terms"].items()
            ) or "—"
            title = c["title"].replace("|", "\\|")
            lines.append(
                f"| {c['outlet']} | {c['owner']} | {title} | {loaded} |"
            )
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


_CSS = """
:root{--ink:#1b1f2a;--paper:#fbfaf7;--rule:#d8d4ca;--flag:#8a2d3b;--dim:#6b7080}
*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);
font:16px/1.55 Georgia,'Times New Roman',serif}
header{border-bottom:3px double var(--rule);padding:28px 5vw 18px}
h1{font:700 30px/1.1 Georgia,serif;margin:0;letter-spacing:.3px}
header p{color:var(--dim);font:13px/1.5 system-ui,sans-serif;max-width:64ch;margin:8px 0 0}
main{padding:8px 5vw 60px}
.story{border-bottom:1px solid var(--rule);padding:26px 0}
.story h2{font-size:21px;margin:0 0 4px}
.meta{font:12px/1.4 system-ui,sans-serif;color:var(--dim);text-transform:uppercase;
letter-spacing:.08em;margin-bottom:14px}
.score{color:var(--flag);font-weight:600}
.diverge{font:14px/1.5 system-ui,sans-serif;background:#f2eee4;border-left:3px solid var(--flag);
padding:8px 12px;margin:0 0 14px}
table{width:100%;border-collapse:collapse;font:14px/1.45 system-ui,sans-serif}
th{text-align:left;font-size:11px;text-transform:uppercase;letter-spacing:.08em;
color:var(--dim);border-bottom:1px solid var(--rule);padding:6px 8px}
td{border-bottom:1px solid #eceadf;padding:8px;vertical-align:top}
.loaded{color:var(--flag)}
.record{font:14px/1.6 system-ui,sans-serif;margin:0 0 14px;padding:12px 14px;
background:#fff;border:1px solid var(--rule)}
.record h3{font:600 12px/1 system-ui,sans-serif;text-transform:uppercase;
letter-spacing:.08em;color:var(--dim);margin:0 0 8px}
.record ul{margin:0;padding-left:18px}
.tier{display:inline-block;font-size:10px;text-transform:uppercase;
letter-spacing:.06em;padding:1px 6px;border-radius:2px;margin-right:6px}
.tier.corroborated{background:#e3ecdf;color:#33502a}
.tier.reported{background:#efe8d6;color:#6b5417}
.tier.discrepancy,.tier.single-source{background:#f3e2e2;color:var(--flag)}
.conseq{font:14px/1.6 system-ui,sans-serif;margin:0 0 14px}
.conseq strong{color:var(--ink)}
@media(max-width:640px){td:nth-child(2),th:nth-child(2){display:none}}
"""


def write_html(stories: list[dict], path: Path) -> None:
    rows = []
    for s in stories:
        diverge = ""
        if s["divergent_labels"]:
            items = " · ".join(
                "same actors, different labels: " + " / ".join(g)
                for g in s["divergent_labels"]
            )
            diverge = f'<p class="diverge">{html.escape(items)}</p>'
        body = "".join(
            "<tr><td>{o}</td><td>{p}</td><td>{t}</td><td class='loaded'>{l}</td></tr>".format(
                o=html.escape(c["outlet"]),
                p=html.escape(c["owner"]),
                t=html.escape(c["title"]),
                l=html.escape(
                    "; ".join(
                        f"{cat}: {', '.join(t)}"
                        for cat, t in c["loaded_terms"].items()
                    )
                    or "—"
                ),
            )
            for c in s["coverage"]
        )
        record = ""
        cons = s.get("consensus")
        if cons and (cons["facts"] or any(
            not n["agreement"] for n in cons.get("numeric_claims", [])
        )):
            items = []
            for f in cons["facts"]:
                when = html.escape(f["first_seen"][:16] or "?")
                items.append(
                    f'<li><span class="tier {f["tier"]}">{f["tier"]}</span>'
                    f'{when} — {html.escape(f["text"])} '
                    f'<em>({html.escape(", ".join(f["outlets"]))})</em></li>'
                )
            for n in cons.get("numeric_claims", []):
                if not n["agreement"]:
                    vals = ", ".join(f"{o}: {v}" for o, v in n["values"].items())
                    items.append(
                        '<li><span class="tier discrepancy">discrepancy</span>'
                        f'“…{html.escape(n["context"])}” — {html.escape(vals)}</li>'
                    )
            record = (
                '<div class="record"><h3>Factual record — corroboration-tiered; '
                "agreement is a weight, not verified truth</h3><ul>"
                + "".join(items) + "</ul></div>"
            )
        conseq = ""
        if s.get("consequences_all"):
            bits = []
            for c in s["consequences_all"]:
                when = html.escape((c["first_seen"] or c.get("logged_at", ""))[:16])
                bits.append(
                    f"<strong>{html.escape(c['type'])}</strong> — first seen "
                    f"{when}, reported by {html.escape(', '.join(c['outlets']))}"
                )
            conseq = (
                '<p class="conseq">Consequences (as reported — what started, '
                "not who arranged it): " + " · ".join(bits) + "</p>"
            )
        rows.append(
            f"""<section class="story">
  <h2>{html.escape(s['label'])}</h2>
  <p class="meta">{len(s['outlets'])} outlets ·
    <span class="score">divergence {s['divergence_score']}</span></p>
  {diverge}{record}{conseq}
  <table><thead><tr><th>Outlet</th><th>Owner</th><th>Headline</th>
  <th>Loaded terms</th></tr></thead><tbody>{body}</tbody></table>
</section>"""
        )
    doc = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Parallax</title><style>{_CSS}</style></head><body>
<header><h1>Parallax</h1>
<p>One event, every headline, side by side. Generated {_now()}.
Signals shown are text-observable only — word choice, entity labels,
voice. Divergence is a comparison, not a verdict on who is right.</p>
</header><main>{''.join(rows)}</main></body></html>"""
    path.write_text(doc, encoding="utf-8")


def write_json(stories: list[dict], path: Path) -> None:
    path.write_text(json.dumps(stories, indent=2), encoding="utf-8")
