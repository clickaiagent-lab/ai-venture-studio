# Market Intelligence Engine v0.1 — Research & Build Spec

Status: PREPARED / NOT YET BUILT
Role in AVS: INPUT ENGINE FOR STEP 03 — FIND
Core impact: NONE. This is a module feeding AVS, not a new AVS core step.

## 1. Purpose

Market Intelligence Engine (MIE) exists to continuously discover, collect, normalize, verify, cluster, and preserve market signals that may become AVS Opportunities.

It must not be a generic "find startup ideas" chatbot.

Primary output:
- source-backed market signals;
- recurring problem patterns;
- contradictory evidence;
- candidate Opportunity Cards for human review.

MIE must preserve provenance and raw evidence before AI interpretation.

---

## 2. Design principle

Do not adopt one GitHub project wholesale.

Use:
- mature open-source components for crawling/search/browser access;
- selected research-agent patterns for planning and synthesis;
- AVS-owned schema, evidence rules, scoring rules, and memory.

AVS remains the system of record.

---

## 3. GitHub projects researched

### A. GPT Researcher
Repository: https://github.com/assafelovic/gpt-researcher
Role: research orchestration pattern / optional research worker
License: Apache-2.0
Why useful:
- deep research pipeline;
- multiple retrievers;
- MCP support;
- web + local documents;
- citations;
- configurable models;
- parallel research.

Decision:
REFERENCE + POSSIBLE COMPONENT.
Do not make GPT Researcher the MIE database or source-of-truth.
Borrow its planner/retriever/research/synthesis pattern.

### B. Crawl4AI
Repository: https://github.com/unclecode/crawl4ai
Role: PRIMARY generic crawler/extractor
License: Apache-2.0
Why useful:
- actively maintained;
- LLM-friendly Markdown;
- Playwright/browser rendering;
- structured extraction;
- robots.txt support;
- proxy support;
- e-commerce/domain extraction patterns;
- self-hostable.

Decision:
SELECT AS PRIMARY CRAWLER FOR MIE v0.1.

### C. Firecrawl
Repository: https://github.com/firecrawl/firecrawl
Role: optional crawler/search fallback
License: AGPL-3.0 for core
Why useful:
- strong search/scrape/crawl APIs;
- self-host;
- MCP/n8n ecosystem;
- high community adoption.

Decision:
OPTIONAL / FALLBACK.
Do not make it the first dependency because Crawl4AI has a simpler permissive license fit for AVS ownership.
Re-evaluate if Crawl4AI reliability becomes a bottleneck.

### D. Browser Use
Repository: https://github.com/browser-use/browser-use
Role: BROWSER FALLBACK / difficult dynamic sites
License: MIT
Why useful:
- real browser interaction;
- JS-heavy sites;
- forms/navigation;
- local or cloud browsers;
- custom tools and structured output.

Decision:
SELECT AS FALLBACK, NOT PRIMARY CRAWLER.
Use only when normal API/crawl paths fail because browser agents cost more and are less deterministic.

### E. Alibaba Tongyi DeepResearch
Repository: https://github.com/Alibaba-NLP/DeepResearch
Role: advanced research-agent reference
License: Apache-2.0
Why useful:
- long-horizon web research;
- web traversal research;
- strong benchmark focus.

Decision:
REFERENCE ONLY FOR NOW.
Too heavy to become MIE v0.1 runtime.
Revisit when AVS needs long-horizon autonomous investigation.

### F. Stanford STORM
Repository: https://github.com/stanford-oval/storm
Role: knowledge synthesis / perspective discovery pattern
License: MIT
Why useful:
- structured research;
- multi-perspective discovery;
- citation-oriented long-form knowledge curation.

Decision:
REFERENCE ONLY.
Useful for synthesis patterns, not for continuous signal ingestion.

### G. PRAW
Repository: https://github.com/praw-dev/praw
Role: PRIMARY Reddit API adapter where API access is available
License: BSD-2-Clause
Why useful:
- mature Reddit API wrapper;
- maintained;
- rate-limit aware;
- structured Reddit objects.

Decision:
SELECT FOR REDDIT API-FIRST COLLECTION.
Browser/no-auth scraping should be fallback rather than canonical collection.

### H. Omnifeed
Repository: https://github.com/kinorai/omnifeed
Role: research-source adapter design reference
License: MIT
Why useful:
- SearXNG + Crawl4AI;
- dedicated Reddit engine;
- Hacker News;
- GitHub issues/PRs;
- Discourse;
- MCP/REST;
- token-efficient output;
- modular engine registry.

Decision:
HIGH-VALUE REFERENCE; DO NOT DEPEND ON IT AS FOUNDATION YET.
Reason: architecture is very relevant but project/community is still small.
Borrow:
- engine registry;
- source-specific adapters;
- generic crawl fallback;
- search -> fetch loop;
- Reddit/HN/Discourse/GitHub handling concepts.

### I. ScrapeGraphAI
Repository: https://github.com/ScrapeGraphAI/Scrapegraph-ai
Role: AI-assisted structured extraction reference
License: MIT
Why useful:
- natural-language/LLM extraction;
- recent active releases;
- structured scraping.

Decision:
REFERENCE / POSSIBLE SECONDARY EXTRACTOR.
Do not add at v0.1 unless Crawl4AI extraction is insufficient.

### J. Reddit pain-point agents
Examples studied:
- https://github.com/the-wc/reddit-painpointer
- https://github.com/lefttree/reddit-pain-points
- https://github.com/Ash-neon/reddit-problem-finder
- https://github.com/michaelrockson/leema-ai-agent

Useful patterns:
- pain-language filters;
- post + comment analysis;
- severity labels;
- category extraction;
- rate limits;
- pipeline stages: scout -> ingress -> analysis -> curation -> persistence;
- trend detection ideas.

Decision:
DO NOT IMPORT WHOLE PROJECTS.
Borrow the workflow patterns only.
Their scale, maintenance, and evidence methodology are not strong enough to become AVS foundation.

---

## 4. Selected MIE v0.1 stack

### Search / discovery
Primary:
- SearXNG or provider-neutral search adapter.

Optional:
- Tavily / Brave / Exa when API quality justifies cost.

Rule:
Search discovers candidate URLs.
Search result snippets are NOT final evidence.

### Generic crawling
PRIMARY:
- Crawl4AI.

### Browser fallback
PRIMARY FALLBACK:
- Browser Use.

### Source-specific adapters
Reddit:
- PRAW/API first;
- browser/crawl fallback only where appropriate.

Hacker News:
- official/public API path.

Discourse:
- public JSON/API endpoints where available.

GitHub:
- GitHub API/connector.

Generic forums:
- Crawl4AI;
- source-specific adapter when repeated value is proven.

App marketplaces / review sites:
- API if available;
- Crawl4AI;
- Browser Use fallback.

### Research orchestration
AVS-owned pipeline inspired by:
- GPT Researcher;
- Omnifeed;
- STORM;
- Tongyi DeepResearch.

Do not couple MIE to one LLM provider.

### Memory
Supabase = structured canonical memory.

Google Drive = human-readable reports / screenshots / source files when necessary.

GitHub = MIE code, prompts, schemas, evals, source adapters.

### Scheduling
Manual first.
n8n later when repeated scheduled collection is useful.

---

## 5. MIE pipeline

1. SOURCE MAP
2. DISCOVER
3. FETCH
4. NORMALIZE
5. DEDUP
6. EXTRACT SIGNAL
7. VERIFY / QUALITY CHECK
8. CLUSTER
9. PATTERN DETECTION
10. OPPORTUNITY CANDIDATE
11. DEEP RESEARCH
12. HUMAN REVIEW
13. HANDOFF TO AVS STEP 03

Flow:

Sources
  -> Search/API adapters
  -> Crawl4AI
  -> Browser fallback if needed
  -> Raw document store
  -> Noise filter
  -> Signal extractor
  -> Dedup/entity normalization
  -> Evidence quality + contradiction
  -> Problem clustering
  -> Candidate Opportunity Card
  -> strong reasoning model
  -> human review
  -> AVS Step 03

---

## 6. Required data objects for future MIE schema

Do NOT modify AVS core tables yet.

Proposed MIE-owned tables/entities:

### mie_sources
- source_id
- source_type
- domain/platform
- source_name
- access_method
- trust_profile
- crawl_policy
- enabled

### mie_documents
- document_id
- source_id
- canonical_url
- external_id
- title
- author/reference
- published_at
- fetched_at
- raw_text
- normalized_text
- content_hash
- metadata
- fetch_method
- status

### mie_signals
- signal_id
- document_id
- signal_type
- icp_candidate
- buyer_candidate
- workflow
- problem
- current_workaround
- impact
- frequency
- spend_or_resource_signal
- exact_evidence_span
- confidence
- created_by
- reviewed

### mie_clusters
- cluster_id
- cluster_label
- workflow
- problem_pattern
- signal_count
- unique_source_count
- time_span
- supporting_signal_ids
- contradictory_signal_ids

### mie_research_runs
- run_id
- query / research objective
- source_scope
- model
- prompts_version
- started_at
- completed_at
- cost
- run_status
- validity

### mie_candidate_opportunities
- candidate_id
- cluster_id
- candidate_problem
- candidate_icp
- candidate_buyer
- reachability
- evidence_summary
- contradictions
- unknowns
- status

Only promoted candidates become AVS Opportunities.

---

## 7. Evidence rules

MIE must NOT equate:
- one complaint = market;
- search result = evidence;
- AI summary = source;
- popularity = willingness to pay;
- repeated copy/repost = independent evidence.

Every important signal needs:
- canonical source;
- retrieval timestamp;
- raw/normalized content;
- evidence span;
- source type;
- independence check;
- AI extraction version;
- confidence;
- contradiction flag where relevant.

Raw source and AI interpretation must remain separate.

---

## 8. Anti-bias rules

MIE must support both:
- hypothesis-driven research;
- hypothesis-free discovery.

For every candidate problem:
1. search for confirming evidence;
2. search for disconfirming evidence;
3. search for existing solutions;
4. search for native platform solutions;
5. search for evidence that users tolerate the problem;
6. search for evidence of payment/current spend.

Do not rank an Opportunity solely from LLM judgment.

---

## 9. Source priority for Campaign #001 — E-commerce

Tier A — highest value initially:
- Reddit seller/operator communities;
- Shopify App Store reviews;
- competitor/app reviews;
- public support forums;
- Discourse communities;
- GitHub issues for commerce tools;
- Hacker News where relevant;
- public job descriptions showing manual workflows;
- product/help documentation revealing workflow complexity.

Tier B:
- YouTube comments;
- independent blogs;
- public social posts;
- product comparison pages.

Tier C:
- generic SEO content;
- affiliate listicles;
- AI-generated articles;
- unattributed summaries.

Tier C can aid discovery but should not drive Opportunity evidence.

---

## 10. What to build first

MIE v0.1 should NOT be a large multi-agent system.

Build only:

1. Source registry
2. Search adapter
3. Crawl4AI fetcher
4. Reddit adapter
5. Discourse/HN/GitHub adapters
6. Normalizer
7. content-hash dedup
8. structured signal extractor
9. Supabase writer
10. basic clusterer
11. research runner
12. human review output

Do not build:
- dashboard;
- multi-agent swarm;
- autonomous final Build/Kill decision;
- continuous 24/7 monitoring;
- complex vector database;
- synthetic market personas.

---

## 11. Future Agent design

When v0.1 workflow is proven, create:

### Market Scout Agent
Responsibilities:
- discover new sources;
- collect raw signals;
- respect source policies;
- schedule/retry;
- write mie_documents.

### Signal Analyst Agent
Responsibilities:
- extract candidate pain/workflow/ICP/buyer/impact;
- flag noise;
- write mie_signals.

### Evidence Analyst
Responsibilities:
- check independence;
- contradictory evidence;
- duplicate claims;
- source quality;
- validate citations.

### Research Lead Agent
Responsibilities:
- investigate strong clusters;
- search alternative explanations;
- produce candidate Opportunity Cards.

Human remains final reviewer before promotion into AVS Opportunities.

---

## 12. Component decisions

USE NOW / BUILD AROUND:
- Supabase
- Crawl4AI
- PRAW / API-first platform adapters
- GitHub APIs
- strong interchangeable LLM
- AVS evidence schema

USE AS FALLBACK:
- Browser Use
- Firecrawl
- ScrapeGraphAI

BORROW PATTERNS FROM:
- GPT Researcher
- Omnifeed
- STORM
- Tongyi DeepResearch
- Reddit pain-point agents

DO NOT YET ADD:
- large agent framework dependency;
- multi-agent swarm;
- continuous scheduler;
- dashboard.

---

## 13. Licensing / operational note

Before production use:
- preserve required open-source attribution/licenses;
- verify current repository licenses again at implementation time;
- respect robots.txt where applicable;
- respect platform Terms of Service and API terms;
- do not collect private/authenticated community content without authorization;
- use rate limits and retry/backoff.

---

## 14. Success criteria for MIE v0.1

MIE v0.1 is successful when it can:

1. ingest at least 5 source types;
2. retain raw source + provenance;
3. deduplicate reliably;
4. extract structured signals;
5. preserve contradictions;
6. cluster repeated problems;
7. create candidate Opportunity Cards with traceable evidence;
8. let a human inspect every promoted claim;
9. rerun without duplicating old data;
10. feed AVS Step 03 without manual copy/paste.

---

## 15. Immediate next action

Before coding MIE:
Run Campaign #001 Step 03 using this protocol manually/semi-manually.

During the campaign record:
- sources that produce useful signals;
- sources that fail or block access;
- repeated extraction fields;
- false positives;
- duplicate patterns;
- cost/time per source;
- places where browser fallback is required.

Use Campaign #001 as the first real eval dataset for MIE.

Do not redesign AVS Core.
Do not create Step 09.
