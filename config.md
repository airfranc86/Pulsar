# config.md — Referencia Técnica de Configuración

> Pulsar v1.0 (release 1.3) · Documento técnico operativo  
> Audiencia: desarrolladores, DevOps, onboarding de nuevos tenants  
> Última actualización: Marzo 2026

---

## ⏱ Resumen de Tiempos por Sección (para presupuesto)

Esta tabla refleja el tiempo real de configuración e implementación por sección, asumiendo un desarrollador con experiencia media en el stack (Python, Supabase, Stripe). No incluye tiempo de desarrollo de features, solo setup, configuración y verificación.

| # | Sección | Tiempo estimado | Condición | Notas |
|---|---------|----------------|-----------|-------|
| 1 | Variables de entorno (todas las obligatorias) | **1–2 hs** | Primera vez | Incluye crear cuentas si no existen |
| 2 | Configuración por entorno (dev + staging + prod) | **2–3 hs** | Primera vez | Staging requiere proyecto Supabase separado |
| 3 | Logging estructurado + integración Logtail | **1–2 hs** | Primera vez | 30 min si solo stdout |
| 4 | Seguridad + validación de entorno | **1 hs** | Primera vez | Incluye test de la función `validate_environment()` |
| 5.1 | Stripe (checkout + webhook + test E2E) | **4–6 hs** | Primera vez | El webhook es la parte más costosa en tiempo |
| 5.2 | MercadoPago (si se activa) | **3–4 hs** | Opcional | Requiere cuenta verificada; el proceso puede tardar días |
| 5.3 | ARCA / AFIP (facturación electrónica) | **8–12 hs** | Opcional / por cliente | Cada tenant necesita certificado propio; burocracia AFIP incluida |
| 5.4 | Resend (email + dominio verificado) | **1–2 hs** | Primera vez | La verificación DNS puede tardar hasta 24 hs |
| 6 | Edge Functions + Supabase secrets | **1–2 hs** | Primera vez | Asume Supabase CLI ya instalado |
| 7 | Checklist pre-launch completo | **2–3 hs** | Por deploy | Incluye tests manuales de cada integración |

**Total estimado (primer setup completo, sin ARCA ni MercadoPago):** 13–21 horas de trabajo  
**Total estimado (con ARCA y MercadoPago):** 24–37 horas de trabajo

### Criterios usados para las estimaciones

Las estimaciones asumen:
- Cuenta Supabase, Stripe y Resend ya creadas (si no: sumar 1–2 hs adicionales)
- Desarrollador nunca configuró el proyecto antes (primera vez)
- Dominio propio disponible (si no hay dominio: agregar tiempo de compra/propagación DNS)
- No incluye tiempo de debugging ante errores imprevistos (sumar 20% como buffer)
- No incluye reuniones con el cliente para recopilar credenciales o accesos

### Escenarios de presupuesto

**Setup básico (variables + Stripe + Resend + deploy):** 8–12 hs  
**Setup completo con staging y monitoring:** 15–20 hs  
**Setup completo + ARCA para cliente B2B argentino:** 25–35 hs

> Para proyectos con cliente nuevo que no tiene cuentas creadas ni dominio, agregar entre 3 y 6 horas de gestión y espera de propagaciones DNS / verificaciones externas.

---

## 1. Variables de Entorno
> ⏱ **Tiempo estimado: 1–2 horas** (primera vez, incluyendo creación de cuentas si es necesario)

### Referencia Completa

| Variable | Tipo | Obligatoria | Descripción | Ejemplo |
|----------|------|-------------|-------------|---------|
| `SUPABASE_URL` | `str` | ✅ Sí | URL del proyecto Supabase | `https://xxxx.supabase.co` |
| `SUPABASE_ANON_KEY` | `str` | ✅ Sí | Clave pública anon (segura para frontend) | `eyJhbGci...` |
| `SUPABASE_SERVICE_ROLE_KEY` | `str` | ✅ Solo backend | Clave de servicio con acceso total. NUNCA en Streamlit. | `eyJhbGci...` |
| `STRIPE_SECRET_KEY` | `str` | ✅ Solo backend | Clave secreta de Stripe. NUNCA en frontend. | `sk_live_...` o `sk_test_...` |
| `STRIPE_PUBLISHABLE_KEY` | `str` | ✅ Sí | Clave pública Stripe (segura para frontend) | `pk_live_...` |
| `STRIPE_WEBHOOK_SECRET` | `str` | ✅ Solo Edge Function | Para verificar firma de webhooks | `whsec_...` |
| `STRIPE_PRICE_ID` | `str` | ✅ Sí | ID del precio de suscripción en Stripe | `price_1OBx...` |
| `ANTHROPIC_API_KEY` | `str` | ✅ Sí | API key de Anthropic para agentes | `sk-ant-...` |
| `SENDGRID_API_KEY` | `str` | ⚠️ Si usa SendGrid | API key para envío de emails | `SG.xxxx...` |
| `RESEND_API_KEY` | `str` | ⚠️ Si usa Resend | Alternativa recomendada a SendGrid | `re_xxxx...` |
| `MERCADOPAGO_ACCESS_TOKEN` | `str` | ❌ Opcional | Token de acceso MercadoPago (LATAM fallback) | `APP_USR-...` |
| `ARCA_API_KEY` | `str` | ❌ Opcional | API key ARCA (facturación AFIP) | `arca_...` |
| `APP_BASE_URL` | `str` | ✅ Sí | URL pública de la app (para redirects de Stripe) | `https://pulsar.streamlit.app` |
| `APP_ENV` | `str` | ✅ Sí | Entorno activo. Controla comportamiento de seguridad y logs. | `production` / `staging` / `development` |
| `LOG_LEVEL` | `str` | ❌ Opcional | Nivel de logging. Default: `INFO` en prod, `DEBUG` en dev. | `INFO` |
| `DEMO_TENANT_ID` | `str (UUID)` | ✅ Sí | UUID del tenant demo para usuarios no autenticados | `00000000-0000-0000-0000-000000000000` |

### Clasificación por Exposición

```
NUNCA exponer (solo Edge Functions / backend):
  SUPABASE_SERVICE_ROLE_KEY
  STRIPE_SECRET_KEY
  STRIPE_WEBHOOK_SECRET

Seguro en Streamlit (puede estar en secrets.toml):
  SUPABASE_URL
  SUPABASE_ANON_KEY          ← RLS protege los datos
  STRIPE_PUBLISHABLE_KEY
  STRIPE_PRICE_ID
  ANTHROPIC_API_KEY
  SENDGRID_API_KEY / RESEND_API_KEY
  APP_BASE_URL
  APP_ENV
  DEMO_TENANT_ID
```

---

## 2. Configuración por Entorno
> ⏱ **Tiempo estimado: 2–3 horas** (primera vez). El staging es lo más costoso porque requiere crear un proyecto Supabase separado y registrar un segundo webhook en Stripe con la URL de staging.

### 2.1 Development

```toml
# .streamlit/secrets.toml (desarrollo local)
# NUNCA commitear este archivo. Está en .gitignore.

SUPABASE_URL = "https://xxxx.supabase.co"
SUPABASE_ANON_KEY = "eyJ..."
STRIPE_SECRET_KEY = "sk_test_..."     # ← SIEMPRE test key en dev
STRIPE_PUBLISHABLE_KEY = "pk_test_..."
STRIPE_PRICE_ID = "price_test_..."   # Price de test en Stripe Dashboard
ANTHROPIC_API_KEY = "sk-ant-..."
RESEND_API_KEY = "re_test_..."
APP_BASE_URL = "http://localhost:8501"
APP_ENV = "development"
LOG_LEVEL = "DEBUG"
DEMO_TENANT_ID = "00000000-0000-0000-0000-000000000000"
```

**Comportamiento en `development`:**
- Logs en `DEBUG` (verbose, incluye stack traces)
- Stripe en modo test (tarjeta `4242 4242 4242 4242`)
- Sin rate limiting en resolución de tenants
- Errores de configuración muestran detalles técnicos completos
- `@st.cache_data` con TTL reducido (60s) para desarrollo rápido

### 2.2 Staging

```toml
# Variables de entorno en Streamlit Community Cloud (Settings → Secrets)
# O en Render → Environment Variables

SUPABASE_URL = "https://yyyy.supabase.co"   # ← Proyecto Supabase SEPARADO
SUPABASE_ANON_KEY = "eyJ..."
STRIPE_SECRET_KEY = "sk_test_..."           # ← Aún en test en staging
STRIPE_PUBLISHABLE_KEY = "pk_test_..."
STRIPE_PRICE_ID = "price_test_..."
ANTHROPIC_API_KEY = "sk-ant-..."
RESEND_API_KEY = "re_..."
APP_BASE_URL = "https://pulsar-staging.streamlit.app"
APP_ENV = "staging"
LOG_LEVEL = "INFO"
DEMO_TENANT_ID = "00000000-0000-0000-0000-000000000000"
```

**Comportamiento en `staging`:**
- Logs en `INFO` (sin stack traces en respuestas)
- Supabase **proyecto separado** del de producción (crítico: no testear sobre datos reales)
- Stripe en modo test con webhooks registrados en staging URL
- Errores muestran mensaje sanitizado al usuario
- Rate limiting activo en slug resolution (mock o real)
- Emails van a dirección de prueba interna, no al cliente

### 2.3 Production

```toml
# Variables de entorno en Streamlit Community Cloud
# Nunca en archivo, siempre en UI de Secrets

SUPABASE_URL = "https://zzzz.supabase.co"   # ← Proyecto de producción
SUPABASE_ANON_KEY = "eyJ..."
STRIPE_SECRET_KEY = "sk_live_..."           # ← LIVE key en producción
STRIPE_PUBLISHABLE_KEY = "pk_live_..."
STRIPE_PRICE_ID = "price_live_..."
ANTHROPIC_API_KEY = "sk-ant-..."
RESEND_API_KEY = "re_..."
APP_BASE_URL = "https://pulsar.streamlit.app"
APP_ENV = "production"
LOG_LEVEL = "INFO"
DEMO_TENANT_ID = "00000000-0000-0000-0000-000000000000"
```

**Comportamiento en `production`:**
- Logs en `INFO`, errores críticos en `ERROR` con alertas
- Stripe LIVE: cargos reales
- Rate limiting estricto en endpoints públicos
- Errores técnicos logueados internamente, mensaje genérico al usuario
- `@st.cache_data` con TTLs optimizados por tipo de dato:
  - KPIs del mes actual: `ttl=300` (5 min)
  - Lista de servicios: `ttl=3600` (1 hora)
  - Datos del tenant: `ttl=600` (10 min)
- CORS: solo dominios propios permitidos si se expone API

---

## 3. Logging
> ⏱ **Tiempo estimado: 1–2 horas**. 30 minutos si solo se configura stdout (Streamlit Community Cloud). 1–2 horas si se integra Logtail u otro agregador externo con alertas.

### Estructura de Log Recomendada

Todos los logs deben emitirse en formato JSON estructurado para consumo por log aggregators.

```python
# config/logging_config.py — estructura recomendada

import logging
import json
from datetime import datetime, timezone

class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
        }
        # Agregar campos extra si existen
        for key in ["tenant_id", "event", "duration_ms", "error"]:
            if hasattr(record, key):
                log_entry[key] = getattr(record, key)
        return json.dumps(log_entry)
```

### Nivel por Entorno

| Entorno | Nivel raíz | `core/` | `agents/` | `services/` |
|---------|-----------|---------|-----------|-------------|
| development | `DEBUG` | `DEBUG` | `DEBUG` | `DEBUG` |
| staging | `INFO` | `INFO` | `INFO` | `INFO` |
| production | `INFO` | `WARNING` | `INFO` | `INFO` |

### Rotación de Logs

En Streamlit Community Cloud los logs son efímeros (stdout). Para producción real:

**Opción A — Logtail (recomendado, free tier disponible):**
```python
# pip install logtail-python
from logtail import LogtailHandler
handler = LogtailHandler(source_token=LOGTAIL_TOKEN)
logging.getLogger().addHandler(handler)
```

**Opción B — Archivo con rotación (solo para deploys propios):**
```python
from logging.handlers import RotatingFileHandler
handler = RotatingFileHandler(
    "logs/pulsar.log",
    maxBytes=10_000_000,  # 10MB
    backupCount=5
)
```

### Campos Obligatorios por Evento

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `timestamp` | ISO 8601 | Momento del evento en UTC |
| `level` | str | INFO / WARNING / ERROR / CRITICAL |
| `event` | str | Identificador semántico del evento (ej. `tenant_resolved`) |
| `tenant_id` | UUID str | Siempre que aplique. Nunca omitir. |
| `duration_ms` | int | En operaciones con latencia medible |
| `error` | str | Mensaje de error sanitizado si level=ERROR |

### Eventos de Negocio a Loguear (obligatorios)

```python
# Ejemplos de eventos de negocio críticos
logger.info("tenant_resolved_from_slug", extra={"tenant_id": tid, "slug": slug})
logger.warning("tenant_slug_not_found", extra={"slug": slug})
logger.info("stripe_checkout_created", extra={"tenant_id": tid})
logger.info("stripe_webhook_received", extra={"event_type": event.type})
logger.info("subscription_activated", extra={"tenant_id": tid})
logger.warning("subscription_payment_failed", extra={"tenant_id": tid})
logger.info("monthly_report_generated", extra={"tenant_id": tid, "period": period, "duration_ms": ms})
logger.error("report_generation_failed", extra={"tenant_id": tid, "error": str(exc)})
logger.info("agent_analysis_completed", extra={"tenant_id": tid, "agent_id": "agent_01", "duration_ms": ms})
```

---

## 4. Seguridad
> ⏱ **Tiempo estimado: 1 hora**. Implementar `validate_environment()`, verificar `.gitignore`, revisar que ninguna key de nivel 2 esté accesible desde Streamlit, y documentar el proceso de rotación para el equipo.

### Gestión de Secretos

**Regla absoluta:** Ninguna credencial en el código fuente. Sin excepciones.

```python
# ❌ NUNCA hacer esto
STRIPE_KEY = "sk_live_xxxx"

# ✅ Siempre así
import streamlit as st
stripe_key = st.secrets["STRIPE_SECRET_KEY"]

# O con pydantic-settings
from pydantic_settings import BaseSettings
class Settings(BaseSettings):
    stripe_secret_key: str
    model_config = SettingsConfigDict(env_file=".env", frozen=True)
```

### Separación por Nivel de Confianza

```
Nivel 0 — Público (sin autenticación):
  SUPABASE_URL, SUPABASE_ANON_KEY, STRIPE_PUBLISHABLE_KEY
  → RLS en Supabase protege los datos. El anon_key solo otorga acceso
    a lo que RLS permite.

Nivel 1 — Streamlit (servidor, no browser):
  ANTHROPIC_API_KEY, RESEND_API_KEY, STRIPE_PRICE_ID
  → Nunca llegan al browser. Están en st.secrets en el servidor.

Nivel 2 — Backend/Edge Functions únicamente:
  SUPABASE_SERVICE_ROLE_KEY, STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET
  → CRÍTICO: Si alguna de estas variables aparece en app.py o pages/,
    es un bug de seguridad. Auditarlas en cada code review.
```

### Protección de Credenciales

**En repositorio:**
- `.gitignore` incluye `.env`, `.env.*`, `.streamlit/secrets.toml`
- Nunca commitear archivos de secrets, ni siquiera vacíos con placeholders de valores reales
- Usar `.streamlit/secrets.toml.example` con valores ficticios como referencia

**Rotación de credenciales:**
- `STRIPE_SECRET_KEY`: rotar si hay sospecha de exposición (Stripe revoca instantáneamente)
- `SUPABASE_SERVICE_ROLE_KEY`: rotar trimestralmente en producción
- `ANTHROPIC_API_KEY`: monitorear uso en el dashboard de Anthropic, alertar ante spike anómalo

**Auditoría de acceso:**
- Log de cada operación que use `service_role_key`
- Log de cada llamada a Stripe con tenant_id
- Revisar logs semanalmente en etapa de lanzamiento

### Buenas Prácticas Adicionales

```python
# Validar que APP_ENV esté configurado correctamente al inicio
def validate_environment():
    env = settings.APP_ENV
    if env not in ("development", "staging", "production"):
        raise ValueError(f"APP_ENV inválido: {env}")
    if env == "production" and "sk_test_" in settings.STRIPE_SECRET_KEY:
        raise ValueError("CRÍTICO: Usando Stripe test key en producción")
    if env == "production" and settings.LOG_LEVEL == "DEBUG":
        logger.warning("LOG_LEVEL=DEBUG en producción puede exponer datos sensibles")
```

---

## 5. Integraciones

### 5.1 Stripe
> ⏱ **Tiempo estimado: 4–6 horas** (primera vez). Desglose: crear producto y precio en Dashboard (30 min), implementar checkout (1 hs), implementar y deployar Edge Function webhook (1.5 hs), registrar webhook en Stripe con eventos correctos (30 min), test E2E completo con tarjeta de prueba + cancelación (1–2 hs). El webhook es el paso más propenso a errores de configuración.

**Configuración mínima:**

```python
# integrations/stripe_client.py
import stripe
from config.settings import settings

stripe.api_key = settings.STRIPE_SECRET_KEY
stripe.api_version = "2023-10-16"  # Pinnear versión de API
stripe.max_network_retries = 3     # Retry automático en errores de red
```

**Timeouts:**

| Operación | Timeout recomendado | Comportamiento ante timeout |
|-----------|--------------------|-----------------------------|
| `checkout.Session.create()` | 10s | Mostrar error al usuario, log WARNING |
| `subscriptions.retrieve()` | 10s | Usar datos cacheados si disponibles |
| Webhook processing | 30s (límite de Stripe) | Responder 200 inmediatamente, procesar async |

**Idempotencia:**
```python
# Para operaciones críticas, usar idempotency_key
session = stripe.checkout.Session.create(
    ...,
    idempotency_key=f"checkout_{tenant_id}_{int(time.time() // 3600)}"
    # Mismo key por hora → mismo resultado si Stripe recibe request duplicado
)
```

**Webhooks — Eventos a registrar en Stripe Dashboard:**
```
checkout.session.completed
customer.subscription.updated
customer.subscription.deleted
customer.subscription.paused
invoice.payment_failed
invoice.payment_succeeded
```

**Verificación obligatoria de firma:**
```python
# integrations/stripe_client.py
def verify_webhook(payload: bytes, sig_header: str) -> stripe.Event:
    try:
        return stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except stripe.error.SignatureVerificationError as e:
        logger.error("stripe_webhook_signature_failed", extra={"error": str(e)})
        raise  # Retornar HTTP 400 desde el handler
```

### 5.2 MercadoPago
> ⏱ **Tiempo estimado: 3–4 horas de implementación** + hasta 3–5 días hábiles de espera si la cuenta del cliente no está verificada. MercadoPago requiere verificación de identidad del titular antes de habilitar pagos reales. Presupuestar este tiempo de espera explícitamente al cliente.

**Estado:** Integración disponible como fallback LATAM. Activar solo cuando Stripe no esté disponible en el mercado del cliente.

```python
# integrations/mercadopago_client.py
import mercadopago
from config.settings import settings

sdk = mercadopago.SDK(settings.MERCADOPAGO_ACCESS_TOKEN)

def create_preference(tenant_id: str, email: str) -> str:
    preference_data = {
        "items": [{"title": "Pulsar v1.0", "quantity": 1, "unit_price": 19.0}],
        "payer": {"email": email},
        "external_reference": tenant_id,  # ← Equivalente a client_reference_id de Stripe
        "back_urls": {
            "success": f"{settings.APP_BASE_URL}?activated=true",
            "failure": f"{settings.APP_BASE_URL}?cancelled=true",
        },
        "auto_return": "approved",
    }
    result = sdk.preference().create(preference_data)
    return result["response"]["init_point"]
```

**Timeout:** 15s en MercadoPago (API más lenta que Stripe). Implementar retry con backoff exponencial.

**Idempotencia MercadoPago:** Usar `external_reference` como identificador único. Verificar en webhook que no se procese dos veces el mismo `external_reference`.

### 5.3 ARCA (AFIP — Facturación Electrónica)
> ⏱ **Tiempo estimado: 8–12 horas de implementación** + 2–5 días hábiles de gestión burocrática por tenant. Cada cliente necesita obtener su propio certificado digital ante AFIP, lo cual no depende del desarrollador pero sí bloquea el avance. Facturar este módulo como ítem separado en el presupuesto: no incluirlo en el precio base del setup.

**Estado:** Opcional. Para clientes que requieren factura electrónica en Argentina.

```python
# integrations/arca_client.py
# ARCA es la plataforma unificada de AFIP para facturación electrónica
# Requiere certificado digital del contribuyente

class ARCAClient:
    BASE_URL = "https://serviciosjava.afip.gov.ar"
    TIMEOUT = 30  # AFIP puede ser lento

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers["Authorization"] = f"Bearer {api_key}"

    def emitir_factura(self, tenant_id: str, monto: float, concepto: str) -> dict:
        # Implementación según spec ARCA
        ...
```

**Nota:** ARCA requiere un certificado digital por CUIT del contribuyente. No es una API genérica; cada tenant debe obtener su propio certificado. El setup por tenant toma 2–5 días hábiles.

### 5.4 Resend (Email)
> ⏱ **Tiempo estimado: 1–2 horas**. La implementación en sí toma 30–45 minutos. El tiempo variable es la verificación del dominio: las entradas DNS pueden tardar entre 15 minutos y 24 horas en propagarse. Iniciar este paso primero para que no bloquee el resto del setup.

**Configuración:**
```python
# services/notification_services.py
import resend
from config.settings import settings

resend.api_key = settings.RESEND_API_KEY

def send_monthly_report(to: str, tenant_name: str, period: str, pdf_url: str):
    params = {
        "from": "reportes@pulsar.app",   # ← Dominio verificado en Resend
        "to": [to],
        "subject": f"Tu reporte mensual Pulsar — {period}",
        "html": _build_report_email_html(tenant_name, period, pdf_url),
    }
    response = resend.Emails.send(params)
    logger.info("report_email_sent", extra={"to": to, "email_id": response["id"]})
    return response
```

**Timeouts:** 10s. Si falla, registrar en `monthly_reports.status = 'email_failed'` y reintentar en la próxima ejecución del cron.

**Dominio:** Registrar y verificar `pulsar.app` (o dominio propio) en Resend antes del lanzamiento. Sin dominio verificado, emails caen en spam.

---

## 6. Supabase Edge Functions — Variables de Entorno
> ⏱ **Tiempo estimado: 1–2 horas**. Incluye instalar Supabase CLI si no está instalado (15 min), configurar los secrets via CLI (15 min), deployar las funciones y verificar que responden correctamente (30–60 min). Si el CLI ya está configurado y las funciones están escritas, el tiempo baja a 30–45 minutos.

Las Edge Functions tienen acceso automático a:
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY` ← Disponible automáticamente, sin configuración adicional
- `SUPABASE_ANON_KEY`

Variables adicionales a configurar manualmente:
```bash
# Via Supabase CLI
supabase secrets set STRIPE_SECRET_KEY=sk_live_...
supabase secrets set STRIPE_WEBHOOK_SECRET=whsec_...
supabase secrets set RESEND_API_KEY=re_...

# Verificar configuración
supabase secrets list
```

---

## 7. Checklist Pre-Launch
> ⏱ **Tiempo estimado: 2–3 horas por deploy a producción**. No es un paso que se hace una vez: cada vez que se hace un deploy a producción se debe recorrer el checklist completo. Incluye tests manuales de cada integración, verificación de logs en vivo y confirmación de que el webhook de Stripe está activo y recibiendo eventos.

```
DESARROLLO
[ ] .env en .gitignore verificado (git status --short | grep .env debe estar vacío)
[ ] requirements.txt con versiones pinneadas (no >=, usar ==)
[ ] APP_ENV=production en secrets de Streamlit Cloud
[ ] Stripe keys: sk_live_ en producción, sk_test_ en staging

BASE DE DATOS
[ ] SUPABASE_SERVICE_ROLE_KEY NUNCA en código Streamlit
[ ] RLS habilitado y verificado en todas las tablas
[ ] pg_cron configurado y testeado manualmente

PAGOS
[ ] Webhook registrado en Stripe Dashboard con URL de producción
[ ] Todos los eventos necesarios suscriptos en el webhook
[ ] Test con tarjeta 4242 4242 4242 4242 en staging completado
[ ] Test de cancelación de suscripción verificado

EMAIL
[ ] Dominio verificado en Resend
[ ] Email de prueba enviado y recibido sin ir a spam
[ ] Reply-to configurado a dirección de soporte real

MONITORING
[ ] Log aggregator configurado (Logtail o equivalente)
[ ] Alertas en ERROR/CRITICAL configuradas
[ ] Dashboard de Anthropic monitoreado para consumo de tokens
[ ] Dashboard de Stripe revisado para pagos fallidos
```

---

*Pulsar — config.md · Documento técnico operativo*  
*No crear documentos paralelos de configuración*
