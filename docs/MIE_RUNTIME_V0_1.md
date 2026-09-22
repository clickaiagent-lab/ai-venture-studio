# MIE Runtime v0.1

Status: BUILDING
Agent runtime: Agno AgentOS
Deployment: Docker Compose
Canonical market memory: Supabase
Crawler: Crawl4AI

## What exists now

The runtime currently contains one constrained agent:

- Market Scout v0.1

Market Scout may:
- read the AVS campaign context;
- read the MIE source registry;
- create/resume a MIE research run;
- discover public URLs;
- fetch selected URLs through Crawl4AI;
- save raw + normalized documents to Supabase;
- attach documents to the research run;
- close the collection run.

Market Scout may NOT:
- create MIE signals;
- create clusters;
- create candidate opportunities;
- create AVS Opportunities;
- create AVS Decisions;
- create AVS Builds;
- call the MIE promotion function.

This is intentional. v0.1 proves ingestion before adding analysis agents.

## Runtime layout

```
Docker Compose
├── mie-runtime
│   ├── Agno AgentOS
│   ├── Market Scout
│   ├── MIE tools
│   └── local AgentOS session DB
│
└── crawl4ai
    └── public-web crawler

External:
- Supabase = canonical AVS/MIE data
- GitHub = code/versioning
- LLM provider API = reasoning
```

## Local setup

From the repository root:

```bash
cd mie
cp .env.example .env
```

Fill only the secrets you need in `.env`.

Required for Supabase-backed operation:

```text
SUPABASE_URL=https://mkkebukeajljuouecmce.supabase.co
SUPABASE_SERVICE_ROLE_KEY=<backend-only secret>
```

Required for the selected LLM provider, for example:

```text
MIE_MODEL=openai:gpt-5.5
OPENAI_API_KEY=<secret>
```

Then run:

```bash
docker compose up --build
```

Expected local services:

- MIE runtime: http://localhost:8000
- MIE health: http://localhost:8000/mie/health
- Crawl4AI: http://localhost:11235

## First health check

Open:

```text
http://localhost:8000/mie/health
```

A healthy system should report:

- Supabase reachable
- Crawl4AI reachable
- enabled MIE sources found
- Market Scout registered

## First campaign

The first runtime target is:

- Campaign: CAMP-0001
- Vertical: E-commerce
- Existing research run: MIE-RUN-0001-DISCOVERY

The first real test should collect a small batch, not the whole market.

Recommended first batch:
- 10-20 public documents;
- 2-3 source types;
- verify dedup and provenance;
- inspect Supabase before expanding.

## Security

Do not:
- commit `.env`;
- expose the Supabase service-role key in a browser;
- put API keys into prompts;
- grant Market Scout direct permission to promote opportunities.

The runtime is a backend service.

## Next build after ingestion is proven

Only after the first batch is verified:

1. Signal Analyst
2. evidence review logic
3. clustering
4. candidate opportunity creation
5. human review
6. MIE -> AVS promotion
