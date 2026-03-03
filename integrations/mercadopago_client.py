"""
Pulsar v1.0 — MercadoPago Client
===================================
Integración con MercadoPago para mercados LATAM donde Stripe no está disponible.
Scope v1.0: solo consulta de preferencias y webhook básico.
No activo por defecto. Habilitado vía variable APP_PAYMENT_PROVIDER=mercadopago.

Nota: Pulsar usa Stripe como provider principal.
MercadoPago es fallback para tenants en Argentina/LatAm sin tarjeta internacional.
"""

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


class MercadoPagoClientError(Exception):
    """Error de integración con MercadoPago."""
    pass


def _get_mp():
    """Importa y configura el SDK de MercadoPago."""
    try:
        import mercadopago  # type: ignore
    except ImportError as exc:
        raise MercadoPagoClientError(
            "mercadopago SDK no instalado. Agregar 'mercadopago' a requirements.txt."
        ) from exc

    from config.settings import settings
    sdk = mercadopago.SDK(settings.stripe.secret_key)  # Reutiliza config; ajustar si se activa
    return sdk


def create_preference(
    tenant_id: str,
    title: str,
    unit_price: float,
    back_url_success: str,
    back_url_failure: str,
    payer_email: Optional[str] = None,
) -> dict[str, Any]:
    """
    Crea una preferencia de pago en MercadoPago.

    Args:
        tenant_id: UUID del tenant.
        title: Descripción del item.
        unit_price: Precio en moneda local.
        back_url_success: URL de retorno exitoso.
        back_url_failure: URL de retorno fallido.
        payer_email: Email del pagador (opcional).

    Returns:
        Dict con 'id' y 'init_point' (URL de checkout).

    Raises:
        MercadoPagoClientError: Si la API retorna error.
    """
    sdk = _get_mp()

    preference_data: dict[str, Any] = {
        "items": [
            {
                "title": title,
                "quantity": 1,
                "unit_price": float(unit_price),
            }
        ],
        "back_urls": {
            "success": back_url_success,
            "failure": back_url_failure,
        },
        "auto_return": "approved",
        "external_reference": tenant_id,
    }

    if payer_email:
        preference_data["payer"] = {"email": payer_email}

    try:
        response = sdk.preference().create(preference_data)
        if response["status"] not in (200, 201):
            raise MercadoPagoClientError(
                f"MercadoPago rechazó la preferencia: {response}"
            )
        data = response["response"]
        logger.info(
            "mercadopago_preference_created",
            extra={"tenant_id": tenant_id, "preference_id": data.get("id")},
        )
        return {"id": data["id"], "init_point": data["init_point"]}
    except MercadoPagoClientError:
        raise
    except Exception as exc:
        logger.error(
            "mercadopago_preference_error",
            extra={"tenant_id": tenant_id, "error": str(exc)},
        )
        raise MercadoPagoClientError(f"Error de MercadoPago: {exc}") from exc
