from __future__ import annotations

from typing import Any

CAMPAIGN_RESEARCH_BRIEFS: dict[str, dict[str, Any]] = {
    "CAMP-0001": {
        "version": "ecommerce-niche-map-v0.3",
        "campaign": "E-commerce Campaign #001",
        "research_goal": "Discover narrow, recurring, economically meaningful workflows for reachable global SMB and prosumer buyers before selecting an opportunity.",
        "buyer_lenses": [
            "merchant or brand operator",
            "marketplace seller",
            "e-commerce accountant or bookkeeper",
            "operations or fulfillment manager",
            "small agency serving merchants",
        ],
        "topic_map": [
            {"id": "inventory_sync", "label": "Inventory and channel synchronization", "workflows": ["multi-channel stock updates", "overselling and stockouts", "SKU mapping", "FBA versus merchant fulfilled availability"]},
            {"id": "returns_refunds", "label": "Returns, refunds and exchanges", "workflows": ["cross-period refunds", "return restocking", "refund exceptions", "exchange accounting"]},
            {"id": "payout_accounting", "label": "Payout reconciliation and accounting", "workflows": ["net payout reconciliation", "fees and reserves", "negative payouts", "multi-processor month close"]},
            {"id": "fulfillment_3pl", "label": "Fulfillment and 3PL operations", "workflows": ["rate-card comparison", "invoice audit", "receiving discrepancies", "claims and lost inventory"]},
            {"id": "listing_catalog", "label": "Listings and catalog operations", "workflows": ["bulk listing updates", "variant and attribute mapping", "marketplace policy errors", "content localization"]},
            {"id": "orders_exceptions", "label": "Order and exception operations", "workflows": ["order routing", "fraud review", "address correction", "cancellation and backorder handling"]},
            {"id": "support_postpurchase", "label": "Customer support and post-purchase work", "workflows": ["where-is-my-order requests", "delivery complaints", "refund status", "escalations and chargebacks"]},
            {"id": "procurement_replenishment", "label": "Procurement and replenishment", "workflows": ["purchase-order planning", "supplier lead times", "MOQ and cash constraints", "forecast overrides"]},
            {"id": "tax_compliance", "label": "Tax and compliance operations", "workflows": ["sales-tax registration and filing", "marketplace facilitator reconciliation", "VAT and customs records", "product compliance evidence"]},
            {"id": "analytics_reporting", "label": "Reporting and decision support", "workflows": ["true profit by SKU", "channel attribution", "cash-flow visibility", "data export and spreadsheet consolidation"]},
        ],
        "source_priority": {
            "tier_a": ["firsthand seller or operator posts", "public support forums with original author and replies", "app and competitor reviews", "public job descriptions showing manual work", "GitHub issues for commerce tools"],
            "tier_b": ["independent practitioner posts", "public videos or social discussions with attributable comments", "official product documentation for solution and counterevidence"],
            "tier_c_discovery_only": ["vendor SEO pages", "affiliate comparisons", "AI summaries", "unattributed listicles"],
        },
        "collection_fields": [
            "buyer and operator role", "platform and workflow", "specific problem",
            "frequency or volume", "labor, loss or operational impact",
            "current workaround or paid tool", "outcome or unresolved gap",
            "author, publication date and exact source passage",
            "independence from other evidence", "counterevidence and native platform solution",
        ],
        "rules": [
            "Search snippets are discovery leads and never evidence.",
            "Retain the original source before interpreting it.",
            "Do not count vendor content as buyer demand.",
            "Do not count reposts or repeated posts by one author as independent evidence.",
            "Collect confirming, contradicting, existing-solution and native-solution evidence.",
            "Check campaign memory and URL novelty before fetching.",
            "A run covers one topic or one explicit cross-topic survey slice.",
            "Stop when the run budget is reached or new searches stop adding useful coverage.",
        ],
        "default_budget": {"query_budget": 6, "document_budget": 10, "source_type_target": 3, "max_minutes": 20},
    }
}

def get_research_brief(campaign_code: str) -> dict[str, Any]:
    brief = CAMPAIGN_RESEARCH_BRIEFS.get(campaign_code)
    if brief is not None:
        return brief
    return {
        "version": "generic-v0.1",
        "campaign": campaign_code,
        "research_goal": "Discover source-backed market problems within the campaign objective.",
        "buyer_lenses": [], "topic_map": [], "source_priority": {}, "collection_fields": [],
        "rules": ["Read campaign memory before searching.", "Search snippets are not evidence.", "Check URL novelty before fetching."],
        "default_budget": {"query_budget": 5, "document_budget": 8, "source_type_target": 2, "max_minutes": 20},
    }
