"""
Pulsar v1.0 — Export Services
================================
Generación de archivos exportables desde datos del dashboard.
Disponible solo en FULL_MODE.

Formatos soportados:
  - CSV (siempre disponible vía pandas)
  - Excel (.xlsx via openpyxl)
  - PDF de KPI snapshot (via reportlab)

Nunca persiste archivos en disco del servidor.
Siempre retorna bytes para enviar al browser.
"""

import logging
from datetime import date
from io import BytesIO
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)


def export_to_csv(data: list[dict[str, Any]], filename_hint: str = "export") -> bytes:
    """
    Exporta una lista de dicts a CSV.

    Args:
        data: Lista de registros a exportar.
        filename_hint: Sugerencia para nombre de archivo (no usada en bytes).

    Returns:
        Bytes del CSV con BOM UTF-8 para compatibilidad con Excel.

    Raises:
        ValueError: Si data está vacío.
    """
    if not data:
        raise ValueError("No hay datos para exportar.")

    try:
        df = pd.DataFrame(data)
        buffer = BytesIO()
        df.to_csv(buffer, index=False, encoding="utf-8-sig")
        csv_bytes = buffer.getvalue()
        logger.info(
            "csv_export_generated",
            extra={"rows": len(data), "columns": len(df.columns)},
        )
        return csv_bytes
    except Exception as exc:
        logger.error("csv_export_failed", extra={"error": str(exc)})
        raise RuntimeError(f"Error al generar CSV: {exc}") from exc


def export_to_excel(
    data: list[dict[str, Any]],
    sheet_name: str = "Datos",
) -> bytes:
    """
    Exporta una lista de dicts a Excel (.xlsx).

    Args:
        data: Lista de registros.
        sheet_name: Nombre de la hoja.

    Returns:
        Bytes del archivo Excel.

    Raises:
        ValueError: Si data está vacío.
        RuntimeError: Si openpyxl no está instalado.
    """
    if not data:
        raise ValueError("No hay datos para exportar.")

    try:
        df = pd.DataFrame(data)
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name=sheet_name[:31])

            # Autoajuste de columnas
            worksheet = writer.sheets[sheet_name[:31]]
            for col_cells in worksheet.columns:
                max_len = max(
                    len(str(cell.value)) if cell.value else 0
                    for cell in col_cells
                )
                col_letter = col_cells[0].column_letter
                worksheet.column_dimensions[col_letter].width = min(max_len + 4, 50)

        excel_bytes = buffer.getvalue()
        logger.info(
            "excel_export_generated",
            extra={"rows": len(data), "sheet": sheet_name},
        )
        return excel_bytes
    except ImportError as exc:
        raise RuntimeError("openpyxl no está instalado. Agregar a requirements.txt.") from exc
    except Exception as exc:
        logger.error("excel_export_failed", extra={"error": str(exc)})
        raise RuntimeError(f"Error al generar Excel: {exc}") from exc


def get_export_filename(
    prefix: str,
    tenant_slug: str,
    fmt: str,
    period: date | None = None,
) -> str:
    """
    Genera un nombre de archivo normalizado para exports.

    Args:
        prefix: Prefijo descriptivo (ej: "turnos", "clientes").
        tenant_slug: Slug del tenant.
        fmt: Extensión sin punto (ej: "csv", "xlsx").
        period: Fecha del período (opcional).

    Returns:
        Nombre de archivo con timestamp.
    """
    from datetime import datetime
    ts = period.strftime("%Y%m") if period else datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    return f"pulsar_{tenant_slug}_{prefix}_{ts}.{fmt}"
