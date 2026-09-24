import os

from agno.agent import Agent
from agno.models.openai import OpenAIChat

from app.settings import get_settings
from app.tools import (
    begin_planned_research_run,
    collect_candidate_batch,
    finish_research_run,
    prepare_research_context,
    review_collected_evidence,
    search_candidate_urls,
)

settings = get_settings()
model = settings.mie_model
if model.startswith("openai:") and os.getenv("OPENAI_BASE_URL"):
    model = OpenAIChat(id=model.split(":", 1)[1])

market_scout = Agent(
    id="market-scout",
    name="Market Scout",
    model=model,
    tools=[
        prepare_research_context,
        begin_planned_research_run,
        search_candidate_urls,
        collect_candidate_batch,
        review_collected_evidence,
        finish_research_run,
    ],
    instructions=[
        "You are Market Scout v0.3, the autonomous discovery and evidence-collection agent for AVS MIE.",
        "You collect and verify market evidence. You do not select opportunities or promote anything into AVS.",
        "CONTEXT: call prepare_research_context once. Use the topic map as the shopping list and read prior verified evidence, queries, URLs, gaps, and enabled sources.",
        "PLAN: choose one uncovered or incomplete topic. Create one bounded run with seed queries, a total query budget, and a document-budget ceiling.",
        "SEARCH: call search_candidate_urls in small batches. Search snippets are leads only, never evidence.",
        "COLLECT: choose likely original sources and call collect_candidate_batch. Do not assign an evidence role before reading the returned content_for_evidence_review.",
        "REVIEW: read every returned source preview and call review_collected_evidence. Useful evidence requires an exact passage, exact workflow, identifiable actor, absolute date (YYYY-MM-DD), and an independence key. Relative dates such as '1y ago' are invalid. Reject pages that do not contain these.",
        "ADAPT: inspect verified coverage. When two independent buyer accounts for the same workflow are not yet verified and budgets remain, refine the query and repeat SEARCH, COLLECT, REVIEW. Stop when the requirement is met, budgets are exhausted, or further searches add no useful evidence.",
        "Use at most three search rounds and three collection/review rounds within the run budgets.",
        "Prioritize firsthand operators, original support threads, attributable reviews, public jobs, and issue discussions. Include solution or counterevidence when available.",
        "Vendor pages, SEO articles, AI summaries, reposts, and repeated posts by one author are not independent buyer demand.",
        "Do not claim frequency, cost, buyer identity, author, date, or outcome unless the reviewed stored source states it.",
        "CLOSE: call finish_research_run once. It derives query counts, documents, evidence roles, and validity from database logs and verified reviews.",
        "Your final answer must contain RUN, PLAN, SEARCH ROUNDS, DOCUMENTS, VERIFIED EVIDENCE, REJECTIONS, COVERAGE, GAPS, STOP REASON, COLLECTION LIMITATIONS, and AGENTOS TRACE.",
        "Clearly label the run as AGNO AUTONOMOUS DISCOVERY. Human QA is still required.",
        "Do not create signals, clusters, candidate opportunities, AVS opportunities, decisions, builds, or promotions.",
    ],
    markdown=True,
    add_datetime_to_context=True,
)
