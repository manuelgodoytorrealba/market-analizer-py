import unittest

from app.services.normalizer import (
    build_comparable_key,
    detect_category,
    detect_category_confidence,
    detect_subcategory,
)
from app.services.query_builder import build_query_catalog, build_wallapop_queries


class QueryBuilderNormalizerTests(unittest.TestCase):
    def test_query_catalog_contains_multi_category_markets(self) -> None:
        catalog = build_query_catalog()

        self.assertIn("consoles", catalog)
        self.assertIn("gpus", catalog)
        self.assertIn("laptops", catalog)
        self.assertIn("audio", catalog)
        self.assertIn("ps5 digital", catalog["consoles"])
        self.assertIn("rtx 3070", catalog["gpus"])
        self.assertIn("macbook pro m1", catalog["laptops"])
        self.assertIn("sony wh-1000xm5", catalog["audio"])
        self.assertEqual(len(build_wallapop_queries()), len(set(build_wallapop_queries())))

    def test_normalizer_detects_category_and_confidence(self) -> None:
        self.assertEqual(detect_category("RTX 3070 8GB", "rtx 3070"), "gpus")
        self.assertEqual(detect_category("PS5 Digital Edition", "ps5 digital"), "consoles")
        self.assertEqual(detect_category("MacBook Pro M2", "macbook pro m2"), "laptops")
        self.assertGreater(detect_category_confidence("RTX 3070 8GB", "rtx 3070"), 0.7)

    def test_comparable_key_is_category_specific(self) -> None:
        self.assertEqual(build_comparable_key("RTX 3070 Ti", "rtx 3070 ti"), "rtx 3070 ti__working")
        self.assertEqual(build_comparable_key("RTX 3080", "rtx 3080"), "rtx 3080__working")
        self.assertEqual(build_comparable_key("PS5 Digital Edition", "ps5 digital"), "ps5 digital__full_console")
        self.assertEqual(build_comparable_key("PS5 con lector", "ps5"), "ps5__full_console")
        self.assertEqual(
            build_comparable_key("MacBook Pro 14 M1", "macbook pro 14 m1"),
            "macbook pro 14 m1__full_laptop",
        )
        self.assertEqual(build_comparable_key("Sony WH-1000XM5", "sony wh-1000xm5"), "sony wh-1000xm5")

    def test_comparable_key_includes_subcategory(self) -> None:
        self.assertEqual(
            detect_subcategory("Sony A7 III solo cuerpo", "sony a7 iii"),
            "camera_body",
        )
        self.assertEqual(
            detect_subcategory("Sony A7 III con lente 28-70", "sony a7 iii"),
            "camera_kit",
        )
        self.assertEqual(
            build_comparable_key("Sony A7 III solo cuerpo", "sony a7 iii"),
            "sony a7 iii__camera_body",
        )
        self.assertEqual(
            build_comparable_key("Sony A7 III con lente 28-70", "sony a7 iii"),
            "sony a7 iii__camera_kit",
        )
        self.assertEqual(
            build_comparable_key("Canon EOS R5", "canon eos r"),
            "canon eos r5__camera_body",
        )
        self.assertEqual(
            build_comparable_key("Pantalla MacBook Pro M1", "macbook pro m1"),
            "macbook pro m1__parts",
        )
        self.assertEqual(
            build_comparable_key("iPhone 13 128GB pantalla rota", "iphone 13 128gb"),
            "iphone 13 128gb__damaged",
        )


if __name__ == "__main__":
    unittest.main()
