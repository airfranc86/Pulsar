"""
Pulsar v1.0 — ARCA Client (ex AFIP)
======================================
Integración con ARCA (Agencia de Recaudación y Control Aduanero) de Argentina.
Scope v1.0: solo consulta de CUIT para validación de clientes.
Facturación electrónica no está en scope del MVP.

Este módulo existe como placeholder documentado para v1.1.
"""

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


class ARCAClientError(Exception):
    """Error de integración con ARCA/AFIP."""
    pass


def validate_cuit(cuit: str) -> bool:
    """
    Valida formato y dígito verificador de un CUIT argentino.
    Validación local (no requiere API externa).

    Args:
        cuit: CUIT con o sin guiones (ej: "20-12345678-9" o "20123456789").

    Returns:
        True si el CUIT es válido.
    """
    cuit_clean = cuit.replace("-", "").replace(" ", "")

    if len(cuit_clean) != 11 or not cuit_clean.isdigit():
        return False

    weights = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]
    digits = [int(d) for d in cuit_clean]
    total = sum(d * w for d, w in zip(digits[:10], weights))
    remainder = total % 11
    check_digit = 0 if remainder == 0 else (11 - remainder)

    if check_digit == 10:
        return False  # CUIT inválido

    return digits[10] == check_digit


def format_cuit(cuit: str) -> str:
    """
    Formatea un CUIT al formato estándar XX-XXXXXXXX-X.

    Args:
        cuit: CUIT en cualquier formato.

    Returns:
        CUIT formateado.

    Raises:
        ValueError: Si el CUIT no tiene 11 dígitos.
    """
    cuit_clean = cuit.replace("-", "").replace(" ", "")
    if len(cuit_clean) != 11:
        raise ValueError(f"CUIT inválido: {cuit}")
    return f"{cuit_clean[:2]}-{cuit_clean[2:10]}-{cuit_clean[10]}"
