"""
core/database.py
================
Clientes Supabase y guards de seguridad multi-tenant.

Responsabilidades:
  - assert_tenant(): primera línea de defensa contra operaciones sin tenant_id
  - get_anon_client(): cliente público con RLS aplicado
  - get_service_client(): cliente privilegiado — SOLO para Edge Functions/scheduler

Regla de oro: NINGUNA operación llega a la base de datos sin pasar por assert_tenant().
"""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# ── Patrón UUID v4 estricto ───────────────────────────────────────────────────
_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


# ── Jerarquía de excepciones ──────────────────────────────────────────────────

class DatabaseError(Exception):
    """Error base para todas las excepciones de acceso a datos."""


class TenantAssertionError(DatabaseError):
    """
    Se lanza cuando assert_tenant() recibe un tenant_id inválido.

    Esta excepción señala un bug de programación, no un error de runtime:
    significa que alguna función CRUD fue llamada sin tenant_id válido,
    lo que podría provocar acceso cruzado entre tenants.
    """


class TenantNotFoundError(DatabaseError):
    """El tenant_id es válido en formato pero no existe en la base de datos."""


class SubscriptionError(DatabaseError):
    """Error relacionado con el estado de suscripción del tenant."""


# ── Guard de seguridad ────────────────────────────────────────────────────────

def assert_tenant(tenant_id: Any) -> str:
    """
    Valida que tenant_id sea un UUID v4 bien formado antes de cualquier
    operación de base de datos.

    Falla rápido con mensaje claro. Esta función es la ÚNICA puerta de entrada
    a cualquier operación CRUD. Si no pasa esta validación, la operación no ocurre.

    Args:
        tenant_id: Valor a validar. Acepta cualquier tipo para dar un error claro
                   si se pasa None, int, etc.

    Returns:
        El tenant_id como str si es válido.

    Raises:
        TenantAssertionError: Si tenant_id es None, vacío, no es string, o no es
                              un UUID v4 válido.

    Examples:
        >>> assert_tenant("550e8400-e29b-41d4-a716-446655440000")
        '550e8400-e29b-41d4-a716-446655440000'

        >>> assert_tenant(None)
        TenantAssertionError: tenant_id no puede ser None ...

        >>> assert_tenant("")
        TenantAssertionError: tenant_id no puede ser vacío ...
    """
    # ── Verificar que no sea None ─────────────────────────────────────────────
    if tenant_id is None:
        raise TenantAssertionError(
            "tenant_id no puede ser None. "
            "Toda operación de base de datos requiere un tenant_id válido. "
            "Verificar que _resolve_tenant_id() se ejecutó antes de esta llamada."
        )

    # ── Verificar tipo string ─────────────────────────────────────────────────
    if not isinstance(tenant_id, str):
        raise TenantAssertionError(
            f"tenant_id debe ser str, recibido {type(tenant_id).__name__!r}. "
            f"Valor: {tenant_id!r}"
        )

    # ── Verificar que no sea vacío ni solo espacios ───────────────────────────
    stripped = tenant_id.strip()
    if not stripped:
        raise TenantAssertionError(
            "tenant_id no puede ser vacío o solo espacios en blanco. "
            f"Valor recibido: {tenant_id!r}"
        )

    # ── Verificar formato UUID v4 ─────────────────────────────────────────────
    if not _UUID_RE.match(stripped):
        raise TenantAssertionError(
            f"tenant_id no tiene formato UUID v4 válido. "
            f"Valor recibido: {stripped!r}. "
            f"Formato esperado: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
        )

    logger.debug("assert_tenant_passed", extra={"tenant_id": stripped})
    return stripped


# ── Clientes Supabase (stubs — requieren configuración real en producción) ────

def _create_client_with_retry(url: str, key: str) -> Any:
    """
    Crea cliente Supabase con reintentos ante fallos transitorios de red.
    No reintenta ImportError (configuración faltante).
    """
    from supabase import create_client
    try:
        from tenacity import retry, stop_after_attempt, retry_if_exception_type
    except ImportError:
        return create_client(url, key)
    # Reintentar solo en errores de red/timeout; no en ImportError ni ValueError
    @retry(
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type((ConnectionError, TimeoutError, OSError)),
        reraise=True,
    )
    def _do_create() -> Any:
        return create_client(url, key)
    return _do_create()


def get_anon_client() -> Any:
    """
    Retorna el cliente Supabase con anon_key.
    RLS filtra automáticamente por tenant_id vía JWT claim.

    En tests, mockear esta función con unittest.mock.patch.
    """
    try:
        from config.settings import settings
        if not settings.use_supabase:
            raise DatabaseError(
                "Supabase no está configurado. Definí SUPABASE_URL y SUPABASE_ANON_KEY "
                "en .env o Streamlit Secrets, o quitá USE_SUPABASE=false."
            )
        return _create_client_with_retry(
            settings.supabase.url,
            settings.supabase.anon_key,
        )
    except ImportError:
        raise DatabaseError(
            "supabase-py no está instalado. Ejecutar: pip install supabase"
        )
    except DatabaseError:
        raise
    except Exception as exc:
        raise DatabaseError(f"No se pudo crear el cliente Supabase: {exc}") from exc


def get_service_client() -> Any:
    """
    Retorna el cliente Supabase con service_role_key.

    ADVERTENCIA: Este cliente bypasea RLS. NUNCA usarlo desde pages/ o UI/.
    Solo válido en: services/scheduler_service.py y Edge Functions.
    """
    try:
        from config.settings import settings
        if not settings.use_supabase:
            raise DatabaseError(
                "Supabase no está configurado. Definí SUPABASE_URL y "
                "SUPABASE_SERVICE_ROLE_KEY en .env o Streamlit Secrets."
            )
        return _create_client_with_retry(
            settings.supabase.url,
            settings.supabase.service_role_key,
        )
    except ImportError:
        raise DatabaseError(
            "supabase-py no está instalado. Ejecutar: pip install supabase"
        )
    except DatabaseError:
        raise
    except Exception as exc:
        raise DatabaseError(
            f"No se pudo crear el cliente de servicio Supabase: {exc}"
        ) from exc


# Alias para compatibilidad. Preferir get_service_client en código nuevo.
# NUNCA usar desde pages/ o UI; solo scheduler y Edge Functions.
get_admin_client = get_service_client
