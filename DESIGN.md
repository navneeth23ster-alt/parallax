# Parallax Design: The Independence-Cluster Model

## The problem this solves

When two outlets report the same fact, that is stronger evidence than one
outlet reporting it — but only to the degree the confirmations are
independent. The things that most commonly break independence between two
newsrooms are structural, not ideological:

1. **Shared ownership** — two mastheads, one corporate voice.
2. **Shared wire copy** — thirty outlets running the same AP/PTI text is
   one report published thirty times.
3. **Editorial direction** — one newsroom effectively steering another.

Of these, ownership is the one that is a *checkable public fact*. Political
lean is a judgment; ownership is a registry entry. So corroboration tiers
key on ownership clusters, and Parallax never assigns political-lean labels
to outlets in regions where no audited public tracker exists.

## The model

Every feed carries two structural fields and one optional context field:

- `owner` — the ownership cluster, stated as a checkable fact
  (e.g. "HT Media (Birla family)", "Network18 / Reliance Industries",
  "Foundation for Independent Journalism (nonprofit)"). Subsidiaries and
  sister publications share one owner string, which is the entire point:
  the string IS the cluster key.
- `country` — where the outlet is based.
- `note` — optional, dated, factual context (e.g. "acquired by Adani
  Group, Dec 2022"). Display-only; never used in computation.

## Corroboration tiers (revised)

| Tier | Requirement |
|---|---|
| `corroborated` | 2+ outlets spanning **2+ distinct ownership clusters** |
| `reported` | 2+ outlets, but all within **one ownership cluster** |
| `single-source` | 1 outlet |

Under the previous placement-based logic, Hindustan Times + LiveMint
(both HT Media), News18 + Moneycontrol (both Network18/Reliance), and
The Hindu + Business Line (both Kasturi & Sons) each counted as
cross-group corroboration. Under this model they correctly collapse to
one confirmation each.

## What this deliberately does NOT do

- **No political-lean ratings.** The UI shows the owner string, a fact.
  Readers who know that a given conglomerate is close to a given
  government can weigh that themselves; Parallax states the ownership
  and stops.
- **No wire-copy detection yet.** Shared wire text is the second big
  independence-breaker and is NOT addressed by ownership clustering.
  Until wire dedup ships (planned: near-duplicate text detection across
  outlets before corroboration counting), even `corroborated` means
  "independently owned publishers printed it," not "independently
  verified." The caveat attached to every consensus record says exactly
  this.

## Maintenance rules

- Owner strings must be revisited when acquisitions happen — an outlet's
  cluster is a fact with a date on it (see NDTV, Dec 2022). The `note`
  field records the date so staleness is visible.
- If two outlets in the registry are later found to share an owner,
  merging their owner strings is a one-line fix that automatically
  corrects all future tiering.
- Sources for owner facts: company filings, registry records, and the
  outlet's own disclosures. If ownership is genuinely contested or
  opaque, the string says so: "ownership opaque (holding structure)".
