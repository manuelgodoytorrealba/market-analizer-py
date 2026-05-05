# Runtime Sequence - Market Analyzer

## Scope
- Muestra un ciclo real de scraping, normalizacion, persistencia y consulta en dashboard.
- Incluye el camino de fallo parcial cuando una fuente bloquea acceso.

## Assumptions
- Assumption: el runtime puede ejecutarse por ciclos con `scripts.cli runtime`.
- Assumption: la salida del dashboard depende de lo persistido en SQLite.

## Diagram

```mermaid
sequenceDiagram
    actor Operator as Operador
    participant CLI as scripts.cli runtime
    participant Runtime as app/services/runtime.py
    participant Scrapers as app/scrapers
    participant Normalizer as normalizer.py
    participant Persistence as persistence.py
    participant Analyzer as analyzer.py
    participant Decision as decision_engine.py
    participant DB as SQLite
    participant Web as FastAPI Dashboard

    Operator->>CLI: iniciar runtime
    CLI->>Runtime: run_market_cycle(selected_sources)
    Runtime->>Scrapers: ejecutar queries por source
    Scrapers-->>Runtime: listings crudos por source

    alt Wallapop API/HTML responde bien
        Runtime->>Normalizer: normalizar listings
    else 403 / bloqueo / challenge
        Scrapers-->>Runtime: error o fallback browser
        Runtime->>Normalizer: normalizar solo lo recuperable
    end

    Normalizer-->>Persistence: listings válidos
    Persistence->>DB: insert/update/deactivate + scrape_run
    Persistence-->>Analyzer: dataset persistido
    Analyzer->>DB: leer comparables activos
    Analyzer->>DB: refrescar opportunities
    Analyzer-->>Decision: opportunities explicables
    Decision-->>DB: datos derivados listos para consulta
    Web->>DB: leer listings / opportunities / runs
    Web-->>Operator: dashboard con evidencia
```

## Notes
- El dashboard no hace scraping.
- El runtime tolera fallos parciales por fuente.
