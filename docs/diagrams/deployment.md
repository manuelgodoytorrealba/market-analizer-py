# Deployment - Market Analyzer

## Scope
- Muestra donde corre cada parte del sistema en local y Docker.
- No cubre observabilidad avanzada ni entornos productivos separados.

## Assumptions
- Assumption: el desarrollo actual corre en Docker Compose.
- Assumption: la carpeta `./data` se monta en ambos contenedores.

## Diagram

```mermaid
flowchart LR
    User["Navegador local"] -->|"HTTP :8000"| WebC["Docker container: web"]
    External1["Wallapop"] -->|"HTTPS"| BotC["Docker container: bot"]
    External2["eBay"] -->|"HTTPS"| BotC

    subgraph Host["Máquina local / servidor"]
        WebC -->|"bind mount ./data"| DataDir["./data"]
        BotC -->|"bind mount ./data"| DataDir
        DataDir --> SQLite[("SQLite file")]
    end

    WebC -->|"python -m scripts.cli serve"| FastAPI["FastAPI + Jinja"]
    BotC -->|"python -m scripts.cli runtime"| Runtime["Loop continuo de scraping/análisis"]
```

## Notes
- No hay cola separada ni worker pool distribuido.
- La simplicidad de despliegue es una ventaja ahora, pero SQLite concentra bastante responsabilidad.
