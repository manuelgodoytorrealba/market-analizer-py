Vale, ahora sí, sin formato raro, sin etiquetas, sin nada fuera.

👉 **Copia TODO este bloque tal cual y guárdalo como `ONBOARDING.md`**

---

````md
# Onboarding — Market Analyzer

## 🎯 Objetivo

Este documento te guía para:

1. Entender cómo funciona el sistema de verdad.
2. Seguir el flujo completo de los datos.
3. Hacer una primera contribución útil y segura.

---

## ⚙️ Setup previo obligatorio

Antes de empezar:

```bash
python3 scripts/setup.py
python3 scripts/dev.py
````

Asegúrate de que:

* el dashboard carga → [http://127.0.0.1:8000](http://127.0.0.1:8000)
* existen listings en la base de datos
* puedes navegar por todas las vistas

👉 Solo después continúa con este documento.

---

## 🧠 Qué hace este proyecto

Market Analyzer detecta oportunidades de reventa comparando precios entre marketplaces.

### Pipeline principal

```
scraper -> listings -> analyzer -> opportunities -> dashboard
```

---

## 🔄 Flujo real del sistema

1. Scraper obtiene anuncios (Wallapop / eBay)
2. Se normalizan los datos
3. Se guardan como `listings`
4. El analyzer compara productos similares
5. Si hay diferencia de precio → `opportunity`
6. El dashboard muestra todo

---

## 🗺️ Mapa del proyecto

Lee el código en este orden:

### 1. Entrada principal

`app/main.py`

* arranque de FastAPI
* routers
* estáticos

---

### 2. Modelos

`app/models.py`

* Listing → anuncio
* Opportunity → oportunidad
* ScrapeRun → ejecución

---

### 3. CLI y runtime

`scripts/cli.py`
`app/services/runtime.py`

* comandos principales
* queries activas
* ciclo completo

---

### 4. Scrapers

`app/scrapers/`

* wallapop.py
* ebay.py
* browser.py

👉 Solo extracción de datos (no lógica de negocio)

---

### 5. Normalización

`app/services/normalizer.py`

* limpieza de datos
* parsing de productos

---

### 6. Analyzer

`app/services/analyzer.py`

* agrupación de comparables
* cálculo de precios
* detección de oportunidades

---

### 7. Persistencia

`app/services/persistence.py`

* guardar listings
* actualizar
* desactivar
* generar oportunidades

---

### 8. Dashboard

`app/routers/dashboard.py`
`app/templates/`

* vistas web
* filtros
* renderizado

---

## 🖥️ Pantallas del dashboard

* Resumen → estado general
* Oportunidades → resultados clave
* Anuncios → datos crudos
* Evidencia → cómo se calculó
* Ejecuciones → histórico
* Ajustes → configuración

---

## 🧪 Validación básica

```bash
python -m unittest discover -s tests -v
```

```bash
python -m scripts.cli once --source wallapop
```

---

## 🔍 Cómo seguir un dato real

1. Ve a `/listings`
2. Elige un producto
3. Identifica:

   * origen (scraper)
   * query
4. Ve a `/opportunities`
5. Revisa si aparece
6. Analiza su evidencia

👉 Si puedes hacer esto → entiendes el sistema

---

## 🚀 Primera contribución recomendada

### Feature: Filtro "Compra directa"

Añadir filtro en `/listings`:

* Todos
* Solo compra directa
* Excluir compra directa

---

### Archivos

* `app/routers/dashboard.py`
* `app/templates/listings.html`

---

### Qué aprenderás

* filtros backend
* query params
* UI + datos
* flujo completo

---

## ⚠️ Qué NO tocar

* scrapers complejos
* analyzer profundo
* estructura DB
* refactors grandes

---

## 🧠 Reglas

* Scrapers → solo extraen datos
* Services → lógica de negocio
* UI → visualización
* No mezclar responsabilidades

---

## 🧾 Git workflow

```bash
git checkout develop
git pull origin develop
git checkout -b feature/tu-feature
```

```bash
git add .
git commit -m "feat: describe cambio"
git push
```

PR → base `develop`

---

## ✅ Criterios de éxito

Puedes:

1. Explicar el pipeline
2. Seguir un dato completo
3. Añadir un filtro sin romper nada
4. Justificar cambios

---

## 🧠 Filosofía

* cambios pequeños
* claridad > complejidad
* entender antes de tocar

---

## 🏁 Primera victoria

* entender sistema
* mejorar algo pequeño
* no romper nada
* explicar bien

---

## 🚀 Siguiente nivel

* mejorar analyzer
* sistema genérico (no solo iPhone)
* nuevos providers
* alertas automáticas
* runtime 24/7

---

## 🔥 Resumen

1. Levanta el sistema
2. Entiende el flujo
3. Haz una mejora pequeña
4. Valida que todo sigue funcionando
```
