---
# Pulsar — Documentación unificada
# El script de generación docx usa solo las secciones listadas en docx_sections.
title: Pulsar — Documentación unificada
version: "1.3"
date: Marzo 2026

# Secciones que el script Python incluirá en la presentación docx ejecutiva de ventas.
# Los títulos deben coincidir EXACTAMENTE con un ## del documento (sin #).
docx_sections:
  - "1. Visión del Producto"
  - "2. Propuesta de Valor"
  - "Checklist de venta listo para cliente"
---

## Cómo modificar el YAML (front matter)

**Sí modificar:**

| Clave | Qué hacer |
|-------|-----------|
| `title` | Actualizar si cambia el nombre del documento. |
| `version` | Poner la versión del producto (ej. `"1.4"`). Mantener entre comillas si incluye punto. |
| `date` | Poner mes/año de referencia (ej. `Abril 2026`). |
| `docx_sections` | Añadir o quitar ítems. Cada ítem es el **texto exacto** de un `##` de este .md que quieras en el docx de ventas. Si añades una sección nueva en el documento, copia aquí su título tal cual (ej. `- "3. Arquitectura del Sistema"`). |

**No modificar:**

- El **nombre** de la clave `docx_sections`: el script la busca por ese nombre; si la renombras, hay que cambiar el script.
- La **forma** de la lista: debe seguir siendo una lista YAML con guiones (`- "Título"`). El script espera una lista.
- Los **dos `---`** que encierran el bloque: el primero justo al inicio del archivo y el segundo antes del primer `#`. Sin ellos, el front matter no se reconoce.

# Pulsar — Documentación unificada

> Fuente única: producto, arquitectura, changelog y auditoría.  
> **Versión 1.3** · Marzo 2026

---

## PARTE A — Para ventas e inversores

*(El script docx extrae solo las secciones listadas en `docx_sections` del YAML. Esas secciones deben ser H2: ##.)*

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

## Checklist de venta listo para cliente

- [ ] **Aislamiento de Datos:** RLS configurado y probado en Supabase. Un tenant no puede ver datos de otro.
- [ ] **Suscripción Automatizada:** El cliente puede pagar con tarjeta y su cuenta se activa instantáneamente sin intervención manual.
- [ ] **Métricas Clave:** El panel muestra Ingresos, Ticket Promedio, Retención y Servicios Top.
- [ ] **Reporte Automático:** El sistema es capaz de generar y enviar un resumen mensual por email.
- [ ] **Modo Demo:** Existe un entorno de prueba público y seguro para mostrar a prospectos.
- [ ] **Seguridad:** Webhooks validados criptográficamente e idempotencia implementada para evitar doble facturación.

---

## PARTE B — Arquitectura y técnica

### Estado actual del sistema

El sistema ha sido refactorizado para soportar una arquitectura SaaS multi-tenant robusta, segura y escalable. Separación de responsabilidades (Clean Architecture):

- **`core/`**: Modelos de base de datos con `tenant_id` como FK, CRUD que inyecta y valida el tenant.
- **`integrations/`**: Patrón Adapter (Stripe, MercadoPago, ARCA), validación criptográfica de webhooks.
- **`services/`**: Lógica de negocio (pagos, reportes, importaciones), agnóstica a DB y UI.
- **`analytics/`**: Funciones puras para KPIs (Ingresos, Retención, LTV, Margen).
- **`agents/`**: Sistema multi-agente orquestado para insights de negocio, finanzas y arquitectura.
- **`UI/` & `pages/`**: Streamlit, Paywall dinámico.

### Estado del sistema generado (bloques)

| Bloque | Archivos | Estado |
|--------|----------|--------|
| `config/` | constants.py, logging_config.py, settings.py | ✅ Completo |
| `core/` | database.py, crud.py, models.py, validators.py, permisos.py | ✅ Completo |
| `services/` | payment_services, scheduler, export, notification, import | ✅ Completo |
| `integrations/` | stripe_client, mercadopago_client, arca_client | ✅ Completo |
| `analytics/` | revenue, retention, profitability, lifecycle, stock_rotation | ✅ Completo |
| `agents/` | config + agent_01/02/03 + orchestrator | ✅ Completo |
| `UI/` | KPI_cards, graficas, tablas, sidebar, layout | ✅ Completo |
| `pages/` | 01_Panel a 08_Upgrade | ✅ Completo |
| `app.py` | Entry point multi-tenant | ✅ Completo |
| `data/migrations/` | 001_initial_schema.sql con RLS | ✅ Completo |

### Arquitectura de capas

```
app.py (entry point)
  └── pages/ (orquestación Streamlit)
        ├── UI/ (solo presentación — sin lógica)
        ├── services/ (lógica de negocio)
        │     ├── analytics/ (cálculos KPI puros)
        │     ├── integrations/ (APIs externas)
        │     └── core/ (acceso a datos)
        │           ├── crud.py (queries con tenant_id)
        │           ├── database.py (clientes Supabase)
        │           ├── models.py (Pydantic)
        │           ├── validators.py (inputs puros)
        │           └── permisos.py (acceso por suscripción)
        └── config/ (constantes + logging + settings)
```

### Multi-tenant y Stripe

- **Multi-tenant:** `tenant_id` en todas las tablas, RLS en Supabase, `assert_tenant()` en core, JWT con `app_metadata.tenant_id`.
- **Stripe:** Checkout con `metadata.tenant_id` → Webhook (Edge Function, no Streamlit) → `process_stripe_webhook` → `subscription_status = 'active'`. Eventos: `checkout.session.completed`, `customer.subscription.updated/deleted`, `invoice.payment_failed`.
- **Demo vs Full:** Controlado por `subscription_status`; demo = dataset estático y features limitados; full = reporte mensual automático y exportaciones.

### Stack tecnológico

| Componente | Tecnología |
|------------|------------|
| UI | Streamlit ≥1.35 |
| Lenguaje | Python 3.11 / 3.12 |
| Validación | Pydantic v2 |
| Agentes IA | Anthropic Claude |
| PDF | ReportLab (server-side) |
| Base de datos | Supabase PostgreSQL + RLS |
| Auth | Supabase Auth (JWT tenant_id) |
| Cron | pg_cron |
| Billing | Stripe (primario), MercadoPago, ARCA |

### Variables de entorno (resumen)

Supabase (opcional si `USE_SUPABASE=false`), Stripe, Anthropic, Resend/SendGrid; todas opcionales al arranque salvo Supabase si está activo. Ver Blueprint original para lista completa.

---

## PARTE C — Historial y auditoría

### Cambios recientes (v1.3 — Marzo 2026)

- **Supabase opcional:** `USE_SUPABASE=false` o sin `SUPABASE_URL`; la app arranca con pantalla de instrucciones.
- **Carga segura de `.env`:** UTF-8 con `errors="replace"`.
- **Constantes:** `CACHE_TTL_CLIENTS`, `CACHE_TTL_SERVICES`, `CACHE_TTL_KPI` en `config/constants.py`.
- **Permisos:** `is_subscription_active(tenant)` en `core/permisos.py` para 08_Upgrade.
- **CRUD:** `list_report_history`, `create_report_history_entry` en `core/crud.py`; `render_report_history_table` en `UI/tablas.py` (pantalla 07 Insights).
- **Dependencias:** `supabase<2.24`, `altair<5.5`; Python 3.11 o 3.12 recomendado.
- **Mensajes:** Aviso claro si falta el paquete `supabase`; `DatabaseError` descriptivo cuando Supabase está desactivado.

### Changelog por versión

| Versión | Contenido principal |
|---------|----------------------|
| v1.0 | Core CRUD, schema, motor KPI |
| v1.1 | Agente financiero, retención, orchestrator |
| v1.2 | Agente pricing, operaciones, generador de reportes estratégicos |
| v1.3 | Capa de pagos, import/export, jobs programados, Supabase opcional, report history, permisos |

### Resumen ejecutivo de auditoría (Febrero 2026)

| Bloque | Estado | Riesgo crítico |
|--------|--------|----------------|
| Arquitectura | Sólida en intención, frágil en `app.py` | Mezcla de responsabilidades en entry point |
| Calidad de código | Buenas prácticas en código visible | Duplicación potencial de lógica de acceso |
| Seguridad | Diseño correcto, ejecución sin validar | Enumeración de tenants por slug sin rate limit |
| Base de datos | Schema correcto y defensivo | Backfill irreversible sin transacción documentada |
| Multi-agente | Sin contratos tipados ni timeouts | Agentes pueden congelar la UI |
| Testing | Carpeta existente, cobertura a ampliar | Sistema billing sin tests = riesgo operacional |
| DevOps | Básico funcional | Sin versiones fijas, sin CI |

**Próximo paso recomendado:** Tests unitarios en `test_crud_guards.py` y `test_permisos.py` antes de migraciones SQL en producción.

---

*Pulsar v1.3 · Documentación unificada. Para detalle completo de auditoría ver AUDITORIA.md histórico si se conserva en repo.*
