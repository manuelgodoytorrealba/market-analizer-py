# Pipeline Component - Market Analyzer

## Scope
- Muestra las responsabilidades internas del pipeline backend.
- No entra en cada helper privado ni en cada clase de soporte.

## Assumptions
- Assumption: `comparable_key` es la pieza central para agrupar listings comparables.
- Assumption: la capa de decision layers consume opportunities ya calculadas.
- Assumption: la capa semantica solo marca `1/0` y una razon corta antes de persistir.

## Diagram

```mermaid
flowchart LR
    Queries["Queries objetivo\nruntime.py"] --> Scrapers["Scrapers\nwallapop.py / ebay.py"]
    Scrapers -->|"Listings crudos"| Normalizer["Normalizer\nnormalizer.py"]
    Normalizer -->|"Listings normalizados"| Semantic["Semantic layer\nsemantic_classifier.py"]
    Semantic -->|"target_match\nhealth_ok\nlanguage"| Persistence["Persistence\npersistence.py"]
    Persistence -->|"Listings activos + scrape_runs"| Analyzer["Analyzer\nanalyzer.py"]
    Analyzer -->|"mean/median/mode\nOpportunities + evidence_json"| Decision["Decision Engine\nbuy_shortlist.py\ncapital_strategy.py\ndeal_validator.py"]
    Decision --> API["FastAPI routers\napi.py / dashboard.py"]
    API --> UI["Dashboard HTML\napp/templates"]

    Scrapers -. "fallo / 403 / challenge" .-> RuntimeLogs["Logs y resumen de ciclo"]
    Semantic -. "damaged / accessory only / target mismatch" .-> RuntimeLogs
    Analyzer -. "rechazos / thresholds" .-> RuntimeLogs
    Decision -. "shortlist_rejections\ncapital_rejections" .-> RuntimeLogs
```

## Notes
- El normalizer no decide compra.
- La capa semantica no decide compra final, solo filtra y etiqueta.
- El analyzer no mezcla UI.
- Las decision layers separan oportunidad, capital y validacion.
