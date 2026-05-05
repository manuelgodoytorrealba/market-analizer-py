

⸻

🧠 Market Analyzer — Onboarding

⸻

⚡ TL;DR (30s mental model)

Find → Analyze → Filter → Decide → Validate → Buy

Market Analyzer is not a scraper.

It is a decision system that answers:

👉 Should I buy this item to resell it?

⸻

🧠 Product Definition (Phase 0 — Manuel)

⸻

🎯 Vision

Build a system that:

* finds real reselling opportunities
* filters noise, scams and low-quality deals
* prioritizes high-confidence decisions
* uses capital efficiently
* reduces manual thinking

⸻

💡 What Is A Real Opportunity?

A “real opportunity” is NOT just a cheap product.

It must pass business constraints:

✔ Profit ≥ 30€
✔ ROI ≥ 30%
✔ High liquidity (fast resale)
✔ Medium or low risk
✔ Enough comparables (confidence)

⸻

🚫 If any of these fail:

→ NOT a real opportunity

⸻

🧪 Mental Filter (quick decision)

Is it cheap? → ❌ not enough
Is it profitable? → 🟡 maybe
Is it sellable FAST? → ✅ now we care
Is risk controlled? → ✅ now it's real

⸻

⚠️ Current Limitations

Right now the system is:

Wallapop → internal comparison

So:

* ❌ no cross-market validation
* ❌ liquidity is estimated
* ❌ risk is heuristic
* ❌ profit can be optimistic
* ❌ confidence is not fully modeled

⸻

🧭 Product Direction

We are building:

multi-market intelligence platform

Future:

* Wallapop ↔ eBay validation
* real liquidity signals
* better risk scoring
* capital optimization
* confidence-based ranking

⸻

🧱 Product Philosophy

Always prefer:

✔ fewer but better opportunities
✔ explainable decisions
✔ realistic profit
✔ capital protection

⸻

🔄 What The System Does

⸻

1. Scrape → get listings
2. Normalize → clean product names
3. Store → database
4. Analyze → find signals
5. Filter → shortlist real deals
6. Decide → allocate capital
7. Validate → final checklist

⸻

🧩 Main Parts (System Map)

⸻

🕷 Scrapers

Get data from marketplaces.

⸻

🧼 Normalizer

Turns messy titles into comparable products.

"iphone 13 pro 128gb azul como nuevo"
→ iPhone 13 Pro 128GB

⸻

💾 Persistence

Stores listings and opportunities.

⸻

📊 Analyzer

Finds possible opportunities using:

* price gaps
* comparables
* market signals

⸻

🎯 BUY SHORTLIST

Filters to real buy candidates

⸻

💰 CAPITAL STRATEGY

Answers:

What should I buy with limited money?

⸻

⚠️ DEAL VALIDATOR

Final human checklist before paying.

⸻

🧠 Decision Flow (IMPORTANT)

⸻

Listings
  ↓
Analyzer (many ideas)
  ↓
Shortlist (serious only)
  ↓
Capital Strategy (what to buy)
  ↓
Deal Validator (human sanity check)

⸻

🚀 Setup

From project root:

python3 scripts/setup.py

If DB does not exist:

.venv/bin/python scripts/init_db.py

⸻

🔁 Run Full Cycle

⸻

1. Scrape

python3 scripts/run_scrapers.py --source wallapop

⸻

2. Inspect

python3 scripts/inspect_opportunities.py

⸻

📊 How To Read The Output

⸻

🔝 TOP OPPORTUNITIES (ALL)

🟡 raw analyzer output
⚠️ can include risky or weak deals

⸻

🟢 BUY SHORTLIST (REAL DECISIONS)

✅ filtered with business rules
👉 THESE are serious candidates

⸻

💰 BUY PLAN (CAPITAL)

🧠 final decision with money constraints

⸻

⚠️ DEAL VALIDATION

🔍 final checklist before buying

⸻

❌ DISCARDED

💡 explains WHY things were rejected

⸻

🧪 Real Example

⸻

MacBook Pro M1 2020
Buy: 420€
Expected profit: 87.50€
ROI: 21%

⸻

🤔 Why selected?

* high confidence
* low risk
* medium liquidity
* strong signal

⸻

⚠️ Still check manually:

* battery health
* physical condition
* charger
* serial / MDM lock
* real photos

⸻

System says: BUYABLE
Human says: VERIFY

⸻

🧰 Useful Commands

⸻

Run decision-layer tests

PYTHONPATH=. .venv/bin/python -m unittest \
  tests.test_buy_shortlist \
  tests.test_capital_strategy \
  tests.test_deal_validator \
  tests.test_decision_engine \
  -v

⸻

Compile code

PYTHONPATH=. .venv/bin/python -m compileall app scripts tests

⸻

Change capital

MARKET_ANALYZER_CAPITAL_AVAILABLE=800 \
python3 scripts/inspect_opportunities.py

⸻

🧪 Quick Health Check (DEV)

⸻

✔ init-db works
✔ scrapers return data
✔ analyzer produces output
✔ shortlist is not empty
✔ capital strategy runs

⸻

📏 Rules For Development

⸻

❌ DO NOT

* put logic in templates
* scrape inside API/dashboard
* change thresholds without reason

⸻

✅ DO

* keep logic in services
* keep changes small
* test decision layers
* follow the pipeline

⸻

scraper → normalizer → database → analyzer → shortlist → capital → validation

⸻

🧠 Final Mental Model

⸻

This is NOT a scraper.
This is a system that protects your money.

⸻

Bad system → buys everything cheap
Good system → buys only what sells
Great system → buys only what is safe + profitable

⸻


