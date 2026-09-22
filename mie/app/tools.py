from __future__ import annotations

import json
from typing import Any

from app.crawl4ai_client import crawl_url
from app.supabase_repo import (
    ensure_research_run,
    get_campaign_by_code,
    get_research_run,
    list_enabled_sources,
    store_document,
    update_research_run,
)


def _json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, default=str)


def get_campaign_context(campaign_code: str) -> str:
    """Return the AVS campaign context for a campaign code such as CAMP-0001."""
    campaign = get_campaign_by_code(campaign_code)
    if not campaign:
        return _json({"error": f"Unknown campaign: {campaign_code}"})
    return _json(campaign)


def list_market_sources() -> str:
    """List enabled MIE sources and the approved access method for each source."""
    return _json(list_enabled_sources())


def begin_research_run(
    run_code: str,
    campaign_code: str,
    objective: str,
    research_query: str,
    source_codes: list[str],
) -> str:
    """Create or retrieve a MIE research run and mark it RUNNING."""
    run = ensure_research_run(
        run_code=run_code,
        campaign_code=campaign_code,
        objective=objective,
        research_query=research_query,
        source_codes=source_codes,
    )
    if run.get("status") != "RUNNING":
        run = update_research_run(run_code, status="RUNNING", mark_started=True)
    return _json(run)


def crawl_and_store_url(
    research_run_code: str,
    source_code: str,
    url: str,
) -> str:
    """Fetch one public URL with Crawl4AI and store the raw/normalized document in MIE."""
    crawled = crawl_url(url)
    markdown = crawled["markdown"] or ""
    html = crawled["html"] or ""
    stored = store_document(
        run_code=research_run_code,
        source_code=source_code,
        canonical_url=crawled["url"],
        title=crawled.get("title"),
        raw_text=html or markdown,
        normalized_text=markdown or html,
        fetch_method="CRAWL4AI",
        metadata=crawled.get("metadata") or {},
    )
    return _json(stored)


def get_research_run_status(run_code: str) -> str:
    """Return the current MIE research-run record."""
    run = get_research_run(run_code)
    if not run:
        return _json({"error": f"Unknown research run: {run_code}"})
    return _json(run)


def finish_research_run(
    run_code: str,
    documents_collected: int,
    useful_notes: str,
    validity: str = "VALID",
) -> str:
    """Mark a research run completed and save collection metrics. Does not approve opportunities."""
    run = update_research_run(
        run_code,
        status="COMPLETED",
        validity=validity,
        run_metrics={
            "documents_collected": documents_collected,
            "market_scout_notes": useful_notes,
        },
        mark_completed=True,
    )
    return _json(run)
