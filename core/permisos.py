"""
core/permisos.py
================
Control de acceso basado en suscripción del tenant.

Fuente de verdad única para decidir qué features están disponibles.
NINGÚN otro módulo reimplementa esta lógica. Todos llaman a get_access_summary().

Tabla Demo vs Full (del blueprint):

Feature               | Demo | Full
----------------------|:----:|:----:
KPIs visibles         |  3   |  8
Registros por tabla   |  10  | sin límite
Exportar CSV/Excel    |  ❌  |  ✅
Exportar PDF          |  ❌  |  ✅
Historial completo    |  ❌  |  ✅
Reporte mensual auto  |  ❌  |  ✅
Analíticas avanzadas  |  ❌  |  ✅
"""

from __future__ import annotations

import logging
from typing import TypedDict

logger = logging.getLogger(__name__)

# ── Constantes de suscripción ─────────────────────────────────────────────────

ACTIVE_STATUSES: frozenset[str] = frozenset({"active"})
INACTIVE_STATUSES: frozenset[str] = frozenset({"inactive", "past_due", "cancelled", "demo"})

# Límites en modo demo
DEMO_MAX_KPI_VISIBLE: int = 3
DEMO_MAX_RECORDS: int = 10
FULL_MAX_KPI_VISIBLE: int = 8


# ── Tipo de retorno formal ────────────────────────────────────────────────────

class AccessSummary(TypedDict):
    """
    Resumen de acceso para un tenant. Estructura inmutable de decisiones de permisos.
    Todos los módulos que necesiten verificar acceso deben usar este dict.
    """
    demo_mode: bool
    subscription_active: bool
    subscription_status: str

    # Features específicas
    can_export_csv: bool
    can_export_pdf: bool
    can_view_full_history: bool
    can_receive_monthly_report: bool
    can_access_advanced_analytics: bool

    # Límites cuantitativos
    max_kpis_visible: int
    max_records_per_table: int


# ── Helpers ───────────────────────────────────────────────────────────────────

def is_subscription_active(tenant: dict) -> bool:
    """
    Indica si el tenant tiene suscripción activa (acceso completo).
    Usar desde pages que necesiten solo este booleano (ej. 08_Upgrade).
    """
    if not tenant or not isinstance(tenant, dict):
        return False
    status: str = tenant.get("subscription_status", "inactive")
    return status in ACTIVE_STATUSES


def get_demo_tenant_fallback(tenant_id: str) -> dict:
    """
    Devuelve un dict de tenant de ejemplo para uso cuando get_tenant() falla
    (sin conexión a Supabase o tenant inexistente). Permite desarrollar sin backend.

    No realiza llamadas a BD. Usar en app.py, 01_Panel y 08_Upgrade cuando tenant sea None/vacío.
    """
    from config.constants import DEMO_TENANT_ID, DEMO_TENANT_NAME
    return {
        "id": tenant_id,
        "name": DEMO_TENANT_NAME,
        "vertical": "pyme_servicios",
        "subscription_status": "inactive",
    }


# ── Función principal ─────────────────────────────────────────────────────────

def get_access_summary(tenant: dict) -> AccessSummary:
    """
    Calcula el resumen de acceso para un tenant dado su estado de suscripción.

    Esta es la ÚNICA función autorizada para tomar decisiones de acceso.
    No cachear su resultado más allá del request actual: el estado de
    suscripción puede cambiar vía webhook de Stripe en cualquier momento.

    Args:
        tenant: dict con al menos las claves 'id' y 'subscription_status'.
                Típicamente retornado por core/crud.get_tenant().

    Returns:
        AccessSummary con todas las decisiones de acceso ya tomadas.

    Raises:
        ValueError: Si tenant es None o no contiene 'subscription_status'.

    Examples:
        >>> tenant = {"id": "uuid...", "subscription_status": "active"}
        >>> summary = get_access_summary(tenant)
        >>> summary["demo_mode"]
        False
        >>> summary["can_export_csv"]
        True

        >>> tenant = {"id": "uuid...", "subscription_status": "inactive"}
        >>> summary = get_access_summary(tenant)
        >>> summary["demo_mode"]
        True
        >>> summary["max_kpis_visible"]
        3
    """
    if tenant is None:
        raise ValueError(
            "get_access_summary() recibió tenant=None. "
            "El tenant debe cargarse antes de verificar permisos."
        )

    if not isinstance(tenant, dict):
        raise ValueError(
            f"get_access_summary() esperaba dict, recibió {type(tenant).__name__!r}"
        )

    # Si falta subscription_status (ej. get_tenant falló por red y se pasó {}), tratar como inactivo
    status: str = tenant.get("subscription_status", "inactive")
    if not status:
        status = "inactive"
    is_active: bool = status in ACTIVE_STATUSES

    summary: AccessSummary = {
        "demo_mode": not is_active,
        "subscription_active": is_active,
        "subscription_status": status,

        # Features — todas bloqueadas en demo
        "can_export_csv": is_active,
        "can_export_pdf": is_active,
        "can_view_full_history": is_active,
        "can_receive_monthly_report": is_active,
        "can_access_advanced_analytics": is_active,

        # Límites cuantitativos
        "max_kpis_visible": FULL_MAX_KPI_VISIBLE if is_active else DEMO_MAX_KPI_VISIBLE,
        "max_records_per_table": _NO_LIMIT_SENTINEL if is_active else DEMO_MAX_RECORDS,
    }

    logger.debug(
        "access_summary_computed",
        extra={
            "tenant_id": tenant.get("id", "unknown"),
            "subscription_status": status,
            "demo_mode": summary["demo_mode"],
        },
    )
    return summary


def require_full_access(summary: AccessSummary, feature: str) -> None:
    """
    Lanza PermissionError si el tenant está en modo demo para el feature solicitado.

    Usar en services/ antes de ejecutar operaciones premium.

    Args:
        summary: Resultado de get_access_summary().
        feature: Nombre del feature para el mensaje de error.

    Raises:
        PermissionError: Si demo_mode es True.

    Example:
        >>> summary = get_access_summary(tenant)
        >>> require_full_access(summary, "exportar CSV")
        # Si demo: lanza PermissionError
        # Si full: no hace nada
    """
    if summary["demo_mode"]:
        raise PermissionError(
            f"El feature '{feature}' requiere suscripción activa. "
            f"Estado actual: {summary['subscription_status']!r}. "
            f"Activar la cuenta desde la página de upgrade."
        )


# ── Constante interna ─────────────────────────────────────────────────────────
# Representa "sin límite" en max_records_per_table para tenants full.
# Usar None semántico sería ambiguo; este centinela es explícito.
_NO_LIMIT_SENTINEL: int = -1  # Convención: -1 = sin límite
