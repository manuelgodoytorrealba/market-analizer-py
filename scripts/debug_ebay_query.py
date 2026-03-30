import argparse
import json
import logging

from app.scrapers.ebay import EbayScraper


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Debug a single eBay query")
    parser.add_argument("query", help="Search query to debug")
    parser.add_argument(
        "--relax-filters",
        action="store_true",
        help="Disable auction filtering during debug comparison",
    )
    args = parser.parse_args()

    scraper = EbayScraper(debug=True)
    result = scraper.debug_scrape(args.query, relax_filters=args.relax_filters)

    print("\n=== EBAY DEBUG SUMMARY ===")
    print(f"query: {result['query']}")
    print(f"page_title: {result['page_title']}")
    print(f"html_saved: {result['saved_path']}")
    print(f"used_mobile_fallback: {result['used_mobile_fallback']}")
    print(f"strategy_counts: {json.dumps(result['strategy_counts'], ensure_ascii=False)}")
    print(f"raw_candidates: {result['raw_candidates']}")
    print(f"auction_filtered: {result['auction_filtered']}")
    print(f"invalid_filtered: {result['invalid_filtered']}")
    print(f"valid_results: {len(result['results'])}")
    for item in result["results"][:5]:
        print(
            f"- {item['title']} | {item['price']} | {item['location']} | {item['url']}"
        )


if __name__ == "__main__":
    main()
