# Market Analyzer Architecture

Market Analyzer detects resale opportunities by turning marketplace listings into explainable buy decisions.

The current production flow is:

```text
scraper/provider -> listings -> normalizer -> persistence -> analyzer -> opportunities -> decision layers -> dashboard/inspect
```

## Current Structure

The backend is organized by responsibility:

```text
app/
  api/                   # FastAPI routers for dashboard pages and JSON endpoints
  core/                  # settings and environment variables
  db/                    # SQLAlchemy engine, session and lightweight SQLite migrations
  models/                # database models: Listing, Opportunity, ScrapeRun
  scrapers/              # Wallapop, eBay and browser helpers
  services/              # business logic and pipeline services
  templates/             # server-rendered dashboard templates
  static/                # CSS/static assets
scripts/                 # operational scripts
tests/                   # unit tests
docs/                    # architecture and onboarding docs
```

Important files:

```text
app/core/config.py
app/db/session.py
app/models/entities.py
app/api/api.py
app/api/dashboard.py
app/services/decision_engine.py
```

The optional future `app/domain/` package can be introduced if business entities grow beyond the current service layer.

## Layer Responsibilities

Scrapers fetch external marketplace data. They should return structured listing candidates and avoid persistence, scoring or UI decisions.

Normalizer standardizes listings. It owns `normalized_name`, `comparable_key`, `category`, `subcategory` and category-specific cleaning.

Persistence stores listings, scrape runs and opportunities. It owns insert/update/deactivate behavior and schema compatibility.

Analyzer calculates market opportunities. It groups comparable listings, estimates market reference prices, computes risk/market/capital signals and writes explainable `evidence_json`.

Buy Shortlist filters analyzer output into realistic buy candidates.

Capital Strategy turns buy candidates into a capital-limited buy plan.

Deal Validator adds final manual warnings before money changes hands.

API will expose prepared data to a frontend. It should consume services, not duplicate business rules.

Templates render current dashboard views. They should not contain business logic.

## Database Tables

`listings` stores marketplace listings:

- source and external id
- title, normalized name, price and URL
- image/location/search metadata
- active status and timestamps

`opportunities` stores analyzer output:

- buy price, estimated resale price and profit
- score, confidence and comparable count
- opportunity type and source listing references
- `reasoning_summary`
- `evidence_json` with market, risk, speed, capital and decision signals

`scrape_runs` stores scraper execution summaries:

- source and status
- query counts and listing counts
- errors and summary JSON
- start/end timestamps

## Known Data Gaps

The schema does not yet store full listing descriptions as first-class columns.

Seller signals are limited. Future versions should persist seller profile, seller type, seller rating and location consistency when available.

Deal validation currently reads description/snippet only if it exists inside `evidence_json`.

No schema change is included in this phase.
