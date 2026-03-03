# Auditoría Técnica Integral — Pulsar v1.0

> Rol: Arquitecto senior + Auditor de calidad + Consultor DevOps + Estratega SaaS  
> Alcance: Análisis basado en blueprint documentado, app.py y estructura declarada  
> Fecha: Febrero 2026

---

## BLOQUE 1 — ARQUITECTURA

### Diagnóstico General

La arquitectura modular declarada es **funcionalmente correcta** en su intención. La separación en capas `pages → UI → services → core → analytics` respeta el principio de dependencia unidireccional. Sin embargo, existen riesgos identificados en la implementación documentada:

#### Problemas detectados

**[ALTA] Lógica de negocio en `app.py`**  
El entry point actual resuelve tenant, carga datos del tenant, llama a `get_access_summary()` y renderiza contenido condicional. Esto mezcla orquestación de sesión con lógica de dominio. `app.py` debería ser un dispatcher puro: resolver tenant y delegar a páginas.

**[ALTA] `pages/` asume demasiado sobre el estado de sesión**  
El patrón de diseño actual requiere que cada página lea `st.session_state["tenant_id"]` directamente. No hay una capa de contexto formal (ej. `RequestContext` o similar). Si el orden de inicialización falla, las páginas fallan silenciosamente.

**[MEDIA] `core/crud.py` es un módulo monolítico de riesgo**  
Un solo archivo de CRUD para todas las entidades (`tenants`, `profiles`, `services`, `appointments`, `monthly_reports`) crecerá rápidamente. A partir de 500 líneas, la cohesión se rompe. No es crítico en v1.0, pero es deuda técnica planificada.

**[MEDIA] `analytics/` no tiene contrato formal con `services/`**  
Las funciones en `revenue_metrics.py`, `retention_metrics.py`, etc. son puras y testables, lo cual es correcto. El riesgo es que `services/scheduler_service.py` las llame directamente sin contrato tipado. Si un módulo de analytics cambia su firma, el scheduler falla en runtime sin detección temprana.

**[BAJA] `agents/` y `analytics/` pueden superponerse funcionalmente**  
El agente `agent_01_product_kpi.py` probablemente calcule KPIs que también existen en `analytics/revenue_metrics.py`. Riesgo de lógica duplicada con resultados divergentes.

**[BAJA] Ausencia de capa DTO entre `core/models.py` y `UI/`**  
La UI consume modelos Pydantic directamente. En fase de crecimiento, esto genera acoplamiento fuerte entre representación de datos y presentación.

### Refactors Priorizados

| Prioridad | Refactor | Impacto |
|-----------|----------|---------|
| ALTA | Extraer `TenantContext` como objeto de sesión inmutable | Elimina bugs de estado entre páginas |
| ALTA | Separar lógica de negocio de `app.py` hacia `services/` | Testabilidad y claridad de responsabilidades |
| MEDIA | Partir `core/crud.py` en `crud_tenants.py`, `crud_appointments.py`, etc. | Mantenibilidad a mediano plazo |
| MEDIA | Definir interfaces tipadas entre `analytics/` y `services/` | Detección temprana de regresiones |
| BAJA | Agregar capa DTO para UI (dataclasses simples, no Pydantic) | Desacoplar representación de modelo |

---

## BLOQUE 2 — CALIDAD DE CÓDIGO

### Cumplimiento PEP 8

`app.py` (la única implementación real disponible) cumple PEP 8 correctamente: importaciones organizadas, docstrings en funciones, uso de `_` para funciones privadas del módulo.

### Type Hints

`app.py` usa type hints consistentemente (`-> str`, `-> bool`, `-> None`). El patrón debe sostenerse en todos los módulos del blueprint.

**[ALTA] Riesgo en funciones que retornan datos de Supabase**  
Las respuestas de Supabase son `dict` no tipados. Sin TypedDicts o modelos Pydantic en la frontera de `core/database.py`, los errores de tipo son invisibles hasta runtime.

```python
# ❌ Riesgo actual (implícito en el diseño)
tenant = get_tenant(db, tenant_id)  # dict | None — sin garantía de estructura

# ✅ Correcto
from core.models import Tenant
tenant: Tenant | None = get_tenant(db, tenant_id)
```

### Logging

`app.py` usa `logging` estructurado con `extra={}` para campos adicionales. Esto es correcto. El riesgo está en que el `extra` se pase como dict libre sin validación de schema, lo que puede generar inconsistencias en los logs de producción.

**Recomendación:** Definir un `LogEvent` TypedDict con campos obligatorios (`tenant_id`, `event`, `timestamp`).

### Manejo de Excepciones

`app.py` captura `DatabaseError` correctamente. Pero el patrón `except DatabaseError as exc: st.error(...)` en el entry point expone detalles de infraestructura al usuario.

**[MEDIA]** La cadena de errores debería tener dos niveles:
- Interno: log con stack trace completo
- Usuario: mensaje sanitizado sin detalles técnicos

### Duplicación de Lógica

**[ALTA — CRÍTICO]** El blueprint documenta lógica de acceso en `core/permisos.py` y también lógica de paywall en `services/payment_services.py`. Si ambos módulos implementan la misma decisión de "¿tiene acceso este tenant?", cualquier divergencia crea un bug de seguridad.

**Regla requerida:** Una única función autoritativa `is_tenant_active(tenant_id) -> bool`. Todos los módulos la llaman. Nadie reimplementa la lógica.

---

## BLOQUE 3 — SEGURIDAD

### Matriz de Riesgos

| Riesgo | Severidad | Estado | Mitigación |
|--------|-----------|--------|------------|
| Credenciales en código | CRÍTICO | No detectado en código visto | `.env` + `st.secrets` — validar en CI |
| `service_role_key` expuesto al browser | CRÍTICO | Arquitectura correcta (solo en Edge Functions) | Auditar que nunca llegue a `pages/` |
| Webhook sin verificación de firma | CRÍTICO | Blueprint implementa verificación | Test obligatorio en staging |
| SQL Injection | ALTO | Supabase SDK previene queries directas | Validar que no se use `supabase.rpc()` con strings sin sanitizar |
| tenant_id manipulable vía query params | ALTO | `_resolve_tenant_id()` acepta tenant del URL | Agregar rate limiting + validación de slug |
| Datos de tenant demo expuestos | MEDIO | Pendiente implementación DEMO_MODE | Validar que datos reales nunca lleguen a demo |
| Stripe webhook sin idempotencia | MEDIO | Mencionado en blueprint | Implementar `processed_events` table |

### Análisis Crítico: `_resolve_tenant_id()`

```python
tenant_slug = query_params.get("tenant")
if tenant_slug:
    tenant = get_tenant_by_slug(db, tenant_slug)
```

**[CRÍTICO]** Un atacante puede probar slugs arbitrarios para enumerar tenants. El sistema no tiene:
- Rate limiting en resolución de slugs
- Logging de intentos fallidos con IP
- CAPTCHA o cualquier fricción

**Mitigación inmediata:** Log de cada resolución fallida con `WARNING` nivel. Agregar `st.stop()` después de N intentos en sesión.

### Tokens de Pago

El blueprint es correcto: `STRIPE_SECRET_KEY` solo en Edge Functions y backend, nunca en el frontend Streamlit. Sin embargo, `STRIPE_PUBLISHABLE_KEY` en `config/settings.py` debe marcarse explícitamente como "seguro para frontend".

### Validación de Inputs

`core/validators.py` existe pero no hay documentación de qué valida. **[ALTA]** Todo input que llegue de formularios Streamlit debe pasar por validators antes de llegar a CRUD. El patrón debe ser: `pages/ → validators → core/crud` sin bypass posible.

---

## BLOQUE 4 — BASE DE DATOS Y PERSISTENCIA

### Diseño de Modelos

El schema documentado en el blueprint es sólido. Los campos `tenant_id UUID NOT NULL REFERENCES tenants(id)` en todas las tablas es el patrón correcto.

**[ALTA] Falta columna `updated_at` con trigger automático en tablas secundarias**  
`tenants` tiene `updated_at` pero no está claro si `appointments` y `services` lo tienen. Sin `updated_at`, el sistema de reportes no puede detectar cambios incrementales.

**[MEDIA] `kpi_snapshot JSONB` en `monthly_reports` es una decisión correcta pero riesgosa**  
El snapshot JSONB es inmutable (bien), pero sin un schema JSON documentado, las consultas sobre el snapshot serán frágiles. Documentar el schema esperado como TypedDict en Python y como JSON Schema en el repo.

### Patrón CRUD

El patrón documentado (`tenant_id` como primer argumento posicional) es correcto y seguro. La función `assert_tenant()` como guard es la decisión de diseño más importante del sistema.

```python
# Patrón obligatorio — nunca omitir
def get_appointments(db, tenant_id: str, ...) -> list[dict]:
    assert_tenant(tenant_id)  # falla rápido, mensaje claro
    ...
```

**[ALTA]** Agregar `assert_tenant()` como decorador en lugar de llamada manual elimina el riesgo de olvidarlo:

```python
@require_tenant
def get_appointments(db, tenant_id: str, ...) -> list[dict]:
    ...
```

### Integridad

**[MEDIA]** El backfill de `tenant_id` en tablas existentes asume que todos los registros son de Santa Barba. Documentar que este paso es irreversible y debe ejecutarse en transacción con rollback disponible.

---

## BLOQUE 5 — SISTEMA MULTI-AGENTE

### Diagnóstico de Responsabilidades

| Agente | Responsabilidad declarada | Riesgo |
|--------|--------------------------|--------|
| `agent_01_product_kpi.py` | KPIs de producto | Posible solapamiento con `analytics/revenue_metrics.py` |
| `agent_02_economic_analyst.py` | Análisis económico | Dependencia implícita de `agent_01` no documentada |
| `agent_03_saas_architect.py` | Recomendaciones SaaS | Acoplamiento con estado del tenant no definido |
| `orchestrator.py` | Coordinación | Sin patrón de retry ni timeout declarado |

### Riesgos Arquitectónicos

**[ALTA] Acoplamiento circular potencial**  
Si `agent_02` necesita datos de `agent_01` y ambos comparten estado en `session_state`, existe riesgo de carrera de condiciones y resultados inconsistentes.

**[ALTA] Ausencia de contrato de salida entre agentes**  
El orchestrator necesita saber qué formato retorna cada agente. Sin TypedDicts o Pydantic models como contrato de salida, el orchestrator puede fallar silenciosamente si un agente cambia su estructura de respuesta.

**[MEDIA] Sin mecanismo de timeout**  
Llamadas a Anthropic API sin timeout en contexto Streamlit bloquean el thread completo. Streamlit no tiene async nativo; una llamada de 30s congela la UI.

### Patrón Recomendado: Mediator con Cola de Resultados

```python
# orchestrator.py — patrón recomendado
class AgentResult(TypedDict):
    agent_id: str
    status: Literal["success", "error", "timeout"]
    payload: dict
    duration_ms: int

class Orchestrator:
    def run_analysis(self, tenant_id: str, context: dict) -> list[AgentResult]:
        results = []
        for agent in self._agents:
            result = self._run_with_timeout(agent, tenant_id, context, timeout=20)
            results.append(result)
        return results
```

**Patrón recomendado:** Mediator. El orchestrator es el único punto de comunicación entre agentes. Los agentes no se llaman entre sí. Los resultados se acumulan en una estructura tipada.

### Logging del Sistema Multi-Agente

**[ALTA]** Cada ejecución de agente debe registrar:
- `agent_id`, `tenant_id`, `start_time`, `end_time`, `duration_ms`
- `tokens_used` (si aplica)
- `status` y `error` si falla

Sin esto, el sistema es una caja negra en producción.

---

## BLOQUE 6 — TESTING

### Estado Actual

La carpeta `tests/` existe pero está vacía según la estructura disponible. **[CRÍTICO]** Un sistema SaaS con billing y multi-tenant sin tests es un riesgo operacional real.

### Estrategia de Testing Recomendada

**Nivel 1 — Unitarios (prioridad inmediata)**

```
tests/
├── unit/
│   ├── test_permisos.py          # is_active(), get_access_summary()
│   ├── test_validators.py        # todos los inputs posibles
│   ├── test_revenue_metrics.py   # cálculos con fixtures
│   ├── test_retention_metrics.py
│   └── test_crud_guards.py       # assert_tenant() rechaza vacío/None
```

**Nivel 2 — Integración (semana 2)**

```
tests/
├── integration/
│   ├── test_stripe_webhook.py    # mock de payload Stripe
│   ├── test_tenant_isolation.py  # tenant A no ve datos de tenant B
│   └── test_report_generation.py # PDF se genera sin error
```

**Nivel 3 — E2E (pre-launch)**

```
tests/
└── e2e/
    └── test_checkout_flow.py     # con stripe-mock
```

### Tests Críticos Faltantes (por prioridad)

| Test | Riesgo si falta |
|------|-----------------|
| `assert_tenant()` rechaza `None` y `""` | Query sin tenant_id contamina todos los tenants |
| Webhook idempotente ante replay | Doble activación de suscripción |
| Demo mode bloquea exports | Usuario demo descarga datos de tenant real |
| RLS bloquea acceso cruzado | Fuga de datos entre tenants |

### Herramientas

- `pytest` + `pytest-cov` para unitarios
- `unittest.mock` para mocking de Supabase y Stripe
- `stripe-mock` para E2E de billing
- Coverage mínima aceptable: **80% en `core/` y `services/`**

---

## BLOQUE 7 — DEVOPS Y DEPLOY

### Estado de `requirements.txt`

El archivo es funcional pero tiene problemas:

**[ALTA]** Sin versiones pinneadas en producción. `streamlit>=1.35.0` puede instalar 1.40.0 con breaking changes.

```
# ❌ Actual
streamlit>=1.35.0

# ✅ Producción
streamlit==1.35.0
```

**Recomendación:** Generar `requirements-dev.txt` (con tools de testing) y `requirements.txt` (solo runtime, versiones fijas).

**[MEDIA]** `mercadopago` está comentado pero el módulo `integrations/mercadopago_client.py` existe. Si el módulo importa `mercadopago` sin el paquete instalado, falla en runtime aunque no se use.

### Separación por Entorno

**[ALTA]** No existe mecanismo de configuración por entorno documentado. El sistema necesita:

```
config/
├── settings.py          # base (actual)
├── settings_dev.py      # override development
├── settings_staging.py  # override staging
└── settings_prod.py     # override production
```

O bien, usar `pydantic-settings` con `model_config = SettingsConfigDict(env_file=".env")` y sobreescritura por variables de entorno (patrón 12-factor).

### Docker

No hay `Dockerfile`. Para Streamlit Community Cloud no es necesario, pero para Render/Railway sí.

```dockerfile
# Dockerfile básico recomendado
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8501
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

### CI/CD Recomendado

```yaml
# .github/workflows/ci.yml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install -r requirements.txt -r requirements-dev.txt
      - run: pytest tests/unit/ --cov=core --cov=services --cov-fail-under=80
      - run: python -m ruff check .
      - run: python -m mypy core/ services/ --strict
```

### Logs en Producción

El `setup_logging()` en `app.py` es correcto. Pero en Streamlit Community Cloud, los logs van a stdout solamente. En producción real (Render, Railway):

- Redirigir logs a un servicio externo (Papertrail, Logtail, Axiom)
- Usar formato JSON para consumo por log aggregators
- Configurar alertas en `ERROR` y `CRITICAL`

### Roadmap DevOps

| Semana | Acción |
|--------|--------|
| 1 | Pinnear versiones en requirements.txt, agregar requirements-dev.txt |
| 1 | Agregar `.github/workflows/ci.yml` con tests y linting |
| 2 | Configurar variables por entorno (dev/staging/prod) |
| 3 | Dockerfile para deploy alternativo a Render |
| 4 | Conectar logs a servicio externo (Logtail recomendado, tier free) |

---

## RESUMEN EJECUTIVO

| Bloque | Estado | Riesgo Crítico |
|--------|--------|----------------|
| Arquitectura | Sólida en intención, frágil en `app.py` | Mezcla de responsabilidades en entry point |
| Calidad de Código | Buenas prácticas en código visible | Duplicación potencial de lógica de acceso |
| Seguridad | Diseño correcto, ejecución sin validar | Enumeración de tenants por slug sin rate limit |
| Base de Datos | Schema correcto y defensivo | Backfill irreversible sin transacción documentada |
| Multi-Agente | Sin contratos tipados ni timeouts | Agentes pueden congelar la UI |
| Testing | Carpeta vacía | Sistema billing sin tests = riesgo operacional |
| DevOps | Básico funcional | Sin versiones fijas, sin CI |

**Próximo paso único recomendado:** Implementar `tests/unit/test_crud_guards.py` y `tests/unit/test_permisos.py` antes de ejecutar cualquier migración SQL en producción. Los tests validan los guards de seguridad que protegen la base de datos multi-tenant.
