"""
Pulsar v1.0 — Settings
========================
Fuente única de verdad para configuración de entorno.
Todos los secrets y variables de entorno se leen aquí.
Ningún otro módulo debe llamar os.getenv() directamente.

Seguridad:
- Falla rápido (fail-fast) si variables críticas no están definidas
- Nunca loggea valores de secrets
- Compatible con Streamlit Secrets y variables de entorno estándar
"""

import logging
import os
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


def _require(key: str) -> str:
    """
    Lee una variable de entorno obligatoria.
    Lanza ValueError con mensaje claro si no existe.
    """
    value = os.getenv(key) or _from_streamlit_secrets(key)
    if not value:
        raise ValueError(
            f"Variable de entorno obligatoria no definida: '{key}'. "
            "Revisar .env o Streamlit Secrets."
        )
    return value


def _optional(key: str, default: str = "") -> str:
    """Lee una variable de entorno opcional con valor por defecto."""
    return os.getenv(key) or _from_streamlit_secrets(key) or default


def _from_streamlit_secrets(key: str) -> Optional[str]:
    """
    Intenta leer desde st.secrets si Streamlit está disponible.
    Retorna None si Streamlit no está en contexto o la clave no existe.
    """
    try:
        import streamlit as st  # type: ignore
        return str(st.secrets.get(key, "")) or None
    except Exception:
        return None


@dataclass(frozen=True)
class SupabaseSettings:
    url: str
    anon_key: str
    service_role_key: str


@dataclass(frozen=True)
class StripeSettings:
    secret_key: str
    publishable_key: str
    webhook_secret: str
    price_id: str
    success_url: str
    cancel_url: str


@dataclass(frozen=True)
class AnthropicSettings:
    api_key: str


@dataclass(frozen=True)
class AppSettings:
    env: str
    demo_mode: bool
    base_url: str
    report_email_from: str
    sendgrid_api_key: str


@dataclass(frozen=True)
class Settings:
    """
    Configuración global de Pulsar v1.0. Instancia única, inmutable.
    """
    supabase: SupabaseSettings
    stripe: StripeSettings
    anthropic: AnthropicSettings
    app: AppSettings
    use_supabase: bool

    @property
    def is_production(self) -> bool:
        return self.app.env == "production"

    @property
    def is_demo_mode(self) -> bool:
        return self.app.demo_mode


def _load_settings() -> Settings:
    # Supabase: opcional. Si USE_SUPABASE=false o no hay SUPABASE_URL, se desactiva.
    use_supabase_env = (_optional("USE_SUPABASE", "true").strip().lower() == "true")
    supabase_url = _optional("SUPABASE_URL", "")
    use_supabase = use_supabase_env and bool(supabase_url)
    supabase = SupabaseSettings(
        url=supabase_url or "",
        anon_key=_optional("SUPABASE_ANON_KEY", ""),
        service_role_key=_optional("SUPABASE_SERVICE_ROLE_KEY", ""),
    )
    stripe = StripeSettings(
        secret_key=_optional("STRIPE_SECRET_KEY", ""),
        publishable_key=_optional("STRIPE_PUBLISHABLE_KEY", ""),
        webhook_secret=_optional("STRIPE_WEBHOOK_SECRET", ""),
        price_id=_optional("STRIPE_PRICE_ID", ""),
        success_url=_optional("STRIPE_SUCCESS_URL", "https://app.pulsar.com/success"),
        cancel_url=_optional("STRIPE_CANCEL_URL", "https://app.pulsar.com/upgrade"),
    )
    anthropic = AnthropicSettings(
        api_key=_optional("ANTHROPIC_API_KEY", ""),
    )
    app = AppSettings(
        env=_optional("APP_ENV", "development"),
        demo_mode=_optional("DEMO_MODE", "false").lower() == "true",
        base_url=_optional("APP_BASE_URL", "http://localhost:8501"),
        report_email_from=_optional("REPORT_EMAIL_FROM", "noreply@pulsar.com"),
        sendgrid_api_key=_optional("SENDGRID_API_KEY", ""),
    )
    logger.info(
        "settings_loaded",
        extra={"env": app.env, "demo_mode": app.demo_mode, "use_supabase": use_supabase},
    )
    return Settings(
        supabase=supabase,
        stripe=stripe,
        anthropic=anthropic,
        app=app,
        use_supabase=use_supabase,
    )


try:
    settings: Settings = _load_settings()
except ValueError as exc:
    logger.critical("settings_load_failed", extra={"error": str(exc)})
    raise
