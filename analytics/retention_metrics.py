"""
Pulsar v1.0 — Retention Metrics
==================================
Cálculo de métricas de retención y segmentación de clientes.
Funciones puras sobre datos ya cargados.
"""

import logging
from datetime import date
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)


def compute_clientes_nuevos_vs_recurrentes(
    turnos_periodo: list[dict[str, Any]],
    turnos_historicos: list[dict[str, Any]],
) -> dict[str, int]:
    """
    Clasifica clientes en nuevos (primera vez) vs recurrentes.

    Lógica: un cliente es NUEVO si no tiene turnos anteriores al período.

    Args:
        turnos_periodo: Turnos del período actual.
        turnos_historicos: Todos los turnos previos al período (para referencia).

    Returns:
        Dict con 'nuevos' y 'recurrentes'.
    """
    if not turnos_periodo:
        return {"nuevos": 0, "recurrentes": 0}

    clientes_historicos = {
        t["client_id"]
        for t in turnos_historicos
        if t.get("client_id")
    }

    clientes_periodo = {t["client_id"] for t in turnos_periodo if t.get("client_id")}

    nuevos = clientes_periodo - clientes_historicos
    recurrentes = clientes_periodo & clientes_historicos

    return {
        "nuevos": len(nuevos),
        "recurrentes": len(recurrentes),
    }


def compute_retention_rate(
    clientes_mes_anterior: set[str],
    clientes_mes_actual: set[str],
) -> float:
    """
    Calcula la tasa de retención entre dos períodos.

    Args:
        clientes_mes_anterior: Set de client_ids del mes anterior.
        clientes_mes_actual: Set de client_ids del mes actual.

    Returns:
        Tasa de retención entre 0.0 y 1.0.
    """
    if not clientes_mes_anterior:
        return 0.0

    retenidos = clientes_mes_anterior & clientes_mes_actual
    return round(len(retenidos) / len(clientes_mes_anterior), 4)


def compute_retention_metrics(
    db: Any,
    tenant_id: str,
    period_start: date,
    period_end: date,
) -> dict[str, Any]:
    """
    Calcula métricas de retención para el período. Accede a DB.
    Usada por scheduler_service. El cliente db debe ser inyectado por el caller
    (scheduler usa get_service_client(); NUNCA llamar desde pages/ con admin client).

    Args:
        db: Cliente Supabase (inyectado; solo scheduler debe pasar service_role).
        tenant_id: UUID del tenant.
        period_start: Inicio del período.
        period_end: Fin del período.

    Returns:
        Dict con métricas de retención.
    """
    from core.crud import list_appointments
    import calendar

    # Turnos del período actual
    turnos_periodo = list_appointments(
        db,
        tenant_id,
        fecha_desde=period_start,
        fecha_hasta=period_end,
        limit=500,
    )

    # Turnos del mes anterior (para detectar nuevos vs recurrentes)
    if period_start.month == 1:
        prev_start = date(period_start.year - 1, 12, 1)
    else:
        prev_start = date(period_start.year, period_start.month - 1, 1)

    prev_end = date(
        prev_start.year,
        prev_start.month,
        calendar.monthrange(prev_start.year, prev_start.month)[1],
    )

    turnos_anteriores = list_appointments(
        db,
        tenant_id,
        fecha_desde=prev_start,
        fecha_hasta=prev_end,
        limit=500,
    )

    segmentacion = compute_clientes_nuevos_vs_recurrentes(
        turnos_periodo, turnos_anteriores
    )

    clientes_anterior = {t["client_id"] for t in turnos_anteriores if t.get("client_id")}
    clientes_actual = {t["client_id"] for t in turnos_periodo if t.get("client_id")}

    return {
        "clientes_nuevos": segmentacion["nuevos"],
        "clientes_recurrentes": segmentacion["recurrentes"],
        "retention_rate": compute_retention_rate(clientes_anterior, clientes_actual),
    }
