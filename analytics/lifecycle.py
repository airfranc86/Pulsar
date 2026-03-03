"""
Pulsar v1.0 — Client Lifecycle Analytics
==========================================
Análisis del ciclo de vida del cliente: churn, LTV, frecuencia de visitas.
Funciones puras. Sin IO.
"""

import logging
from datetime import date
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)


def compute_average_visits_per_client(
    turnos: list[dict[str, Any]],
) -> float:
    """
    Calcula el promedio de visitas por cliente en el período.

    Args:
        turnos: Lista de turnos del período.

    Returns:
        Promedio de visitas. 0.0 si no hay clientes.
    """
    if not turnos:
        return 0.0

    df = pd.DataFrame(turnos)
    if "client_id" not in df.columns:
        return 0.0

    visits_per_client = df.groupby("client_id").size()
    return round(float(visits_per_client.mean()), 2)


def compute_ltv_estimate(
    ticket_promedio: float,
    visitas_por_mes: float,
    meses_retencion: float = 12.0,
) -> float:
    """
    Estimación simple del Lifetime Value del cliente.

    Args:
        ticket_promedio: Ticket promedio por visita.
        visitas_por_mes: Visitas promedio por mes.
        meses_retencion: Meses de retención esperados.

    Returns:
        LTV estimado.
    """
    return round(ticket_promedio * visitas_por_mes * meses_retencion, 2)
