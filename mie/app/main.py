from __future__ import annotations

from agno.db.sqlite import SqliteDb
from agno.os import AgentOS
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

from app.agents.market_scout import market_scout
from app.crawl4ai_client import healthcheck as crawl4ai_healthcheck
from app.settings import get_settings
from app.supabase_repo import (
    get_campaign_by_code,
    list_campaign_documents,
    list_campaign_runs,
    list_enabled_sources,
)

settings = get_settings()
runtime_db = SqliteDb(db_file=settings.agentos_db_file)
base_app = FastAPI(title="AVS Market Intelligence Engine", version="0.2.0")


@base_app.get("/mie/health")
def mie_health() -> dict:
    supabase_ok = False
    source_count = None
    error = None
    try:
        source_count = len(list_enabled_sources())
        supabase_ok = True
    except Exception as exc:
        error = str(exc)
    crawl4ai_ok = crawl4ai_healthcheck()
    return {
        "status": "ok" if supabase_ok and crawl4ai_ok else "degraded",
        "supabase": supabase_ok, "crawl4ai": crawl4ai_ok,
        "enabled_source_count": source_count,
        "market_scout_agent": "market-scout", "market_scout_version": "0.2",
        "model": settings.mie_model,
        "agentos_control_plane_endpoint": "http://localhost:8000",
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


@base_app.get("/mie/research/{campaign_code}")
def research_status(campaign_code: str) -> dict:
    try:
        return {
            "campaign": get_campaign_by_code(campaign_code),
            "runs": list_campaign_runs(campaign_code, limit=100),
            "documents": list_campaign_documents(campaign_code, limit=1000),
        }
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@base_app.get("/mie", response_class=HTMLResponse)
def mie_home() -> str:
    return """
    <!doctype html><html lang="en"><head><meta charset="utf-8"><title>AVS MIE</title>
    <style>body{font-family:Segoe UI,Arial,sans-serif;max-width:900px;margin:48px auto;padding:0 24px;color:#172033}.card{border:1px solid #d8deea;border-radius:12px;padding:20px;margin:16px 0}a{color:#3157d5}code{background:#f1f4f9;padding:3px 7px;border-radius:5px}</style>
    </head><body><h1>AVS Market Intelligence Engine</h1>
    <div class="card"><h2>Agno AgentOS UI</h2>
    <p>Open <a href="https://os.agno.com" target="_blank">AgentOS Control Plane</a>, choose <b>Add new OS</b>, and connect <code>http://localhost:8000</code>.</p>
    <p>Choose <b>Market Scout</b>. Chat shows live output and tool calls. Traces shows each model and tool step.</p></div>
    <div class="card"><h2>Runtime</h2>
    <p><a href="/mie/health">Health</a> · <a href="/mie/research/CAMP-0001">CAMP-0001 data</a> · <a href="/docs">API</a></p></div>
    </body></html>
    """


agent_os = AgentOS(
    id="avs-mie-runtime", name="AVS Market Intelligence Engine",
    description="Agent runtime for AVS Market Intelligence Engine. Supabase remains canonical market memory.",
    agents=[market_scout], db=runtime_db, base_app=base_app,
    on_route_conflict="preserve_agentos", tracing=True, scheduler=True,
    scheduler_base_url="http://127.0.0.1:8000", mcp=True,
)
app = agent_os.get_app()

if __name__ == "__main__":
    agent_os.serve(app="app.main:app", host="0.0.0.0", port=8000)
