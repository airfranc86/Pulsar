# Pulsar v1.0 — Product Overview

> Documento de referencia para inversores, partners estratégicos y equipos técnicos.  
> Versión: 1.0 · Febrero 2026

---

## 1. Visión del Producto

### Qué es Pulsar

Pulsar es un **BusinessOps Dashboard SaaS multi-vertical** diseñado para dueños de pequeños negocios de servicios en Latinoamérica. Convierte datos operativos crudos (turnos, pagos, clientes) en decisiones accionables, entregadas automáticamente el primer día de cada mes en el inbox del dueño.

### Problema que Resuelve

El dueño de una barbería, veterinaria o taller en Córdoba opera con visibilidad cero de su negocio:

- No sabe cuánto ganó hasta que mira el cajón al final del mes
- No identifica qué días y horarios tiene capacidad ociosa
- No distingue qué servicios generan margen real vs. cuáles generan volumen sin rentabilidad
- No recibe ningún reporte automático sin contratar a un contador o un analista

Las herramientas existentes (Reservo, Turnero, agenda física) resuelven la **gestión operativa**. Pulsar resuelve la **inteligencia operativa**.

### Mercado Objetivo

**Primario:** Negocios de servicios de 1–10 empleados en Argentina y Latinoamérica con ticket promedio entre USD 10–80 y al menos 50 turnos/mes.

**Verticales en v1.0:** Barbería / Peluquería, Veterinaria, Taller mecánico, Concesionaria posventa, Clínica pequeña, Pyme de servicios genérica.

**Tamaño de mercado (Argentina):** >500.000 negocios de servicios que operan sin software de analítica. Penetración objetivo en 12 meses: 500 tenants activos a USD 19/mes = USD 9.500 MRR.

---

## 2. Propuesta de Valor

### Diferencial Competitivo

| Dimensión | Pulsar | Competidores |
|-----------|--------|--------------|
| Foco | Inteligencia operativa | Gestión de agenda |
| Entrega | Reporte mensual automático en email | Dashboard que requiere acceso activo |
| Barrera de adopción | Demo gratuita, sin setup técnico | Requiere migración de datos o onboarding |
| Precio | USD 19/mes | USD 40–80/mes (herramientas equivalentes) |
| Multi-vertical | Un sistema, N vocabularios | Soluciones verticales separadas |
| Tiempo hasta valor | Primer reporte en 30 días | Semanas de configuración |

**Argumento de venta basado en ROI medible:** Si Pulsar detecta que el martes a las 15h tiene 0 turnos de manera consistente, y ese slot representa 3 turnos perdidos a $15.000 ARS cada uno, el sistema se paga con recuperar 2 horas muertas al mes. El ROI es calculable, específico y atribuible.

### Componentes de IA Multi-Agente

Pulsar integra un sistema de tres agentes especializados coordinados por un orchestrator:

**Agent 01 — Product KPI Analyst**  
Analiza métricas de producto: ingresos, ticket promedio, ocupación, cancelaciones, clientes nuevos vs. recurrentes. Genera narrativa interpretativa sobre los números, no solo los números.

**Agent 02 — Economic Analyst**  
Contextualiza los KPIs del negocio en el contexto económico del período (inflación, estacionalidad, sector). Identifica si una caída de ingresos es del negocio o del mercado.

**Agent 03 — SaaS Architect / Operations Advisor**  
Genera recomendaciones operativas concretas basadas en los patrones detectados. Ejemplos: "Tu martes a las 15h tiene 0 ocupación en los últimos 3 meses. Considerá una promoción de horario bajo demanda."

**Orchestrator**  
Coordina los tres agentes, agrega resultados en un reporte cohesivo y gestiona el contexto del tenant entre ejecuciones. El reporte mensual PDF es el output principal del sistema multi-agente.

### Integraciones de Pago

**Stripe (primario):** Checkout, webhooks, gestión de suscripciones, manejo de pago fallido y cancelaciones. Activación y desactivación de acceso completamente automáticos.

**MercadoPago (LATAM fallback):** Para mercados donde Stripe tiene menor penetración. Integrado en `integrations/mercadopago_client.py`.

**ARCA (Argentina):** Integración con el sistema de facturación electrónica de AFIP para emisión de comprobantes a clientes B2B.

---

## 3. Arquitectura del Sistema

### Diagrama Lógico

```
┌─────────────────────────────────────────────────────────────────┐
│                        USUARIO FINAL                            │
│                    (browser / mobile)                           │
└───────────────────────────┬─────────────────────────────────────┘
                            │ HTTPS
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                   STREAMLIT APP (app.py)                        │
│   Tenant Resolution → Auth Guard → Page Router                  │
│                                                                 │
│   pages/                          UI/                           │
│   ├── 01_Panel.py                 ├── KPI_cards.py              │
│   ├── 02_Clientes.py              ├── graficas.py               │
│   ├── 03_Servicios.py             ├── tablas.py                 │
│   ├── 04_Turnos.py                └── sidebar.py               │
│   ├── 05_Facturacion.py                                         │
│   ├── 06_Analiticas.py                                         │
│   └── 07_Insights.py                                           │
└───────────────────────────┬─────────────────────────────────────┘
                            │
              ┌─────────────┼─────────────┐
              ▼             ▼             ▼
    ┌──────────────┐ ┌──────────────┐ ┌──────────────────────┐
    │   services/  │ │  analytics/  │ │      agents/         │
    │ payment_svc  │ │ revenue      │ │ agent_01_product_kpi │
    │ scheduler    │ │ retention    │ │ agent_02_economic    │
    │ export_svc   │ │ lifecycle    │ │ agent_03_saas        │
    │ import_svc   │ │ profitability│ │ orchestrator         │
    │ notification │ │ stock_rot.   │ └──────────┬───────────┘
    └──────┬───────┘ └──────┬───────┘            │
           │                │                    │ Anthropic API
           └────────────────┴────────────────────┘
                            │
                            ▼
              ┌─────────────────────────┐
              │         core/           │
              │ database.py (Supabase)  │
              │ crud.py (tenant-safe)   │
              │ models.py (Pydantic)    │
              │ permisos.py (access)    │
              │ validators.py (inputs)  │
              └────────────┬────────────┘
                           │
                           ▼
              ┌─────────────────────────┐
              │       SUPABASE          │
              │ PostgreSQL + RLS        │
              │ Auth                    │
              │ Storage (PDF reports)   │
              │ Edge Functions          │
              └────────────┬────────────┘
                           │
          ┌────────────────┼────────────────┐
          ▼                ▼                ▼
    ┌──────────┐    ┌──────────────┐  ┌──────────┐
    │  Stripe  │    │   Resend /   │  │  pg_cron │
    │ Checkout │    │  SendGrid    │  │ (cron    │
    │ Webhooks │    │  (email)     │  │  jobs)   │
    └──────────┘    └──────────────┘  └──────────┘
```

### Flujo de Datos Principal

**Flujo de activación de tenant:**
```
Demo User → Stripe Checkout → Webhook (Edge Function) →
tenants.subscription_status = 'active' → Streamlit detecta cambio →
Dashboard completo desbloqueado
```

**Flujo de reporte mensual:**
```
pg_cron (día configurado, 08:00 UTC) →
Edge Function: check-report-schedule →
Edge Function: generate-monthly-report →
analytics/ KPIs → PDF (reportlab) →
Supabase Storage → Resend email →
monthly_reports.status = 'sent'
```

**Flujo de análisis con agentes:**
```
pages/07_Insights.py →
orchestrator.run_analysis(tenant_id, context) →
[agent_01, agent_02, agent_03] (paralelo con timeout) →
AgentResult[] → UI narrative render
```

---

## 4. Stack Tecnológico

### Backend y Lógica

| Componente | Tecnología | Justificación |
|------------|-----------|---------------|
| Framework UI | Streamlit ≥1.35 | Time-to-market, sin frontend separado, nativo Python |
| Lenguaje | Python 3.11 | Ecosistema de datos, tipado estático con mypy |
| Validación | Pydantic v2 | Performance, serialización, contratos de datos |
| Agentes IA | Anthropic Claude (anthropic SDK) | Calidad de razonamiento analítico, latencia aceptable |
| PDF | ReportLab | Server-side, compatible con Streamlit Cloud sin browser |

### Base de Datos

| Componente | Tecnología | Justificación |
|------------|-----------|---------------|
| Base de datos | Supabase PostgreSQL | Ya en producción, RLS nativo, no migrar |
| Auth | Supabase Auth | JWT con `app_metadata.tenant_id` |
| Storage | Supabase Storage | PDFs mensuales, URLs firmadas |
| Serverless | Supabase Edge Functions (Deno) | Webhooks persistentes, Stripe callbacks |
| Cron | pg_cron | Nativo en Supabase, sin infraestructura adicional |

### Integraciones

| Integración | Propósito | SDK |
|-------------|-----------|-----|
| Stripe | Billing principal | `stripe` Python SDK |
| MercadoPago | Billing LATAM fallback | `mercadopago` Python SDK |
| ARCA (AFIP) | Facturación electrónica Argentina | REST API custom |
| Resend / SendGrid | Email transaccional | REST API |

### Infraestructura Sugerida

**v1.0:** Streamlit Community Cloud (gratis, suficiente para MVP)  
**v1.1:** Render (1 instancia, USD 7/mes) para mayor control de uptime  
**v2.0:** Railway o Fly.io para multi-instancia si escala requiere

---

## 5. Roadmap Evolutivo

### v1.1 — Analítica Avanzada (Q2 2026)

- Comparativa mensual vs. año anterior (12 meses de historia)
- Alertas automáticas por email cuando ocupación cae >15% semana a semana
- Exportación CSV/Excel para contador (feature premium de retención)
- API REST pública para integraciones de terceros (primeros partners)

### v1.2 — Expansión de Verticales (Q3 2026)

- Soporte para stock y productos físicos (`stock_rotation.py` ya incluido)
- Módulo de fidelización: programa de puntos básico integrado en el dashboard
- Facturación electrónica Argentina (AFIP/ARCA) para clientes B2B
- Integración con Google Calendar para sincronización de turnos

### v2.0 — Plataforma Multi-Sede (Q4 2026)

- Un tenant puede tener múltiples sucursales con dashboard consolidado
- Benchmarking anónimo entre negocios del mismo vertical ("tu ticket promedio vs. el promedio del sector")
- Marketplace de integraciones: WhatsApp, Mercado Pago Punto de Venta, sistemas de caja
- API pública documentada para que terceros construyan sobre Pulsar

---

## 6. Escalabilidad

### Qué Puede Migrar a Microservicios (y cuándo)

La arquitectura modular actual es intencionalmente monolítica para v1.0. La extracción a servicios independientes tiene sentido cuando:

**`analytics/` → Servicio de Analytics** (cuando >100 tenants)  
Los cálculos de KPIs son CPU-intensivos y puros. Pueden migrar a un worker Python en Render que expone una API REST consumida por Streamlit. Trigger: latencia de carga de dashboard >3 segundos.

**`agents/` → Servicio de Agentes** (cuando >50 reportes/mes)  
Las llamadas a Anthropic API tienen latencia variable (5–30s). Un servicio async dedicado (FastAPI + Celery) permite desacoplar la generación del reporte del thread de Streamlit. Trigger: reportes mensuales >50 generaciones simultáneas.

**`services/scheduler_service.py` → Job Queue** (cuando >200 tenants)  
pg_cron escala bien hasta ~500 tenants. Más allá, un sistema de colas dedicado (Redis Queue o Supabase Queues cuando esté disponible) es más robusto.

### Cómo Escalar Pagos

Stripe maneja el volumen sin cambios de implementación hasta miles de tenants. El único cambio necesario es implementar **Stripe Connect** cuando se quiera cobrar comisiones a revendedores o partners verticales.

MercadoPago requiere manejo manual de webhooks idempotentes desde el inicio, lo cual ya está contemplado en la arquitectura.

### Cómo Escalar Analíticas

El schema PostgreSQL con `tenant_id` indexado y RLS está diseñado para escalar horizontalmente con **Supabase read replicas** (disponible en plan Pro). Para analíticas históricas masivas (>2 años de datos por tenant), particionar tablas por `tenant_id + YEAR` es el siguiente paso natural.

### Constraint de Memoria (512MB)

Streamlit Community Cloud limita a 512MB de RAM. Las operaciones de mayor consumo identificadas:

- Generación de PDF con ReportLab: ~50MB por reporte
- Cálculo de KPIs mensuales: ~30MB para datasets de hasta 10.000 turnos

**Mitigación implementada:** `@st.cache_data(ttl=N)` por tipo de dato reduce recálculos. Los PDFs se generan en Edge Functions (sin límite de Streamlit). Si el análisis de un tenant supera 500MB, migrar ese tenant a instancia dedicada en Render.

---

*Pulsar v1.0 — BusinessOps Dashboard · Powered by Supabase + Stripe + Anthropic*  
*Documento operativo · No crear documentos paralelos*
