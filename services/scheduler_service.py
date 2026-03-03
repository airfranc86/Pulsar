"""
Pulsar v1.0 — Scheduler Service
=================================
Lógica de negocio para el reporte mensual automático.
Orquesta: KPI computation → PDF generation → Storage → Email → History.

Este módulo es llamado desde:
  1. Supabase pg_cron (production) — función SQL que invoca Edge Function
  2. CLI manual (testing / re-run)
  3. Page 07_Insights.py (trigger manual desde UI, solo FULL_MODE)

Nunca se llama directamente desde el frontend con datos de usuario.
"""

import logging
from datetime import date, datetime
from typing import Any, Optional

from config.constants import (
    REPORT_STORAGE_BUCKET,
    TABLE_REPORT_HISTORY,
)
from core.crud import (
    create_report_history_entry,
    list_report_history,
)
from core.database import DatabaseError, get_admin_client, assert_tenant

logger = logging.getLogger(__name__)


def run_monthly_report_for_tenant(
    tenant_id: str,
    *,
    period: Optional[date] = None,
    force: bool = False,
) -> dict[str, Any]:
    """
    Ejecuta el ciclo completo del reporte mensual para un tenant.

    Flujo:
      1. Verificar que el tenant tiene suscripción activa
      2. Verificar que no existe reporte para el período (idempotente)
      3. Calcular KPIs del período
      4. Generar PDF
      5. Subir PDF a Supabase Storage
      6. Enviar email
      7. Registrar en historial

    Args:
        tenant_id: UUID del tenant.
        period: Fecha del período (usa primer día del mes anterior si None).
        force: Si True, regenera aunque ya exista para el período.

    Returns:
        Dict con resultado de la operación.

    Raises:
        ValueError: Si el tenant no tiene suscripción activa.
        RuntimeError: Si algún paso falla.
    """
    tenant_id = assert_tenant(tenant_id)

    if period is None:
        today = date.today()
        # Mes anterior
        if today.month == 1:
            period = date(today.year - 1, 12, 1)
        else:
            period = date(today.year, today.month - 1, 1)

    period_label = period.strftime("%Y-%m")

    logger.info(
        "monthly_report_started",
        extra={"tenant_id": tenant_id, "period_label": period_label, "force": force},
    )

    db = get_admin_client()

    # ── Verificar suscripción ─────────────────────────────────────────────────
    tenant_data = _get_tenant_or_raise(db, tenant_id)
    if not _is_active(tenant_data) and not force:
        raise ValueError(
            f"Tenant {tenant_id} no tiene suscripción activa. Reporte no generado."
        )

    # ── Idempotencia ──────────────────────────────────────────────────────────
    if not force and _report_exists(db, tenant_id, period_label):
        logger.info(
            "monthly_report_already_exists",
            extra={"tenant_id": tenant_id, "period_label": period_label},
        )
        return {
            "status": "skipped",
            "reason": "report_already_exists",
            "period_label": period_label,
        }

    # ── Calcular KPIs ─────────────────────────────────────────────────────────
    kpi_data = _compute_period_kpis(db, tenant_id, period)

    # ── Generar PDF ───────────────────────────────────────────────────────────
    pdf_bytes = _generate_pdf_report(tenant_data, kpi_data, period_label)

    # ── Subir a Storage ───────────────────────────────────────────────────────
    storage_path = _upload_to_storage(db, tenant_id, period_label, pdf_bytes)

    # ── Enviar Email ──────────────────────────────────────────────────────────
    report_email = tenant_data.get("report_email")
    sent_at: Optional[str] = None
    if report_email:
        _send_report_email(report_email, tenant_data, period_label, storage_path)
        sent_at = datetime.utcnow().isoformat()

    # ── Registrar en historial ────────────────────────────────────────────────
    create_report_history_entry(
        db,
        tenant_id,
        {
            "period_label": period_label,
            "storage_path": storage_path,
            "sent_to_email": report_email,
            "sent_at": sent_at,
        },
    )

    logger.info(
        "monthly_report_completed",
        extra={
            "tenant_id": tenant_id,
            "period_label": period_label,
            "storage_path": storage_path,
            "email_sent": bool(sent_at),
        },
    )

    return {
        "status": "success",
        "period_label": period_label,
        "storage_path": storage_path,
        "email_sent": bool(sent_at),
    }


# ─── Helpers privados ─────────────────────────────────────────────────────────

def _get_tenant_or_raise(db: Any, tenant_id: str) -> dict[str, Any]:
    """Obtiene datos del tenant o lanza RuntimeError."""
    from core.crud import get_tenant

    tenant = get_tenant(db, tenant_id)
    if not tenant:
        raise RuntimeError(f"Tenant no encontrado: {tenant_id}")
    return tenant


def _is_active(tenant: dict[str, Any]) -> bool:
    """Evalúa si la suscripción está activa."""
    from core.permisos import is_subscription_active
    return is_subscription_active(tenant)


def _report_exists(db: Any, tenant_id: str, period_label: str) -> bool:
    """Verifica si ya existe un reporte para el período."""
    try:
        history = list_report_history(db, tenant_id, limit=24)
        return any(r.get("period_label") == period_label for r in history)
    except DatabaseError:
        return False


def _compute_period_kpis(db: Any, tenant_id: str, period: date) -> dict[str, Any]:
    """
    Calcula KPIs del período.
    Delega a analytics layer. db es el cliente con service_role (solo scheduler).
    """
    from analytics.revenue_metrics import compute_period_revenue
    from analytics.retention_metrics import compute_retention_metrics

    period_end = _last_day_of_month(period)

    revenue_data = compute_period_revenue(db, tenant_id, period, period_end)
    retention_data = compute_retention_metrics(db, tenant_id, period, period_end)

    return {**revenue_data, **retention_data}


def _generate_pdf_report(
    tenant: dict[str, Any],
    kpi_data: dict[str, Any],
    period_label: str,
) -> bytes:
    """
    Genera el PDF del reporte mensual.
    Usa reportlab para generación server-side sin dependencias de browser.
    """
    try:
        from io import BytesIO
        from reportlab.lib.pagesizes import A4  # type: ignore
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle  # type: ignore
        from reportlab.lib.units import cm  # type: ignore
        from reportlab.lib import colors  # type: ignore
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle  # type: ignore

        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=2 * cm,
            rightMargin=2 * cm,
            topMargin=2 * cm,
            bottomMargin=2 * cm,
        )

        styles = getSampleStyleSheet()
        story = []

        tenant_name = tenant.get("name", "Negocio")
        story.append(Paragraph(f"Pulsar — Reporte Mensual", styles["Heading1"]))
        story.append(Paragraph(f"{tenant_name} | Período: {period_label}", styles["Heading2"]))
        story.append(Spacer(1, 0.5 * cm))

        kpi_rows = [
            ["KPI", "Valor"],
            ["Ingresos del Período", f"$ {kpi_data.get('ingresos_mensuales', 0):,.2f}"],
            ["Ticket Promedio", f"$ {kpi_data.get('ticket_promedio', 0):,.2f}"],
            ["Total Turnos", str(kpi_data.get('total_turnos', 0))],
            ["Ocupación", f"{kpi_data.get('ocupacion_turnos', 0) * 100:.1f}%"],
            ["Clientes Nuevos", str(kpi_data.get('clientes_nuevos', 0))],
            ["Clientes Recurrentes", str(kpi_data.get('clientes_recurrentes', 0))],
            ["Cancelaciones", str(kpi_data.get('cancelaciones', 0))],
            ["No-Shows", str(kpi_data.get('no_shows', 0))],
        ]

        table = Table(kpi_rows, colWidths=[10 * cm, 5 * cm])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a1a2e")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f5f5")]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
            ("PADDING", (0, 0), (-1, -1), 8),
        ]))

        story.append(table)
        story.append(Spacer(1, cm))
        story.append(Paragraph(
            f"Reporte generado automáticamente el {datetime.utcnow().strftime('%d/%m/%Y %H:%M')} UTC — Pulsar v1.0",
            styles["Italic"],
        ))

        doc.build(story)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes

    except ImportError as exc:
        logger.error("reportlab_not_installed", extra={"error": str(exc)})
        raise RuntimeError("reportlab no está instalado. Agregar a requirements.txt.") from exc
    except Exception as exc:
        logger.error("pdf_generation_failed", extra={"error": str(exc)})
        raise RuntimeError(f"Error al generar PDF: {exc}") from exc


def _upload_to_storage(
    db: Any,
    tenant_id: str,
    period_label: str,
    pdf_bytes: bytes,
) -> str:
    """
    Sube el PDF a Supabase Storage.
    Path: monthly-reports/{tenant_id}/{period_label}.pdf
    """
    path = f"{tenant_id}/{period_label}.pdf"
    try:
        db.storage.from_(REPORT_STORAGE_BUCKET).upload(
            path=path,
            file=pdf_bytes,
            file_options={"content-type": "application/pdf", "upsert": "true"},
        )
        logger.info(
            "report_uploaded_to_storage",
            extra={"tenant_id": tenant_id, "path": path},
        )
        return path
    except Exception as exc:
        logger.error(
            "storage_upload_failed",
            extra={"tenant_id": tenant_id, "path": path, "error": str(exc)},
        )
        raise RuntimeError(f"Error al subir reporte a Storage: {exc}") from exc


def _send_report_email(
    to_email: str,
    tenant: dict[str, Any],
    period_label: str,
    storage_path: str,
) -> None:
    """
    Envía el reporte por email vía SendGrid.
    """
    from config.settings import settings

    if not settings.app.sendgrid_api_key:
        logger.warning(
            "sendgrid_not_configured",
            extra={"tenant_id": tenant.get("id")},
        )
        return

    try:
        import sendgrid  # type: ignore
        from sendgrid.helpers.mail import Mail  # type: ignore

        sg = sendgrid.SendGridAPIClient(api_key=settings.app.sendgrid_api_key)
        tenant_name = tenant.get("name", "Negocio")

        message = Mail(
            from_email=settings.app.report_email_from,
            to_emails=to_email,
            subject=f"[Pulsar] Reporte Mensual {period_label} — {tenant_name}",
            html_content=f"""
            <h2>Reporte Mensual — {tenant_name}</h2>
            <p>Tu reporte mensual de <strong>{period_label}</strong> ya está disponible.</p>
            <p>Ingresá al panel para descargarlo: {settings.app.base_url}</p>
            <p style="color:#888;font-size:12px;">
                Enviado automáticamente por Pulsar v1.0
            </p>
            """,
        )
        sg.send(message)
        logger.info(
            "report_email_sent",
            extra={"tenant_id": tenant.get("id"), "to_email": to_email},
        )
    except Exception as exc:
        logger.error(
            "report_email_failed",
            extra={"tenant_id": tenant.get("id"), "error": str(exc)},
        )
        # No relanzar: email es best-effort, no bloquea el reporte


def _last_day_of_month(first_day: date) -> date:
    """Retorna el último día del mes dado el primer día."""
    import calendar
    last_day = calendar.monthrange(first_day.year, first_day.month)[1]
    return date(first_day.year, first_day.month, last_day)
