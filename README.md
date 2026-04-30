# Market Analyzer

Market Analyzer detects resale opportunities by comparing real marketplace listings against market reference prices.

The current focus is Wallapop flipping: fewer false positives, better evidence and decisions that can be reviewed before spending real money.

## What It Does

The pipeline is:

```text
scraper -> normalizer -> persistence -> analyzer -> shortlist -> capital strategy -> deal validator
```

It can:

- scrape marketplace listings
- normalize products by category and subcategory
- group comparable products
- estimate market price, profit, ROI, risk and speed
- build a buy shortlist
- build a capital-aware buy plan
- show final manual warnings before buying

## Install

```bash
python3 scripts/setup.py
```

Initialize the database if needed:

```bash
.venv/bin/python scripts/init_db.py
```

## Run

Run a Wallapop cycle:

```bash
python3 scripts/run_scrapers.py --source wallapop
```

Inspect opportunities and buy decisions:

```bash
python3 scripts/inspect_opportunities.py
```

## Understand Results

The inspector prints:

- `TOP OPPORTUNITIES (ALL)`: raw analyzer opportunities ordered by score
- `BUY SHORTLIST (REAL DECISIONS)`: opportunities that passed hard buy filters
- `BUY PLAN (CAPITAL 500EUR)`: what to buy with current capital
- `DEAL VALIDATION`: final warnings/checklist before paying
- `DISCARDED FROM BUY SHORTLIST`: rejected opportunities and reasons

## Configuration

Useful environment variables:

```bash
MARKET_ANALYZER_CAPITAL_AVAILABLE=500
MARKET_ANALYZER_HIGH_CONVICTION_BUY_SCORE=30
MARKET_ANALYZER_HIGH_CONVICTION_MAX_RATIO=0.85
```

Example:

```bash
MARKET_ANALYZER_CAPITAL_AVAILABLE=800 python3 scripts/inspect_opportunities.py
```

## Decision Engine

The future frontend/API should consume:

```text
app/services/decision_engine.py
```

It coordinates:

```text
opportunities -> shortlist -> buy plan -> deal validation
```

## Docs

- [Architecture](docs/architecture.md)
- [Decision Engine](docs/decision-engine.md)
- [Onboarding](docs/onboarding.md)

## Tests

Compile:

```bash
PYTHONPATH=. .venv/bin/python -m compileall app scripts tests
```

Focused decision-layer tests:

```bash
PYTHONPATH=. .venv/bin/python -m unittest \
  tests.test_buy_shortlist \
  tests.test_capital_strategy \
  tests.test_deal_validator \
  tests.test_decision_engine \
  -v
```
