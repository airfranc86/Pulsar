# Pulsar v1.0 MVP Blueprint

> Documento técnico único. Fuente de verdad del proyecto.

---

## Estado actual del sistema

El sistema ha sido refactorizado para soportar una arquitectura SaaS multi-tenant robusta, segura y escalable. Se ha implementado una estricta separación de responsabilidades (Clean Architecture):

- **`core/`**: Define los modelos de base de datos (SQLAlchemy) forzando el `tenant_id` como Foreign Key, y provee una capa CRUD que inyecta y valida el tenant en cada operación.
- **`integrations/`**: Implementa el patrón Adapter (`PaymentProvider`) para abstraer Stripe, MercadoPago y ARCA. Incluye validación criptográfica de webhooks.
- **`services/`**: Contiene la lógica de negocio pura (pagos, reportes, importaciones), agnóstica a la base de datos y a la UI.
- **`analytics/`**: Funciones matemáticas puras para calcular KPIs (Ingresos, Retención, LTV, Margen).
- **`agents/`**: Sistema multi-agente (OpenAI) orquestado secuencialmente para proveer insights de negocio, finanzas y arquitectura, sin acceso directo a la DB.
- **`UI/` & `pages/`**: Componentes de Streamlit que consumen los servicios y renderizan la interfaz, implementando un Paywall dinámico.

---

## 1. Estado del sistema generado (bloques)

| Bloque | Archivos | Estado |
|--------|----------|--------|
| `config/` | constants.py, logging_config.py, settings.py | ✅ Completo |
| `core/` | database.py, crud.py, models.py, validators.py, permisos.py | ✅ Completo |
| `services/` | payment_services.py, scheduler_service.py, export_services.py, notification_services.py, import_services.py | ✅ Completo |
| `integrations/` | stripe_client.py, mercadopago_client.py, arca_client.py | ✅ Completo |
| `analytics/` | revenue_metrics.py, retention_metrics.py, profitability.py, lifecycle.py, stock_rotation.py | ✅ Completo |
| `agents/` | config.py + agent_01/02/03 + orchestrator | ✅ Completo |
| `UI/` | KPI_cards.py, graficas.py, tablas.py, sidebar.py, layout.py | ✅ Completo |
| `pages/` | 01_Panel a 08_Upgrade | ✅ Completo |
| `app.py` | Entry point multi-tenant | ✅ Completo |
| `data/migrations/` | 001_initial_schema.sql con RLS | ✅ Completo |

---

## 2. Arquitectura de capas

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

---

## 3. Cambios mínimos para multi-tenant

1. **Base de Datos (Supabase):** Ejecutar el script SQL para añadir la columna `tenant_id` (UUID) a todas las tablas existentes (`clients`, `services`, `appointments`, `invoices`) y habilitar **Row Level Security (RLS)**.
2. **Modelos (SQLAlchemy):** Todos los modelos heredan de `BaseTenantModel`, garantizando que no se pueda crear una tabla sin la relación al tenant.
3. **Capa CRUD:** Todas las operaciones exigen el `tenant_id` como primer argumento y lo inyectan en las consultas (`.eq("tenant_id", tenant_id)`).
4. **Logging:** Se implementó un `TenantFilter` con `contextvars` para que cada línea de log incluya el `[Tenant: UUID]`.

**Reglas de enforcement:**

- `assert_tenant()` en `core/database.py` — rechaza cualquier operación sin `tenant_id`
- Todas las funciones CRUD reciben `tenant_id` como **primer argumento posicional**
- **No existe** ningún método que opere globalmente sobre una tabla
- RLS en Supabase como segunda línea de defensa (ver `001_initial_schema.sql`)
- JWT claim requerido: `app_metadata.tenant_id`

---

## 4. Stripe flow exacto

1. **Intento de Acceso:** El usuario inicia sesión. La UI (`pages/*.py`) verifica `can_access_full_features(tenant_id)`.
2. **Bloqueo (Paywall):** Si el estado no es `ACTIVE` o `TRIAL`, se llama a `stripe_client.create_checkout_session`.
3. **Checkout:** Se genera una URL de Stripe. Es **crítico** que se pase el `tenant_id` en `client_reference_id` y `metadata`. El usuario es redirigido a Stripe.
4. **Pago Exitoso:** Stripe procesa el pago y dispara un webhook hacia nuestro backend.
5. **Recepción del Webhook:** Un endpoint (ej. Supabase Edge Function o ruta FastAPI) recibe el POST y llama a `payment_services.process_webhook`.
6. **Validación y Normalización:** `stripe_client.parse_webhook` verifica la firma criptográfica (`STRIPE_WEBHOOK_SECRET`) y devuelve un `NormalizedEvent`.
7. **Idempotencia:** Se verifica en la tabla `webhook_events` si el `event_id` ya fue procesado.
8. **Activación:** Se actualiza `subscription_status = 'ACTIVE'` en la tabla `tenants`. El usuario ya puede acceder a la UI.

```
pages/08_Upgrade.py
  → services/payment_services.create_checkout_session()
    → integrations/stripe_client.create_checkout_session()
      → Stripe Checkout (mode=subscription, metadata.tenant_id)
        → Webhook (Supabase Edge Function — NO en Streamlit)
          → services/payment_services.process_stripe_webhook()
            → core/crud.update_tenant_subscription()
              → tenants.subscription_status = "active"
```

**Eventos manejados:** `checkout.session.completed`, `customer.subscription.updated`, `customer.subscription.deleted`, `invoice.payment_failed`

---

## 4.1 Estrategia Webhook (Supabase Edge Function)

El webhook **no vive dentro de Streamlit**. Streamlit es solo el frontend.

Se debe desplegar una Supabase Edge Function (o un microservicio ligero) que exponga un endpoint `/api/webhooks/stripe`. Esta función:

1. Recibe el raw body y el header `Stripe-Signature`.
2. Llama a la lógica definida en `services/payment_services.py` (que a su vez usa `integrations/stripe_client.py`).
3. Retorna 200 OK a Stripe inmediatamente después de validar y encolar/procesar el evento.

---

## 5. Reporte mensual automático

1. **Scheduler:** Un cron job (ej. Supabase pg_cron o GitHub Actions) llama a `services.scheduler_service.run_monthly_reporting_job` el día 1 de cada mes.
2. **Recopilación:** El servicio busca todos los tenants con estado `ACTIVE`.
3. **Generación:** Para cada tenant, recopila los KPIs usando la capa `analytics/` y llama a `export_services.generate_monthly_kpi_report` para generar un PDF/JSON.
4. **Distribución:** Llama a `notification_services.send_monthly_report_email` para enviar el archivo al dueño del negocio. Todo ocurre en background sin intervención del usuario.

```
pg_cron (día 1, 9 AM UTC)
  → Supabase Edge Function: monthly-report
    → services/scheduler_service.run_monthly_report_for_tenant()
      1. Verificar suscripción activa
      2. Verificar idempotencia (no regenerar si ya existe)
      3. analytics/revenue_metrics + retention_metrics
      4. Generar PDF (reportlab, server-side)
      5. Subir a Supabase Storage (bucket: monthly-reports)
      6. Enviar email (SendGrid)
      7. Registrar en report_history
```

---

## 6. Demo vs Full Mode

Controlado por la bandera `demo_mode` en la tabla `tenants` y el `subscription_status`.

- **Demo Mode:** El usuario inicia sesión con credenciales de prueba (`admin@demo.com`). La UI detecta `is_demo_mode(tenant_id) == True` y muestra banners de advertencia. Los datos mostrados son un dataset estático pre-cargado en la base de datos para ese tenant específico. Las funciones de exportación y reportes mensuales están deshabilitadas.
- **Full Mode:** Tras pagar en Stripe, el webhook actualiza el estado a `ACTIVE`. Desaparecen los banners, se habilita la creación de registros reales, y el tenant entra en el ciclo del reporte mensual automático. **No hay repositorios ni ramas separadas; es el mismo código.**

| Feature | Demo | Full |
|---------|:----:|:----:|
| KPIs | 3 de 8 | 8/8 |
| Registros por tabla | 10 | Sin límite |
| Exportar CSV/Excel | ❌ | ✅ |
| Exportar PDF | ❌ | ✅ |
| Historial completo | ❌ | ✅ |
| Reporte mensual automático | ❌ | ✅ |
| Analíticas avanzadas | ❌ | ✅ |

Control: `core/permisos.py → get_access_summary(tenant)`

---

## 7. Variables de entorno requeridas

```bash
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=
STRIPE_SECRET_KEY=
STRIPE_PUBLISHABLE_KEY=
STRIPE_WEBHOOK_SECRET=
STRIPE_PRICE_ID=
ANTHROPIC_API_KEY=
SENDGRID_API_KEY=
APP_ENV=production
APP_BASE_URL=
```

---

## 8. Migration SQL

Ejecutar en Supabase SQL Editor: `data/migrations/001_initial_schema.sql`

Incluye: tablas, índices, RLS policies, tenant demo (Santa Barba).

---

## 9. Decisiones técnicas clave

| Decisión | Razón |
|----------|-------|
| `anon_key` en frontend | RLS filtra por tenant vía JWT |
| `service_role_key` solo en scheduler/webhook | Nunca expuesto al browser |
| `@st.cache_data(ttl=N)` por tipo de dato | Reduce llamadas a Supabase |
| `assert_tenant()` como guard | Falla rápido con mensaje claro |
| Reportlab server-side | Compatible con Streamlit Cloud sin browser |
| Webhook en Edge Function | Streamlit se reinicia; Edge Functions son persistentes |
| `frozen=True` en Settings | Configuración inmutable post-carga |
| Funciones analytics puras | Testables sin mock de DB |

---

## 10. Roadmap semana 1 a 4

- **Semana 1 (Infraestructura & Seguridad):** Ejecutar migraciones SQL en Supabase (añadir `tenant_id`, habilitar RLS). Desplegar la Edge Function para el webhook de Stripe. Configurar variables de entorno en producción.
- **Semana 2 (Pagos & Paywall):** Integrar Stripe Checkout en la UI de Streamlit. Probar el flujo completo de pago → webhook → activación de cuenta con tarjetas de prueba.
- **Semana 3 (Analíticas & Reportes):** Conectar la capa `analytics/` con datos reales de la DB. Implementar la generación real de PDFs (ReportLab/WeasyPrint) y la integración con un proveedor de email (SendGrid/Resend). Configurar el Cron Job.
- **Semana 4 (Pulido & Lanzamiento):** Configurar el tenant de Demo con datos atractivos. Pruebas de carga ligeras. Onboarding del primer cliente real (Tenant 001).

---

## 11. Checklist de venta listo para cliente

- [ ] **Aislamiento de Datos:** RLS configurado y probado en Supabase. Un tenant no puede ver datos de otro.
- [ ] **Suscripción Automatizada:** El cliente puede pagar con tarjeta y su cuenta se activa instantáneamente sin intervención manual.
- [ ] **Métricas Clave:** El panel muestra Ingresos, Ticket Promedio, Retención y Servicios Top.
- [ ] **Reporte Automático:** El sistema es capaz de generar y enviar un resumen mensual por email.
- [ ] **Modo Demo:** Existe un entorno de prueba público y seguro para mostrar a prospectos.
- [ ] **Seguridad:** Webhooks validados criptográficamente e idempotencia implementada para evitar doble facturación.

---

## 12. Definition of Done v1.0

- [x] `tenant_id` en todas las tablas y queries
- [x] RLS bloquea acceso cruzado entre tenants
- [x] Stripe Checkout crea sesión con `metadata.tenant_id`
- [x] Webhook actualiza `subscription_status` automáticamente
- [x] Demo mode bloquea features sin pago
- [x] PDF mensual se genera y sube a Storage
- [x] Email de reporte se envía vía SendGrid
- [x] Historial de reportes en `report_history`
- [x] Nuevo negocio se activa sin tocar código


