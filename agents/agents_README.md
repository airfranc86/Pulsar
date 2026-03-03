# Pulsar v1.0 — Multi-Agent System

## Agentes

| Agente | Responsabilidad | Sandbox |
|--------|----------------|---------|
| Agent 01 | Product & KPI Designer | KPIs, pantallas, reporte mensual |
| Agent 02 | Economic Analyst | Pricing, insights de mercado |
| Agent 03 | SaaS Architect | Arquitectura técnica, infra |

## Uso

```bash
python agents/orchestrator.py
```

## Orden de ejecución
1. Agent 01 → KPIs + pantallas
2. Agent 02 → pricing + insights (recibe output del 01)
3. Agent 03 → arquitectura (recibe output del 01 + 02)
