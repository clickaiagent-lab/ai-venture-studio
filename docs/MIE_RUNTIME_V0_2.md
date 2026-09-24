# MIE Runtime v0.2

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
- previous queries;
- unresolved gaps;
- enabled source registry.

Each run covers one topic, stores its plan in `mie_research_runs.run_metrics.research_plan`, and has explicit query and document budgets.

## Visible execution stages

1. **Prepare** — read campaign brief and research memory.
2. **Plan** — choose one uncovered or incomplete topic and save bounded queries.
3. **Search** — execute the planned query batch.
4. **Collect** — classify candidates, reuse old URLs, crawl new URLs, reject thin captures and save provenance.
5. **Close** — compute counts from Supabase and save coverage, gaps and validity.

Candidates require an evidence role:

- `buyer_firsthand`;
- `solution`;
- `counterevidence`;
- `context`.

A completed collection run is VALID only when it reaches its query/document targets and contains at least one document labeled `buyer_firsthand`. Human QA may override validity.

## Duplicate and cost controls

- Exact prior queries require a stated repeat reason.
- URLs are canonicalized before comparison.
- Existing documents are linked to the new run without another crawl.
- Search snippets are never stored as evidence.
- Document totals are calculated from `mie_run_documents`; the model cannot supply the count.
- Search and collection run as batches to reduce model round trips.

Acceptance results:

| Run | Queries | Documents | AgentOS spans | Total tokens | Result |
|---|---:|---:|---:|---:|---|
| #009 | 3 | 4 | 31 | 131,171 | Baseline before batching |
| #010 | 2 | 2 | 16 | 89,899 | Found schema retry; human QA changed VALID to PARTIAL |
| #011 | 2 | 2 | 12 | 38,511 | Batch flow passed; one old URL reused and one new URL stored |

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

> Run a research batch for CAMP-0001. Choose one uncovered topic from the research brief. Use 4 planned queries and a 6-document budget. Prefer original buyer accounts, include solution or counterevidence when available, avoid prior URLs, close the run, and return the structured collection report.

## Current limitations

- Historical Runs #001–#008 have no v0.2 topic label and appear as `legacy_unclassified`.
- Evidence-role classification is produced by the agent and still requires human QA.
- Publication author/date extraction depends on source metadata and remains incomplete on some platforms.
- A VALID research run means collection requirements passed. It does not mean the niche is validated or approved.

