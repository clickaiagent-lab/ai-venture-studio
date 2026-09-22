from __future__ import annotations

from agno.db.sqlite import SqliteDb
from agno.os import AgentOS
from fastapi import FastAPI, HTTPException

from app.agents.market_scout import market_scout
from app.crawl4ai_client import healthcheck as crawl4ai_healthcheck
from app.settings import get_settings
from app.supabase_repo import get_campaign_by_code, list_enabled_sources

settings = get_settings()
runtime_db = SqliteDb(db_file=settings.agentos_db_file)

base_app = FastAPI(
    title="AVS Market Intelligence Engine",
    version="0.1.0",
)


@base_app.get("/mie/health")
def mie_health() -> dict:
    supabase_ok = False
    source_count = None
    error = None

    try:
        sources = list_enabled_sources()
        source_count = len(sources)
        supabase_ok = True
    except Exception as exc:
        error = str(exc)

    crawl4ai_ok = crawl4ai_healthcheck()

    return {
        "status": "ok" if supabase_ok and crawl4ai_ok else "degraded",
        "supabase": supabase_ok,
        "crawl4ai": crawl4ai_ok,
        "enabled_source_count": source_count,
        "market_scout_agent": "market-scout",
        "model": settings.mie_model,
        "error": error,
    }


@base_app.get("/mie/campaigns/{campaign_code}")
def campaign_context(campaign_code: str) -> dict:
    try:
        campaign = get_campaign_by_code(campaign_code)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign


agent_os = AgentOS(
    id="avs-mie-runtime",
    name="AVS Market Intelligence Engine",
    description=(
        "Agent runtime for AVS Market Intelligence Engine. "
        "Supabase remains the canonical market-memory store."
    ),
    agents=[market_scout],
    db=runtime_db,
    base_app=base_app,
    on_route_conflict="preserve_agentos",
    tracing=True,
    scheduler=True,
    scheduler_base_url="http://127.0.0.1:8000",
    mcp=True,
)

app = agent_os.get_app()


if __name__ == "__main__":
    agent_os.serve(app="app.main:app", host="0.0.0.0", port=8000)
