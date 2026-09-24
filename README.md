# AI Venture Studio

Central repository for the AVS operating system and its technical assets.

## Current scope

This repo contains:
- Supabase schema/migrations for AVS Central Memory
- Campaign seeds
- Prompts / evals / workflow exports as they become reusable
- Technical documentation

## Operating rule

AVS does not force every opportunity into an app or agent.

Core loop:
Find -> Validate -> Build -> Sell -> Decide -> Learn -> Repeat

## Storage ownership

- Structured business data: Supabase
- Human-readable docs/research: Google Drive
- Code/prompts/config/evals: GitHub
- AI traces: observability layer when needed
- Product usage: analytics layer when needed

## Current implementation

Phase 1 — Central Memory v0.1

Supabase project:
- name: ai-venture-studio
- region: ap-southeast-1 (Singapore)

Do not add dashboards, agents, or automation until Campaign #001 reveals a repeated need.


## Market Intelligence Engine

MIE is the dedicated intelligence intake system for **Step 03 — FIND**.

It is integrated into the same Supabase project but separated from AVS Core by a human-reviewed promotion boundary.

Flow:

```
Market Sources
-> MIE Sources/Documents/Signals/Clusters
-> MIE Candidate Opportunity
-> Human Approval
-> AVS Opportunity + AVS Evidence
-> Step 04 VALIDATE
```

Key rule: raw crawled content and unreviewed AI signals never become AVS Opportunities automatically.

Technical contract:
- `docs/MIE_AVS_DATA_CONTRACT_V0_1.md`
- `docs/MARKET_INTELLIGENCE_ENGINE_V0_1.md`

## Market Scout v0.3

- Runtime and Agno UI guide: `docs/MIE_RUNTIME_V0_3.md`
- Adaptive bounded search, post-crawl evidence review and campaign evidence memory.
- Useful evidence requires a stored exact passage, verified actor and absolute publication date.
- Run validity requires two independently authored buyer accounts for one exact workflow.
- Local MIE start page: `http://localhost:8000/mie`
- Agno Control Plane endpoint: `http://localhost:8000`
