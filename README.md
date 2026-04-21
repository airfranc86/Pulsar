# Pulsar v1.0 — MVP Blueprint
**BusinessOps Dashboard · SaaS Multi-Vertical**
*Documento operativo único · No crear documentos paralelos*

Fecha: 19-02-2026

---

## SECCIÓN 1 — Estado actual del sistema

### 1.1 Lo que ya existe y funciona

El sistema actual tiene:

- Supabase en producción con tablas
- Streamlit UI con páginas de dashboard, turnos, servicios, configuración
- Autenticación
- Agentes de análisis
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

---

## SECCIÓN 5 — Demo vs Full Mode

### 5.1 Un solo repositorio, un solo sistema

El modo se controla exclusivamente por `subscription_status` del tenant autenticado. No hay rama demo separada. No hay código duplicado.

### 5.2 DEMO_MODE — comportamiento

| Feature | DEMO_MODE | FULL_MODE |
|---|---|---|
| KPIs visibles | Sí, pero valores ocultos (`████`) | Sí, valores reales |
| Datos | Sintéticos (dataset hardcodeado) | Reales del tenant |
| Exportar PDF | ❌ Bloqueado | ✅ Disponible |
| Historial reportes | ❌ Bloqueado | ✅ Disponible |
| Configurar día de reporte | ❌ Bloqueado | ✅ Disponible |
| Horas pico | Visible parcial | Completo |
| CTA de upgrade | ✅ Siempre visible | ❌ Oculto |

---

*Pulsar v1.0 — BusinessOps Dashboard*
*Powered by Supabase + Stripe + Streamlit*
*Documento operativo único — No crear documentos paralelos*
