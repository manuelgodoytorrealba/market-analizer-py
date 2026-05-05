

---

# 🧠 Market Analyzer

> **AI-powered flipping decision engine**
> Convierte listings de marketplaces en decisiones reales de compra.

---

## ✨ Overview

**Market Analyzer** es un sistema diseñado para detectar, analizar y validar oportunidades de reventa en marketplaces como Wallapop.

A diferencia de herramientas básicas, no solo encuentra productos baratos.

👉 Evalúa si realmente deberías comprarlos.

---

## 🚀 What it does

Market Analyzer transforma datos crudos en decisiones accionables:

```text
Listings → Análisis → Oportunidades → Decisión → Plan de compra
```

Responde preguntas clave:

* ¿Es una oportunidad real o un falso positivo?
* ¿Qué beneficio se puede esperar?
* ¿Es seguro comprarlo?
* ¿Cuánto capital debería invertir?
* ¿Qué debo revisar antes de pagar?

---

## 🧠 Core Principles

```text
Clarity over complexity
Decisions over raw data
Quality over quantity
```

---

## 🏗️ Architecture

Sistema modular basado en separación de responsabilidades:

```text
scraper
→ normalizer
→ persistence
→ analyzer (V5)
→ buy_shortlist
→ capital_strategy
→ deal_validator
→ decision_engine
→ API / frontend
```

Cada capa tiene un rol específico y desacoplado.

---

## 🔍 Key Concepts

### Comparable Key

El sistema agrupa productos comparables mediante una clave normalizada:

```text
iphone 13 128gb__complete
rtx 3070__working
macbook pro m1__full_laptop
```

Esto permite:

* comparar precios correctamente
* detectar productos infravalorados
* evitar errores de análisis

---

### Multi-layer Decision System

El sistema separa claramente cada fase:

```text
Analyzer → detecta oportunidades
Shortlist → filtra oportunidades válidas
Capital Strategy → decide inversión
Deal Validator → evalúa riesgos
```

👉 Detección ≠ Compra

---

## ⚙️ Quick Start

```bash
git clone <repo-url>
cd market-analyzer

python -m venv .venv
source .venv/bin/activate   # Linux/Mac
pip install -r requirements.txt

python scripts/setup.py
python scripts/init_db.py
```

---

## ▶️ Run the system

### Scraping

```bash
python scripts/run_scrapers.py --source wallapop
```

---

### Inspect opportunities

```bash
python scripts/inspect_opportunities.py
```

Obtendrás:

* oportunidades detectadas
* shortlist de compra
* plan de inversión
* advertencias de riesgo

---

### API & UI

```bash
uvicorn app.main:app --reload
```

Abrir:

```text
http://localhost:8000/decision-engine-view
```

Endpoint:

```text
GET /decision-engine
```

---

## ⚙️ Configuration

Variables clave:

```bash
MARKET_ANALYZER_CAPITAL_AVAILABLE=500
MARKET_ANALYZER_HIGH_CONVICTION_BUY_SCORE=30
MARKET_ANALYZER_HIGH_CONVICTION_MAX_RATIO=0.85
```

---

## 🧪 Testing

```bash
PYTHONPATH=. python -m unittest \
  tests.test_buy_shortlist \
  tests.test_capital_strategy \
  tests.test_deal_validator \
  tests.test_decision_engine \
  -v
```

---

## 📚 Documentation

Leer:

```text
docs/onboarding.md
```

Incluye:

* arquitectura completa
* flujo de datos
* lógica de decisiones

---

## 🎯 Current Focus

* Wallapop flipping
* multi-categoría
* decisiones más seguras
* optimización de capital

---

## ⚠️ Limitations

* scraping dependiente del marketplace
* datos incompletos en algunos listings
* tests legacy en transición

---

## 🧭 Roadmap

* [ ] enriquecer datos (imágenes, ubicación, descripción)
* [ ] sistema de alertas (Telegram / WhatsApp)
* [ ] multi-market arbitrage (eBay, Vinted…)
* [ ] tracking real de ventas
* [ ] runtime 24/7

---

## 💡 Vision

Convertirse en:

```text
Un sistema automatizado capaz de detectar, validar y ejecutar oportunidades de reventa de forma inteligente.
```

---

## 🧠 Philosophy

```text
No todo lo barato es una oportunidad
No toda oportunidad debe comprarse
No toda compra debe ejecutarse
```

---

## 🤝 Contributing

Pull requests bienvenidos.

Antes de contribuir:

* entender el onboarding
* respetar la separación de capas
* evitar lógica mezclada

---

## 📄 License

MIT (o la que tú quieras definir)

---

## 🔥 Final Thought

> Este proyecto no trata de scraping.
> Trata de tomar mejores decisiones que el mercado.

---

