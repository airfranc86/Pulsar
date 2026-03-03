"""
Pulsar v1.0 — Notification Services
======================================
Envío de notificaciones al usuario (email, futuro: WhatsApp).
Actualmente: confirmaciones de turno vía email.

No usa queue real en v1.0. Best-effort, no bloquea el flujo principal.
"""

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


def notify_appointment_confirmation(
    to_email: str,
    client_name: str,
    service_name: str,
    fecha: str,
    hora: str,
    tenant_name: str,
) -> bool:
    """
    Envía confirmación de turno al cliente vía email.

    Args:
        to_email: Email del cliente.
        client_name: Nombre completo del cliente.
        service_name: Nombre del servicio agendado.
        fecha: Fecha del turno en formato legible.
        hora: Hora del turno.
        tenant_name: Nombre del negocio.

    Returns:
        True si el email fue enviado, False si falló (best-effort).
    """
    from config.settings import settings

    if not settings.app.sendgrid_api_key:
        logger.warning("notification_sendgrid_not_configured")
        return False

    try:
        import sendgrid  # type: ignore
        from sendgrid.helpers.mail import Mail  # type: ignore

        sg = sendgrid.SendGridAPIClient(api_key=settings.app.sendgrid_api_key)
        message = Mail(
            from_email=settings.app.report_email_from,
            to_emails=to_email,
            subject=f"Confirmación de turno — {tenant_name}",
            html_content=f"""
            <h2>Tu turno está confirmado</h2>
            <p>Hola <strong>{client_name}</strong>,</p>
            <p>Tu turno de <strong>{service_name}</strong> fue confirmado:</p>
            <ul>
                <li><strong>Fecha:</strong> {fecha}</li>
                <li><strong>Hora:</strong> {hora}</li>
                <li><strong>Negocio:</strong> {tenant_name}</li>
            </ul>
            <p style="color:#888;font-size:12px;">Pulsar v1.0</p>
            """,
        )
        sg.send(message)
        logger.info(
            "appointment_confirmation_sent",
            extra={"to_email": to_email, "service": service_name},
        )
        return True
    except Exception as exc:
        logger.error(
            "appointment_confirmation_failed",
            extra={"to_email": to_email, "error": str(exc)},
        )
        return False


def notify_upgrade_required(
    to_email: str,
    tenant_name: str,
    base_url: str,
) -> bool:
    """
    Envía recordatorio de upgrade a un tenant en demo mode.
    Best-effort. No bloquea.
    """
    from config.settings import settings

    if not settings.app.sendgrid_api_key:
        return False

    try:
        import sendgrid  # type: ignore
        from sendgrid.helpers.mail import Mail  # type: ignore

        sg = sendgrid.SendGridAPIClient(api_key=settings.app.sendgrid_api_key)
        message = Mail(
            from_email=settings.app.report_email_from,
            to_emails=to_email,
            subject=f"Activá tu cuenta de Pulsar — {tenant_name}",
            html_content=f"""
            <h2>Tu período de prueba está activo</h2>
            <p>Para acceder a todas las funciones de Pulsar,
            <a href="{base_url}/upgrade">activá tu suscripción mensual</a>.</p>
            <p style="color:#888;font-size:12px;">Pulsar v1.0</p>
            """,
        )
        sg.send(message)
        logger.info("upgrade_notification_sent", extra={"to_email": to_email})
        return True
    except Exception as exc:
        logger.error(
            "upgrade_notification_failed",
            extra={"to_email": to_email, "error": str(exc)},
        )
        return False
