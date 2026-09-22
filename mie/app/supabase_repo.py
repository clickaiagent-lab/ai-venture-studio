from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

from supabase import Client, create_client

from app.settings import get_settings

_client: Client | None = None


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_client() -> Client:
    global _client
    settings = get_settings()
    if not settings.supabase_configured:
        raise RuntimeError(
            "Supabase is not configured. Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY."
        )
    if _client is None:
        _client = create_client(
            settings.supabase_url,
            settings.supabase_service_role_key,
        )
    return _client


def get_campaign_by_code(campaign_code: str) -> dict[str, Any] | None:
    result = (
        get_client()
        .table("avs_campaigns")
        .select("id,code,name,vertical,objective,status,owner,start_date,end_date,notes")
        .eq("code", campaign_code)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


def list_enabled_sources() -> list[dict[str, Any]]:
    result = (
        get_client()
        .table("mie_sources")
        .select(
            "id,code,source_type,platform,source_name,base_url,adapter_key,"
            "access_method,trust_profile,crawl_policy,config,notes"
        )
        .eq("enabled", True)
        .order("code")
        .execute()
    )
    return result.data or []


def get_source_by_code(source_code: str) -> dict[str, Any] | None:
    result = (
        get_client()
        .table("mie_sources")
        .select("id,code,platform,source_name,adapter_key,access_method,trust_profile")
        .eq("code", source_code)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


def get_research_run(run_code: str) -> dict[str, Any] | None:
    result = (
        get_client()
        .table("mie_research_runs")
        .select("*")
        .eq("code", run_code)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


def ensure_research_run(
    *,
    run_code: str,
    campaign_code: str,
    objective: str,
    research_query: str,
    source_codes: list[str],
    mode: str = "DISCOVERY",
) -> dict[str, Any]:
    existing = get_research_run(run_code)
    if existing:
        return existing

    campaign = get_campaign_by_code(campaign_code)
    if not campaign:
        raise ValueError(f"Unknown AVS campaign: {campaign_code}")

    payload = {
        "code": run_code,
        "campaign_id": campaign["id"],
        "mode": mode,
        "objective": objective,
        "research_query": research_query,
        "source_scope": source_codes,
        "orchestrator": "Agno-Market-Scout-v0.1",
        "model_name": get_settings().mie_model,
        "prompt_version": "market-scout-v0.1",
        "status": "DRAFT",
        "created_by_type": "AGENT",
        "created_by_id": "market-scout",
    }
    result = get_client().table("mie_research_runs").insert(payload).execute()
    if not result.data:
        raise RuntimeError("Supabase did not return the created research run.")
    return result.data[0]


def update_research_run(
    run_code: str,
    *,
    status: str | None = None,
    validity: str | None = None,
    run_metrics: dict[str, Any] | None = None,
    mark_started: bool = False,
    mark_completed: bool = False,
) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    if status is not None:
        payload["status"] = status
    if validity is not None:
        payload["validity"] = validity
    if run_metrics is not None:
        payload["run_metrics"] = run_metrics
    if mark_started:
        payload["started_at"] = _utcnow()
    if mark_completed:
        payload["completed_at"] = _utcnow()
    if not payload:
        current = get_research_run(run_code)
        if not current:
            raise ValueError(f"Unknown research run: {run_code}")
        return current

    result = (
        get_client()
        .table("mie_research_runs")
        .update(payload)
        .eq("code", run_code)
        .execute()
    )
    if not result.data:
        raise ValueError(f"Unknown research run: {run_code}")
    return result.data[0]


def store_document(
    *,
    run_code: str,
    source_code: str,
    canonical_url: str,
    title: str | None,
    raw_text: str,
    normalized_text: str,
    fetch_method: str,
    external_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    run = get_research_run(run_code)
    if not run:
        raise ValueError(f"Unknown research run: {run_code}")
    source = get_source_by_code(source_code)
    if not source:
        raise ValueError(f"Unknown MIE source: {source_code}")

    content_for_hash = normalized_text or raw_text
    content_hash = hashlib.sha256(
        content_for_hash.encode("utf-8", errors="ignore")
    ).hexdigest()

    existing = (
        get_client()
        .table("mie_documents")
        .select("id,canonical_url,content_hash,title,status")
        .eq("canonical_url", canonical_url)
        .eq("content_hash", content_hash)
        .limit(1)
        .execute()
    )

    deduplicated = bool(existing.data)
    if deduplicated:
        document = existing.data[0]
    else:
        payload = {
            "source_id": source["id"],
            "canonical_url": canonical_url,
            "external_id": external_id,
            "title": title,
            "fetched_at": _utcnow(),
            "fetch_method": fetch_method,
            "raw_text": raw_text,
            "normalized_text": normalized_text,
            "content_hash": content_hash,
            "metadata": metadata or {},
            "status": "NORMALIZED",
        }
        created = get_client().table("mie_documents").insert(payload).execute()
        if not created.data:
            raise RuntimeError("Supabase did not return the created MIE document.")
        document = created.data[0]

    get_client().table("mie_run_documents").upsert(
        {
            "research_run_id": run["id"],
            "document_id": document["id"],
        },
        on_conflict="research_run_id,document_id",
    ).execute()

    return {
        "document_id": document["id"],
        "canonical_url": canonical_url,
        "content_hash": content_hash,
        "deduplicated": deduplicated,
        "title": document.get("title") or title,
    }
