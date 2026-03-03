"""
services/payment_services.py
=============================
Lógica de negocio de pagos y suscripciones para Pulsar v1.0.

Orquesta: Stripe → Supabase → Estado de suscripción.
El webhook handler vive en integrations/stripe_client.py;
este servicio procesa el resultado ya validado.
"""
from __future__ import annotations
import logging
from datetime import datetime
from typing import Any, Optional

from core.database import get_anon_client, get_service_client
from core.crud import update_tenant_subscription, get_tenant
from core.database import assert_tenant as require_tenant
from integrations.stripe_client import StripeClient

logger = logging.getLogger(__name__)


class PaymentServiceError(Exception):
    """Error en operaciones de pago."""


def create_checkout_session(tenant_id: str, user_email: str) -> str:
    """
    Crea una sesión de Stripe Checkout para el tenant.

    Args:
        tenant_id: UUID del tenant que quiere suscribirse.
        user_email: Email del usuario para pre-llenado en Stripe.

    Returns:
        str: URL de la sesión de Checkout para redirigir al usuario.

    Raises:
        PaymentServiceError: Si no se pudo crear la sesión.
    """
    tid = require_tenant(tenant_id)
    try:
        stripe = StripeClient()
        session_url = stripe.create_checkout_session(
            tenant_id=tid,
            customer_email=user_email,
        )
        logger.info(
            "checkout_session_created",
            extra={"event": "checkout_created", "tenant_id": tid}
        )
        return session_url
    except Exception as exc:
        logger.error(
            "checkout_session_failed",
            extra={"tenant_id": tid, "error": str(exc)}
        )
        raise PaymentServiceError(f"Error creando sesión de pago: {exc}") from exc


def process_subscription_activated(
    tenant_id: str,
    stripe_subscription_id: str,
    stripe_customer_id: str,
    current_period_end: datetime,
) -> bool:
    """
    Procesa la activación de suscripción luego de checkout exitoso.
    Llamado desde el handler de webhook Stripe.

    Args:
        tenant_id: UUID del tenant.
        stripe_subscription_id: ID de suscripción en Stripe.
        stripe_customer_id: ID de cliente en Stripe.
        current_period_end: Fecha de vencimiento del período.

    Returns:
        bool: True si la actualización fue exitosa.
    """
    tid = require_tenant(tenant_id)
    try:
        db = get_service_client()  # bypass RLS para escritura de servidor

        # Actualizar suscripción
        success = update_tenant_subscription(
            db=db,
            tenant_id=tid,
            subscription_status="active",
            stripe_subscription_id=stripe_subscription_id,
            current_period_end=current_period_end,
        )

        # También guardar stripe_customer_id
        db.table("tenants").update(
            {"stripe_customer_id": stripe_customer_id}
        ).eq("id", tid).execute()

        logger.info(
            "subscription_activated",
            extra={"event": "subscription_activated", "tenant_id": tid}
        )
        return success
    except Exception as exc:
        logger.error(
            "process_subscription_activated_failed",
            extra={"tenant_id": tid, "error": str(exc)}
        )
        return False


def process_subscription_cancelled(
    tenant_id: str,
    stripe_subscription_id: str,
) -> bool:
    """
    Procesa la cancelación de suscripción.

    Args:
        tenant_id: UUID del tenant.
        stripe_subscription_id: ID de la suscripción en Stripe.

    Returns:
        bool: True si fue exitoso.
    """
    tid = require_tenant(tenant_id)
    try:
        db = get_service_client()
        success = update_tenant_subscription(
            db=db,
            tenant_id=tid,
            subscription_status="canceled",
            stripe_subscription_id=stripe_subscription_id,
            current_period_end=datetime.utcnow(),
        )
        logger.info(
            "subscription_cancelled",
            extra={"event": "subscription_cancelled", "tenant_id": tid}
        )
        return success
    except Exception as exc:
        logger.error(
            "process_subscription_cancelled_failed",
            extra={"tenant_id": tid, "error": str(exc)}
        )
        return False


def get_subscription_status(tenant_id: str) -> dict[str, Any]:
    """
    Obtiene el estado completo de suscripción del tenant.

    Args:
        tenant_id: UUID del tenant.

    Returns:
        dict con subscription_status, current_period_end, is_active.
    """
    tid = require_tenant(tenant_id)
    db = get_anon_client()
    tenant = get_tenant(db, tid)

    if not tenant:
        return {
            "subscription_status": "inactive",
            "current_period_end": None,
            "is_active": False,
        }

    from config.constants import ACTIVE_SUBSCRIPTION_STATES
    status = tenant.get("subscription_status", "inactive")

    return {
        "subscription_status": status,
        "current_period_end": tenant.get("current_period_end"),
        "stripe_customer_id": tenant.get("stripe_customer_id"),
        "is_active": status in ACTIVE_SUBSCRIPTION_STATES,
    }
