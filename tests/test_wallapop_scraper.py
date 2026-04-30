from app.scrapers.wallapop import WallapopScraper

scraper = WallapopScraper(debug=True)

for query in ["iphone 13 128gb", "ps5", "nintendo switch", "macbook air m1"]:
    result = scraper.debug_scrape(query)

    print("\nQUERY:", query)
    print("raw_candidates:", result.get("raw_candidates"))
    print("valid_results:", len(result.get("results", [])))
    print("discard_reasons:", result.get("discard_reasons"))
    print("saved_path:", result.get("saved_path"))

    for item in result.get("results", [])[:3]:
        print("-", item["title"], item["price"], item["url"])
