# Pulsar v1.0 — MVP Blueprint
**BusinessOps Dashboard · SaaS Multi-Vertical**
*Documento operativo único · No crear documentos paralelos*
*Release: 1.3 · Objetivo: MVP vendible en 4 semanas*

Fecha: 19-02-2026

---

## ESTADO DEL AGENTE

**Qué hizo este documento:**
Estructurar y profesionalizar Pulsar v1.0 sobre la infraestructura existente (Supabase + Streamlit). No inventa producto nuevo. Parte de la base de Santa Barba como primer tenant real. Extiende el sistema a multi-vertical por configuración, no por código separado.

**Qué no tocó (fuera de scope):**
No rediseñó el stack. No migró fuera de Supabase. No creó segundo repositorio. No agregó infraestructura externa innecesaria. No propuso microservicios. No cambió KPIs base. No introdujo features enterprise.

**Próximo paso único recomendado:**
Ejecutar el bloque SQL de la Sección 3.1 (agregar `tenant_id` a tablas existentes + RLS) en el Supabase de producción actual antes de cualquier otra tarea.

**Completado (remediación feb 2026):**
- **Fase 1:** Corregido import `require_tenant` en crud y `payment_services`.
- **Fase 2:** Seguridad — tenant por slug, JWT, `get_admin_client` para operaciones admin.
- **Fase 3:** Lógica y UX — ocupación, singular/plural, precio Upgrade.
- **Fase 4:** Caché quirúrgico, cliente fuera de caché, limpieza de imports.
- **Fase 5:** Tests analytics, retry Supabase, `requirements.txt` actualizado.

**Completado (marzo 2026):**
- **Supabase opcional:** `USE_SUPABASE=false` o sin `SUPABASE_URL`; la app arranca y muestra instrucciones. Stripe/Anthropic también opcionales al inicio.
- **Constantes de caché:** `CACHE_TTL_CLIENTS`, `CACHE_TTL_SERVICES`, `CACHE_TTL_KPI` en `config/constants.py`.
- **Report history:** `list_report_history`, `create_report_history_entry` en `core/crud.py`; `render_report_history_table` en `UI/tablas.py`; pantalla Insights operativa.
- **Permisos:** `is_subscription_active(tenant)` en `core/permisos.py` para Upgrade.
- **Dependencias:** `supabase>=2.10.0,<2.24` (evitar pyiceberg); `altair>=5.4.0,<5.5` (Python 3.14). Python 3.11/3.12 recomendado en `requirements.txt`.
- **Entorno:** Carga segura de `.env` (UTF-8 con `errors="replace"`); mensaje claro si falta el paquete `supabase`.

---

## SECCIÓN 1 — Estado actual del sistema

### 1.1 Lo que ya existe y funciona

El sistema actual tiene:

- Supabase en producción con tablas `profiles`, `services`, `appointments`
- Streamlit UI con páginas de dashboard, turnos, servicios, configuración
- Autenticación via Supabase Auth
- Módulos: `auth_manager.py`, `supabase_client.py`, `appointment_utils.py`, `export_utils.py`, `cache_utils.py`, `audit_logger.py`
- Agentes de análisis: `agent_01_product_kpi.py`, `agent_02_economic_analyst.py`, `agent_03_saas_architect.py`
- Generación de QR, confirmación de turnos por email, historial de acceso

### 1.2 Lo que falta para ser SaaS vendible

| Componente | Estado actual | Acción requerida |
|---|---|---|
| `tenant_id` en tablas | ❌ Ausente | Agregar columna UUID + backfill con Tenant 001 |
| Row Level Security | ❌ Sin RLS real | Implementar policies por `tenant_id` |
| Tabla `tenants` | ❌ No existe | Crear con `subscription_status` |
| Stripe Checkout | ❌ No existe | Implementar `src/billing/` |
| Stripe Webhook | ❌ No existe | Supabase Edge Function |
| Reporte mensual PDF | ❌ No existe | Edge Function + pg_cron + Storage |
| Demo pública | ❌ No existe | DEMO_MODE flag + datos sintéticos |
| `monthly_reports` tabla | ❌ No existe | Crear para historial |

### 1.3 Diagnóstico crítico del schema

El schema actual opera como **single-tenant implícito**. Todas las filas en `appointments` y `services` pertenecen a Santa Barba sin marcador de tenant. La prioridad absoluta es agregar `tenant_id` y aplicar RLS antes de cualquier otra cosa.

---

## SECCIÓN 2 — Propuesta de valor multi-vertical

### 2.1 El problema real del dueño de negocio

El dueño de una barbería, veterinaria, taller o clínica pequeña en Córdoba:
- No sabe cuánto ganó hasta que mira el cajón
- No sabe si el martes a las 15h siempre está vacío
- No sabe qué servicio le genera más margen
- No recibe ningún reporte mensual

**Lo que Pulsar v1.0 resuelve:** Un resumen ejecutivo de 1 página que llega al email del dueño el primer día del mes, sin que él tenga que hacer nada. Y un dashboard siempre disponible que dice exactamente cómo va el negocio.

### 2.2 Propuesta de valor por vertical

Todos usan el mismo sistema. Solo cambian los labels:

| Vertical | "Servicio" se llama | "Turno" se llama | Caso de uso principal |
|---|---|---|---|
| Barbería / Peluquería | Corte, barba | Turno | Ocupación por barbero y hora pico |
| Veterinaria | Consulta, cirugía | Cita | Recurrencia por mascota/dueño |
| Taller mecánico | Reparación, service | Orden de trabajo | Ticket promedio por tipo de trabajo |
| Concesionaria | Servicio posventa | Turno taller | Horas pico y eficiencia técnica |
| Clínica pequeña | Consulta, procedimiento | Turno médico | Pacientes nuevos vs recurrentes |
| Pyme de servicios | Servicio genérico | Reserva | Ingresos y cancelaciones |

> **Argumento de venta basado en ROI:** Si Pulsar detecta que el martes a las 15h hay 0 turnos y eso representa 3 turnos perdidos a $15.000 ARS cada uno, el sistema se paga solo con recuperar 2 horas muertas por mes.

### 2.3 Pricing recomendado

| Plan | Precio | Qué incluye |
|---|---|---|
| **Demo** | Gratis | KPIs con datos sintéticos borrosos, sin historial, sin reporte, CTA de upgrade |
| **Básico** | USD 19/mes | Dashboard completo, reporte mensual automático, 1 local |
| **Pro** | USD 39/mes | Todo lo anterior + comparativa anual, alertas automáticas, exportación CSV |

**Precio de lanzamiento:** USD 19/mes para los primeros 10 clientes. Sube a USD 29 en lanzamiento público.

**3 features premium de retención (post-MVP):**
1. Reporte con comparativa anual (12 meses de historia, mes a mes)
2. Alerta automática cuando la ocupación cae más de 15% vs semana anterior
3. Exportación CSV para el contador

---

## SECCIÓN 3 — Cambios mínimos para multi-tenant

### 3.1 Migraciones SQL requeridas (ejecutar en orden)

```sql
-- ============================================================
-- PASO 1: Crear tabla de tenants
-- ============================================================
CREATE TABLE IF NOT EXISTS tenants (
  id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  slug                    TEXT UNIQUE NOT NULL,
  name                    TEXT NOT NULL,
  vertical                TEXT NOT NULL DEFAULT 'generic',
    -- valores: 'barberia' | 'veterinaria' | 'taller' | 'concesionaria' | 'clinica' | 'generic'
  email                   TEXT NOT NULL,
  plan                    TEXT NOT NULL DEFAULT 'demo',
    -- valores: 'demo' | 'active' | 'cancelled'
  subscription_status     TEXT NOT NULL DEFAULT 'inactive',
    -- valores: 'inactive' | 'active' | 'past_due' | 'cancelled'
  stripe_customer_id      TEXT,
  stripe_subscription_id  TEXT,
  current_period_end      TIMESTAMP WITH TIME ZONE,
  report_day              INTEGER DEFAULT 1 CHECK (report_day BETWEEN 1 AND 28),
  report_email            TEXT,
  service_label           TEXT DEFAULT 'Servicio',
    -- label dinámico por vertical: 'Corte', 'Consulta', 'Reparación', etc.
  created_at              TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at              TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================
-- PASO 2: Crear tabla de monthly_reports
-- ============================================================
CREATE TABLE IF NOT EXISTS monthly_reports (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id   UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  period      TEXT NOT NULL,  -- 'YYYY-MM'
  pdf_url     TEXT,
  sent_at     TIMESTAMP WITH TIME ZONE,
  status      TEXT DEFAULT 'pending',
    -- 'pending' | 'generated' | 'sent' | 'failed'
  kpi_snapshot JSONB,  -- snapshot de KPIs del mes
  created_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================
-- PASO 3: Agregar tenant_id a tablas existentes
-- ============================================================
ALTER TABLE profiles
  ADD COLUMN IF NOT EXISTS tenant_id UUID REFERENCES tenants(id);

ALTER TABLE services
  ADD COLUMN IF NOT EXISTS tenant_id UUID REFERENCES tenants(id);

ALTER TABLE appointments
  ADD COLUMN IF NOT EXISTS tenant_id UUID REFERENCES tenants(id);

-- ============================================================
-- PASO 4: Crear Tenant 001 — Santa Barba (demo real)
-- ============================================================
INSERT INTO tenants (id, slug, name, vertical, email, plan, subscription_status, service_label)
VALUES (
  'tenant-001-id',
  'santa-barba',
  'Santa Barba',
  'barberia',
  'admin@santabarba.com',
  'active',
  'active',
  'Corte'
)
ON CONFLICT (slug) DO NOTHING;

-- ============================================================
-- PASO 5: Backfill de datos existentes → Tenant 001
-- ============================================================
UPDATE profiles
SET tenant_id = 'tenant-001-id'
WHERE tenant_id IS NULL;

UPDATE services
SET tenant_id = 'tenant-001-id'
WHERE tenant_id IS NULL;

UPDATE appointments
SET tenant_id = 'tenant-001-id'
WHERE tenant_id IS NULL;

-- ============================================================
-- PASO 6: Hacer tenant_id NOT NULL después del backfill
-- ============================================================
ALTER TABLE profiles   ALTER COLUMN tenant_id SET NOT NULL;
ALTER TABLE services   ALTER COLUMN tenant_id SET NOT NULL;
ALTER TABLE appointments ALTER COLUMN tenant_id SET NOT NULL;

-- ============================================================
-- PASO 7: Índices de performance
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_appointments_tenant_id ON appointments(tenant_id);
CREATE INDEX IF NOT EXISTS idx_services_tenant_id ON services(tenant_id);
CREATE INDEX IF NOT EXISTS idx_monthly_reports_tenant_id ON monthly_reports(tenant_id);
CREATE INDEX IF NOT EXISTS idx_monthly_reports_period ON monthly_reports(tenant_id, period);

-- ============================================================
-- PASO 8: Verificación post-migración
-- ============================================================
SELECT
  (SELECT COUNT(*) FROM appointments WHERE tenant_id IS NULL) AS appointments_sin_tenant,
  (SELECT COUNT(*) FROM services     WHERE tenant_id IS NULL) AS services_sin_tenant,
  (SELECT COUNT(*) FROM profiles     WHERE tenant_id IS NULL) AS profiles_sin_tenant;
-- Resultado esperado: todo en 0
```

### 3.2 Row Level Security (RLS)

```sql
-- ============================================================
-- Habilitar RLS en todas las tablas
-- ============================================================
ALTER TABLE tenants       ENABLE ROW LEVEL SECURITY;
ALTER TABLE profiles      ENABLE ROW LEVEL SECURITY;
ALTER TABLE services      ENABLE ROW LEVEL SECURITY;
ALTER TABLE appointments  ENABLE ROW LEVEL SECURITY;
ALTER TABLE monthly_reports ENABLE ROW LEVEL SECURITY;

-- ============================================================
-- Helper function: obtener tenant_id del usuario autenticado
-- ============================================================
CREATE OR REPLACE FUNCTION get_user_tenant_id()
RETURNS UUID
LANGUAGE sql
STABLE
AS $$
  SELECT tenant_id FROM profiles
  WHERE id = auth.uid()
  LIMIT 1;
$$;

-- ============================================================
-- Policies: cada usuario solo ve datos de su tenant
-- ============================================================

-- profiles
CREATE POLICY "profiles_tenant_isolation"
ON profiles FOR ALL
USING (tenant_id = get_user_tenant_id());

-- services
CREATE POLICY "services_tenant_isolation"
ON services FOR ALL
USING (tenant_id = get_user_tenant_id());

-- appointments
CREATE POLICY "appointments_tenant_isolation"
ON appointments FOR ALL
USING (tenant_id = get_user_tenant_id());

-- monthly_reports
CREATE POLICY "monthly_reports_tenant_isolation"
ON monthly_reports FOR ALL
USING (tenant_id = get_user_tenant_id());

-- tenants: solo el propio tenant
CREATE POLICY "tenants_own_record"
ON tenants FOR SELECT
USING (id = get_user_tenant_id());

-- ============================================================
-- Verificación RLS: este query debe devolver 0 filas
-- si el usuario no pertenece a tenant 'tenant-002-id'
-- ============================================================
-- SELECT COUNT(*) FROM appointments
-- WHERE tenant_id = 'tenant-002-id';
-- Expected: 0
```

---

## SECCIÓN 4 — KPIs universales y adaptación por vertical

### 4.1 Los 8 KPIs obligatorios del MVP (no modificables)

Todos los KPIs se calculan por `tenant_id` y por rango de fechas (mes actual por defecto).

| KPI | Query base | Fuente |
|---|---|---|
| **Ingresos mensuales** | `SUM(payments.amount) WHERE status = 'completed'` | `appointments` (campo `precio_cobrado`) |
| **Ticket promedio** | `AVG(precio_cobrado) WHERE estado = 'completado'` | `appointments` |
| **Servicios más vendidos** | `COUNT(*) GROUP BY service_id ORDER BY DESC LIMIT 5` | `appointments` + `services` |
| **Clientes nuevos vs recurrentes** | Primera aparición ever vs visita #2+ en el mes | `appointments` por `telefono` + `fecha` |
| **Ocupación de turnos (%)** | `(completados / slots_disponibles) * 100` | `appointments` vs horario configurado |
| **Cancelaciones / no-shows** | `COUNT(*) WHERE estado IN ('cancelado', 'no_show')` | `appointments` |
| **Horas pico** | `COUNT(*) GROUP BY EXTRACT(HOUR FROM hora)` | `appointments` |
| **Comparación vs mes anterior** | Delta % de ingresos, ticket y ocupación | cálculo Python sobre queries anteriores |

### 4.2 Adaptación semántica por vertical (mismo KPI, distinto label)

El campo `service_label` en la tabla `tenants` controla el vocabulario visible:

| Vertical | "Servicios más vendidos" | "Turnos" | "Clientes" |
|---|---|---|---|
| Barbería | Cortes más realizados | Turnos de corte | Clientes |
| Veterinaria | Consultas más frecuentes | Citas veterinarias | Pacientes/dueños |
| Taller mecánico | Reparaciones más solicitadas | Órdenes de trabajo | Vehículos atendidos |
| Concesionaria | Servicios posventa top | Turnos taller | Titulares |
| Clínica | Procedimientos más realizados | Turnos médicos | Pacientes |
| Generic | Servicios más vendidos | Reservas | Clientes |

**Implementación en Streamlit:**
```python
# src/kpis/labels.py
VERTICAL_LABELS = {
    "barberia":      {"service": "Corte", "appointment": "Turno",     "client": "Cliente"},
    "veterinaria":   {"service": "Consulta", "appointment": "Cita",   "client": "Paciente"},
    "taller":        {"service": "Reparación", "appointment": "Orden","client": "Vehículo"},
    "concesionaria": {"service": "Service",  "appointment": "Turno",  "client": "Titular"},
    "clinica":       {"service": "Procedimiento","appointment":"Turno","client": "Paciente"},
    "generic":       {"service": "Servicio", "appointment": "Reserva","client": "Cliente"},
}

def get_labels(vertical: str) -> dict:
    return VERTICAL_LABELS.get(vertical, VERTICAL_LABELS["generic"])
```

---

## SECCIÓN 5 — Stripe flow exacto

### 5.1 Arquitectura del paywall

```
Usuario en Demo
    │
    ▼
[ Botón "Activar mi dashboard" ]
    │
    ▼
src/billing/stripe_checkout.py
→ stripe.checkout.Session.create(
    mode="subscription",
    price=STRIPE_PRICE_ID,
    client_reference_id=tenant_id,
    success_url=APP_BASE_URL + "?activated=true",
    cancel_url=APP_BASE_URL + "?cancelled=true"
  )
    │
    ▼
Stripe procesa el pago
    │
    ▼
Stripe envía POST al webhook
    │
    ▼
Supabase Edge Function: stripe-webhook
→ Verifica firma (STRIPE_WEBHOOK_SECRET)
→ Detecta evento: checkout.session.completed
→ Extrae tenant_id de client_reference_id
→ UPDATE tenants SET
    subscription_status = 'active',
    stripe_customer_id = ...,
    stripe_subscription_id = ...,
    current_period_end = ...
  WHERE id = tenant_id
    │
    ▼
Streamlit lee subscription_status en cada request
→ Si 'active': muestra dashboard completo
→ Si != 'active': muestra pantalla de upgrade
```

**CRÍTICO: el webhook NO vive dentro de Streamlit.** Vive exclusivamente en una Supabase Edge Function.

### 5.2 Implementación Python — Stripe Checkout

```python
# src/billing/stripe_checkout.py
import stripe
import streamlit as st
from src.db.tenants import get_tenant

stripe.api_key = st.secrets["STRIPE_SECRET_KEY"]
STRIPE_PRICE_ID = st.secrets["STRIPE_PRICE_ID"]
APP_BASE_URL = st.secrets["APP_BASE_URL"]

def create_checkout_session(tenant_id: str) -> str:
    """Crea una Stripe Checkout Session y retorna la URL de pago."""
    tenant = get_tenant(tenant_id)
    session = stripe.checkout.Session.create(
        mode="subscription",
        line_items=[{"price": STRIPE_PRICE_ID, "quantity": 1}],
        client_reference_id=tenant_id,
        customer_email=tenant["email"],
        success_url=f"{APP_BASE_URL}?activated=true",
        cancel_url=f"{APP_BASE_URL}?cancelled=true",
    )
    return session.url

def enforce_paywall(tenant_id: str) -> bool:
    """Retorna True si el tenant tiene acceso. Muestra pantalla de upgrade si no."""
    from src.db.tenants import get_subscription_status
    status = get_subscription_status(tenant_id)
    if status == "active":
        return True
    # Mostrar pantalla de upgrade
    st.warning("⚠️ Tu suscripción no está activa.")
    st.markdown("### Activá tu dashboard completo")
    st.markdown("Acceso completo a todos los KPIs, reporte mensual automático y más.")
    checkout_url = create_checkout_session(tenant_id)
    st.link_button("💳 Activar ahora — USD 19/mes", checkout_url)
    st.stop()
    return False
```

### 5.3 Supabase Edge Function — stripe-webhook

```typescript
// supabase/functions/stripe-webhook/index.ts
import { serve } from "https://deno.land/std@0.168.0/http/server.ts"
import { createClient } from "https://esm.sh/@supabase/supabase-js@2"
import Stripe from "https://esm.sh/stripe@12.0.0"

const stripe = new Stripe(Deno.env.get("STRIPE_SECRET_KEY")!, {
  apiVersion: "2023-10-16",
  httpClient: Stripe.createFetchHttpClient(),
})

const supabase = createClient(
  Deno.env.get("SUPABASE_URL")!,
  Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!
)

serve(async (req) => {
  const signature = req.headers.get("stripe-signature")!
  const body = await req.text()

  let event: Stripe.Event
  try {
    event = stripe.webhooks.constructEventAsync(
      body, signature, Deno.env.get("STRIPE_WEBHOOK_SECRET")!
    )
  } catch (err) {
    return new Response(`Webhook signature verification failed: ${err.message}`, { status: 400 })
  }

  switch (event.type) {
    case "checkout.session.completed": {
      const session = event.data.object as Stripe.Checkout.Session
      const tenantId = session.client_reference_id
      const subscriptionId = session.subscription as string
      const subscription = await stripe.subscriptions.retrieve(subscriptionId)

      await supabase.from("tenants").update({
        subscription_status: "active",
        plan: "active",
        stripe_customer_id: session.customer,
        stripe_subscription_id: subscriptionId,
        current_period_end: new Date(subscription.current_period_end * 1000).toISOString(),
        updated_at: new Date().toISOString(),
      }).eq("id", tenantId)
      break
    }
    case "customer.subscription.deleted":
    case "customer.subscription.paused": {
      const subscription = event.data.object as Stripe.Subscription
      await supabase.from("tenants").update({
        subscription_status: "cancelled",
        plan: "demo",
        updated_at: new Date().toISOString(),
      }).eq("stripe_subscription_id", subscription.id)
      break
    }
    case "invoice.payment_failed": {
      const invoice = event.data.object as Stripe.Invoice
      await supabase.from("tenants").update({
        subscription_status: "past_due",
        updated_at: new Date().toISOString(),
      }).eq("stripe_customer_id", invoice.customer)
      break
    }
  }

  return new Response(JSON.stringify({ received: true }), {
    headers: { "Content-Type": "application/json" },
  })
})
```

### 5.4 Variables de entorno requeridas

```bash
# Streamlit secrets (.streamlit/secrets.toml)
SUPABASE_URL = "https://xxx.supabase.co"
SUPABASE_ANON_KEY = "eyJ..."
STRIPE_SECRET_KEY = "sk_live_..."
STRIPE_PRICE_ID = "price_..."
APP_BASE_URL = "https://pulsar.streamlit.app"

# Supabase Edge Function secrets (Dashboard → Settings → Edge Functions)
STRIPE_SECRET_KEY = "sk_live_..."
STRIPE_WEBHOOK_SECRET = "whsec_..."
SUPABASE_URL         # auto-disponible
SUPABASE_SERVICE_ROLE_KEY  # auto-disponible
```

---

## SECCIÓN 6 — Reporte mensual automático

### 6.1 Arquitectura del flujo automático

```
pg_cron: diario a las 08:00 UTC
    │
    ▼
SQL Function: check_report_schedule()
→ SELECT tenants WHERE
    subscription_status = 'active'
    AND EXTRACT(DAY FROM NOW()) = report_day
    AND NOT EXISTS (
        SELECT 1 FROM monthly_reports
        WHERE tenant_id = tenants.id
        AND period = TO_CHAR(NOW() - INTERVAL '1 month', 'YYYY-MM')
    )
    │
    ▼
Para cada tenant que cumple condición:
→ HTTP call a Edge Function: generate-monthly-report
    │
    ▼
Edge Function: generate-monthly-report
→ Consulta KPIs del mes anterior para ese tenant
→ Genera PDF con reportlab (o WeasyPrint en Python worker)
→ Sube PDF a Supabase Storage: monthly-reports/{tenant_id}/{YYYY-MM}.pdf
→ Obtiene URL pública del PDF
→ INSERT INTO monthly_reports (tenant_id, period, pdf_url, status, kpi_snapshot)
→ Llama a Edge Function: send-report-email
    │
    ▼
Edge Function: send-report-email
→ Resend API → email al report_email del tenant
→ UPDATE monthly_reports SET sent_at = NOW(), status = 'sent'
```

### 6.2 SQL — pg_cron scheduler

```sql
-- Habilitar pg_cron (una sola vez en Supabase Dashboard → Extensions)
-- CREATE EXTENSION IF NOT EXISTS pg_cron;

-- Job: revisar todos los días a las 08:00 UTC quién debe recibir reporte
SELECT cron.schedule(
  'check-monthly-reports',
  '0 8 * * *',
  $$
  SELECT net.http_post(
    url := current_setting('app.supabase_url') || '/functions/v1/check-report-schedule',
    headers := jsonb_build_object(
      'Authorization', 'Bearer ' || current_setting('app.service_role_key'),
      'Content-Type', 'application/json'
    ),
    body := '{}'::jsonb
  );
  $$
);
```

### 6.3 Edge Function — check-report-schedule

```typescript
// supabase/functions/check-report-schedule/index.ts
import { serve } from "https://deno.land/std@0.168.0/http/server.ts"
import { createClient } from "https://esm.sh/@supabase/supabase-js@2"

const supabase = createClient(
  Deno.env.get("SUPABASE_URL")!,
  Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!
)

serve(async () => {
  const today = new Date()
  const currentDay = today.getDate()
  const lastMonth = new Date(today.getFullYear(), today.getMonth() - 1, 1)
  const period = `${lastMonth.getFullYear()}-${String(lastMonth.getMonth() + 1).padStart(2, '0')}`

  // Obtener tenants activos donde hoy es su report_day y aún no tienen reporte del mes anterior
  const { data: tenants } = await supabase
    .from("tenants")
    .select("id, email, name, report_email, vertical")
    .eq("subscription_status", "active")
    .eq("report_day", currentDay)

  if (!tenants || tenants.length === 0) {
    return new Response(JSON.stringify({ processed: 0 }), { status: 200 })
  }

  let processed = 0
  for (const tenant of tenants) {
    // Verificar que no se generó ya el reporte este mes
    const { data: existing } = await supabase
      .from("monthly_reports")
      .select("id")
      .eq("tenant_id", tenant.id)
      .eq("period", period)
      .single()

    if (existing) continue

    // Disparar generación del reporte
    await fetch(
      Deno.env.get("SUPABASE_URL")! + "/functions/v1/generate-monthly-report",
      {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ tenant_id: tenant.id, period }),
      }
    )
    processed++
  }

  return new Response(JSON.stringify({ processed }), { status: 200 })
})
```

### 6.4 Generación del PDF (Python worker alternativo)

Si la generación de PDF se realiza en Python (más simple que en Deno), la Edge Function `generate-monthly-report` puede llamar a un endpoint de Streamlit en modo script o a un worker Python en Render mínimo. Sin embargo, **para mantener la arquitectura dentro del stack existente**, la opción recomendada es:

1. La Edge Function consulta los KPIs y guarda el snapshot en JSONB en `monthly_reports`
2. Un script Python (`src/reports/generate_pdf.py`) se ejecuta vía GitHub Actions (cron mensual) o como Streamlit script batch
3. El PDF se genera con `reportlab` y se sube a Supabase Storage

```python
# src/reports/generate_pdf.py
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from src.db.kpis import get_monthly_kpis
from src.db.supabase_storage import upload_pdf

def generate_report(tenant_id: str, period: str) -> str:
    """Genera PDF de reporte mensual. Retorna la URL pública en Storage."""
    kpis = get_monthly_kpis(tenant_id, period)
    tenant = get_tenant(tenant_id)
    labels = get_labels(tenant["vertical"])

    # Generar PDF en memoria
    from io import BytesIO
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    w, h = A4

    # Header
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, h - 60, f"{tenant['name']} — Resumen Operativo {period}")

    # KPIs
    c.setFont("Helvetica", 12)
    y = h - 120
    line_height = 24

    c.drawString(50, y, f"Ingresos del mes: ${kpis['ingresos']:,.0f}"); y -= line_height
    c.drawString(50, y, f"Ticket promedio: ${kpis['ticket_promedio']:,.0f}"); y -= line_height
    c.drawString(50, y, f"Turnos realizados: {kpis['turnos_completados']}"); y -= line_height
    c.drawString(50, y, f"Ocupación: {kpis['ocupacion']:.1f}%"); y -= line_height
    c.drawString(50, y, f"Clientes nuevos: {kpis['clientes_nuevos']}"); y -= line_height
    c.drawString(50, y, f"Clientes recurrentes: {kpis['clientes_recurrentes']}"); y -= line_height
    c.drawString(50, y, f"Cancelaciones: {kpis['cancelaciones']} ({kpis['tasa_cancelacion']:.1f}%)"); y -= line_height
    c.drawString(50, y, f"No-shows: {kpis['no_shows']}"); y -= line_height

    y -= 20
    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, y, f"Top {labels['service']}s del mes:"); y -= line_height
    c.setFont("Helvetica", 11)
    for i, srv in enumerate(kpis["top_services"][:5], 1):
        c.drawString(60, y, f"{i}. {srv['nombre']} — {srv['count']} realizados"); y -= line_height

    y -= 20
    c.setFont("Helvetica", 10)
    c.drawString(50, y, f"Powered by Pulsar v1.0 — Próximo reporte: 1 del mes siguiente")

    c.save()
    buffer.seek(0)

    # Subir a Supabase Storage
    path = f"monthly-reports/{tenant_id}/{period}.pdf"
    url = upload_pdf(path, buffer.read())
    return url
```

### 6.5 Email de entrega — Resend API

```python
# src/reports/send_email.py
import resend

resend.api_key = RESEND_API_KEY

def send_report_email(tenant: dict, period: str, pdf_url: str):
    resend.Emails.send({
        "from": "reportes@pulsar.app",
        "to": tenant["report_email"],
        "subject": f"Tu reporte mensual Pulsar — {period}",
        "html": f"""
        <h2>Hola {tenant['name']},</h2>
        <p>Tu reporte operativo de <strong>{period}</strong> ya está disponible.</p>
        <p><a href="{pdf_url}" style="background:#1a1a1a;color:white;padding:12px 24px;
           text-decoration:none;border-radius:4px;">Ver reporte PDF</a></p>
        <p>También podés verlo en tu dashboard en cualquier momento.</p>
        <br><small>Pulsar v1.0 · Responder este email para soporte</small>
        """,
    })
```

---

## SECCIÓN 7 — Demo vs Full Mode

### 7.1 Un solo repositorio, un solo sistema

El modo se controla exclusivamente por `subscription_status` del tenant autenticado. No hay rama demo separada. No hay código duplicado.

```python
# app.py — lógica central de modo
import streamlit as st
from src.auth.auth_guard import get_current_tenant
from src.billing.stripe_checkout import enforce_paywall

def get_app_mode(tenant: dict) -> str:
    """Retorna 'demo' o 'full' según el estado de suscripción."""
    if not tenant:
        return "demo"  # Usuario no autenticado: demo pública
    if tenant["subscription_status"] == "active":
        return "full"
    return "demo"
```

### 7.2 DEMO_MODE — comportamiento

| Feature | DEMO_MODE | FULL_MODE |
|---|---|---|
| KPIs visibles | Sí, pero valores ocultos (`████`) | Sí, valores reales |
| Datos | Sintéticos (dataset hardcodeado) | Reales del tenant |
| Exportar PDF | ❌ Bloqueado | ✅ Disponible |
| Historial reportes | ❌ Bloqueado | ✅ Disponible |
| Configurar día de reporte | ❌ Bloqueado | ✅ Disponible |
| Horas pico | Visible parcial | Completo |
| CTA de upgrade | ✅ Siempre visible | ❌ Oculto |

### 7.3 Dataset sintético para demo pública

```python
# src/kpis/demo_data.py
DEMO_KPIs = {
    "ingresos": 1_840_000,
    "ticket_promedio": 12_400,
    "turnos_completados": 148,
    "ocupacion": 78.3,
    "clientes_nuevos": 23,
    "clientes_recurrentes": 125,
    "cancelaciones": 14,
    "no_shows": 6,
    "tasa_cancelacion": 8.7,
    "delta_ingresos": 12.0,
    "delta_ticket": 5.0,
    "delta_ocupacion": -3.0,
    "top_services": [
        {"nombre": "Servicio A", "count": 142},
        {"nombre": "Servicio B", "count": 98},
        {"nombre": "Servicio C", "count": 67},
    ],
    "horas_pico": {10: 28, 11: 31, 15: 18, 16: 22, 17: 25}
}
```

---

## SECCIÓN 9 — Roadmap semana 1 a 4

### Semana 1 — Infraestructura multi-tenant + RLS

**Objetivo:** Santa Barba funciona como tenant real, aislado y seguro.

- [ ] Ejecutar migración SQL de la Sección 3.1 en Supabase producción
- [ ] Verificar query de validación: 0 filas sin `tenant_id`
- [ ] Aplicar RLS de la Sección 3.2
- [ ] Test de aislamiento: crear segundo tenant de prueba, confirmar que no ve datos del primero
- [ ] Verificar que los módulos existentes (auth, dashboard, turnos) siguen funcionando con RLS activo
- [ ] Ajustar queries existentes que puedan fallar por RLS (agregar `.eq("tenant_id", tenant_id)` donde corresponda)
- [ ] Commit y deploy a Streamlit Cloud

**Entregable:** Login funcional para Santa Barba. Dashboard muestra datos reales. RLS activo y verificado sin regresiones.

---

### Semana 2 — Stripe Paywall

**Objetivo:** Checkout funcional. Webhook activa y desactiva acceso automáticamente.

- [ ] Crear producto "Pulsar v1.0 — Básico" en Stripe Dashboard (USD 19/mes)
- [ ] Implementar `src/billing/stripe_checkout.py`
- [ ] Implementar `enforce_paywall()` en `app.py`
- [ ] Deployar Edge Function `stripe-webhook` en Supabase
- [ ] Registrar webhook URL en Stripe Dashboard (todos los eventos requeridos)
- [ ] Test end-to-end con tarjeta de prueba Stripe (`4242 4242 4242 4242`)
- [ ] Verificar que `subscription_status` cambia a `active` en tabla `tenants`
- [ ] Test: suscripción cancelada → acceso bloqueado → pantalla upgrade
- [ ] Test: pago exitoso → acceso completo desbloqueado sin reiniciar app

**Entregable:** Flujo completo Demo → Checkout → Dashboard activo. Webhook verificado en producción.

---

### Semana 3 — Reporte mensual automático

**Objetivo:** PDF llega al email del dueño sin intervención manual.

- [ ] Crear bucket `monthly-reports` en Supabase Storage (public read con signed URLs)
- [ ] Implementar `src/reports/generate_pdf.py` con reportlab
- [ ] Deployar Edge Function `check-report-schedule`
- [ ] Deployar Edge Function `generate-monthly-report`
- [ ] Configurar `pg_cron` job diario a las 08:00 UTC
- [ ] Configurar cuenta Resend e implementar `src/reports/send_email.py`
- [ ] Test manual: trigger del reporte para Santa Barba (período actual)
- [ ] Verificar PDF en Storage y email recibido en inbox
- [ ] Implementar pantalla `04_Reportes.py` (historial con links de descarga)
- [ ] Permitir al dueño configurar `report_day` y `report_email` desde dashboard

**Entregable:** Reporte de Santa Barba generado, subido a Storage y enviado por email. Historial visible en dashboard.

---

### Semana 4 — Demo pública + primer cliente externo

**Objetivo:** Demo pública lista para mostrar. Un cliente real fuera de Santa Barba.

- [ ] Implementar DEMO_MODE completo con `demo_data.py`
- [ ] Ocultar valores reales en modo demo (mostrar `████` sobre métricas)
- [ ] CTA de upgrade claro y convincente en demo
- [ ] Implementar labels dinámicos por vertical (Sección 4.2)
- [ ] Test: crear veterinaria como segundo tenant → labels correctos en UI
- [ ] Documentar proceso de alta de nuevo tenant (< 15 minutos, sin deploy)
- [ ] Grabar demo de 2 minutos (Loom)
- [ ] README técnico completo en GitHub
- [ ] Contactar 3 negocios en Córdoba para demo presencial

**Entregable:** Demo pública online. Proceso de alta de nuevo tenant documentado y probado. Pipeline de ventas activo.

---

## SECCIÓN 10 — Checklist de venta

### Definition of Done — criterios de lanzamiento

```
INFRAESTRUCTURA
[ ] Santa Barba funciona como Tenant 001 con datos reales
[ ] RLS activo y verificado (0 cross-tenant data leaks)
[ ] Segundo tenant creado sin modificar código (solo INSERT en tenants)
[ ] Deploy estable en Streamlit Community Cloud

BILLING
[ ] Checkout Stripe funciona en producción (no solo test mode)
[ ] Webhook actualiza subscription_status en < 5 segundos
[ ] Suscripción cancelada bloquea acceso automáticamente
[ ] Pago exitoso desbloquea acceso sin reiniciar la app

REPORTE
[ ] PDF generado automáticamente el día configurado por el dueño
[ ] Email entregado al inbox sin intervención manual
[ ] PDF visible y descargable en historial del dashboard
[ ] Dueño puede cambiar día de envío y email destino desde el panel

DEMO
[ ] URL pública accesible sin login (datos sintéticos)
[ ] Valores reales ocultos (████) en modo demo
[ ] CTA de upgrade visible y funcional
[ ] Demo NO muestra datos reales de ningún tenant

MULTI-VERTICAL
[ ] Labels dinámicos funcionan según el vertical del tenant
[ ] Una barbería y una veterinaria usan el mismo código, distinto vocabulario
[ ] KPIs idénticos, semántica adaptada por vertical

NUEVO TENANT
[ ] Alta documentada: < 15 minutos para activar cliente nuevo
[ ] Sin deploys, sin migraciones manuales por cliente
[ ] Nuevo tenant recibe primer reporte al final del mes siguiente
[ ] Proceso repetible sin intervención del desarrollador

KPIs
[ ] Los 8 KPIs obligatorios visibles en dashboard full
[ ] Comparación vs mes anterior funcional con deltas
[ ] Horas pico con visualización de mapa de calor
[ ] Configuración de día de reporte y email desde el panel
```

### Argumento de venta ejecutivo (para dueño de negocio)

> "Pulsar te dice exactamente cuánto ganaste este mes, qué días tuviste más clientes y dónde perdiste plata. Y el primer día de cada mes, te manda un resumen de 1 página al email. Sin entrar al panel. Sin contratar a nadie. USD 19 por mes."

**Objeción más común:** "Ya tengo Reservo / Turnero / agenda de papel."  
**Respuesta:** "Perfecto. Esas herramientas te ayudan a tomar turnos. Pulsar te dice si esos turnos están siendo rentables."

---

## APÉNDICE — Configuración de Supabase Edge Functions

```bash
# Deployar Edge Functions (requiere Supabase CLI)
supabase functions deploy stripe-webhook
supabase functions deploy check-report-schedule
supabase functions deploy generate-monthly-report

# Configurar secrets de Edge Functions
supabase secrets set STRIPE_SECRET_KEY=sk_live_...
supabase secrets set STRIPE_WEBHOOK_SECRET=whsec_...
supabase secrets set RESEND_API_KEY=re_...

# Registrar webhook en Stripe Dashboard
# URL: https://[project-ref].supabase.co/functions/v1/stripe-webhook
# Eventos a escuchar:
#   - checkout.session.completed
#   - customer.subscription.deleted
#   - customer.subscription.paused
#   - invoice.payment_failed
```

---

## Estructura del proyecto (árbol de directorios)

*(No existe `01_Panel.py`; el entry point es `app.py` y la primera página es 02_Clientes.)*

```
Pulsar v1.0/
├── .gitignore
├── app.py
├── CHANGELOG.md
├── README.md
├── requirements.txt
├── agents/
│   ├── agents_README.md
│   ├── agents_requirements.txt
│   ├── agent_01_product_kpi.py
│   ├── agent_02_economic_analyst.py
│   ├── agent_03_saas_architect.py
│   ├── config.py
│   └── orchestrator.py
├── analytics/
│   ├── lifecycle.py
│   ├── profitability.py
│   ├── retention_metrics.py
│   ├── revenue_metrics.py
│   └── stock_rotation.py
├── assets/
│   ├── pulsar_192x192.png
│   ├── pulsar_32x32.png
│   └── pulsar_512x512.png
├── config/
│   ├── constants.py
│   ├── logging_config.py
│   └── settings.py
├── core/
│   ├── crud.py
│   ├── database.py
│   ├── models.py
│   ├── permisos.py
│   └── validators.py
├── data/
│   ├── price.md
│   ├── migrations/
│   └── seeds/
├── integrations/
│   ├── arca_client.py
│   ├── mercadopago_client.py
│   ├── README.md
│   └── stripe_client.py
├── pages/
│   ├── 02_Clientes.py
│   ├── 03_Servicios.py
│   ├── 04_Turnos.py
│   ├── 05_Facturacion.py
│   ├── 06_Analiticas.py
│   ├── 07_Insights.py
│   └── 08_Upgrade.py
├── services/
│   ├── export_services.py
│   ├── import_services.py
│   ├── notification_services.py
│   ├── payment_services.py
│   └── scheduler_service.py
├── tests/
└── UI/
    ├── graficas.py
    ├── KPI_cards.py
    ├── layout.py
    ├── sidebar.py
    └── tablas.py
```

---

*Pulsar v1.0 — BusinessOps Dashboard*
*Powered by Supabase + Stripe + Streamlit*
*Documento operativo único — No crear documentos paralelos*