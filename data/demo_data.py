"""
data/demo_data.py
=================
Datos de ejemplo para el tenant demo cuando no hay conexión a Supabase.
Solo se devuelven datos si tenant_id == DEMO_TENANT_ID.
Estructura compatible con lo que esperan las páginas y UI/tablas.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from config.constants import DEMO_TENANT_ID

# IDs fijos para referencias entre entidades demo
_DEMO_CLIENT_1 = "10000000-0000-0000-0000-000000000001"
_DEMO_CLIENT_2 = "10000000-0000-0000-0000-000000000002"
_DEMO_CLIENT_3 = "10000000-0000-0000-0000-000000000003"
_DEMO_SERVICE_1 = "20000000-0000-0000-0000-000000000001"
_DEMO_SERVICE_2 = "20000000-0000-0000-0000-000000000002"
_DEMO_SERVICE_3 = "20000000-0000-0000-0000-000000000003"


def get_demo_clients(tenant_id: str) -> list[dict[str, Any]]:
    """
    Lista de clientes de ejemplo para el tenant demo.
    Retorna lista vacía si tenant_id no es DEMO_TENANT_ID.
    """
    if tenant_id != DEMO_TENANT_ID:
        return []
    return [
        {
            "id": _DEMO_CLIENT_1,
            "tenant_id": tenant_id,
            "nombre": "María",
            "apellido": "García",
            "email": "maria.garcia@ejemplo.com",
            "telefono": "+54 11 1234-5678",
            "created_at": "2024-01-15T10:00:00",
        },
        {
            "id": _DEMO_CLIENT_2,
            "tenant_id": tenant_id,
            "nombre": "Juan",
            "apellido": "López",
            "email": "juan.lopez@ejemplo.com",
            "telefono": "+54 11 2345-6789",
            "created_at": "2024-02-01T09:30:00",
        },
        {
            "id": _DEMO_CLIENT_3,
            "tenant_id": tenant_id,
            "nombre": "Ana",
            "apellido": "Martínez",
            "email": "",
            "telefono": "4567-8901",
            "created_at": "2024-02-10T14:00:00",
        },
    ]


def get_demo_services(tenant_id: str) -> list[dict[str, Any]]:
    """
    Lista de servicios de ejemplo para el tenant demo.
    Retorna lista vacía si tenant_id no es DEMO_TENANT_ID.
    """
    if tenant_id != DEMO_TENANT_ID:
        return []
    return [
        {
            "id": _DEMO_SERVICE_1,
            "tenant_id": tenant_id,
            "nombre": "Consulta estándar",
            "precio": 5000.0,
            "activo": True,
            "categoria": "General",
            "duracion_minutos": 30,
        },
        {
            "id": _DEMO_SERVICE_2,
            "tenant_id": tenant_id,
            "nombre": "Servicio premium",
            "precio": 12000.0,
            "activo": True,
            "categoria": "Premium",
            "duracion_minutos": 60,
        },
        {
            "id": _DEMO_SERVICE_3,
            "tenant_id": tenant_id,
            "nombre": "Sesión express",
            "precio": 2500.0,
            "activo": True,
            "categoria": "Express",
            "duracion_minutos": 15,
        },
    ]


def get_demo_appointments(
    tenant_id: str,
    fecha_desde: date | None = None,
    fecha_hasta: date | None = None,
) -> list[dict[str, Any]]:
    """
    Lista de turnos de ejemplo para el tenant demo.
    Filtra por rango de fechas si se indican fecha_desde/fecha_hasta.
    Retorna lista vacía si tenant_id no es DEMO_TENANT_ID.
    """
    if tenant_id != DEMO_TENANT_ID:
        return []
    hoy = date.today()
    base = [
        {
            "id": "30000000-0000-0000-0000-000000000001",
            "tenant_id": tenant_id,
            "fecha": (hoy - timedelta(days=2)).isoformat(),
            "hora": "10:00",
            "estado": "completado",
            "service_id": _DEMO_SERVICE_1,
            "client_id": _DEMO_CLIENT_1,
            "cliente_nombre": "María García",
            "servicio_nombre": "Consulta estándar",
            "precio": 5000.0,
            "clients": {"nombre": "María García", "telefono": "+54 11 1234-5678"},
            "services": {"nombre": "Consulta estándar", "precio": 5000.0},
        },
        {
            "id": "30000000-0000-0000-0000-000000000002",
            "tenant_id": tenant_id,
            "fecha": (hoy - timedelta(days=1)).isoformat(),
            "hora": "11:30",
            "estado": "completado",
            "service_id": _DEMO_SERVICE_2,
            "client_id": _DEMO_CLIENT_2,
            "cliente_nombre": "Juan López",
            "servicio_nombre": "Servicio premium",
            "precio": 12000.0,
            "clients": {"nombre": "Juan López", "telefono": "+54 11 2345-6789"},
            "services": {"nombre": "Servicio premium", "precio": 12000.0},
        },
        {
            "id": "30000000-0000-0000-0000-000000000003",
            "tenant_id": tenant_id,
            "fecha": hoy.isoformat(),
            "hora": "09:00",
            "estado": "confirmado",
            "service_id": _DEMO_SERVICE_3,
            "client_id": _DEMO_CLIENT_3,
            "cliente_nombre": "Ana Martínez",
            "servicio_nombre": "Sesión express",
            "precio": 2500.0,
            "clients": {"nombre": "Ana Martínez", "telefono": "4567-8901"},
            "services": {"nombre": "Sesión express", "precio": 2500.0},
        },
        {
            "id": "30000000-0000-0000-0000-000000000004",
            "tenant_id": tenant_id,
            "fecha": hoy.isoformat(),
            "hora": "16:00",
            "estado": "pendiente",
            "service_id": _DEMO_SERVICE_1,
            "client_id": _DEMO_CLIENT_1,
            "cliente_nombre": "María García",
            "servicio_nombre": "Consulta estándar",
            "precio": 5000.0,
            "clients": {"nombre": "María García", "telefono": "+54 11 1234-5678"},
            "services": {"nombre": "Consulta estándar", "precio": 5000.0},
        },
    ]
    if fecha_desde is None and fecha_hasta is None:
        return base
    result: list[dict[str, Any]] = []
    for t in base:
        d = date.fromisoformat(t["fecha"])
        if fecha_desde is not None and d < fecha_desde:
            continue
        if fecha_hasta is not None and d > fecha_hasta:
            continue
        result.append(t)
    return result
