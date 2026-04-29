# Market Analyzer

Sistema para detectar oportunidades de reventa comparando anuncios reales contra una referencia de mercado.

Pipeline actual:

`provider / scraper -> listings (SQLite) -> analyzer -> opportunities -> dashboard`

## Estado actual

- Backend y dashboard con FastAPI
- Persistencia SQLite
- Runtime continuo por ciclos
- Providers activos:
  - `wallapop`
  - `ebay` HTML
- Analyzer con:
  - `generic_market_gap`
  - `wallapop_to_ebay_arbitrage`

## Arranque rápido

Usa siempre el entorno virtual del proyecto:

```bash
source .venv/bin/activate
```

Inicializar base de datos:

```bash
PYTHONPATH=. .venv/bin/python -m scripts.cli init-db
```

Ver queries activas:

```bash
PYTHONPATH=. .venv/bin/python -m scripts.cli queries
```

Ejecutar un solo ciclo:

```bash
PYTHONPATH=. .venv/bin/python -m scripts.cli once
```

Ejecutar solo Wallapop:

```bash
PYTHONPATH=. .venv/bin/python -m scripts.cli once --source wallapop
```

Levantar runtime continuo:

```bash
PYTHONPATH=. .venv/bin/python -m scripts.cli runtime --interval 180
```

Levantar runtime solo Wallapop:

```bash
PYTHONPATH=. .venv/bin/python -m scripts.cli runtime --source wallapop --interval 180
```

Levantar dashboard:

```bash
PYTHONPATH=. .venv/bin/python -m scripts.cli serve --reload
```

URL local:

```text
http://127.0.0.1:8000
```

## Comandos CLI

El entrypoint principal es:

```bash
PYTHONPATH=. .venv/bin/python -m scripts.cli <comando>
```

Comandos disponibles:

- `init-db`
  - Inicializa el esquema SQLite.
- `queries`
  - Muestra las queries activas por source.
- `once`
  - Ejecuta un ciclo completo de scraping, persistencia y análisis.
- `runtime`
  - Ejecuta el loop continuo.
- `serve`
  - Levanta el dashboard FastAPI.
- `repair-wallapop-urls`
  - Recalcula URLs públicas de Wallapop ya guardadas en DB.

Ejemplos:

```bash
PYTHONPATH=. .venv/bin/python -m scripts.cli once --source wallapop
PYTHONPATH=. .venv/bin/python -m scripts.cli runtime --source wallapop --interval 180
PYTHONPATH=. .venv/bin/python -m scripts.cli serve --reload
PYTHONPATH=. .venv/bin/python -m scripts.cli repair-wallapop-urls
```

## Variables de entorno

Configuración principal:

```bash
MARKET_ANALYZER_DB_URL=sqlite:///./data/app.db
MARKET_ANALYZER_RUNTIME_INTERVAL=180
MARKET_ANALYZER_DASHBOARD_REFRESH=12
MARKET_ANALYZER_LOG_LEVEL=INFO
MARKET_ANALYZER_REQUEST_TIMEOUT=20
MARKET_ANALYZER_RETRY_ATTEMPTS=2
MARKET_ANALYZER_BACKOFF_BASE=1.5
MARKET_ANALYZER_USER_AGENT="Mozilla/5.0 ..."
MARKET_ANALYZER_EBAY_MAX_ITEMS=20
MARKET_ANALYZER_EBAY_BUY_IT_NOW_ONLY=true
MARKET_ANALYZER_ENABLE_WALLAPOP=true
MARKET_ANALYZER_WALLAPOP_LATITUDE=40.4168
MARKET_ANALYZER_WALLAPOP_LONGITUDE=-3.7038
MARKET_ANALYZER_WALLAPOP_ORDER_BY=most_relevance
MARKET_ANALYZER_ARBITRAGE_FEE_RATE=0.13
MARKET_ANALYZER_ARBITRAGE_PROFIT_THRESHOLD=20
MARKET_ANALYZER_ARBITRAGE_MIN_COMPARABLES=3
```

## Qué mirar en la UI

Listings:

```text
http://127.0.0.1:8000/listings
http://127.0.0.1:8000/listings?source=wallapop
http://127.0.0.1:8000/listings?source=ebay
```

Opportunities:

```text
http://127.0.0.1:8000/opportunities
http://127.0.0.1:8000/opportunities?source=wallapop
http://127.0.0.1:8000/opportunities?source=ebay
```

Runs:

```text
http://127.0.0.1:8000/runs
```

## Qué mirar en la base de datos

Resumen por source:

```bash
sqlite3 data/app.db "select source, is_active, count(*) from listings group by source, is_active;"
sqlite3 data/app.db "select source, opportunity_type, count(*) from opportunities group by source, opportunity_type;"
sqlite3 data/app.db "select id, source, status, listings_seen, listings_normalized from scrape_runs order by id desc limit 10;"
```

Ver URLs de Wallapop:

```bash
sqlite3 data/app.db "select id, title, url from listings where source='wallapop' order by id desc limit 20;"
```

## Dónde añadir cosas

### 1. Añadir o quitar queries

Archivo:

[app/services/runtime.py](/home/manuel/Desarrollos/market-analyzer/app/services/runtime.py)

Puntos concretos:

- `EBAY_TARGET_QUERIES`
- `WALLAPOP_TARGET_QUERIES`
- `TARGET_QUERIES_BY_SOURCE`

Si mañana quieres meter más iPhones o quitar modelos, ese es el sitio.

### 2. Añadir un nuevo provider

Archivos:

- [app/scrapers](/home/manuel/Desarrollos/market-analyzer/app/scrapers)
- [app/services/runtime.py](/home/manuel/Desarrollos/market-analyzer/app/services/runtime.py)

Pasos:

1. Crear el scraper/provider nuevo en `app/scrapers/<provider>.py`
2. Implementar el contrato común `fetch_listings(query)`
3. Registrarlo en `build_market_providers(...)`
4. Añadir sus queries

### 3. Cambiar la normalización

Archivo:

[app/services/normalizer.py](/home/manuel/Desarrollos/market-analyzer/app/services/normalizer.py)

Aquí se decide:

- qué modelos son válidos
- qué capacidades son válidas
- qué variantes se excluyen
- cómo se normaliza el nombre del producto

### 4. Cambiar el analyzer

Archivo:

[app/services/analyzer.py](/home/manuel/Desarrollos/market-analyzer/app/services/analyzer.py)

Aquí se decide:

- cómo se agrupan comparables
- cómo se calcula profit
- qué thresholds filtran oportunidades
- qué tipos de oportunidad existen

### 5. Cambiar persistencia

Archivos:

- [app/models.py](/home/manuel/Desarrollos/market-analyzer/app/models.py)
- [app/services/persistence.py](/home/manuel/Desarrollos/market-analyzer/app/services/persistence.py)
- [app/db.py](/home/manuel/Desarrollos/market-analyzer/app/db.py)

Aquí añades:

- columnas nuevas
- preservación de decisiones manuales
- lógica de sync y ciclo de vida de listings

### 6. Cambiar dashboard

Archivos:

- [app/routers/dashboard.py](/home/manuel/Desarrollos/market-analyzer/app/routers/dashboard.py)
- [app/templates](/home/manuel/Desarrollos/market-analyzer/app/templates)
- [app/static/styles.css](/home/manuel/Desarrollos/market-analyzer/app/static/styles.css)

## Limitaciones reales ahora mismo

- `ebay` HTML sigue siendo frágil y puede caer por challenge antibot.
- `wallapop` funciona mejor por HTML/SEO que por API pública directa; la API está devolviendo `403` en este entorno.
- Algunas oportunidades siguen dependiendo de que eBay tenga comparables frescos.

## Comandos de validación

Tests:

```bash
PYTHONPATH=. .venv/bin/python -m unittest discover -s tests -v
```

Compilación rápida:

```bash
python3 -m compileall app scripts tests
```

## Referencia rápida de desarrollo

Si mañana quieres seguir desde aquí:

1. Ejecuta `queries`
2. Ejecuta `once --source wallapop`
3. Revisa `listings?source=wallapop`
4. Revisa `opportunities?source=wallapop`
5. Si ves enlaces rotos antiguos, ejecuta `repair-wallapop-urls`

Ese es el circuito mínimo para iterar sin perder tiempo.


ramon eres gay 