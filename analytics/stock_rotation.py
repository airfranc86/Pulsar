"""
Pulsar v1.0 — Stock / Inventory Analytics
===========================================
Métricas de rotación para negocios con productos (ej: peluquerías con productos,
talleres con repuestos). Scope v1.0: placeholder documentado.
Activo en v1.1 cuando se agregue tabla de inventario.
"""

import logging

logger = logging.getLogger(__name__)


def compute_stock_rotation_placeholder() -> dict[str, str]:
    """
    Retorna un indicador de que stock analytics no está activo en v1.0.
    Evita NotImplementedError — retorna data estructurada vacía.
    """
    logger.info("stock_rotation_not_active_v1")
    return {
        "status": "not_active",
        "version": "v1.1",
        "message": "Rotación de stock disponible en v1.1 con tabla de inventario.",
    }
