# Market Analyzer

Sistema para detectar oportunidades de reventa comparando anuncios reales contra una referencia de mercado.

Pipeline actual:

```text
provider / scraper -> listings (SQLite) -> analyzer -> opportunities -> dashboard
```

## Estado actual

- Backend y dashboard con FastAPI.
- Persistencia SQLite.
- Runtime continuo por ciclos.
- Providers actuales:
  - `wallapop`: API directa -> HTML estático -> fallback renderizado con Playwright.
  - `ebay` HTML: disponible, pero frágil ante challenge antibot; fallback browser pendiente.
- Analyzer actual:
  - `generic_market_gap`
  - `wallapop_to_ebay_arbitrage`
- Limitación de producto actual: el normalizer/analyzer siguen siendo principalmente iPhone-first. Antes de buscar cualquier producto de forma fiable hay que rediseñar `app/services/normalizer.py` y revisar agrupación de comparables en `app/services/analyzer.py`.

## Scraping renderizado con navegador

Wallapop usa un fallback renderizado con Playwright porque en algunos entornos la API devuelve `403 Forbidden` y el HTML estático de `/app/search` solo trae una app shell/skeleton de Next.js, sin anuncios reales.

Flujo actual de Wallapop:

```text
API directa de Wallapop
  -> HTML estático de /app/search
  -> Playwright Chromium
  -> Playwright Firefox como fallback
  -> HTML renderizado
  -> extractor existente
  -> normalización
  -> SQLite
  -> analyzer
  -> dashboard
```

Archivos implicados:

- `app/scrapers/browser.py`: helper genérico para renderizar URLs con Playwright. No contiene lógica de Wallapop, eBay, DB ni analyzer.
- `app/scrapers/wallapop.py`: usa el fallback si API/HTML estático no producen candidatos.
- `app/config.py`: carga `.env` y settings de browser.

Debug generado:

```text
data/raw/wallapop_debug_<query>.html              # HTML estático por requests
data/raw/wallapop_rendered_debug_<query>.html     # HTML renderizado por Playwright
```

### Configuración de navegador

Añade estas variables a `.env`:

```env
MARKET_ANALYZER_BROWSER=chromium
MARKET_ANALYZER_BROWSER_FALLBACK=firefox
MARKET_ANALYZER_BROWSER_HEADLESS=true
MARKET_ANALYZER_BROWSER_TIMEOUT_MS=60000
MARKET_ANALYZER_BROWSER_RENDER_WAIT_MS=5000
MARKET_ANALYZER_BROWSER_TIMEZONE=Europe/Madrid
```

Notas:

- Chromium es el navegador principal.
- Firefox es fallback si Chromium falla.
- No se usa Brave ni el navegador predeterminado como base, porque eso depende de rutas del sistema y rompe portabilidad entre Windows, Linux y Docker.
- Para depurar visualmente, cambia temporalmente `MARKET_ANALYZER_BROWSER_HEADLESS=false`.

### Instalación Playwright

Windows:

```powershell
D:\market-analizer-py\.venv\Scripts\python.exe -m playwright install chromium firefox
```

Linux:

```bash
python -m playwright install chromium firefox
```

Si Linux falla por dependencias del sistema, instala con dependencias:

```bash
python -m playwright install --with-deps chromium firefox
```

### Estado actual de eBay

`ebay` HTML sigue siendo frágil ante challenge antibot (`403`, `503`, páginas tipo “Disculpa la interrupción…”). El helper `app/scrapers/browser.py` ya existe y puede reutilizarse más adelante, pero todavía no está conectado al scraper de eBay.

## Arranque rápido

### Windows

Desde la raíz real del repo:

```powershell
cd D:\market-analizer-py\market-analizer-py
D:\market-analizer-py\.venv\Scripts\python.exe -m playwright install chromium firefox
D:\market-analizer-py\.venv\Scripts\python.exe -m scripts.cli init-db
D:\market-analizer-py\.venv\Scripts\python.exe -m scripts.cli once --source wallapop
D:\market-analizer-py\.venv\Scripts\python.exe -m scripts.cli serve --reload
```

Dashboard:

```text
http://127.0.0.1:8000
```

### Linux/macOS

Usa siempre el entorno virtual del proyecto:

```bash
source .venv/bin/activate
python -m playwright install chromium firefox
PYTHONPATH=. python -m scripts.cli init-db
PYTHONPATH=. python -m scripts.cli once --source wallapop
PYTHONPATH=. python -m scripts.cli serve --reload
```

Dashboard:

```text
http://127.0.0.1:8000
```

## Comandos CLI

El entrypoint principal es:

```bash
PYTHONPATH=. python -m scripts.cli <comando>
```

En Windows, usa el intérprete explícito del venv:

```powershell
D:\market-analizer-py\.venv\Scripts\python.exe -m scripts.cli <comando>
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
PYTHONPATH=. python -m scripts.cli queries
PYTHONPATH=. python -m scripts.cli once --source wallapop
PYTHONPATH=. python -m scripts.cli runtime --source wallapop --interval 180
PYTHONPATH=. python -m scripts.cli serve --reload
PYTHONPATH=. python -m scripts.cli repair-wallapop-urls
```

## Variables de entorno

Configuración principal recomendada:

```env
MARKET_ANALYZER_DB_URL=sqlite:///./data/app.db
MARKET_ANALYZER_RUNTIME_INTERVAL=180
MARKET_ANALYZER_DASHBOARD_REFRESH=12
MARKET_ANALYZER_LOG_LEVEL=INFO

MARKET_ANALYZER_REQUEST_TIMEOUT=20
MARKET_ANALYZER_RETRY_ATTEMPTS=2
MARKET_ANALYZER_BACKOFF_BASE=1.5
MARKET_ANALYZER_USER_AGENT="Mozilla/5.0 ..."

MARKET_ANALYZER_EBAY_PROVIDER=html
MARKET_ANALYZER_EBAY_MAX_ITEMS=20
MARKET_ANALYZER_EBAY_BUY_IT_NOW_ONLY=true

MARKET_ANALYZER_ENABLE_WALLAPOP=true
MARKET_ANALYZER_WALLAPOP_LATITUDE=40.4168
MARKET_ANALYZER_WALLAPOP_LONGITUDE=-3.7038
MARKET_ANALYZER_WALLAPOP_ORDER_BY=most_relevance

MARKET_ANALYZER_BROWSER=chromium
MARKET_ANALYZER_BROWSER_FALLBACK=firefox
MARKET_ANALYZER_BROWSER_HEADLESS=true
MARKET_ANALYZER_BROWSER_TIMEOUT_MS=60000
MARKET_ANALYZER_BROWSER_RENDER_WAIT_MS=5000
MARKET_ANALYZER_BROWSER_TIMEZONE=Europe/Madrid

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

- `app/services/runtime.py`

Puntos concretos:

- `EBAY_TARGET_QUERIES`
- `WALLAPOP_TARGET_QUERIES`
- `TARGET_QUERIES_BY_SOURCE`

Si mañana quieres meter más iPhones o quitar modelos, ese es el sitio. Para productos genéricos todavía hay que revisar normalización/analyzer.

### 2. Añadir un nuevo provider

Archivos:

- `app/scrapers/`
- `app/services/runtime.py`

Pasos:

1. Crear el scraper/provider nuevo en `app/scrapers/<provider>.py`.
2. Implementar el contrato común `fetch_listings(query)`.
3. Registrarlo en `build_market_providers(...)`.
4. Añadir sus queries.

### 3. Cambiar la normalización

Archivo:

- `app/services/normalizer.py`

Aquí se decide:

- qué modelos son válidos
- qué capacidades son válidas
- qué variantes se excluyen
- cómo se normaliza el nombre del producto

### 4. Cambiar el analyzer

Archivo:

- `app/services/analyzer.py`

Aquí se decide:

- cómo se agrupan comparables
- cómo se calcula profit
- qué thresholds filtran oportunidades
- qué tipos de oportunidad existen

### 5. Cambiar persistencia

Archivos:

- `app/models.py`
- `app/services/persistence.py`
- `app/db.py`

Aquí añades:

- columnas nuevas
- preservación de decisiones manuales
- lógica de sync y ciclo de vida de listings

### 6. Cambiar dashboard

Archivos:

- `app/routers/dashboard.py`
- `app/templates/`
- `app/static/styles.css`

## Limitaciones reales ahora mismo

- `wallapop` ya puede obtener resultados reales vía browser fallback, pero sigue dependiendo de que la web renderizada exponga cards parseables.
- `ebay` HTML sigue siendo frágil y puede caer por challenge antibot.
- Algunas oportunidades siguen dependiendo de que eBay tenga comparables frescos.
- El sistema todavía no es product-agnostic: para analizar productos fuera de iPhone hay que rehacer la normalización y revisar cómo se agrupan comparables.

## Comandos de validación

Tests:

```bash
PYTHONPATH=. python -m unittest discover -s tests -v
```

Compilación rápida:

```bash
python -m compileall app scripts tests
```

Validación Windows:

```powershell
D:\market-analizer-py\.venv\Scripts\python.exe -m compileall app scripts tests
D:\market-analizer-py\.venv\Scripts\python.exe -m unittest discover -s tests -v
D:\market-analizer-py\.venv\Scripts\python.exe -m scripts.cli once --source wallapop
```

## Referencia rápida de desarrollo

Si mañana quieres seguir desde aquí:

1. Ejecuta `queries`.
2. Ejecuta `once --source wallapop`.
3. Revisa `listings?source=wallapop`.
4. Revisa `opportunities?source=wallapop`.
5. Si ves enlaces rotos antiguos, ejecuta `repair-wallapop-urls`.

Ese es el circuito mínimo para iterar sin perder tiempo.
