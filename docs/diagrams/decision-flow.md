# Decision Flow - Market Analyzer

## Scope
- Muestra como una oportunidad cruza las capas de decision.
- No sustituye el detalle economico del analyzer.

## Assumptions
- Assumption: una listing barata no es automaticamente una compra.
- Assumption: capital y validacion manual pueden bloquear una oportunidad buena.
- Assumption: la capa semantica descarta accesorios, piezas y dañados antes de llegar al scorer.

## Diagram

```mermaid
flowchart TD
    A["Listing detectado"] --> B["Semantic layer\n¿Es el producto correcto y no está dañado?"]
    B -->|No| X["Descartar o etiquetar como accesorio/piezas"]
    B -->|Si| C["Analyzer\n¿Hay comparables y profit estimado?"]
    C -->|No| Y["Descartar o dejar sin oportunidad"]
    C -->|Si| D["BUY SHORTLIST\n¿Es una compra seriamente candidata?"]
    D -->|No| Z["Rechazo con motivo"]
    D -->|Si| E["CAPITAL STRATEGY\n¿Cabe en el bankroll actual?"]
    E -->|No| W["Rechazo por capital / prioridad"]
    E -->|Si| F["DEAL VALIDATOR\nChecklist manual antes de pagar"]
    F -->|Riesgo alto o evidencia debil| G["No ejecutar compra todavia"]
    F -->|Checklist aceptable| H["Buy Plan accionable"]
```

## Notes
- Este flujo refleja la filosofia del producto.
- La decision final no es solo matematica; tambien incluye riesgo y evidencia.
- La semantica reduce ruido multilenguaje antes de gastar analisis de mercado.
