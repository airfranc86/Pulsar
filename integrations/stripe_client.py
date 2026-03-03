"""
Pulsar v1.0 — Stripe Client
==============================
Wrapper de bajo nivel sobre la SDK de Stripe.
Solo expone las operaciones necesarias para v1.0.
Toda lógica de negocio vive en services/payment_services.py.

Este módulo:
  - Configura el cliente Stripe con la key correcta
  - Provee funciones tipadas para crear sessions y gestionar customers
  - Maneja StripeError y lo convierte en excepciones de dominio
  - NUNCA es llamado desde el frontend directamente
"""

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


class StripeClientError(Exception):
    """Error de integración con Stripe. Wrappea stripe.StripeError."""
    pass


def _get_stripe():
    """
    Importa y configura stripe con la secret key.
    Importación lazy para no fallar en contextos sin stripe instalado.
    """
    try:
        import stripe  # type: ignore
    except ImportError as exc:
        raise StripeClientError(
            "stripe no está instalado. Agregar 'stripe' a requirements.txt."
        ) from exc

    from config.settings import settings
    stripe.api_key = settings.stripe.secret_key
    return stripe


def create_checkout_session(
    price_id: str,
    tenant_id: str,
    success_url: str,
    cancel_url: str,
    *,
    customer_id: Optional[str] = None,
    customer_email: Optional[str] = None,
) -> dict[str, str]:
    """
    Crea una Stripe Checkout Session para suscripción mensual.

    Args:
        price_id: Stripe Price ID del plan.
        tenant_id: UUID del tenant (guardado en metadata).
        success_url: URL de redirección en caso de éxito.
        cancel_url: URL de redirección si el usuario cancela.
        customer_id: ID de customer existente en Stripe (opcional).
        customer_email: Email para pre-llenar el checkout (opcional).

    Returns:
        Dict con 'id' (session_id) y 'url' (checkout_url).

    Raises:
        StripeClientError: Si la API de Stripe retorna error.
    """
    stripe = _get_stripe()

    params: dict[str, Any] = {
        "mode": "subscription",
        "line_items": [{"price": price_id, "quantity": 1}],
        "success_url": success_url,
        "cancel_url": cancel_url,
        "metadata": {"tenant_id": tenant_id},
        "subscription_data": {"metadata": {"tenant_id": tenant_id}},
        "allow_promotion_codes": True,
    }

    if customer_id:
        params["customer"] = customer_id
    elif customer_email:
        params["customer_email"] = customer_email

    try:
        session = stripe.checkout.Session.create(**params)
        logger.info(
            "stripe_checkout_session_created",
            extra={
                "session_id": session.id,
                "tenant_id": tenant_id,
            },
        )
        return {"id": session.id, "url": session.url}
    except Exception as exc:  # stripe.error.StripeError
        logger.error(
            "stripe_checkout_session_error",
            extra={"tenant_id": tenant_id, "error": str(exc)},
        )
        raise StripeClientError(f"Error de Stripe al crear sesión: {exc}") from exc


def construct_webhook_event(
    payload: bytes,
    sig_header: str,
    webhook_secret: str,
) -> dict[str, Any]:
    """
    Verifica y construye un evento de Stripe Webhook.

    Args:
        payload: Body raw del request HTTP (bytes).
        sig_header: Valor del header 'Stripe-Signature'.
        webhook_secret: Stripe webhook signing secret.

    Returns:
        Evento de Stripe como dict.

    Raises:
        StripeClientError: Si la firma es inválida o el payload malformado.
    """
    stripe = _get_stripe()

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
        logger.debug(
            "stripe_webhook_event_constructed",
            extra={"event_type": event.get("type")},
        )
        return dict(event)
    except Exception as exc:
        logger.warning(
            "stripe_webhook_verification_failed",
            extra={"error": str(exc)},
        )
        raise StripeClientError(f"Webhook inválido: {exc}") from exc


def get_subscription(subscription_id: str) -> Optional[dict[str, Any]]:
    """
    Obtiene los datos de una suscripción de Stripe por ID.

    Args:
        subscription_id: Stripe Subscription ID.

    Returns:
        Dict con datos de la suscripción, o None si no existe.
    """
    stripe = _get_stripe()

    try:
        sub = stripe.Subscription.retrieve(subscription_id)
        return dict(sub)
    except Exception as exc:
        logger.error(
            "stripe_get_subscription_failed",
            extra={"subscription_id": subscription_id, "error": str(exc)},
        )
        return None


def cancel_subscription(subscription_id: str, *, at_period_end: bool = True) -> bool:
    """
    Cancela una suscripción de Stripe.

    Args:
        subscription_id: ID de la suscripción a cancelar.
        at_period_end: Si True, cancela al final del período actual.

    Returns:
        True si la cancelación fue exitosa.
    """
    stripe = _get_stripe()

    try:
        if at_period_end:
            stripe.Subscription.modify(
                subscription_id,
                cancel_at_period_end=True,
            )
        else:
            stripe.Subscription.cancel(subscription_id)

        logger.info(
            "stripe_subscription_cancelled",
            extra={
                "subscription_id": subscription_id,
                "at_period_end": at_period_end,
            },
        )
        return True
    except Exception as exc:
        logger.error(
            "stripe_cancel_subscription_failed",
            extra={"subscription_id": subscription_id, "error": str(exc)},
        )
        return False
