"""
core/crud.py
============
Operaciones CRUD de Pulsar v1.0.

Cada función recibe tenant_id obligatorio como primer argumento.
Nunca ejecutar queries sin tenant_id — enforced aquí y por RLS en Supabase.

Patrón: función recibe tenant_id + params → valida → query → retorna dict/list.
Sin transformación de dominio — eso vive en services/.
"""
from __future__ import annotations
import logging
from datetime import date, datetime
from typing import Any, Optional

from supabase import Client  # type: ignore

from core.database import DatabaseError, assert_tenant as require_tenant
from config.constants import (
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
    APPOINTMENT_STATES,
)

logger = logging.getLogger(__name__)


class CRUDError(DatabaseError):
    """Error en operación CRUD."""


# ─── TENANTS ──────────────────────────────────────────────────────────────────

def get_tenant(db: Client, tenant_id: str) -> Optional[dict[str, Any]]:
    """
    Obtiene los datos del tenant incluida su suscripción.

    Args:
        db: Cliente Supabase.
        tenant_id: UUID del tenant.

    Returns:
        dict con datos del tenant o None si no existe.
    """
    tid = require_tenant(tenant_id)
    try:
        result = (
            db.table("tenants")
            .select("*")
            .eq("id", tid)
            .single()
            .execute()
        )
        return result.data
    except Exception as exc:
        logger.error("get_tenant_failed", extra={"tenant_id": tid, "error": str(exc)})
        return None


def update_tenant_subscription(
    db: Client,
    tenant_id: str,
    subscription_status: str,
    stripe_subscription_id: str,
    current_period_end: datetime,
) -> bool:
    """
    Actualiza el estado de suscripción del tenant (llamado por webhook Stripe).
    Debe usar service_client (bypass RLS).

    Args:
        db: Cliente Supabase con service_role.
        tenant_id: UUID del tenant.
        subscription_status: Nuevo estado (active, canceled, etc.).
        stripe_subscription_id: ID de suscripción Stripe.
        current_period_end: Fin del período de facturación.

    Returns:
        bool: True si la actualización fue exitosa.
    """
    tid = require_tenant(tenant_id)
    try:
        db.table("tenants").update(
            {
                "subscription_status": subscription_status,
                "stripe_subscription_id": stripe_subscription_id,
                "current_period_end": current_period_end.isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }
        ).eq("id", tid).execute()
        logger.info(
            "tenant_subscription_updated",
            extra={
                "tenant_id": tid,
                "status": subscription_status,
                "event": "subscription_update",
            }
        )
        return True
    except Exception as exc:
        logger.error(
            "update_tenant_subscription_failed",
            extra={"tenant_id": tid, "error": str(exc)},
        )
        return False


# ─── REPORT HISTORY ───────────────────────────────────────────────────────────

def list_report_history(
    db: Client,
    tenant_id: str,
    limit: int = 12,
) -> list[dict[str, Any]]:
    """
    Lista el historial de reportes mensuales del tenant (orden descendente por fecha).

    Args:
        db: Cliente Supabase.
        tenant_id: UUID del tenant.
        limit: Cantidad máxima de registros.

    Returns:
        Lista de dicts con period_label, storage_path, sent_to_email, sent_at, created_at.
    """
    tid = require_tenant(tenant_id)
    try:
        result = (
            db.table("report_history")
            .select("id, period_label, storage_path, sent_to_email, sent_at, created_at")
            .eq("tenant_id", tid)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data or []
    except Exception as exc:
        logger.error(
            "list_report_history_failed",
            extra={"tenant_id": tid, "error": str(exc)},
        )
        return []


def create_report_history_entry(
    db: Client,
    tenant_id: str,
    data: dict[str, Any],
) -> dict[str, Any]:
    """
    Crea una entrada en report_history (usado por scheduler/Edge Function).

    Args:
        db: Cliente Supabase (service_role).
        tenant_id: UUID del tenant.
        data: period_label, storage_path, sent_to_email (opcional), sent_at (opcional).

    Returns:
        dict con la fila insertada.
    """
    tid = require_tenant(tenant_id)
    row = {
        "tenant_id": tid,
        "period_label": data.get("period_label", ""),
        "storage_path": data.get("storage_path", ""),
        "sent_to_email": data.get("sent_to_email"),
        "sent_at": data.get("sent_at"),
    }
    try:
        result = db.table("report_history").insert(row).execute()
        return (result.data or [{}])[0]
    except Exception as exc:
        logger.error(
            "create_report_history_entry_failed",
            extra={"tenant_id": tid, "error": str(exc)},
        )
        raise CRUDError(f"Error creando entrada en report_history: {exc}") from exc


# ─── CLIENTS ──────────────────────────────────────────────────────────────────

def list_clients(
    db: Client,
    tenant_id: str,
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
    search: Optional[str] = None,
) -> list[dict[str, Any]]:
    """
    Lista clientes del tenant con paginación opcional.

    Args:
        db: Cliente Supabase.
        tenant_id: UUID del tenant.
        page: Página actual (1-indexed).
        page_size: Registros por página (máx MAX_PAGE_SIZE).
        search: Filtro por nombre o email.

    Returns:
        Lista de dicts con datos de clientes.
    """
    tid = require_tenant(tenant_id)
    ps = min(page_size, MAX_PAGE_SIZE)
    offset = (page - 1) * ps

    try:
        query = db.table("clients").select("*").eq("tenant_id", tid)
        if search and search.strip():
            term = search.strip()
            query = query.or_(f"nombre.ilike.%{term}%,email.ilike.%{term}%")
        result = query.order("nombre").range(offset, offset + ps - 1).execute()
        return result.data or []
    except Exception as exc:
        logger.error("list_clients_failed", extra={"tenant_id": tid, "error": str(exc)})
        raise CRUDError(f"Error listando clientes: {exc}") from exc


def create_client(db: Client, data: dict[str, Any]) -> dict[str, Any]:
    """
    Crea un nuevo cliente. Requiere data ya validada por validators.py.

    Args:
        db: Cliente Supabase.
        data: Datos validados del cliente (debe incluir tenant_id).

    Returns:
        dict con el cliente creado.
    """
    require_tenant(data.get("tenant_id"))
    try:
        result = db.table("clients").insert(data).execute()
        logger.info("client_created", extra={"tenant_id": data["tenant_id"], "event": "client_created"})
        return result.data[0]
    except Exception as exc:
        logger.error("create_client_failed", extra={"error": str(exc)})
        raise CRUDError(f"Error creando cliente: {exc}") from exc


def create_client_record(
    db: Client, tenant_id: str, data: dict[str, Any]
) -> dict[str, Any]:
    """
    Alias para crear cliente inyectando tenant_id. Usado por pages/02_Clientes.
    """
    payload = dict(data)
    payload["tenant_id"] = tenant_id
    return create_client(db, payload)


def update_client(
    db: Client, tenant_id: str, client_id: str, data: dict[str, Any]
) -> dict[str, Any]:
    """Actualiza un cliente verificando que pertenece al tenant."""
    tid = require_tenant(tenant_id)
    try:
        data.pop("tenant_id", None)  # No permitir cambiar el tenant
        data["updated_at"] = datetime.utcnow().isoformat()
        result = (
            db.table("clients")
            .update(data)
            .eq("id", client_id)
            .eq("tenant_id", tid)
            .execute()
        )
        if not result.data:
            raise CRUDError("Cliente no encontrado o no pertenece a este tenant")
        logger.info("client_updated", extra={"tenant_id": tid, "client_id": client_id})
        return result.data[0]
    except CRUDError:
        raise
    except Exception as exc:
        logger.error("update_client_failed", extra={"error": str(exc)})
        raise CRUDError(f"Error actualizando cliente: {exc}") from exc


def delete_client(db: Client, tenant_id: str, client_id: str) -> bool:
    """Elimina un cliente verificando que pertenece al tenant."""
    tid = require_tenant(tenant_id)
    try:
        db.table("clients").delete().eq("id", client_id).eq("tenant_id", tid).execute()
        logger.info("client_deleted", extra={"tenant_id": tid, "client_id": client_id})
        return True
    except Exception as exc:
        logger.error("delete_client_failed", extra={"error": str(exc)})
        raise CRUDError(f"Error eliminando cliente: {exc}") from exc


# ─── SERVICES ─────────────────────────────────────────────────────────────────

def list_services(
    db: Client,
    tenant_id: str,
    active_only: bool = True,
) -> list[dict[str, Any]]:
    """Lista servicios del tenant."""
    tid = require_tenant(tenant_id)
    try:
        query = db.table("services").select("*").eq("tenant_id", tid)
        if active_only:
            query = query.eq("activo", True)
        result = query.order("nombre").execute()
        return result.data or []
    except Exception as exc:
        logger.error("list_services_failed", extra={"tenant_id": tid, "error": str(exc)})
        raise CRUDError(f"Error listando servicios: {exc}") from exc


def create_service(db: Client, data: dict[str, Any]) -> dict[str, Any]:
    """Crea un nuevo servicio."""
    require_tenant(data.get("tenant_id"))
    try:
        result = db.table("services").insert(data).execute()
        logger.info("service_created", extra={"tenant_id": data["tenant_id"]})
        return result.data[0]
    except Exception as exc:
        logger.error("create_service_failed", extra={"error": str(exc)})
        raise CRUDError(f"Error creando servicio: {exc}") from exc


def update_service(
    db: Client, tenant_id: str, service_id: str, data: dict[str, Any]
) -> dict[str, Any]:
    """Actualiza un servicio verificando que pertenece al tenant."""
    tid = require_tenant(tenant_id)
    try:
        data.pop("tenant_id", None)
        data["updated_at"] = datetime.utcnow().isoformat()
        result = (
            db.table("services")
            .update(data)
            .eq("id", service_id)
            .eq("tenant_id", tid)
            .execute()
        )
        if not result.data:
            raise CRUDError("Servicio no encontrado o no pertenece a este tenant")
        return result.data[0]
    except CRUDError:
        raise
    except Exception as exc:
        raise CRUDError(f"Error actualizando servicio: {exc}") from exc


# ─── APPOINTMENTS ─────────────────────────────────────────────────────────────

def list_appointments(
    db: Client,
    tenant_id: str,
    fecha_desde: Optional[date] = None,
    fecha_hasta: Optional[date] = None,
    estado: Optional[str] = None,
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
) -> list[dict[str, Any]]:
    """
    Lista turnos del tenant con filtros opcionales.

    Args:
        db: Cliente Supabase.
        tenant_id: UUID del tenant.
        fecha_desde: Fecha inicio del rango.
        fecha_hasta: Fecha fin del rango.
        estado: Filtrar por estado específico.
        page: Página actual.
        page_size: Registros por página.

    Returns:
        Lista de turnos.
    """
    tid = require_tenant(tenant_id)
    ps = min(page_size, MAX_PAGE_SIZE)
    offset = (page - 1) * ps

    try:
        query = (
            db.table("appointments")
            .select("*, clients(nombre, telefono), services(nombre, precio)")
            .eq("tenant_id", tid)
        )
        if fecha_desde:
            query = query.gte("fecha", fecha_desde.isoformat())
        if fecha_hasta:
            query = query.lte("fecha", fecha_hasta.isoformat())
        if estado and estado in APPOINTMENT_STATES:
            query = query.eq("estado", estado)

        result = query.order("fecha", desc=True).order("hora").range(offset, offset + ps - 1).execute()
        return result.data or []
    except Exception as exc:
        logger.error("list_appointments_failed", extra={"tenant_id": tid, "error": str(exc)})
        raise CRUDError(f"Error listando turnos: {exc}") from exc


def create_appointment(db: Client, data: dict[str, Any]) -> dict[str, Any]:
    """Crea un nuevo turno."""
    require_tenant(data.get("tenant_id"))
    try:
        result = db.table("appointments").insert(data).execute()
        logger.info("appointment_created", extra={"tenant_id": data["tenant_id"]})
        return result.data[0]
    except Exception as exc:
        logger.error("create_appointment_failed", extra={"error": str(exc)})
        raise CRUDError(f"Error creando turno: {exc}") from exc


def update_appointment_status(
    db: Client,
    tenant_id: str,
    appointment_id: str,
    new_status: str,
) -> bool:
    """
    Actualiza el estado de un turno.

    Args:
        db: Cliente Supabase.
        tenant_id: UUID del tenant.
        appointment_id: UUID del turno.
        new_status: Nuevo estado a asignar.

    Returns:
        bool: True si fue exitoso.
    """
    tid = require_tenant(tenant_id)
    if new_status not in APPOINTMENT_STATES:
        raise CRUDError(f"Estado inválido: {new_status}")
    try:
        db.table("appointments").update(
            {"estado": new_status, "updated_at": datetime.utcnow().isoformat()}
        ).eq("id", appointment_id).eq("tenant_id", tid).execute()
        logger.info(
            "appointment_status_updated",
            extra={"tenant_id": tid, "appointment_id": appointment_id, "status": new_status}
        )
        return True
    except Exception as exc:
        logger.error("update_appointment_status_failed", extra={"error": str(exc)})
        raise CRUDError(f"Error actualizando estado de turno: {exc}") from exc


# ─── ANALYTICS RAW DATA ───────────────────────────────────────────────────────

def get_appointments_for_period(
    db: Client,
    tenant_id: str,
    fecha_desde: date,
    fecha_hasta: date,
) -> list[dict[str, Any]]:
    """
    Obtiene todos los turnos de un período para cálculo de KPIs.
    Sin paginación — usado internamente por analytics/.

    Args:
        db: Cliente Supabase.
        tenant_id: UUID del tenant.
        fecha_desde: Inicio del período.
        fecha_hasta: Fin del período.

    Returns:
        Lista completa de turnos del período.
    """
    tid = require_tenant(tenant_id)
    try:
        result = (
            db.table("appointments")
            .select("id, fecha, hora, estado, service_id, client_id, services(precio)")
            .eq("tenant_id", tid)
            .gte("fecha", fecha_desde.isoformat())
            .lte("fecha", fecha_hasta.isoformat())
            .execute()
        )
        return result.data or []
    except Exception as exc:
        logger.error("get_appointments_for_period_failed", extra={"tenant_id": tid, "error": str(exc)})
        raise CRUDError(f"Error obteniendo turnos del período: {exc}") from exc


# ─── MONTHLY REPORTS ──────────────────────────────────────────────────────────

def save_monthly_report(
    db: Client,
    tenant_id: str,
    year: int,
    month: int,
    storage_path: str,
) -> dict[str, Any]:
    """Registra un reporte mensual generado en la tabla de histórico."""
    tid = require_tenant(tenant_id)
    try:
        data = {
            "tenant_id": tid,
            "year": year,
            "month": month,
            "storage_path": storage_path,
            "created_at": datetime.utcnow().isoformat(),
        }
        result = db.table("monthly_reports").insert(data).execute()
        logger.info("monthly_report_saved", extra={"tenant_id": tid, "year": year, "month": month})
        return result.data[0]
    except Exception as exc:
        logger.error("save_monthly_report_failed", extra={"error": str(exc)})
        raise CRUDError(f"Error guardando reporte mensual: {exc}") from exc


def list_monthly_reports(
    db: Client, tenant_id: str
) -> list[dict[str, Any]]:
    """Lista el histórico de reportes mensuales del tenant."""
    tid = require_tenant(tenant_id)
    try:
        result = (
            db.table("monthly_reports")
            .select("*")
            .eq("tenant_id", tid)
            .order("year", desc=True)
            .order("month", desc=True)
            .execute()
        )
        return result.data or []
    except Exception as exc:
        logger.error("list_monthly_reports_failed", extra={"tenant_id": tid, "error": str(exc)})
        raise CRUDError(f"Error listando reportes: {exc}") from exc
