"""
Pulsar v1.0 — Revenue Metrics
================================
Cálculo de KPIs de ingresos. Funciones puras sobre datos ya cargados.
No accede a DB directamente. Recibe DataFrames o dicts ya obtenidos.

Excepción: compute_period_revenue sí accede a DB (función de conveniencia
para el scheduler). El resto son funciones puras testables.
"""

import logging
from datetime import date
from typing import Any

import pandas as pd

from config.constants import APPOINTMENT_STATES_BILLABLE

logger = logging.getLogger(__name__)


def compute_ingresos_mensuales(
    turnos: list[dict[str, Any]],
    servicios: dict[str, float],
) -> float:
    """
    Calcula ingresos totales del período.

    Args:
        turnos: Lista de turnos (dicts con servicio_id y estado).
        servicios: Dict {servicio_id: precio}.

    Returns:
        Total de ingresos como float.
    """
    total = 0.0
    for t in turnos:
        if t.get("estado") in APPOINTMENT_STATES_BILLABLE:
            precio = servicios.get(t.get("servicio_id", ""), 0.0)
            total += float(precio)
    return round(total, 2)


def compute_ticket_promedio(ingresos: float, total_turnos: int) -> float:
    """
    Calcula el ticket promedio.

    Args:
        ingresos: Total de ingresos del período.
        total_turnos: Cantidad de turnos facturables.

    Returns:
        Ticket promedio. 0.0 si no hay turnos.
    """
    if total_turnos == 0:
        return 0.0
    return round(ingresos / total_turnos, 2)


def compute_ocupacion(
    turnos_completados: int,
    capacidad_maxima: int,
) -> float:
    """
    Calcula la tasa de ocupación de turnos.

    Args:
        turnos_completados: Cantidad de turnos completados/confirmados.
        capacidad_maxima: Capacidad máxima del período.

    Returns:
        Ratio entre 0.0 y 1.0. 0.0 si capacidad es 0.
    """
    if capacidad_maxima <= 0:
        return 0.0
    return round(min(turnos_completados / capacidad_maxima, 1.0), 4)


def compute_servicios_mas_vendidos(
    turnos: list[dict[str, Any]],
    servicios: dict[str, str],
    *,
    top_n: int = 5,
) -> list[dict[str, Any]]:
    """
    Ranking de servicios más vendidos por cantidad de turnos.

    Args:
        turnos: Lista de turnos con servicio_id.
        servicios: Dict {servicio_id: nombre_servicio}.
        top_n: Cantidad de servicios a retornar.

    Returns:
        Lista de dicts [{nombre, cantidad, pct}] ordenados desc.
    """
    if not turnos:
        return []

    billable = [
        t for t in turnos
        if t.get("estado") in APPOINTMENT_STATES_BILLABLE
    ]

    if not billable:
        return []

    df = pd.DataFrame(billable)
    counts = df["servicio_id"].value_counts().head(top_n)
    total = counts.sum()

    result = []
    for servicio_id, count in counts.items():
        result.append({
            "nombre": servicios.get(str(servicio_id), str(servicio_id)),
            "cantidad": int(count),
            "pct": round(int(count) / total * 100, 1),
        })
    return result


def compute_horas_pico(turnos: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Detecta las horas pico de turnos en el período.

    Args:
        turnos: Lista de turnos con campo 'hora' (HH:MM).

    Returns:
        Lista de dicts [{hora, cantidad}] ordenados por cantidad desc.
    """
    if not turnos:
        return []

    df = pd.DataFrame(turnos)
    if "hora" not in df.columns:
        return []

    df["hour"] = pd.to_datetime(df["hora"], format="%H:%M", errors="coerce").dt.hour
    counts = df["hour"].value_counts().sort_index()

    return [
        {"hora": f"{int(h):02d}:00", "cantidad": int(c)}
        for h, c in counts.items()
        if pd.notna(h)
    ]


def compute_comparacion_mes_anterior(
    ingresos_actual: float,
    ingresos_anterior: float,
) -> float:
    """
    Calcula ratio de variación respecto al mes anterior.

    Args:
        ingresos_actual: Ingresos del mes actual.
        ingresos_anterior: Ingresos del mes anterior.

    Returns:
        Ratio de variación. ej: 0.15 = +15%. 0.0 si no hay base.
    """
    if ingresos_anterior == 0:
        return 0.0
    return round((ingresos_actual - ingresos_anterior) / ingresos_anterior, 4)


def compute_period_revenue(
    db: Any,
    tenant_id: str,
    period_start: date,
    period_end: date,
) -> dict[str, Any]:
    """
    Calcula todos los KPIs de ingresos para un período.
    Función de conveniencia que accede a DB. Usada por scheduler_service.
    El cliente db debe ser inyectado (scheduler usa get_service_client();
    NUNCA llamar desde pages/ con admin client).

    Args:
        db: Cliente Supabase (inyectado).
        tenant_id: UUID del tenant.
        period_start: Primer día del período.
        period_end: Último día del período.

    Returns:
        Dict con todos los KPIs de ingresos.
    """
    from core.crud import list_appointments, list_services

    logger.info(
        "computing_period_revenue",
        extra={
            "tenant_id": tenant_id,
            "period_start": str(period_start),
            "period_end": str(period_end),
        },
    )

    turnos = list_appointments(
        db,
        tenant_id,
        fecha_desde=period_start,
        fecha_hasta=period_end,
        limit=500,
    )

    services_list = list_services(db, tenant_id)
    servicios_precio = {s["id"]: float(s.get("precio", 0)) for s in services_list}
    servicios_nombre = {s["id"]: s.get("nombre", "") for s in services_list}

    billable = [t for t in turnos if t.get("estado") in APPOINTMENT_STATES_BILLABLE]
    cancelados = [t for t in turnos if t.get("estado") == "cancelado"]
    no_shows = [t for t in turnos if t.get("estado") == "no_show"]

    ingresos = compute_ingresos_mensuales(billable, servicios_precio)
    ticket = compute_ticket_promedio(ingresos, len(billable))

    # Ocupación contra slots del período (días × slots/día), no contra total turnos.
    from config.constants import SLOTS_POR_DIA_DEFAULT
    dias = (period_end - period_start).days + 1
    capacidad = max(dias * SLOTS_POR_DIA_DEFAULT, 1)

    return {
        "ingresos_mensuales": ingresos,
        "ticket_promedio": ticket,
        "total_turnos": len(billable),
        "cancelaciones": len(cancelados),
        "no_shows": len(no_shows),
        "ocupacion_turnos": compute_ocupacion(len(billable), capacidad),
        "servicios_mas_vendidos": compute_servicios_mas_vendidos(billable, servicios_nombre),
        "horas_pico": compute_horas_pico(turnos),
    }
