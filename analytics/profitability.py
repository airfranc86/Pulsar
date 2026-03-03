"""
Pulsar v1.0 — Profitability Analytics
========================================
Análisis de rentabilidad por servicio y por período.
Funciones puras. Sin IO.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def compute_revenue_by_service(
    turnos: list[dict[str, Any]],
    servicios: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Calcula ingresos y rentabilidad por servicio.

    Args:
        turnos: Lista de turnos facturables.
        servicios: Dict {servicio_id: {nombre, precio, duracion_minutos}}.

    Returns:
        Lista de dicts [{nombre, cantidad, ingresos, precio_promedio}].
    """
    from config.constants import APPOINTMENT_STATES_BILLABLE

    revenue_map: dict[str, dict[str, Any]] = {}

    for t in turnos:
        if t.get("estado") not in APPOINTMENT_STATES_BILLABLE:
            continue
        sid = t.get("servicio_id", "")
        svc = servicios.get(sid, {})
        precio = float(svc.get("precio", 0))

        if sid not in revenue_map:
            revenue_map[sid] = {
                "nombre": svc.get("nombre", sid),
                "cantidad": 0,
                "ingresos": 0.0,
            }
        revenue_map[sid]["cantidad"] += 1
        revenue_map[sid]["ingresos"] += precio

    result = []
    for data in revenue_map.values():
        data["ingresos"] = round(data["ingresos"], 2)
        data["precio_promedio"] = (
            round(data["ingresos"] / data["cantidad"], 2)
            if data["cantidad"] > 0
            else 0.0
        )
        result.append(data)

    return sorted(result, key=lambda x: x["ingresos"], reverse=True)
