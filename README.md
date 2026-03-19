# Pulsar v1.0 — MVP Blueprint
**BusinessOps Dashboard · SaaS Multi-Vertical**
*Documento operativo único · No crear documentos paralelos*

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

## SECCIÓN 5 — Reporte mensual automático

### 5.1 Arquitectura del flujo automático

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

### 5.2 Generación del PDF (Python worker alternativo)

Si la generación de PDF se realiza en Python (más simple que en Deno), la Edge Function `generate-monthly-report` puede llamar a un endpoint de Streamlit en modo script o a un worker Python en Render mínimo. Sin embargo, **para mantener la arquitectura dentro del stack existente**, la opción recomendada es:

1. La Edge Function consulta los KPIs y guarda el snapshot en JSONB en `monthly_reports`
2. Un script Python (`src/reports/generate_pdf.py`) se ejecuta vía GitHub Actions (cron mensual) o como Streamlit script batch
3. El PDF se genera con `reportlab` y se sube a Supabase Storage

---

## SECCIÓN 6 — Demo vs Full Mode

### 6.1 Un solo repositorio, un solo sistema

El modo se controla exclusivamente por `subscription_status` del tenant autenticado. No hay rama demo separada. No hay código duplicado.

### 6.2 DEMO_MODE — comportamiento

| Feature | DEMO_MODE | FULL_MODE |
|---|---|---|
| KPIs visibles | Sí, pero valores ocultos (`████`) | Sí, valores reales |
| Datos | Sintéticos (dataset hardcodeado) | Reales del tenant |
| Exportar PDF | ❌ Bloqueado | ✅ Disponible |
| Historial reportes | ❌ Bloqueado | ✅ Disponible |
| Configurar día de reporte | ❌ Bloqueado | ✅ Disponible |
| Horas pico | Visible parcial | Completo |
| CTA de upgrade | ✅ Siempre visible | ❌ Oculto |

### 6.3 Dataset sintético para demo pública

---

## SECCIÓN 7 — Roadmap semana 1 a 4

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

## SECCIÓN 8 — Checklist de venta

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
