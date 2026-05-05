# Decision Flow - Market Analyzer

## Scope
- Muestra como una oportunidad cruza las capas de decision.
- No sustituye el detalle economico del analyzer.

## Assumptions
- Assumption: una listing barata no es automaticamente una compra.
- Assumption: capital y validacion manual pueden bloquear una oportunidad buena.

## Diagram

```mermaid
flowchart TD
    A["Listing barato detectado"] --> B["Analyzer\n¿Hay comparables y profit estimado?"]
    B -->|No| X["Descartar o dejar sin oportunidad"]
    B -->|Si| C["BUY SHORTLIST\n¿Es una compra seriamente candidata?"]
    C -->|No| Y["Rechazo con motivo"]
    C -->|Si| D["CAPITAL STRATEGY\n¿Cabe en el bankroll actual?"]
    D -->|No| Z["Rechazo por capital / prioridad"]
    D -->|Si| E["DEAL VALIDATOR\nChecklist manual antes de pagar"]
    E -->|Riesgo alto o evidencia debil| W["No ejecutar compra todavia"]
    E -->|Checklist aceptable| F["Buy Plan accionable"]
```

## Notes
- Este flujo refleja la filosofia del producto.
- La decision final no es solo matematica; tambien incluye riesgo y evidencia.
