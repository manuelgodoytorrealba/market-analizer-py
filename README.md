## Market Analyzer

### Puesta en marcha

```bash
python scripts/init_db.py
python scripts/run_scrapers.py
uvicorn app.main:app --reload
```

### Variables de entorno

```bash
MARKET_ANALYZER_DB_URL=sqlite:///./data/app.db
MARKET_ANALYZER_REQUEST_TIMEOUT=20
MARKET_ANALYZER_RETRY_ATTEMPTS=2
MARKET_ANALYZER_BACKOFF_BASE=1.5
MARKET_ANALYZER_USER_AGENT="Mozilla/5.0 ..."
MARKET_ANALYZER_EBAY_MAX_ITEMS=20
MARKET_ANALYZER_EBAY_BUY_IT_NOW_ONLY=true
```

### Notas de esta fase

- El scraper de eBay trabaja ahora en modo síncrono real.
- Se filtran subastas de forma conservadora y además la búsqueda usa `Buy It Now`.
- Los listings se actualizan, mantienen ciclo de vida y las oportunidades se persisten.
