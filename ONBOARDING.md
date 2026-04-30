Perfecto, vamos a hacerlo bien:
te voy a generar un **onboarding completo listo para copiar y pegar**, **manteniendo TODO lo que ya tienes** y **añadiendo lo que falta para que sea usable por otra persona sin romper nada**.

👉 No elimino nada. Solo **expando y profesionalizo**.

---

# 📄 `docs/onboarding.md` (VERSIÓN FINAL)

Copia esto completo y reemplaza tu archivo:

---

# 🧠 Market Analyzer — Onboarding (Senior Version)

---

## 0. TL;DR (cómo explicar este proyecto en 30 segundos)

> Market Analyzer es un sistema de decisión automatizado que analiza listings de marketplaces (como Wallapop) para detectar oportunidades de reventa, evaluarlas con métricas de mercado, filtrarlas por riesgo, asignar capital y producir decisiones de compra accionables.

---

## 1. Modelo mental del sistema

Olvídate del código por un momento. Piensa en esto:

```text
INPUT → DATA → INTELLIGENCE → DECISION → ACTION
```

Más detallado:

```text
Listings crudos
→ estructuración
→ comparación de mercado
→ detección de oportunidades
→ filtrado realista
→ asignación de capital
→ validación final
→ decisión ejecutable
```

👉 Esto no es un scraper.
👉 Es un **decision engine financiero aplicado a flipping**.

---

## 2. 🚀 Cómo levantar el proyecto (IMPORTANTE)

### Opción recomendada (Docker)

```bash
docker compose up --build
```

Abrir en navegador:

```text
http://localhost:8000
```

---

### Opción manual (sin Docker)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python scripts/init_db.py
uvicorn app.main:app --reload
```

---

## 3. 🧪 Verificación rápida (para onboarding)

Una vez levantado:

1. Ir a:

```text
http://localhost:8000/listings
```

2. Probar filtros:

```text
?category=iphone
?category=gpu
?category=macbook
```

3. Verificar:

* ✔ Se cargan datos
* ✔ Cambian los resultados
* ✔ No hay errores en consola

---

## 4. Arquitectura real (visión de sistema)

```text
                ┌──────────────┐
                │  Scrapers    │
                └──────┬───────┘
                       ↓
                ┌──────────────┐
                │ Normalizer   │
                └──────┬───────┘
                       ↓
                ┌──────────────┐
                │ Persistence  │
                └──────┬───────┘
                       ↓
                ┌──────────────┐
                │ Analyzer V5  │
                └──────┬───────┘
                       ↓
     ┌─────────────────┼─────────────────┐
     ↓                 ↓                 ↓
Buy Shortlist   Capital Strategy   Deal Validator
     └──────────────┬──────────────┘
                    ↓
            ┌──────────────┐
            │ Decision     │
            │ Engine       │
            └──────┬───────┘
                   ↓
           API / Frontend
```

---

## 5. Principio clave: separación de responsabilidades

| Capa            | Qué hace               | Qué NO hace     |
| --------------- | ---------------------- | --------------- |
| Scraper         | Extraer datos          | Pensar          |
| Normalizer      | Estructurar            | Decidir         |
| Analyzer        | Detectar oportunidades | Comprar         |
| Shortlist       | Filtrar                | Asignar dinero  |
| Capital         | Gestionar dinero       | Analizar        |
| Validator       | Detectar riesgo        | Optimizar       |
| Decision Engine | Orquestar              | Lógica compleja |

---

## 6. El corazón del sistema: Comparable Key

```text
producto → normalización → comparable_key
```

Ejemplo:

```text
"iPhone 13 128GB en buen estado"
→ iphone 13 128gb__complete
```

👉 TODO depende de esto:

* comparaciones de precio
* cálculo de ROI
* detección de oportunidades

---

## 7. Cómo piensa el sistema

```text
Listings agrupados por comparable_key
→ cálculo de mediana
→ detección de outliers
→ estimación de profit
→ validación de riesgo
→ decisión final
```

---

## 8. 🆕 Sistema de filtros (IMPORTANTE)

El sistema ahora incluye filtros dinámicos en backend + UI.

### Filtro por categoría

```text
iphone
macbook
gpu
```

### Cómo funciona

Se aplica en backend:

```python
_apply_category_filter()
```

Basado en:

```text
title + normalized_name
```

---

### Ejemplos reales

```text
/opportunities?category=iphone
/listings?category=gpu&source=wallapop
```

---

👉 Esto es importante porque:

* permite multi-categoría real
* prepara el sistema para escalar
* separa lógica de UI y backend

---

## 9. Flujo real de una oportunidad

```text
Wallapop listing:
"iPhone 13 128GB - 320€"
```

↓

```text
Normalizer:
iphone 13 128gb__complete
```

↓

```text
Analyzer:
median = 450€
profit = +90€
```

↓

```text
Decision Engine:
→ BUY
```

---

## 10. Qué hace especial este sistema

### ✔ Multi-layer decision

```text
Detección ≠ Compra
```

---

### ✔ Capital-aware

No todas las oportunidades se compran.

---

### ✔ Risk-aware

Buenos números ≠ compra segura.

---

### ✔ Liquidity-aware

Se evalúa si se puede vender.

---

## 11. Riesgos técnicos actuales

⚠ Dependencia del scraper
⚠ Normalización imperfecta
⚠ Datos incompletos
⚠ Falta de feedback loop

---

## 12. Developer Notes (IMPORTANTE)

El sistema usa:

* FastAPI + Jinja templates
* filtros backend por query params
* selección de entidad por URL

Ejemplo:

```text
/opportunities?category=iphone&source=wallapop
```

---

## 13. Filosofía del sistema

```text
No todo lo barato es una oportunidad
No toda oportunidad debe comprarse
No toda compra debe ejecutarse
```

---

## 14. Siguiente paso lógico

Implementar:

```text
tracking real de resultados
```

* compras reales
* ventas reales
* profit real

👉 Esto convierte el sistema en:

```text
learning system
```

---

# ✅ Con esto ya tienes

✔ Onboarding técnico
✔ Onboarding conceptual
✔ Setup real
✔ Debug básico
✔ Sistema entendible por otra persona

---

# 🚀 Siguiente paso lógico

Ahora haz esto:

👉 Dáselo a tu hermano SIN explicarle nada
👉 Observa dónde falla

Y me dices:

> “se pierde en X”

Y te lo convierto en:

🔥 onboarding nivel empresa real (con roles, checklist, etc.)

---

Si sigues este ritmo, esto ya no es un proyecto…
es una base seria de producto.
