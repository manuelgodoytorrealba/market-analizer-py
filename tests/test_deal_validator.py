import json
import unittest

from app.models.entities import Opportunity
from app.services.deal_validator import validate_deal


class DealValidatorTests(unittest.TestCase):
    def test_marks_clean_high_conviction_listing_as_safe(self) -> None:
        opportunity = _opportunity(
            title="MacBook Pro M1 2020 Plata",
            description="MacBook en buen estado, bateria 88%, incluye cargador original.",
            risk_score=2.94,
            roi=0.2083,
        )

        validation = validate_deal(opportunity)

        self.assertTrue(validation.safe_to_buy)
        self.assertEqual(validation.confidence_manual, "high")
        self.assertIn("posible defecto: revisar 'bateria'", validation.warnings)
        self.assertIn("Buen candidato", validation.notes)

    def test_blocks_possible_scam_when_price_is_extremely_low(self) -> None:
        opportunity = _opportunity(
            title="MacBook Pro M1 barato",
            description="Pago bizum y envio solo.",
            buy_price=120.0,
            p25=420.0,
            risk_score=2.0,
        )

        validation = validate_deal(opportunity)

        self.assertFalse(validation.safe_to_buy)
        self.assertEqual(validation.confidence_manual, "low")
        self.assertTrue(any(warning.startswith("posible scam") for warning in validation.warnings))

    def test_poor_listing_lowers_manual_confidence(self) -> None:
        opportunity = _opportunity(
            title="iPhone 15",
            description="",
            risk_score=4.8,
        )

        validation = validate_deal(opportunity)

        self.assertTrue(validation.safe_to_buy)
        self.assertEqual(validation.confidence_manual, "medium")
        self.assertIn("listing pobre", validation.warnings[0])


def _opportunity(
    *,
    title: str,
    description: str,
    buy_price: float = 420.0,
    p25: float = 390.0,
    risk_score: float = 2.0,
    roi: float = 0.25,
) -> Opportunity:
    evidence = {
        "title": title,
        "description": description,
        "item_price": buy_price,
        "risk_score": risk_score,
        "roi": roi,
        "p25": p25,
        "category": "laptops",
        "subcategory": "full_laptop",
        "speed_category": "medium",
    }
    return Opportunity(
        title=title,
        source="wallapop",
        buy_price=buy_price,
        estimated_sale_price=520.0,
        expected_profit=80.0,
        profit_estimate=80.0,
        score=120.0,
        confidence="high",
        url="https://example.com",
        evidence_json=json.dumps(evidence),
    )


if __name__ == "__main__":
    unittest.main()
