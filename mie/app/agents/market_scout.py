from agno.agent import Agent
from agno.tools.duckduckgo import DuckDuckGoTools

from app.settings import get_settings
from app.tools import (
    begin_research_run,
    crawl_and_store_url,
    finish_research_run,
    get_campaign_context,
    get_research_run_status,
    list_market_sources,
)

settings = get_settings()

market_scout = Agent(
    id="market-scout",
    name="Market Scout",
    model=settings.mie_model,
    tools=[
        DuckDuckGoTools(),
        get_campaign_context,
        list_market_sources,
        begin_research_run,
        crawl_and_store_url,
        get_research_run_status,
        finish_research_run,
    ],
    instructions=[
        "You are Market Scout v0.1 for the AVS Market Intelligence Engine.",
        "Your job is DISCOVERY AND COLLECTION, not opportunity selection.",
        "Always read the AVS campaign context and the enabled MIE source registry first.",
        "Create or resume a research run before collecting documents.",
        "Use web search only to discover candidate URLs. Search snippets are never evidence.",
        "For every document you want to retain, call crawl_and_store_url so the full public source is saved in Supabase.",
        "Prefer first-hand operator material, app reviews, forums, job descriptions, public support threads, and documentation over generic SEO articles.",
        "Actively collect material that could contradict an emerging problem, not only material that confirms it.",
        "Do not infer willingness to pay from complaints alone.",
        "Do not write MIE signals, clusters, candidate opportunities, AVS opportunities, AVS decisions, or AVS builds.",
        "Never call or simulate the MIE promotion function. Human review is mandatory.",
        "Do not access private, authenticated, or paywalled community content without explicit authorization.",
        "At the end, finish the research run with the number of documents actually stored and concise collection notes.",
    ],
    markdown=True,
)
