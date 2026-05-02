# Decision Engine

The Decision Engine is the backend facade for future frontend/API consumption.

It does not replace the analyzer. It coordinates the existing decision layers:

```text
opportunities
  -> buy shortlist
  -> capital strategy
  -> deal validation
```

## Service

The service lives in:

```text
app/services/decision_engine.py
```

Main functions:

```python
build_decision_engine()
build_decision_engine_from_opportunities(opportunities, capital_available=None)
```

`build_decision_engine()` reads current opportunities from the database and returns a `DecisionEngineResult`.

`build_decision_engine_from_opportunities()` is useful for tests and future API endpoints that already have a list of opportunities.

## Output

The result contains:

- `opportunities`: all opportunities ordered by analyzer score
- `shortlist`: opportunities approved by BUY SHORTLIST
- `buy_plan`: capital-aware buying plan
- `validation`: final manual validation for planned buys
- `shortlist_rejections`: top rejected opportunities with reasons
- `capital_rejections`: shortlist items rejected by capital rules

## Pipeline Meaning

Analyzer answers:

```text
Is this listing cheap, profitable and supported by market evidence?
```

BUY SHORTLIST answers:

```text
Would I seriously consider buying this?
```

CAPITAL STRATEGY answers:

```text
Given my current bankroll, what exactly should I buy?
```

DEAL VALIDATOR answers:

```text
Before paying, what should I manually verify?
```

## Current Example

With `500 EUR` available, the current data produces one high-conviction buy:

```text
MacBook Pro M1 2020 Plata
Buy: 420 EUR
Expected profit: 87.50 EUR
Portfolio ROI: 0.21
```

It breaks the normal 50% capital rule because it passes high-conviction checks:

- confidence is high
- risk is low
- market speed is not slow
- ROI is above 20%
- buy score is above threshold

Deal validation still asks for manual checks before paying:

- battery health
- physical condition
- charger included
- serial number / lock status
- enough photos or proof of condition
