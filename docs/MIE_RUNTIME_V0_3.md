# MIE Runtime v0.3

Status: TESTED LOCALLY  
Agent runtime: Agno AgentOS  
Canonical market memory: Supabase  
Crawler: Crawl4AI

## Responsibility

Market Scout owns autonomous discovery and collection. It does not choose an AVS Opportunity.

The assistant and human reviewer inspect source quality, analyze evidence, and decide whether later MIE stages may create or promote signals.

## Research control model

Each campaign has a research brief containing:

- a topic map;
- buyer lenses;
- workflows to inspect;
- source priorities;
- required collection fields;
- a default query, document, source and time budget.

For CAMP-0001 the brief contains ten E-commerce topics.

Before every run, Market Scout reads:

- campaign objective;
- topic map;
- previous run coverage;
- previous and near-duplicate queries;
- verified evidence from prior v0.3 runs;
- unresolved gaps;
- enabled source registry.

Each run covers one topic, stores its plan in `mie_research_runs.run_metrics.research_plan`, and has explicit query and document budgets.

## Visible execution stages

1. **Prepare** — read campaign brief, previous evidence and research memory.
2. **Plan** — choose one uncovered or incomplete topic and save bounded seed queries.
3. **Search** — search in small batches; the tool records the queries actually executed.
4. **Collect** — reuse known URLs or crawl new ones, reject thin captures and return stored content to the agent.
5. **Review** — read stored content, quote an exact passage, and verify actor, absolute publication date, workflow and independence.
6. **Adapt** — refine the next query when evidence is weak and budgets remain.
7. **Close** — compute counts, evidence roles, gaps and validity from Supabase logs.

Evidence roles are assigned only after content review:

- `buyer_firsthand`;
- `solution`;
- `counterevidence`;
- `context`;
- `rejected`.

A run is `VALID` only when at least two verified, independently authored buyer accounts describe the same exact workflow. Each counted item must have an exact stored passage, a verified actor and an absolute date. Document and query budgets are ceilings, not collection quotas. Human QA may override validity.

## Duplicate and cost controls

- Exact and near-duplicate prior queries require a stated repeat reason.
- URLs are canonicalized before comparison.
- Existing documents are linked to the new run without another crawl.
- Search snippets are leads only; evidence must match stored content.
- Query counts come from the tool search log; document totals come from `mie_run_documents`.
- Search, collection and review may repeat within ceilings so the agent can fill evidence gaps.
- Source metadata extraction checks JSON-LD, article metadata and HTML time elements for absolute dates.

Acceptance results:

| Run | Queries | Documents | AgentOS spans | Total tokens | Result |
|---|---:|---:|---:|---:|---|
| #009 | 3 | 4 | 31 | 131,171 | v0.2 baseline before batching |
| #011 | 2 | 2 | 12 | 38,511 | v0.2 batch flow passed |
| #014 | 2 | 3 | 14 | 77,644 | v0.3 post-read review worked; human QA changed VALID to PARTIAL because two years were inferred from relative dates |
| #015 | 2 | 4 | 22 | — | Stopped after a null optional-field compatibility error; schema repaired |
| #016 | 1 | 2 | 14 | 79,510 | Final stability acceptance passed with zero trace errors and two dated, independently authored buyer accounts |

## Agno UI

1. Start Docker Desktop and the MIE compose stack.
2. Open [http://localhost:8000/mie](http://localhost:8000/mie).
3. Open [https://os.agno.com](https://os.agno.com) and sign in.
4. Choose **Add new OS**.
5. Select **Local**, enter endpoint `http://localhost:8000`, and name it `AVS MIE Local`.
6. Open **Agents → Market Scout** to run research and watch tool activity.
7. Open **Traces** to inspect model calls, tool calls, duration and errors.
8. Open [http://localhost:8000/mie/research/CAMP-0001](http://localhost:8000/mie/research/CAMP-0001) to inspect canonical runs and documents from Supabase.

Example request:

> Run a research batch for CAMP-0001. Choose one uncovered topic. Use ceilings of 4 queries and 6 documents. Search adaptively in small batches. Read every collected source before assigning an evidence role. Count useful evidence only when the stored passage, identifiable actor and absolute publication date are verified. Seek two independent buyer accounts for one exact workflow; include solution or counterevidence when available. Close the run and report rejected sources and gaps.

## Current limitations

- Historical Runs #001–#008 have no v0.3 topic label and appear as `legacy_unclassified`.
- Evidence roles, workflow equivalence and buyer identity still require human QA.
- Some platforms expose only relative dates; those sources are rejected unless an absolute date is extracted from metadata.
- Broad page captures increase tokens because the agent must read stored evidence; future work should return smaller query-focused passages without losing the original document.
- A `VALID` research run means the collection threshold passed. It does not validate the niche, approve a Signal or justify an AVS Opportunity.

