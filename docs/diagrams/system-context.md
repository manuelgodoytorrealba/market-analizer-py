# System Context - Market Analyzer

## Scope
- Muestra actores, fuentes externas y salidas del sistema.
- No muestra detalles internos de clases ni tablas.

## Assumptions
- Assumption: el usuario consulta el dashboard local por HTTP en `localhost:8000`.
- Assumption: Wallapop y eBay son fuentes externas de listings.

## Diagram

```mermaid
flowchart LR
    User["Operador / Analista"] -->|"HTTP localhost:8000"| UserUI["Market Analyzer Dashboard"]

    subgraph Product["Market Analyzer"]
        Runtime["Runtime de ciclos"]
        Decision["Decision Layers"]
        DB[("SQLite data/app.db")]
        Dashboard["FastAPI Dashboard + API"]
    end

    Wallapop["Wallapop"] -->|"Listings"| Runtime
    Ebay["eBay"] -->|"Listings"| Runtime
    Runtime -->|"Listings normalizados"| DB
    DB -->|"Listings + Opportunities + Runs"| Dashboard
    DB -->|"Opportunities"| Decision
    Decision -->|"Shortlist / Buy Plan / Validation"| Dashboard
```

## Notes
- El sistema no es solo scraping.
- La parte visible para el usuario es el dashboard, pero la decisión se genera antes en backend.
