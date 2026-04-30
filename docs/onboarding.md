# Onboarding

Welcome to Market Analyzer. The project helps find things on Wallapop that might be worth buying and reselling.

The goal is not to find every cheap item. The goal is to find the few items that are cheap, sellable and not too risky.

## What The System Does

In simple terms:

1. It searches Wallapop.
2. It cleans product names so similar products can be compared.
3. It stores listings in the database.
4. It calculates market prices and profit.
5. It filters down to realistic buy candidates.
6. It decides what to buy with limited capital.
7. It gives a final checklist before buying.

## Main Parts

Scrapers get data from marketplaces.

Normalizer cleans names and decides category/subcategory.

Persistence saves listings and opportunities.

Analyzer finds possible opportunities using market signals.

BUY SHORTLIST keeps only serious buy candidates.

CAPITAL STRATEGY decides what to buy with the available budget.

DEAL VALIDATOR gives manual warnings before spending money.

## Setup

From the project root:

```bash
python3 scripts/setup.py
```

If the database does not exist:

```bash
.venv/bin/python scripts/init_db.py
```

## Run A Full Cycle

Scrape Wallapop and refresh opportunities:

```bash
python3 scripts/run_scrapers.py --source wallapop
```

Inspect results:

```bash
python3 scripts/inspect_opportunities.py
```

## How To Read The Output

`TOP OPPORTUNITIES (ALL)` shows analyzer results. These can still include risky items, slow markets or listings with weak confidence.

`BUY SHORTLIST (REAL DECISIONS)` shows opportunities that passed stronger business filters.

`BUY PLAN (CAPITAL 500EUR)` shows what the system would actually buy with the configured capital.

`DEAL VALIDATION` shows the final manual checklist before paying.

`DISCARDED FROM BUY SHORTLIST` explains why top analyzer items were rejected.

## Real Example

With `500 EUR`, the system currently chooses:

```text
MacBook Pro M1 2020 Plata
Buy: 420 EUR
Expected profit: 87.50 EUR
Capital remaining: 80 EUR
Portfolio ROI: 0.21
```

Why?

It has high confidence, low risk, medium market speed and enough ROI. Because it is high conviction, CAPITAL STRATEGY allows a larger allocation than usual.

What still needs manual checking?

- battery health
- physical condition
- charger included
- serial number and lock/MDM status
- more photos if the listing is short

The system says: this is buyable, but do the checklist before paying.

## Useful Commands

Run tests that are relevant to the decision layers:

```bash
PYTHONPATH=. .venv/bin/python -m unittest \
  tests.test_buy_shortlist \
  tests.test_capital_strategy \
  tests.test_deal_validator \
  tests.test_decision_engine \
  -v
```

Compile Python files:

```bash
PYTHONPATH=. .venv/bin/python -m compileall app scripts tests
```

Change available capital:

```bash
MARKET_ANALYZER_CAPITAL_AVAILABLE=800 python3 scripts/inspect_opportunities.py
```

## Rules For New Development

Do not put business logic in templates.

Do not scrape inside dashboard or API handlers.

Do not change analyzer thresholds without explaining the business impact.

Keep changes small and testable.

When in doubt, follow the data:

```text
scraper -> normalizer -> database -> analyzer -> shortlist -> capital -> validation
```
