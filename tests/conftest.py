"""
tests/unit/conftest.py
======================
Fixtures compartidas para todos los tests unitarios de Pulsar v1.0.

Convenciones:
  - Fixtures de tenant usan UUIDs reales válidos
  - Los nombres de fixture indican el estado: tenant_active, tenant_demo, etc.
  - Ninguna fixture hace llamadas reales a Supabase o Stripe
"""

import pytest


# ── UUIDs de fixtures ─────────────────────────────────────────────────────────

TENANT_UUID_A = "550e8400-e29b-41d4-a716-446655440001"
TENANT_UUID_B = "550e8400-e29b-41d4-a716-446655440002"
TENANT_UUID_DEMO = "00000000-0000-0000-0000-000000000001"

# UUIDs malformados para tests negativos
INVALID_UUID_NO_DASHES = "550e8400e29b41d4a716446655440001"
INVALID_UUID_SHORT = "550e8400-e29b-41d4"
INVALID_UUID_EXTRA = "550e8400-e29b-41d4-a716-446655440001-extra"
INVALID_UUID_SPACES = "  550e8400-e29b-41d4-a716-446655440001  "  # solo espacios


# ── Fixtures de tenant base ───────────────────────────────────────────────────

@pytest.fixture
def tenant_active() -> dict:
    """Tenant con suscripción activa. Acceso completo a todas las features."""
    return {
        "id": TENANT_UUID_A,
        "slug": "santa-barba",
        "name": "Santa Barba",
        "vertical": "barberia",
        "email": "admin@santabarba.com",
        "subscription_status": "active",
        "plan": "active",
        "stripe_customer_id": "cus_test_001",
        "stripe_subscription_id": "sub_test_001",
    }


@pytest.fixture
def tenant_inactive() -> dict:
    """Tenant con suscripción inactiva (recién creado, nunca pagó)."""
    return {
        "id": TENANT_UUID_B,
        "slug": "nueva-peluqueria",
        "name": "Nueva Peluquería",
        "vertical": "barberia",
        "email": "admin@nuevapeluqueria.com",
        "subscription_status": "inactive",
        "plan": "demo",
        "stripe_customer_id": None,
        "stripe_subscription_id": None,
    }


@pytest.fixture
def tenant_past_due() -> dict:
    """Tenant con pago fallido. Tratado como demo hasta que regularice."""
    return {
        "id": TENANT_UUID_A,
        "slug": "taller-gomez",
        "name": "Taller Gómez",
        "vertical": "taller",
        "email": "admin@tallergomez.com",
        "subscription_status": "past_due",
        "plan": "active",
        "stripe_customer_id": "cus_test_002",
        "stripe_subscription_id": "sub_test_002",
    }


@pytest.fixture
def tenant_cancelled() -> dict:
    """Tenant que canceló su suscripción."""
    return {
        "id": TENANT_UUID_A,
        "slug": "vet-norte",
        "name": "Veterinaria Norte",
        "vertical": "veterinaria",
        "email": "admin@vetnorte.com",
        "subscription_status": "cancelled",
        "plan": "demo",
        "stripe_customer_id": "cus_test_003",
        "stripe_subscription_id": None,
    }


@pytest.fixture
def tenant_demo() -> dict:
    """Tenant demo público. Sin datos reales."""
    return {
        "id": TENANT_UUID_DEMO,
        "slug": "demo",
        "name": "Demo",
        "vertical": "pyme_servicios",
        "email": "demo@pulsar.app",
        "subscription_status": "demo",
        "plan": "demo",
        "stripe_customer_id": None,
        "stripe_subscription_id": None,
    }


# ── Fixture de todos los estados inactivos (para parametrización) ─────────────

@pytest.fixture(params=["inactive", "past_due", "cancelled", "demo"])
def tenant_any_inactive(request) -> dict:
    """
    Fixture parametrizada: itera sobre todos los estados que resultan en demo_mode=True.
    Usar en tests que deben pasar para CUALQUIER estado inactivo.
    """
    return {
        "id": TENANT_UUID_B,
        "slug": "tenant-test",
        "name": "Tenant Test",
        "vertical": "pyme_servicios",
        "email": "test@test.com",
        "subscription_status": request.param,
        "plan": "demo",
    }
