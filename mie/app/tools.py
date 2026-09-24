from __future__ import annotations

import json
import re
from typing import Any

from ddgs import DDGS
from pydantic import BaseModel, Field

from app.crawl4ai_client import crawl_url
from app.research_briefs import get_research_brief as load_research_brief
from app.supabase_repo import (
    attach_document_to_run,
    ensure_research_run,
    find_document_by_url,
    get_campaign_by_code,
    get_research_run,
    list_campaign_documents,
    list_campaign_runs,
    list_enabled_sources,
    list_run_documents,
    store_document,
    update_research_run,
)


def _json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, default=str)


def _normalized_query(query: str) -> str:
    return " ".join((query or "").lower().split())


def _visible_length(markdown: str, html: str) -> int:
    text = markdown or re.sub(r"<[^>]+>", " ", html or "")
    return len(" ".join(text.split()))




class CandidateInput(BaseModel):
    url: str
    source_code: str
    discovery_query: str
    relevance_hint: str
    evidence_role: str = Field(description="One of buyer_firsthand, solution, counterevidence, context")
    discovery_rank: int | None = None


def prepare_research_context(campaign_code: str, reason: str = "") -> str:
    """Load compact campaign, shopping-list, prior coverage and source registry in one call."""
    campaign = get_campaign_by_code(campaign_code)
    if not campaign:
        raise ValueError(f"Unknown campaign: {campaign_code}")
    memory = json.loads(get_campaign_research_memory(campaign_code))
    compact_memory = {
        "run_count": memory["run_count"],
        "unique_document_count": memory["unique_document_count"],
        "topic_coverage": memory["topic_coverage"],
        "studied_queries": memory["studied_queries"],
        "unresolved_gaps": memory["unresolved_gaps"],
    }
    sources = [
        {key: item.get(key) for key in ("code", "source_type", "platform", "access_method", "trust_profile")}
        for item in list_enabled_sources()
    ]
    return _json({
        "campaign": {key: campaign.get(key) for key in ("code", "name", "vertical", "objective", "status")},
        "research_brief": load_research_brief(campaign_code),
        "research_memory": compact_memory,
        "enabled_sources": sources,
    })


def search_candidate_urls(
    run_code: str,
    queries: list[str],
    max_results_per_query: int = 4,
    reason: str = "",
) -> str:
    """Execute the approved query batch once and return compact discovery leads."""
    run = get_research_run(run_code)
    if not run:
        raise ValueError(f"Unknown research run: {run_code}")
    plan = (run.get("run_metrics") or {}).get("research_plan") or {}
    planned = {_normalized_query(item) for item in plan.get("planned_queries") or []}
    cleaned = list(dict.fromkeys(item.strip() for item in queries if item and item.strip()))
    if any(_normalized_query(item) not in planned for item in cleaned):
        raise ValueError("All batch queries must be present in the approved research plan.")
    if len(cleaned) > int(plan.get("query_budget") or 0):
        raise ValueError("Query batch exceeds the run query budget.")
    max_results_per_query = max(1, min(int(max_results_per_query), 5))
    output: list[dict[str, Any]] = []
    client = DDGS()
    for query in cleaned:
        results = client.text(query, max_results=max_results_per_query)
        compact = []
        for rank, item in enumerate(results or [], start=1):
            compact.append({
                "rank": rank,
                "title": item.get("title"),
                "url": item.get("href") or item.get("url"),
                "snippet": (item.get("body") or item.get("snippet") or "")[:180],
            })
        output.append({"query": query, "results": compact})
    return _json({
        "run_code": run_code,
        "executed_queries": cleaned,
        "result_batches": output,
        "rule": "Results are discovery leads only. Choose original sources; snippets are not evidence.",
    })


def collect_candidate_batch(
    run_code: str,
    candidates: list[CandidateInput],
    reason: str = "",
) -> str:
    """Check novelty and collect a bounded candidate batch without another model turn per URL."""
    run = get_research_run(run_code)
    if not run:
        raise ValueError(f"Unknown research run: {run_code}")
    plan = (run.get("run_metrics") or {}).get("research_plan") or {}
    budget = int(plan.get("document_budget") or 0)
    allowed_sources = set(plan.get("source_codes") or [])
    existing_count = len(list_run_documents(run_code))
    remaining = max(0, budget - existing_count)
    results: list[dict[str, Any]] = []
    for candidate in candidates:
        if remaining <= 0:
            break
        url = candidate.url.strip()
        source_code = candidate.source_code.strip()
        query = candidate.discovery_query.strip()
        hint = candidate.relevance_hint.strip()
        role = candidate.evidence_role.strip().lower()
        rank = candidate.discovery_rank
        if role not in {"buyer_firsthand", "solution", "counterevidence", "context"}:
            results.append({"decision": "REJECTED_INPUT", "url": url, "reason": "invalid evidence_role"})
            continue
        tagged_hint = f"[{role}] {hint}"
        if source_code not in allowed_sources:
            results.append({"decision": "REJECTED_INPUT", "url": url, "reason": f"source {source_code} is outside run scope"})
            continue
        existing = find_document_by_url(url)
        if existing:
            attach_document_to_run(
                run_code=run_code, document_id=existing["id"],
                discovery_query=query, discovery_rank=rank, relevance_hint=tagged_hint,
            )
            results.append({"decision": "REUSED", "url": existing["canonical_url"], "document_id": existing["id"], "title": existing.get("title")})
            remaining -= 1
            continue
        try:
            crawled = crawl_url(url)
            markdown = crawled["markdown"] or ""
            html = crawled["html"] or ""
            visible_length = _visible_length(markdown, html)
            if visible_length < 300:
                results.append({"decision": "REJECTED_THIN", "url": url, "visible_length": visible_length})
                continue
            stored = store_document(
                run_code=run_code, source_code=source_code,
                canonical_url=crawled["url"], title=crawled.get("title"),
                raw_text=html or markdown, normalized_text=markdown or html,
                fetch_method="CRAWL4AI", metadata=crawled.get("metadata") or {},
            )
            attach_document_to_run(
                run_code=run_code, document_id=stored["document_id"],
                discovery_query=query, discovery_rank=rank, relevance_hint=tagged_hint,
            )
            results.append({
                "decision": "STORED", "url": stored["canonical_url"],
                "document_id": stored["document_id"], "title": stored.get("title"),
                "visible_length": visible_length,
            })
            remaining -= 1
        except Exception as exc:
            results.append({"decision": "FAILED", "url": url, "error": str(exc)[:300]})
    return _json({
        "run_code": run_code,
        "document_budget": budget,
        "documents_before_batch": existing_count,
        "documents_after_batch": len(list_run_documents(run_code)),
        "results": results,
    })


def get_campaign_context(campaign_code: str, reason: str = "") -> str:
    """Return the AVS campaign context."""
    campaign = get_campaign_by_code(campaign_code)
    if not campaign:
        return _json({"error": f"Unknown campaign: {campaign_code}"})
    return _json(campaign)


def get_research_brief(campaign_code: str, reason: str = "") -> str:
    """Return the campaign topic map, buyer lenses, evidence fields, rules and default budget."""
    return _json(load_research_brief(campaign_code))


def list_market_sources(reason: str = "") -> str:
    """List enabled MIE sources and approved access methods."""
    return _json(list_enabled_sources())


def get_campaign_research_memory(campaign_code: str, reason: str = "") -> str:
    """Return prior topics, queries, gaps, runs and URL coverage before planning."""
    runs = list_campaign_runs(campaign_code, limit=100)
    documents = list_campaign_documents(campaign_code, limit=1000)
    studied_queries: list[str] = []
    coverage: dict[str, dict[str, Any]] = {}
    unresolved_gaps: list[str] = []
    for run in runs:
        metrics = run.get("run_metrics") or {}
        plan = metrics.get("research_plan") or {}
        topic = plan.get("focus_topic") or "legacy_unclassified"
        bucket = coverage.setdefault(topic, {"run_count": 0, "document_count": 0, "validity": [], "last_run": None})
        bucket["run_count"] += 1
        bucket["document_count"] += int(metrics.get("documents_linked") or metrics.get("documents_collected") or 0)
        if run.get("validity"):
            bucket["validity"].append(run["validity"])
        if bucket["last_run"] is None:
            bucket["last_run"] = run["code"]
        for query in (plan.get("planned_queries") or []) + (metrics.get("executed_queries") or []):
            if query and query not in studied_queries:
                studied_queries.append(query)
        for gap in metrics.get("unresolved_gaps") or []:
            if gap and gap not in unresolved_gaps:
                unresolved_gaps.append(gap)
    return _json({
        "campaign_code": campaign_code,
        "run_count": len(runs),
        "unique_document_count": len(documents),
        "topic_coverage": coverage,
        "studied_queries": studied_queries,
        "unresolved_gaps": unresolved_gaps,
        "seen_urls": [{"url": d.get("canonical_url"), "title": d.get("title"), "status": d.get("status")} for d in documents],
        "instruction": "Choose an uncovered or incomplete topic. Reuse an exact query only with a repeat_reason. Check each URL before fetch.",
    })


def begin_planned_research_run(
    run_code: str,
    campaign_code: str,
    focus_topic: str,
    objective: str,
    planned_queries: list[str],
    source_codes: list[str],
    query_budget: int = 6,
    document_budget: int = 10,
    mode: str = "DISCOVERY",
    repeat_reason: str = "",
    reason: str = "",
) -> str:
    """Create a bounded run after checking topic and query overlap with campaign memory."""
    brief = load_research_brief(campaign_code)
    allowed = {item["id"] for item in brief.get("topic_map") or []}
    if allowed and focus_topic not in allowed:
        raise ValueError(f"Unknown focus_topic {focus_topic}. Choose one of: {sorted(allowed)}")
    query_budget = max(1, min(int(query_budget), 12))
    document_budget = max(1, min(int(document_budget), 20))
    planned_queries = [item.strip() for item in planned_queries if item and item.strip()]
    if not planned_queries:
        raise ValueError("At least one planned query is required.")
    if len(planned_queries) > query_budget:
        raise ValueError("planned_queries exceeds query_budget.")
    prior_queries: set[str] = set()
    for run in list_campaign_runs(campaign_code, limit=100):
        metrics = run.get("run_metrics") or {}
        plan = metrics.get("research_plan") or {}
        for query in (plan.get("planned_queries") or []) + (metrics.get("executed_queries") or []):
            prior_queries.add(_normalized_query(query))
    repeated = [query for query in planned_queries if _normalized_query(query) in prior_queries]
    if repeated and not repeat_reason.strip():
        raise ValueError("Exact queries already used. Change them or provide repeat_reason: " + " | ".join(repeated))
    research_plan = {
        "focus_topic": focus_topic,
        "objective": objective,
        "planned_queries": planned_queries,
        "query_budget": query_budget,
        "document_budget": document_budget,
        "source_codes": source_codes,
        "repeat_reason": repeat_reason.strip() or None,
        "origin": "AGNO_AUTONOMOUS",
        "brief_version": brief.get("version"),
    }
    run = ensure_research_run(
        run_code=run_code, campaign_code=campaign_code, objective=objective,
        research_query=" | ".join(planned_queries), source_codes=source_codes,
        mode=mode, initial_metrics={"research_plan": research_plan},
    )
    if run.get("status") != "RUNNING":
        run = update_research_run(run_code, status="RUNNING", mark_started=True)
    return _json({"run_code": run["code"], "status": run["status"], "research_plan": research_plan, "repeated_queries": repeated})


def check_candidate_url(research_run_code: str, url: str, discovery_query: str, relevance_hint: str, reason: str = "") -> str:
    """Check URL novelty before spending a crawl; link an existing document for reuse."""
    if not get_research_run(research_run_code):
        raise ValueError(f"Unknown research run: {research_run_code}")
    existing = find_document_by_url(url)
    if not existing:
        return _json({"decision": "FETCH", "url": url, "reason": "new canonical URL"})
    attach_document_to_run(
        run_code=research_run_code, document_id=existing["id"],
        discovery_query=discovery_query, relevance_hint=relevance_hint,
    )
    return _json({
        "decision": "REUSE", "url": existing["canonical_url"],
        "document_id": existing["id"], "status": existing.get("status"),
        "reason": "already present in MIE; linked without crawling",
    })


def crawl_and_store_url(
    research_run_code: str,
    source_code: str,
    url: str,
    discovery_query: str,
    relevance_hint: str,
    discovery_rank: int | None = None,
    force_refresh: bool = False,
    reason: str = "",
) -> str:
    """Fetch one new public URL, reject thin captures and save it with discovery provenance."""
    if not force_refresh:
        existing = find_document_by_url(url)
        if existing:
            attach_document_to_run(
                run_code=research_run_code, document_id=existing["id"],
                discovery_query=discovery_query, discovery_rank=discovery_rank,
                relevance_hint=relevance_hint,
            )
            return _json({
                "decision": "REUSED_WITHOUT_CRAWL", "document_id": existing["id"],
                "canonical_url": existing["canonical_url"], "title": existing.get("title"),
                "status": existing.get("status"),
            })
    crawled = crawl_url(url)
    markdown = crawled["markdown"] or ""
    html = crawled["html"] or ""
    visible_length = _visible_length(markdown, html)
    if visible_length < 300:
        raise RuntimeError(f"Capture rejected as empty or too thin ({visible_length} visible chars): {url}")
    stored = store_document(
        run_code=research_run_code, source_code=source_code,
        canonical_url=crawled["url"], title=crawled.get("title"),
        raw_text=html or markdown, normalized_text=markdown or html,
        fetch_method="CRAWL4AI", metadata=crawled.get("metadata") or {},
    )
    attach_document_to_run(
        run_code=research_run_code,
        document_id=stored["document_id"],
        discovery_query=discovery_query,
        discovery_rank=discovery_rank,
        relevance_hint=relevance_hint,
    )
    stored.update({"decision": "FETCHED_AND_STORED", "visible_length": visible_length})
    return _json(stored)


def get_research_run_status(run_code: str, reason: str = "") -> str:
    """Return the run, its plan and documents actually linked to it."""
    run = get_research_run(run_code)
    if not run:
        return _json({"error": f"Unknown research run: {run_code}"})
    documents = list_run_documents(run_code)
    return _json({"run": run, "documents": documents, "document_count": len(documents)})


def finish_research_run(
    run_code: str,
    useful_notes: str,
    executed_queries: list[str],
    coverage_summary: dict[str, Any],
    unresolved_gaps: list[str],
    reason: str = "",
) -> str:
    """Close a run using stored counts and deterministic completeness checks."""
    run = get_research_run(run_code)
    if not run:
        raise ValueError(f"Unknown research run: {run_code}")
    documents = list_run_documents(run_code)
    usable = [item for item in documents if item.get("status") not in {"FAILED", "IGNORED"}]
    metrics = run.get("run_metrics") or {}
    plan = metrics.get("research_plan") or {}
    query_budget = int(plan.get("query_budget") or 0)
    document_budget = int(plan.get("document_budget") or 0)
    executed = list(dict.fromkeys(item.strip() for item in executed_queries if item.strip()))
    planned = {_normalized_query(item) for item in plan.get("planned_queries") or []}
    unplanned = [item for item in executed if _normalized_query(item) not in planned]
    role_counts = {"buyer_firsthand": 0, "solution": 0, "counterevidence": 0, "context": 0}
    for item in usable:
        hint = item.get("relevance_hint") or ""
        for role in role_counts:
            if hint.startswith(f"[{role}]"):
                role_counts[role] += 1
                break
    if not usable:
        validity = "INVALID"
    elif (
        len(usable) < document_budget
        or len(executed) < min(query_budget, len(planned))
        or role_counts["buyer_firsthand"] < 1
    ):
        validity = "PARTIAL"
    else:
        validity = "VALID"
    closed = {
        "documents_linked": len(documents), "usable_documents": len(usable),
        "executed_queries": executed, "unplanned_queries": unplanned,
        "coverage_summary": coverage_summary, "unresolved_gaps": unresolved_gaps,
        "market_scout_notes": useful_notes, "evidence_role_counts": role_counts,
        "completion_check": {
            "query_target": query_budget, "document_target": document_budget,
            "query_count": len(executed), "document_count": len(usable),
            "counted_from_database": True,
        },
    }
    updated = update_research_run(
        run_code, status="COMPLETED", validity=validity, run_metrics=closed,
        merge_metrics=True, mark_completed=True,
    )
    return _json({
        "run_code": updated["code"], "status": updated["status"],
        "validity_computed": validity,
        "actual_document_count": len(documents),
        "usable_document_count": len(usable),
        "evidence_role_counts": role_counts,
        "unplanned_queries": unplanned,
    })
