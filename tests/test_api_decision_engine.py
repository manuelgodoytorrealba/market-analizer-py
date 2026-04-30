import json
import unittest
from dataclasses import dataclass
from datetime import datetime
from unittest.mock import patch

from app.models.entities import Opportunity
from app.api.api import decision_engine_endpoint
from app.services.deal_validator import DealValidation


@dataclass(frozen=True)
class FakeBuyPlan:
    capital_available: float
    capital_used_total: float
    capital_remaining: float
    expected_profit_total: float
    roi_total: float
    items: list[dict]


@dataclass(frozen=True)
class FakeDecisionEngineResult:
    opportunities: list[Opportunity]
    shortlist: list[Opportunity]
    buy_plan: FakeBuyPlan
    validation: list[dict]
    shortlist_rejections: list[dict]
    capital_rejections: list[dict]


class DecisionEngineApiTests(unittest.TestCase):
    def test_decision_engine_endpoint_returns_frontend_payload(self) -> None:
        opportunity = Opportunity(
            id=1,
            title="MacBook Pro M1 2020 Plata",
            source="wallapop",
            buy_price=420.0,
            estimated_sale_price=514.5,
            estimated_resale_price=514.5,
            expected_profit=87.5,
            profit_estimate=87.5,
            score=227.77,
            confidence="high",
            url="https://example.com/macbook",
            created_at=datetime(2026, 4, 30, 12, 0, 0),
            evidence_json=json.dumps({"roi": 0.2083, "risk_score": 2.94}),
        )
        result = FakeDecisionEngineResult(
            opportunities=[opportunity],
            shortlist=[opportunity],
            buy_plan=FakeBuyPlan(
                capital_available=500.0,
                capital_used_total=420.0,
                capital_remaining=80.0,
                expected_profit_total=87.5,
                roi_total=0.2083,
                items=[
                    {
                        "title": opportunity.title,
                        "buy_price": 420.0,
                        "capital_used": 420.0,
                    }
                ],
            ),
            validation=[
                {
                    "opportunity": opportunity,
                    "validation": DealValidation(
                        safe_to_buy=True,
                        warnings=["verificar bateria"],
                        confidence_manual="high",
                        notes="Buen candidato.",
                    ),
                }
            ],
            shortlist_rejections=[],
            capital_rejections=[],
        )

        with patch("app.api.api.build_decision_engine", return_value=result):
            payload = decision_engine_endpoint()

        self.assertEqual(payload["summary"]["capital_available"], 500.0)
        self.assertEqual(payload["summary"]["capital_used"], 420.0)
        self.assertEqual(payload["opportunities"][0]["title"], opportunity.title)
        self.assertEqual(payload["opportunities"][0]["evidence"]["roi"], 0.2083)
        self.assertEqual(payload["buy_plan"][0]["buy_price"], 420.0)
        self.assertTrue(payload["validation"][0]["validation"]["safe_to_buy"])


if __name__ == "__main__":
    unittest.main()
