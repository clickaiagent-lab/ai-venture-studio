from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any, Literal

from ddgs import DDGS
from pydantic import BaseModel, Field

from app.crawl4ai_client import crawl_url
from app.research_briefs import get_research_brief as load_research_brief
from app.supabase_repo import (
    attach_document_to_run,
    ensure_research_run,
    find_document_by_url,
    get_document_by_id,
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


def _normalized_text(value: str) -> str:
    return " ".join((value or "").lower().split())


def _iso_source_date(value: str) -> str | None:
    raw = (value or "").strip()
    if not raw:
        return None
    candidate = raw[:10]
    try:
        return datetime.strptime(candidate, "%Y-%m-%d").date().isoformat()
    except ValueError:
        pass
    for fmt in ("%b %d, %Y", "%B %d, %Y"):
        try:
            return datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _actor_key(value: str) -> str:
    return _normalized_text(re.split(r"\s*\(", value or "", maxsplit=1)[0])


def _query_tokens(query: str) -> set[str]:
    tokens = set()
    for token in re.findall(r"[a-z0-9]+", (query or "").lower()):
        if len(token) > 4 and token.endswith("s"):
            token = token[:-1]
        if len(token) > 2:
            tokens.add(token)
    return tokens


def _query_similarity(left: str, right: str) -> float:
    a, b = _query_tokens(left), _query_tokens(right)
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _document_preview(document: dict[str, Any], max_chars: int = 8000) -> dict[str, Any]:
    content = document.get("normalized_text") or ""
    metadata = document.get("metadata") or {}
    published_at = (
        document.get("published_at")
        or metadata.get("published_at")
        or metadata.get("article:published_time")
        or metadata.get("datePublished")
    )
    author = document.get("author_reference") or metadata.get("author")
    return {
        "document_id": document.get("id") or document.get("document_id"),
        "url": document.get("canonical_url"),
        "title": document.get("title"),
        "author_metadata": author,
        "published_at_metadata": published_at,
        "content_length": len(content),
        "content_for_evidence_review": content[:max_chars],
        "review_rule": "Assign a role only after reading. Useful evidence needs an exact passage, verified author, and an absolute source date such as YYYY-MM-DD. Relative dates like '1y ago' are invalid.",
    }


class CandidateInput(BaseModel):
    url: str
    source_code: str
    discovery_query: str
    relevance_hint: str
    discovery_rank: int | None = None


class EvidenceReview(BaseModel):
    document_id: str
    useful: bool
    evidence_role: str = Field(description="One of buyer_firsthand, solution, counterevidence, context, rejected")
    workflow: str
    exact_passage: str | None = None
    source_actor: str | None = None
    source_date: str | None = None
    independence_key: str | None = None
    rejection_reason: str | None = None


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
        "verified_evidence_memory": memory["verified_evidence_memory"],
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
    max_results_per_query: int = 6,
    repeat_reason: str = "",
    reason: str = "",
) -> str:
    """Search in adaptive batches, persist the actual query log, and flag known URLs."""
    run = get_research_run(run_code)
    if not run:
        raise ValueError(f"Unknown research run: {run_code}")
    metrics = run.get("run_metrics") or {}
    plan = metrics.get("research_plan") or {}
    query_budget = int(plan.get("query_budget") or 0)
    search_log = list(metrics.get("search_log") or [])
    prior = [item.get("query", "") for item in search_log]
    cleaned = list(dict.fromkeys(item.strip() for item in queries if item and item.strip()))
    repeated = [
        query for query in cleaned
        if any(_normalized_query(query) == _normalized_query(old) or _query_similarity(query, old) >= 0.86 for old in prior)
    ]
    if repeated and not repeat_reason.strip():
        raise ValueError("Query already searched or near-duplicate in this run. Refine it or provide repeat_reason: " + " | ".join(repeated))
    remaining = max(0, query_budget - len(search_log))
    if not remaining:
        raise ValueError("Run query budget is exhausted.")
    cleaned = cleaned[:remaining]
    max_results_per_query = max(1, min(int(max_results_per_query), 8))
    seen_urls = {
        item.get("canonical_url")
        for item in list_campaign_documents(plan.get("campaign_code") or run.get("campaign_code") or "CAMP-0001", limit=1000)
    }
    output: list[dict[str, Any]] = []
    client = DDGS()
    for query in cleaned:
        results = client.text(query, max_results=max_results_per_query)
        compact = []
        for rank, item in enumerate(results or [], start=1):
            url = item.get("href") or item.get("url")
            compact.append({
                "rank": rank,
                "title": item.get("title"),
                "url": url,
                "already_in_campaign_memory": url in seen_urls,
                "snippet": (item.get("body") or item.get("snippet") or "")[:500],
            })
        output.append({"query": query, "results": compact})
        search_log.append({
            "query": query,
            "result_count": len(compact),
            "repeat_reason": repeat_reason.strip() or None,
        })
    update_research_run(run_code, run_metrics={"search_log": search_log}, merge_metrics=True)
    return _json({
        "run_code": run_code,
        "queries_executed_by_tool": cleaned,
        "query_budget_remaining": query_budget - len(search_log),
        "result_batches": output,
        "rule": "Snippets are leads only. Collect candidates, read returned content, then review evidence. Refine the next query when coverage is weak.",
    })


def collect_candidate_batch(
    run_code: str,
    candidates: list[CandidateInput],
    reason: str = "",
) -> str:
    """Collect candidates within the budget and return source content for evidence review."""
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
        rank = candidate.discovery_rank
        if source_code not in allowed_sources:
            results.append({"decision": "REJECTED_INPUT", "url": url, "reason": f"source {source_code} is outside run scope"})
            continue
        existing = find_document_by_url(url)
        if existing:
            attach_document_to_run(
                run_code=run_code, document_id=existing["id"],
                discovery_query=query, discovery_rank=rank,
                relevance_hint=f"[unreviewed] {hint}",
            )
            results.append({"decision": "REUSED", **_document_preview(existing)})
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
                discovery_query=query, discovery_rank=rank,
                relevance_hint=f"[unreviewed] {hint}",
            )
            document = get_document_by_id(stored["document_id"]) or {
                **stored, "id": stored["document_id"], "normalized_text": markdown or html,
            }
            results.append({"decision": "STORED", **_document_preview(document)})
            remaining -= 1
        except Exception as exc:
            results.append({"decision": "FAILED", "url": url, "error": str(exc)[:300]})
    return _json({
        "run_code": run_code,
        "document_budget_ceiling": budget,
        "document_budget_remaining": max(0, budget - len(list_run_documents(run_code))),
        "documents_before_batch": existing_count,
        "documents_after_batch": len(list_run_documents(run_code)),
        "results": results,
        "next_action": "Read content_for_evidence_review and call review_collected_evidence. Search again with refined queries if evidence is weak and budget remains.",
    })


def review_collected_evidence(
    run_code: str,
    reviews: list[EvidenceReview],
    reason: str = "",
) -> str:
    """Verify exact passages against stored content and persist post-read evidence reviews."""
    run = get_research_run(run_code)
    if not run:
        raise ValueError(f"Unknown research run: {run_code}")
    linked_ids = {item.get("id") for item in list_run_documents(run_code)}
    metrics = run.get("run_metrics") or {}
    stored_reviews = {
        item.get("document_id"): item
        for item in metrics.get("evidence_reviews") or []
        if item.get("document_id")
    }
    results: list[dict[str, Any]] = []
    allowed_roles = {"buyer_firsthand", "solution", "counterevidence", "context", "rejected"}
    for review in reviews:
        if review.document_id not in linked_ids:
            results.append({"document_id": review.document_id, "accepted": False, "reason": "document is not linked to this run"})
            continue
        role = review.evidence_role.strip().lower()
        document = get_document_by_id(review.document_id)
        if not document or role not in allowed_roles:
            results.append({"document_id": review.document_id, "accepted": False, "reason": "missing document or invalid role"})
            continue
        useful = bool(review.useful and role != "rejected")
        content_normalized = _normalized_text(document.get("normalized_text") or "")
        passage = (review.exact_passage or "").strip()
        passage_verified = bool(passage and _normalized_text(passage) in content_normalized)
        metadata = document.get("metadata") or {}
        metadata_date = _iso_source_date(str(
            document.get("published_at")
            or metadata.get("published_at")
            or metadata.get("article:published_time")
            or metadata.get("datePublished")
            or ""
        ))
        source_date_iso = _iso_source_date(review.source_date)
        date_verified = bool(
            source_date_iso
            and (
                source_date_iso == metadata_date
                or _normalized_text(review.source_date) in content_normalized
            )
        )
        actor = _actor_key(review.source_actor)
        metadata_actor = _actor_key(str(document.get("author_reference") or metadata.get("author") or ""))
        actor_verified = bool(actor and (actor == metadata_actor or actor in content_normalized))
        complete = bool(
            useful
            and passage_verified
            and actor_verified
            and date_verified
            and review.workflow.strip()
            and (review.independence_key or "").strip()
        )
        if useful and not complete:
            results.append({
                "document_id": review.document_id,
                "accepted": False,
                "reason": "useful evidence requires verified passage, workflow, identifiable actor, absolute source date, and independence_key",
                "passage_verified": passage_verified,
                "actor_verified": actor_verified,
                "date_verified": date_verified,
                "metadata_date": metadata_date,
            })
            continue
        stored = {
            "document_id": review.document_id,
            "url": document.get("canonical_url"),
            "title": document.get("title"),
            "useful": useful,
            "evidence_role": role if useful else "rejected",
            "workflow": review.workflow.strip(),
            "exact_passage": passage if passage_verified else "",
            "passage_verified": passage_verified,
            "source_actor": (review.source_actor or "").strip(),
            "actor_key": actor,
            "actor_verified": actor_verified,
            "source_date": source_date_iso or "",
            "date_verified": date_verified,
            "independence_key": (review.independence_key or "").strip(),
            "rejection_reason": (review.rejection_reason or "").strip(),
            "review_origin": "MARKET_SCOUT_POST_READ",
        }
        stored_reviews[review.document_id] = stored
        results.append({"document_id": review.document_id, "accepted": True, "useful": useful, "role": stored["evidence_role"]})
    review_list = list(stored_reviews.values())
    update_research_run(run_code, run_metrics={"evidence_reviews": review_list}, merge_metrics=True)
    return _json({
        "run_code": run_code,
        "results": results,
        "reviewed_document_count": len(review_list),
        "verified_useful_count": sum(
            1 for item in review_list
            if item.get("useful") and item.get("passage_verified")
            and item.get("actor_verified") and item.get("date_verified")
        ),
        "next_action": "Search and collect again if two independent buyer accounts for the same workflow are not yet verified and budgets remain.",
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
    verified_evidence_memory: list[dict[str, Any]] = []
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
        logged_queries = [item.get("query") for item in metrics.get("search_log") or []]
        for query in (plan.get("planned_queries") or []) + (metrics.get("executed_queries") or []) + logged_queries:
            if query and query not in studied_queries:
                studied_queries.append(query)
        for evidence in metrics.get("evidence_reviews") or []:
            if (
                evidence.get("useful")
                and evidence.get("passage_verified")
                and evidence.get("actor_verified")
                and evidence.get("date_verified")
            ):
                verified_evidence_memory.append({
                    "run_code": run.get("code"),
                    "focus_topic": topic,
                    "document_id": evidence.get("document_id"),
                    "url": evidence.get("url"),
                    "evidence_role": evidence.get("evidence_role"),
                    "workflow": evidence.get("workflow"),
                    "source_actor": evidence.get("source_actor"),
                    "source_date": evidence.get("source_date"),
                    "independence_key": evidence.get("independence_key"),
                    "exact_passage": evidence.get("exact_passage"),
                })
        for gap in metrics.get("unresolved_gaps") or []:
            if gap and gap not in unresolved_gaps:
                unresolved_gaps.append(gap)
    return _json({
        "campaign_code": campaign_code,
        "run_count": len(runs),
        "unique_document_count": len(documents),
        "topic_coverage": coverage,
        "studied_queries": studied_queries,
        "verified_evidence_memory": verified_evidence_memory[-50:],
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
    mode: Literal["DISCOVERY", "HYPOTHESIS", "DEEP_DIVE", "MONITORING"] = "DISCOVERY",
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
    prior_queries: list[str] = []
    for run in list_campaign_runs(campaign_code, limit=100):
        metrics = run.get("run_metrics") or {}
        prior_plan = metrics.get("research_plan") or {}
        logged = [item.get("query") for item in metrics.get("search_log") or []]
        prior_queries.extend(
            query for query in
            (prior_plan.get("planned_queries") or []) + (metrics.get("executed_queries") or []) + logged
            if query
        )
    repeated = [
        query for query in planned_queries
        if any(_normalized_query(query) == _normalized_query(old) or _query_similarity(query, old) >= 0.86 for old in prior_queries)
    ]
    if repeated and not repeat_reason.strip():
        raise ValueError("Queries already used or near-duplicates. Refine them or provide repeat_reason: " + " | ".join(repeated))
    research_plan = {
        "campaign_code": campaign_code,
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
    coverage_summary: str,
    unresolved_gaps: list[str],
    stop_reason: str,
    reason: str = "",
) -> str:
    """Close a run from database logs and post-read reviews, never from self-reported counts."""
    run = get_research_run(run_code)
    if not run:
        raise ValueError(f"Unknown research run: {run_code}")
    documents = list_run_documents(run_code)
    usable = [item for item in documents if item.get("status") not in {"FAILED", "IGNORED"}]
    metrics = run.get("run_metrics") or {}
    plan = metrics.get("research_plan") or {}
    search_log = metrics.get("search_log") or []
    reviews = metrics.get("evidence_reviews") or []
    linked_ids = {item.get("id") for item in usable}
    verified = [
        item for item in reviews
        if item.get("document_id") in linked_ids
        and item.get("useful")
        and item.get("passage_verified")
        and item.get("actor_verified")
        and item.get("date_verified")
    ]
    role_counts = {"buyer_firsthand": 0, "solution": 0, "counterevidence": 0, "context": 0}
    buyer_workflows: dict[str, set[str]] = {}
    for item in verified:
        role = item.get("evidence_role")
        if role in role_counts:
            role_counts[role] += 1
        if role == "buyer_firsthand":
            workflow = _normalized_text(item.get("workflow") or "")
            independent_actor = item.get("actor_key") or _actor_key(item.get("source_actor") or "")
            if workflow and independent_actor:
                buyer_workflows.setdefault(workflow, set()).add(independent_actor)
    qualified_workflows = [
        workflow for workflow, independent_sources in buyer_workflows.items()
        if len(independent_sources) >= 2
    ]
    reviewed_ids = {item.get("document_id") for item in reviews}
    unreviewed_ids = sorted(item for item in linked_ids if item not in reviewed_ids)
    if not usable or not reviews:
        validity = "INVALID"
    elif qualified_workflows:
        validity = "VALID"
    else:
        validity = "PARTIAL"
    executed = [item.get("query") for item in search_log if item.get("query")]
    closed = {
        "documents_linked": len(documents),
        "usable_documents": len(usable),
        "executed_queries": executed,
        "coverage_summary": coverage_summary,
        "unresolved_gaps": unresolved_gaps,
        "market_scout_notes": useful_notes,
        "stop_reason": stop_reason,
        "evidence_role_counts": role_counts,
        "qualified_workflows": qualified_workflows,
        "unreviewed_document_ids": unreviewed_ids,
        "completion_check": {
            "query_budget_ceiling": int(plan.get("query_budget") or 0),
            "document_budget_ceiling": int(plan.get("document_budget") or 0),
            "queries_executed_from_tool_log": len(executed),
            "documents_counted_from_database": len(usable),
            "verified_evidence_count": len(verified),
            "valid_requires_two_independent_buyer_accounts_same_workflow": True,
        },
    }
    updated = update_research_run(
        run_code, status="COMPLETED", validity=validity, run_metrics=closed,
        merge_metrics=True, mark_completed=True,
    )
    return _json({
        "run_code": updated["code"],
        "status": updated.get("status", "COMPLETED"),
        "validity_computed": validity,
        "validity_meaning": "VALID means collection has two verified independent buyer accounts for at least one exact workflow; human QA is still required.",
        "actual_document_count": len(documents),
        "usable_document_count": len(usable),
        "verified_evidence_count": len(verified),
        "evidence_role_counts": role_counts,
        "qualified_workflows": qualified_workflows,
        "unreviewed_document_ids": unreviewed_ids,
        "queries_executed_from_tool_log": executed,
    })
