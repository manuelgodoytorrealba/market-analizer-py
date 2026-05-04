# Pipeline Component - Market Analyzer

## Scope
- Muestra las responsabilidades internas del pipeline backend.
- No entra en cada helper privado ni en cada clase de soporte.

## Assumptions
- Assumption: `comparable_key` es la pieza central para agrupar listings comparables.
- Assumption: la capa de decision layers consume opportunities ya calculadas.

## Diagram

```mermaid
flowchart LR
    Queries["Queries objetivo\nruntime.py"] --> Scrapers["Scrapers\nwallapop.py / ebay.py"]
    Scrapers -->|"Listings crudos"| Normalizer["Normalizer\nnormalizer.py"]
    Normalizer -->|"Listings válidos + comparable_key + categoría"| Persistence["Persistence\npersistence.py"]
    Persistence -->|"Listings activos + scrape_runs"| Analyzer["Analyzer\nanalyzer.py"]
    Analyzer -->|"Opportunities + evidence_json"| Decision["Decision Engine\nbuy_shortlist.py\ncapital_strategy.py\ndeal_validator.py"]
    Decision --> API["FastAPI routers\napi.py / dashboard.py"]
    API --> UI["Dashboard HTML\napp/templates"]

    Scrapers -. "fallo / 403 / challenge" .-> RuntimeLogs["Logs y resumen de ciclo"]
    Analyzer -. "rechazos / thresholds" .-> RuntimeLogs
    Decision -. "shortlist_rejections\ncapital_rejections" .-> RuntimeLogs
```

## Notes
- El normalizer no decide compra.
- El analyzer no mezcla UI.
- Las decision layers separan oportunidad, capital y validacion.
