from __future__ import annotations

import time
from typing import Any

import httpx

from app.settings import get_settings


def _markdown_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        for key in ("fit_markdown", "raw_markdown", "markdown_with_citations"):
            candidate = value.get(key)
            if isinstance(candidate, str) and candidate.strip():
                return candidate
    return ""


def _extract_result(data: dict[str, Any]) -> dict[str, Any] | None:
    results = data.get("results")
    if isinstance(results, list) and results:
        first = results[0]
        return first if isinstance(first, dict) else None

    result = data.get("result")
    if isinstance(result, dict):
        return result

    return None


def _auth_headers() -> dict[str, str]:
    token = get_settings().crawl4ai_api_token.strip()
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}


def crawl_url(url: str) -> dict[str, Any]:
    settings = get_settings()
    base_url = settings.crawl4ai_base_url.rstrip("/")
    headers = _auth_headers()

    with httpx.Client(timeout=settings.crawl_timeout_seconds, headers=headers) as client:
        response = client.post(f"{base_url}/crawl", json={"urls": [url]})
        response.raise_for_status()
        data = response.json()

        item = _extract_result(data)
        if item is None and data.get("task_id"):
            task_id = data["task_id"]
            for _ in range(settings.crawl_poll_attempts):
                time.sleep(settings.crawl_poll_seconds)
                task_response = client.get(f"{base_url}/task/{task_id}")
                task_response.raise_for_status()
                task_data = task_response.json()
                item = _extract_result(task_data)
                if item is not None:
                    break
                if task_data.get("status") in {"failed", "error"}:
                    raise RuntimeError(f"Crawl4AI task failed: {task_data}")

        if item is None:
            raise RuntimeError(f"Crawl4AI returned no result for {url}")

        metadata = (
            item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
        )
        markdown = _markdown_text(item.get("markdown"))
        html = item.get("html") if isinstance(item.get("html"), str) else ""

        if not markdown and not html:
            raise RuntimeError(f"Crawl4AI returned empty content for {url}")

        return {
            "url": item.get("url") or url,
            "title": metadata.get("title") or item.get("title"),
            "markdown": markdown,
            "html": html,
            "metadata": metadata,
        }


def healthcheck() -> bool:
    settings = get_settings()
    base_url = settings.crawl4ai_base_url.rstrip("/")
    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.get(f"{base_url}/health")
            return response.status_code < 500
    except Exception:
        return False
