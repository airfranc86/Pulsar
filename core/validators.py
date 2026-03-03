"""
Pulsar v1.0 — Input Validators
================================
Validaciones de inputs de usuario antes de llegar al CRUD.
Funciones puras: reciben datos, retornan resultado validado o levantan ValueError.
Sin IO. Sin acceso a DB.

Filosofía: validar early, fallar con mensajes claros, nunca exponer internals.
"""

import re
import logging
from datetime import date, datetime, time
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ─── Expresiones regulares compiladas ────────────────────────────────────────
_EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")
_PHONE_RE = re.compile(r"^[\d\s\+\-\(\)]{6,20}$")
_HORA_RE = re.compile(r"^\d{2}:\d{2}$")
_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


# ─── UUID ─────────────────────────────────────────────────────────────────────

def validate_uuid(value: str, field_name: str = "id") -> str:
    """
    Valida que un string sea un UUID v4 válido.

    Args:
        value: String a validar.
        field_name: Nombre del campo para mensajes de error.

    Returns:
        UUID en minúsculas.

    Raises:
        ValueError: Si el formato es inválido.
    """
    if not value or not _UUID_RE.match(str(value)):
        raise ValueError(f"'{field_name}' no es un UUID válido: '{value}'")
    return str(value).lower()


# ─── Email ────────────────────────────────────────────────────────────────────

def validate_email(email: Optional[str]) -> Optional[str]:
    """
    Valida formato de email. Retorna None si email es None/vacío.

    Returns:
        Email en lowercase o None.

    Raises:
        ValueError: Si el formato es inválido.
    """
    if not email:
        return None
    email = email.strip().lower()
    if not _EMAIL_RE.match(email):
        raise ValueError(f"Email inválido: '{email}'")
    return email


# ─── Teléfono ─────────────────────────────────────────────────────────────────

def validate_phone(phone: Optional[str]) -> Optional[str]:
    """
    Valida formato de teléfono permisivo (internacional).

    Returns:
        Teléfono limpio o None.
    """
    if not phone:
        return None
    phone = phone.strip()
    if not _PHONE_RE.match(phone):
        raise ValueError(f"Teléfono inválido: '{phone}'")
    return phone


# ─── Strings ──────────────────────────────────────────────────────────────────

def validate_non_empty_string(
    value: Optional[str],
    field_name: str,
    max_length: int = 255,
) -> str:
    """
    Valida que un string no sea vacío y no exceda max_length.

    Returns:
        String sin espacios extremos.

    Raises:
        ValueError: Si el valor es inválido.
    """
    if not value or not str(value).strip():
        raise ValueError(f"'{field_name}' no puede estar vacío.")
    cleaned = str(value).strip()
    if len(cleaned) > max_length:
        raise ValueError(
            f"'{field_name}' excede el máximo de {max_length} caracteres."
        )
    return cleaned


# ─── Números ──────────────────────────────────────────────────────────────────

def validate_positive_float(
    value: Any,
    field_name: str,
    allow_zero: bool = True,
) -> float:
    """
    Valida que un valor sea un float positivo.

    Args:
        value: Valor a validar.
        field_name: Nombre del campo.
        allow_zero: Si False, el valor debe ser > 0.

    Returns:
        float validado.

    Raises:
        ValueError: Si el valor no es numérico o está fuera de rango.
    """
    try:
        num = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"'{field_name}' debe ser un número: '{value}'")
    if not allow_zero and num <= 0:
        raise ValueError(f"'{field_name}' debe ser mayor a 0.")
    if num < 0:
        raise ValueError(f"'{field_name}' no puede ser negativo.")
    return round(num, 2)


def validate_positive_int(
    value: Any,
    field_name: str,
    min_val: int = 1,
    max_val: int = 10_000,
) -> int:
    """Valida que un valor sea un entero dentro de rango."""
    try:
        num = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"'{field_name}' debe ser un entero: '{value}'")
    if not min_val <= num <= max_val:
        raise ValueError(
            f"'{field_name}' debe estar entre {min_val} y {max_val}."
        )
    return num


# ─── Fecha y Hora ─────────────────────────────────────────────────────────────

def validate_future_date(value: date, field_name: str = "fecha") -> date:
    """
    Valida que una fecha sea hoy o futura.

    Raises:
        ValueError: Si la fecha es en el pasado.
    """
    if value < date.today():
        raise ValueError(
            f"'{field_name}' no puede ser en el pasado: {value.isoformat()}"
        )
    return value


def validate_hora(value: str) -> str:
    """
    Valida formato HH:MM con hora y minutos en rango válido.

    Returns:
        Hora validada.

    Raises:
        ValueError: Si el formato es incorrecto.
    """
    if not _HORA_RE.match(str(value)):
        raise ValueError(f"Hora debe tener formato HH:MM: '{value}'")
    h, m = int(value[:2]), int(value[3:])
    if not (0 <= h <= 23 and 0 <= m <= 59):
        raise ValueError(f"Hora fuera de rango: '{value}'")
    return value


# ─── Appointment-specific ─────────────────────────────────────────────────────

VALID_APPOINTMENT_STATES = frozenset([
    "pendiente", "confirmado", "completado", "cancelado", "no_show",
])


def validate_appointment_state(state: str) -> str:
    """
    Valida que el estado de un turno sea uno de los permitidos.

    Returns:
        Estado validado.

    Raises:
        ValueError: Si el estado no es válido.
    """
    if state not in VALID_APPOINTMENT_STATES:
        raise ValueError(
            f"Estado inválido: '{state}'. Permitidos: {sorted(VALID_APPOINTMENT_STATES)}"
        )
    return state


# ─── Appointment Create Payload ───────────────────────────────────────────────

def validate_appointment_payload(data: dict[str, Any]) -> dict[str, Any]:
    """
    Valida y limpia el payload completo de creación de un turno.

    Returns:
        Dict validado listo para persistir.

    Raises:
        ValueError: Ante cualquier campo inválido.
    """
    return {
        "client_id": validate_uuid(data.get("client_id", ""), "client_id"),
        "servicio_id": validate_uuid(data.get("servicio_id", ""), "servicio_id"),
        "fecha": data["fecha"].isoformat() if isinstance(data["fecha"], date) else data["fecha"],
        "hora": validate_hora(data.get("hora", "")),
        "estado": validate_appointment_state(data.get("estado", "pendiente")),
        "notas": str(data["notas"])[:500] if data.get("notas") else None,
    }


# ─── Service Payload ──────────────────────────────────────────────────────────

def validate_service_payload(data: dict[str, Any]) -> dict[str, Any]:
    """
    Valida payload de creación/edición de servicio.

    Returns:
        Dict validado.

    Raises:
        ValueError: Ante campos inválidos.
    """
    return {
        "nombre": validate_non_empty_string(data.get("nombre"), "nombre", max_length=120),
        "descripcion": str(data["descripcion"])[:500] if data.get("descripcion") else None,
        "precio": validate_positive_float(data.get("precio", 0), "precio"),
        "duracion_minutos": validate_positive_int(
            data.get("duracion_minutos", 60), "duracion_minutos", min_val=5, max_val=480
        ),
        "activo": bool(data.get("activo", True)),
    }


# ─── Client Payload ───────────────────────────────────────────────────────────

def validate_client_payload(data: dict[str, Any]) -> dict[str, Any]:
    """
    Valida payload de creación/edición de cliente.

    Returns:
        Dict validado.

    Raises:
        ValueError: Ante campos inválidos.
    """
    return {
        "nombre": validate_non_empty_string(data.get("nombre"), "nombre", max_length=120),
        "apellido": validate_non_empty_string(data.get("apellido"), "apellido", max_length=120)
        if data.get("apellido")
        else None,
        "email": validate_email(data.get("email")),
        "telefono": validate_phone(data.get("telefono")),
        "notas": str(data["notas"])[:500] if data.get("notas") else None,
    }
