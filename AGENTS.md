# AGENTS.md — Market Analyzer

## Project Purpose

Market Analyzer detects resale opportunities by comparing real marketplace listings against market reference prices.

Current pipeline:

scraper/provider -> listings -> normalizer -> persistence -> analyzer -> opportunities -> dashboard

The priority is not to make many changes quickly.

The priority is:

1. Understand the system.
2. Follow data from source to dashboard.
3. Make small, safe, reviewable improvements.
4. Validate every change.

## Development Rules

Before editing code, explain:

1. What task you understand.
2. Which part of the pipeline it affects.
3. Which files you need to inspect.
4. Which files you expect to modify.
5. Which files should not be touched.
6. The smallest safe implementation plan.
7. How you will validate the change.

Do not start by editing files blindly.

## Layer Responsibilities

### Scrapers / Providers

Scrapers fetch external marketplace data.

They should:

- Handle external HTML/API instability.
- Return structured listing candidates.
- Avoid persistence decisions.
- Avoid opportunity calculations.
- Avoid dashboard/UI concerns.

### Normalizer

The normalizer cleans and standardizes product data.

It decides:

- valid models
- valid capacities
- excluded variants
- normalized product names
- comparable product identity

### Persistence

Persistence stores, updates, deactivates, and queries data.

It handles:

- inserting listings
- updating listings
- deactivating missing listings
- recording scrape runs
- refreshing opportunities
- preserving manual decisions when applicable

### Analyzer

The analyzer calculates opportunities.

It handles:

- grouping comparable listings
- calculating market references
- calculating profit or market gap
- applying thresholds
- storing evidence

Every opportunity should be explainable with:

- source
- query
- comparable listings
- calculation basis
- reason

### Dashboard / Router

Routers coordinate requests and prepare data for templates.

Avoid deep business logic in routers.

### Templates

Templates render data.

Do not put business rules in templates.

### CSS

CSS controls presentation.

Do not use CSS to hide missing backend logic or unclear data modeling.

## Hard Rules

- Do not mix unrelated tasks.
- Do not do large refactors unless explicitly requested.
- Do not add dependencies without approval.
- Do not change database schema without explaining migration and rollback implications.
- Do not change analyzer thresholds without explaining product impact.
- Do not hide scraper failures.
- Do not use broad `except Exception: pass`.
- Do not hardcode production data, paths, tokens, users, IDs, or URLs in core logic.
- Do not scrape inside dashboard request handlers unless explicitly requested.
- Do not calculate opportunity logic inside templates.

## Practical Clean Code Rules

Use KISS:

- Choose the simplest correct solution.
- Avoid clever code.
- Avoid unnecessary abstractions.
- Do not create internal frameworks for small features.

Use DRY carefully:

- Do not duplicate business logic.
- Do not duplicate normalization rules.
- Do not extract helpers too early.
- Small UI duplication is acceptable if abstraction would make the code harder to read.

Use SOLID pragmatically:

- One clear responsibility per function/module.
- Add extension points only when they reduce real complexity.
- Keep core logic independent from frameworks, database clients, HTTP clients, and UI.
- Avoid fat interfaces.

Priority order:

1. Correctness
2. Security
3. Clarity
4. Testability
5. Maintainability
6. Performance
7. Abstraction

## Scope Discipline

Work in small PR-sized batches.

Prefer modifying 1 to 4 files.

If the task is too broad, propose the smallest useful first step.

Do not combine:

- feature + refactor
- feature + visual redesign
- feature + dependency change
- feature + schema change

unless absolutely required.

## Validation Commands

Use the virtual environment.

Run tests when relevant:

```bash
PYTHONPATH=. .venv/bin/python -m unittest discover -s tests -v