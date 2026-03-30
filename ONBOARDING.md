# Onboarding — Market Analyzer

## Objetivo de este documento

Este documento existe para que puedas incorporarte al proyecto con contexto real, una ruta clara de aprendizaje y una primera contribución pequeña pero útil.

La prioridad no es que hagas muchas cosas rápido.

La prioridad es esta:

1. Entender cómo funciona el sistema de verdad.
2. Entender dónde nace cada dato y dónde termina.
3. Hacer una primera mejora real sin tocar zonas de alto riesgo.

---

## 1. Qué hace este proyecto

`Market Analyzer` detecta oportunidades de compra en marketplaces.

Hoy el flujo principal funciona así:

1. El scraper consulta eBay.
2. Extrae anuncios válidos.
3. Guarda esos anuncios como `listings` en base de datos.
4. El analyzer compara anuncios parecidos.
5. Si detecta una diferencia clara de precio, genera `opportunities`.
6. El dashboard muestra:
   - resumen del sistema
   - oportunidades detectadas
   - anuncios crudos
   - evidencia del cálculo
   - historial de ejecuciones
   - ajustes activos

La idea más importante del proyecto es esta:

`scraper -> listings -> analyzer -> opportunities -> dashboard`

Si entiendes bien esa tubería, entiendes el proyecto.

---

## 2. Estado actual del proyecto

Ahora mismo el proyecto ya tiene una base bastante seria:

- scraper de eBay funcionando parcialmente con resultados reales
- persistencia de `listings`
- generación de `opportunities`
- dashboard web funcional
- UI refinada en español
- explicabilidad básica:
  - comparables usados
  - variantes descartadas
  - query utilizada
  - origen de datos
  - contexto de ejecución

Lo que **no** necesitas tocar en esta fase:

- Wallapop
- scraper complejo de eBay
- lógica avanzada del analyzer
- cambios de arquitectura grandes

---

## 3. Mapa mental del sistema

Lee el proyecto en este orden.

### 3.1 Punto de entrada

- [app/main.py](./app/main.py)

Qué debes entender:

- cómo arranca FastAPI
- cómo se montan los estáticos
- cómo entra el router del dashboard

### 3.2 Modelos de datos

- [app/models.py](./app/models.py)

Qué debes entender:

- `Listing`: anuncio individual scrapeado
- `Opportunity`: oportunidad detectada por el analyzer
- `ScrapeRun`: registro de una ejecución del scraper

### 3.3 Flujo web

- [app/routers/dashboard.py](./app/routers/dashboard.py)

Qué debes entender:

- qué ruta sirve cada pantalla
- qué datos consulta cada vista
- cómo se aplican filtros
- cómo se pasa el contexto al template

### 3.4 Flujo operativo real

- [scripts/run_scrapers.py](./scripts/run_scrapers.py)

Qué debes entender:

- qué queries se ejecutan
- cómo se llama al scraper
- cómo se sincronizan los listings
- cuándo se recalculan oportunidades
- cuándo se registra una ejecución

### 3.5 Persistencia

- [app/services/persistence.py](./app/services/persistence.py)

Qué debes entender:

- inserción de listings nuevos
- actualización de listings existentes
- desactivación de listings desaparecidos
- refresco completo de oportunidades
- registro de ejecuciones

### 3.6 Analyzer

- [app/services/analyzer.py](./app/services/analyzer.py)

Qué debes entender:

- cómo se agrupan anuncios comparables
- cómo se calcula la mediana
- cuándo algo se considera oportunidad
- qué evidencia se guarda

### 3.7 Scraper actual

- [app/scrapers/ebay.py](./app/scrapers/ebay.py)

Qué debes entender:

- qué devuelve el scraper
- qué forma tiene cada resultado
- qué filtros básicos aplica

No lo toques todavía salvo lectura.

### 3.8 Frontend

Plantillas:

- [app/templates/base.html](./app/templates/base.html)
- [app/templates/overview.html](./app/templates/overview.html)
- [app/templates/opportunities.html](./app/templates/opportunities.html)
- [app/templates/listings.html](./app/templates/listings.html)
- [app/templates/analysis.html](./app/templates/analysis.html)
- [app/templates/runs.html](./app/templates/runs.html)
- [app/templates/settings.html](./app/templates/settings.html)

Estilos:

- [app/static/styles.css](./app/static/styles.css)

Qué debes entender:

- layout base
- navegación
- tablas
- panel derecho
- CTA principal
- estilos glass

### 3.9 Tests existentes

- [tests/test_ebay_scraper.py](./tests/test_ebay_scraper.py)
- [tests/test_analyzer.py](./tests/test_analyzer.py)
- [tests/test_persistence.py](./tests/test_persistence.py)

No cubren todo, pero sirven para entender responsabilidades y puntos críticos.

---

## 4. Pantallas actuales del dashboard

Hoy el dashboard tiene estas pantallas:

- `Resumen`
- `Oportunidades`
- `Anuncios`
- `Evidencia`
- `Ejecuciones`
- `Ajustes`

Debes poder contestar para cada una:

1. Qué propósito tiene.
2. Qué datos muestra.
3. De qué tabla o consulta vienen esos datos.
4. Qué template la renderiza.

---

## 5. Onboarding por fases

### Fase A — Levantar y entender el sistema

Objetivo: verlo funcionar de punta a punta.

Tareas:

1. Inicializar la base de datos:

```bash
PYTHONPATH=. .venv/bin/python scripts/init_db.py
```

2. Ejecutar el scraper:

```bash
PYTHONPATH=. .venv/bin/python scripts/run_scrapers.py
```

3. Levantar la app web:

```bash
PYTHONPATH=. .venv/bin/uvicorn app.main:app --reload
```

4. Abrir el dashboard.
5. Entrar en todas las pantallas.
6. Elegir una oportunidad concreta y seguir su rastro:
   - qué título tiene
   - qué query la originó
   - qué comparables la soportan
   - en qué vista aparece su evidencia

Resultado esperado:

- puedes explicar el flujo completo sin mirar código

### Fase B — Entender cómo se renderiza el dashboard

Objetivo: relacionar ruta, datos y template.

Tareas:

1. Leer [app/routers/dashboard.py](./app/routers/dashboard.py).
2. Hacer una tabla como esta:

| Ruta | Función | Template | Datos principales | Propósito |
| --- | --- | --- | --- | --- |

3. Leer [app/templates/base.html](./app/templates/base.html).
4. Leer una a una las plantillas del dashboard.
5. Localizar en [app/static/styles.css](./app/static/styles.css):
   - layout
   - tablas
   - paneles
   - botones
   - clases reutilizables

Resultado esperado:

- sabes dónde tocar si una vista cambia

### Fase C — Primera contribución pequeña y real

Objetivo: hacer una mejora útil sin entrar en zonas peligrosas.

Tu primera tarea recomendada será:

**añadir filtro de “Compra directa” en la pantalla `Anuncios`**

Por qué:

- es pequeña
- tiene impacto real
- toca datos reales
- obliga a entender request params, filtros y UI
- no te mete todavía en scraping complejo

---

## 6. Primera feature recomendada

### Feature

Añadir filtro `Compra directa` en la pantalla `Anuncios`.

### Qué debe hacer

Permitir:

- `Todos`
- `Solo compra directa`
- `Excluir compra directa`

### Archivos probablemente implicados

- [app/routers/dashboard.py](./app/routers/dashboard.py)
- [app/templates/listings.html](./app/templates/listings.html)
- [app/static/styles.css](./app/static/styles.css) si hace falta ajuste visual pequeño

### Qué aprenderás con esta tarea

- cómo llegan filtros por query string
- cómo se filtran listas en backend
- cómo se preserva el estado del formulario
- cómo se muestra el dato en tabla y detalle
- cómo cerrar una mejora pequeña de producto

---

## 7. Tickets propuestos

### Ticket 1 — Levantar el proyecto y explicar el pipeline

**Objetivo**  
Entender el sistema de punta a punta.

**Contexto**  
Antes de tocar código debes ver el producto funcionando.

**Archivos implicados**

- [scripts/init_db.py](./scripts/init_db.py)
- [scripts/run_scrapers.py](./scripts/run_scrapers.py)
- [app/main.py](./app/main.py)

**Criterios de aceptación**

- puedes levantar la base
- puedes ejecutar una corrida
- puedes abrir el dashboard
- puedes explicar `scraper -> listings -> analyzer -> opportunities -> dashboard`

**Dificultad**  
Baja

**Por qué te hace crecer**  
Aprendes a entender sistema antes de editarlo.

### Ticket 2 — Mapear rutas, vistas y datos

**Objetivo**  
Entender la capa web del proyecto.

**Contexto**  
El dashboard ya tiene varias pantallas; necesitas saber qué alimenta cada una.

**Archivos implicados**

- [app/routers/dashboard.py](./app/routers/dashboard.py)
- [app/templates/base.html](./app/templates/base.html)
- [app/templates/overview.html](./app/templates/overview.html)
- [app/templates/opportunities.html](./app/templates/opportunities.html)
- [app/templates/listings.html](./app/templates/listings.html)
- [app/templates/analysis.html](./app/templates/analysis.html)
- [app/templates/runs.html](./app/templates/runs.html)
- [app/templates/settings.html](./app/templates/settings.html)

**Criterios de aceptación**

- entregas una tabla con ruta, template, datos y propósito
- sabes qué vista es la más segura para una primera mejora

**Dificultad**  
Baja

**Por qué te hace crecer**  
Aprendes a leer producto y código como una sola cosa.

### Ticket 3 — Añadir filtro “Compra directa” en Anuncios

**Objetivo**  
Permitir filtrar listings por tipo de compra.

**Contexto**  
La vista `Anuncios` ya filtra por texto, fuente, estado y precio, pero aún no por `buy_it_now`.

**Archivos implicados**

- [app/routers/dashboard.py](./app/routers/dashboard.py)
- [app/templates/listings.html](./app/templates/listings.html)

**Criterios de aceptación**

- aparece un selector nuevo en la pantalla `Anuncios`
- permite `Todos / Solo compra directa / Excluir compra directa`
- el filtro cambia realmente los resultados
- el valor del selector se mantiene al recargar
- no rompe filtros existentes

**Dificultad**  
Baja-media

**Por qué te hace crecer**  
Tocas una mejora real con impacto de producto y poco riesgo técnico.

### Ticket 4 — Hacer visible “Compra directa” en tabla y detalle

**Objetivo**  
Mejorar la legibilidad del dato que acabas de filtrar.

**Contexto**  
Si el dato existe pero no se ve claro, el filtro pierde valor.

**Archivos implicados**

- [app/templates/listings.html](./app/templates/listings.html)
- [app/static/styles.css](./app/static/styles.css)

**Criterios de aceptación**

- el dato se ve en la tabla
- el dato se ve en el panel derecho
- se mantiene la consistencia visual del dashboard

**Dificultad**  
Baja

**Por qué te hace crecer**  
Aprendes a cerrar el ciclo completo entre dato, interfaz y claridad.

### Ticket 5 — Validación manual y nota de cierre

**Objetivo**  
Cerrar la contribución como si estuvieras en un equipo serio.

**Contexto**  
No basta con “parece que funciona”.

**Archivos implicados**

- sin archivo obligatorio

**Criterios de aceptación**

- describes cómo probaste el cambio
- muestras al menos un caso real donde el filtro modifica el resultado
- anotas una limitación o mejora futura

**Dificultad**  
Baja

**Por qué te hace crecer**  
Aprendes validación, comunicación y criterio técnico.

---

## 8. Orden exacto recomendado

Haz las tareas en este orden:

1. Ticket 1 — Levantar el proyecto y explicar el pipeline.
2. Ticket 2 — Mapear rutas, vistas y datos.
3. Leer con calma:
   - [app/models.py](./app/models.py)
   - [app/services/persistence.py](./app/services/persistence.py)
   - [app/services/analyzer.py](./app/services/analyzer.py)
4. Ticket 3 — Añadir filtro `Compra directa`.
5. Ticket 4 — Hacer visible `Compra directa`.
6. Ticket 5 — Validación manual y nota de cierre.

No cambies este orden. Está pensado para que entiendas antes de tocar.

---

## 9. Qué NO debes tocar todavía

No toques todavía estas zonas:

- lógica principal de [app/scrapers/ebay.py](./app/scrapers/ebay.py)
- Wallapop
- heurísticas del analyzer
- estructura de tablas o migraciones
- refactors grandes
- cambios globales del diseño sin ticket cerrado

La razón es simple:

esas zonas tienen más riesgo y todavía no te dan la mejor relación entre aprendizaje y seguridad.

---

## 10. Cómo validar que de verdad entendiste el proyecto

Se considerará que entendiste el proyecto si puedes hacer estas cosas sin ayuda:

1. Explicar con tus palabras el flujo principal.
2. Dibujar el pipeline:

`run_scrapers.py -> Listing -> analyze_opportunities -> Opportunity -> dashboard`

3. Coger un dato real y responder:
   - dónde nace
   - dónde se guarda
   - dónde se transforma
   - dónde se muestra

4. Abrir [app/routers/dashboard.py](./app/routers/dashboard.py) y señalar:
   - qué función sirve cada pantalla
   - qué datos pasan al template

5. Explicar por qué tu primera feature toca esos archivos y no otros.

Si solo sigues pasos sin poder explicar esto, todavía no has entendido el proyecto.

---

## 11. Qué esperamos de tu primera victoria

Tu primera victoria real no es hacer algo “grande”.

Tu primera victoria real es esta:

- entender el sistema
- hacer un cambio útil
- no romper nada
- explicar qué hiciste y por qué

Si consigues eso, ya estás aportando de verdad.

---

## 12. Mini brief para ti

Primero vas a levantar el proyecto y recorrerlo entero.

Después vas a seguir un dato real desde el scraper hasta el dashboard.

Luego vas a mapear qué hace cada pantalla.

Y solo cuando eso esté claro, harás tu primera mejora:

**añadir el filtro `Compra directa` en la vista `Anuncios`**

No tienes que tocar todavía:

- Wallapop
- scraping complejo
- analyzer profundo
- arquitectura grande

Tu objetivo ahora no es reescribir el sistema.

Tu objetivo es demostrar que entiendes cómo funciona y que puedes hacer una mejora pequeña, correcta y útil.

