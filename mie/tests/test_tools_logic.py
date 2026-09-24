import json
import unittest
from unittest.mock import patch

from app import tools


class MarketScoutToolTests(unittest.TestCase):
    def test_query_similarity_detects_near_duplicate(self):
        left = "shopify payout reconciliation quickbooks refunds"
        near = "quickbooks shopify payout refund reconciliation"
        far = "amazon listing localization policy errors"
        self.assertGreaterEqual(tools._query_similarity(left, near), 0.86)
        self.assertLess(tools._query_similarity(left, far), 0.2)

    def test_review_requires_passage_in_stored_content(self):
        run = {"run_metrics": {}}
        document = {
            "id": "doc-1",
            "canonical_url": "https://example.com/thread",
            "title": "Merchant thread",
            "normalized_text": "I spend three hours every Friday reconciling Shopify payouts.",
        }
        captured = {}
        def update(_code, **kwargs):
            captured.update(kwargs)
            return {"code": "RUN-TEST"}

        with (
            patch.object(tools, "get_research_run", return_value=run),
            patch.object(tools, "list_run_documents", return_value=[{"id": "doc-1"}]),
            patch.object(tools, "get_document_by_id", return_value=document),
            patch.object(tools, "update_research_run", side_effect=update),
        ):
            result = json.loads(tools.review_collected_evidence(
                "RUN-TEST",
                [tools.EvidenceReview(
                    document_id="doc-1",
                    useful=True,
                    evidence_role="buyer_firsthand",
                    workflow="weekly payout reconciliation",
                    exact_passage="This quote is not in the source.",
                    source_actor="Shopify merchant",
                    source_date="2026-09-01",
                    independence_key="merchant-a",
                )],
            ))
        self.assertFalse(result["results"][0]["accepted"])
        self.assertEqual(captured["run_metrics"]["evidence_reviews"], [])

    def test_optional_review_fields_accept_null(self):
        review = tools.EvidenceReview(
            document_id="doc-1",
            useful=False,
            evidence_role="rejected",
            workflow="",
            exact_passage=None,
            source_actor=None,
            source_date=None,
            independence_key=None,
            rejection_reason=None,
        )
        self.assertIsNone(review.rejection_reason)

    def test_finish_valid_requires_two_independent_buyers_same_workflow(self):
        reviews = [
            {
                "document_id": "doc-1", "useful": True, "passage_verified": True,
                "evidence_role": "buyer_firsthand", "workflow": "payout reconciliation",
                "independence_key": "merchant-a", "actor_key": "merchant-a",
                "actor_verified": True, "date_verified": True,
            },
            {
                "document_id": "doc-2", "useful": True, "passage_verified": True,
                "evidence_role": "buyer_firsthand", "workflow": "payout reconciliation",
                "independence_key": "merchant-b", "actor_key": "merchant-b",
                "actor_verified": True, "date_verified": True,
            },
        ]
        run = {
            "run_metrics": {
                "research_plan": {"query_budget": 4, "document_budget": 6},
                "search_log": [{"query": "q1"}, {"query": "q2"}],
                "evidence_reviews": reviews,
            }
        }
        captured = {}
        def update(_code, **kwargs):
            captured.update(kwargs)
            return {"code": "RUN-TEST"}

        with (
            patch.object(tools, "get_research_run", return_value=run),
            patch.object(tools, "list_run_documents", return_value=[
                {"id": "doc-1", "status": "NORMALIZED"},
                {"id": "doc-2", "status": "NORMALIZED"},
            ]),
            patch.object(tools, "update_research_run", side_effect=update),
        ):
            result = json.loads(tools.finish_research_run(
                "RUN-TEST",
                useful_notes="test",
                coverage_summary="two buyer accounts",
                unresolved_gaps=[],
                stop_reason="evidence threshold reached",
            ))
        self.assertEqual(result["validity_computed"], "VALID")
        self.assertEqual(result["queries_executed_from_tool_log"], ["q1", "q2"])
        self.assertEqual(captured["validity"], "VALID")


if __name__ == "__main__":
    unittest.main()
