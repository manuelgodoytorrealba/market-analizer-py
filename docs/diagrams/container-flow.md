# Container Flow - Market Analyzer

## Scope
- Muestra los contenedores runtime principales y cómo se conectan.
- No detalla funciones internas ni modelo de datos.

## Assumptions
- Assumption: `web` sirve FastAPI y `bot` ejecuta el runtime continuo.
- Assumption: ambos comparten la misma carpeta `./data` para SQLite.

## Diagram

```mermaid
flowchart LR
    User["Operador"] -->|"Navega"| Web["Contenedor web"]
    Wallapop["Wallapop"] -->|"HTML/API/fallback browser"| Bot["Contenedor bot"]
    Ebay["eBay"] -->|"HTML"| Bot

    subgraph WebBox["web"]
        FastAPI["FastAPI app.main"]
        Routers["app/api/api.py + dashboard.py"]
        Templates["Jinja templates"]
    end

    subgraph BotBox["bot"]
        CLI["python -m scripts.cli runtime"]
        Runtime["app/services/runtime.py"]
        Scrapers["app/scrapers/*"]
        Analyzer["analyzer + decision layers"]
    end

    subgraph DataBox["Persistencia compartida"]
        SQLite[("SQLite en ./data")]
    end

    Web -->|"Lee"| SQLite
    FastAPI --> Routers
    Routers --> Templates

    Bot --> CLI
    CLI --> Runtime
    Runtime --> Scrapers
    Runtime --> Analyzer
    Analyzer -->|"Escribe listings, runs, opportunities"| SQLite
```

## Notes
- No hay cola ni cache distribuida en esta fase.
- SQLite es el punto de intercambio entre runtime y dashboard.
