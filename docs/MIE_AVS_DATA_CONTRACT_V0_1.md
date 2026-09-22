# MIE ↔ AVS Data Contract v0.1

## Purpose

This document defines the permanent boundary between the Market Intelligence Engine (MIE) and AVS Core.

MIE is the intelligence intake layer for **AVS Step 03 — FIND**.
It is not a new AVS step and must not bypass human review.

## Canonical ownership

### MIE owns
- raw source registry;
- fetched documents;
- research runs;
- extracted market signals;
- clusters;
- candidate opportunities.

### AVS Core owns
- promoted Opportunities;
- accepted Evidence;
- Validation experiments;
- Builds;
- Decisions;
- Learnings;
- reusable Assets.

## Data flow

```
Market sources
  ↓
mie_sources
  ↓
mie_documents
  ↓
mie_signals
  ↓
mie_clusters
  ↓
mie_candidate_opportunities
  ↓
HUMAN REVIEW
  ↓
mie_promote_candidate(...)
  ↓
avs_opportunities
+
avs_evidence
  ↓
AVS Step 04 VALIDATE
```

## Non-negotiable rule

Raw market content never writes directly into `avs_opportunities`.

AI-extracted signals never become AVS Evidence automatically.

A candidate must be explicitly marked `APPROVED`, then promoted through the human-gated bridge.

## Lineage

Every promoted MIE signal retains:
- original MIE signal id;
- source document;
- canonical URL;
- evidence span;
- review status;
- resulting AVS Evidence id.

Every promoted candidate retains:
- MIE candidate id/code;
- AVS Opportunity id;
- promotion timestamp.

Use:
- `mie_candidate_readiness_v` before human review;
- `mie_avs_lineage_v` after promotion.

## Campaign linkage

Every research run, signal, cluster and candidate is linked to `avs_campaigns.id`.

For Campaign #001:
- AVS campaign: `CAMP-0001`
- vertical: E-commerce
- MIE research should write under that campaign.

This prevents MIE from becoming a detached research warehouse.

## Human gate

Promotion requires:
1. candidate status = `APPROVED`;
2. reviewer identity;
3. only signals with `review_status = APPROVED` are copied to AVS Evidence.

The database function:
`mie_promote_candidate(candidate_id, reviewed_by)`

is idempotent for already-promoted candidates.

## Evidence semantics

MIE signal direction:
- SUPPORTS
- CONTRADICTS
- NEUTRAL

maps directly to AVS Evidence direction.

MIE exact evidence span becomes AVS `extracted_fact`.
Original canonical URL becomes AVS `source_reference`.

This keeps the claim traceable back to the source.

## Storage map

Supabase:
- all structured AVS + MIE records.

GitHub:
- migrations;
- MIE adapters;
- prompts;
- evals;
- workflows;
- data contracts.

Google Drive:
- human-readable research reports;
- screenshots/PDFs where raw text is insufficient.

## GitHub → Supabase rule

All future schema changes:
1. add a new migration in `supabase/migrations/`;
2. merge/push to `main`;
3. GitHub Actions runs Supabase CLI;
4. Supabase applies pending migrations.

Do not mutate production schema manually unless performing an emergency repair that is immediately backfilled into Git history.

## Security

All `mie_*` tables use RLS and are closed by default.
No public client policy is added until a concrete runtime/app requires one.

Backend workers should use controlled server-side credentials, never browser-exposed service-role keys.

## Future Market Scout Agent

The future Agent will write only into MIE-owned tables:
- Scout -> `mie_documents`
- Signal Analyst -> `mie_signals`
- Evidence Analyst -> review fields / candidate evidence
- Research Lead -> `mie_clusters` + `mie_candidate_opportunities`

It must NOT write directly into:
- `avs_opportunities`
- `avs_decisions`
- `avs_builds`

## Definition of connected

MIE is considered correctly connected to AVS when:
- every MIE record belongs to an AVS campaign;
- raw data stays on MIE side;
- promotion is human-gated;
- promoted evidence is traceable;
- promotion creates an AVS Opportunity;
- AVS Step 04 consumes only promoted Opportunities.
