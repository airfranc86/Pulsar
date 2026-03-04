# Pulsar v1.0 — Multi-Agent System

## Agentes

| Agente | Responsabilidad | Alcance |
|--------|-----------------|---------|
| Agent 01 | Product KPI Analyst | KPIs, pantallas, reporte mensual; narrativa sobre ingresos, ticket, ocupación, cancelaciones, clientes nuevos vs recurrentes |
| Agent 02 | Economic Analyst | Pricing, insights de mercado; contextualiza KPIs con inflación, estacionalidad, sector |
| Agent 03 | SaaS Architect / Operations Advisor | Arquitectura técnica, infra; recomendaciones operativas (ej. horarios con baja ocupación) |

## Uso

```bash
python agents/orchestrator.py
```

## Orden de ejecución
1. Agent 01 → KPIs + pantallas
2. Agent 02 → pricing + insights (recibe output del 01)
3. Agent 03 → arquitectura (recibe output del 01 + 02)
