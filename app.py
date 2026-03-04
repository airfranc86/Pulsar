"""
Pulsar v1.0 — Entry Point
===========================
Punto de entrada de la aplicación Streamlit multi-tenant.

Responsabilidades:
  1. Inicializar logging estructurado
  2. Cargar y validar configuración
  3. Resolver tenant activo (demo o real)
  4. Renderizar landing page / redirección al Panel

Arquitectura de sesión:
  - tenant_id se establece en st.session_state en este módulo
  - Todas las páginas lo leen de session_state
  - No se re-evalúa en cada página (single source of truth)

Multi-tenant:
  - Sin query param → carga tenant demo (DEMO_TENANT_ID)
  - Con ?tenant=slug → resuelve tenant real por slug
  - Con ?upgrade=true → redirige a upgrade page
"""

# ─── Cargar .env con tolerancia a encoding (evita utf-8 decode error en Windows) ─
import os
_env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
if os.path.isfile(_env_path):
    try:
        with open(_env_path, encoding="utf-8", errors="replace") as _f:
            for _line in _f:
                _line = _line.strip()
                if _line and not _line.startswith("#") and "=" in _line:
                    _key, _, _val = _line.partition("=")
                    _key = _key.strip()
                    if _key and _key not in os.environ:
                        os.environ[_key] = _val.strip().strip('"').strip("'")
    except OSError:
        pass

import logging

import streamlit as st

# ─── Inicializar logging ANTES de cualquier otro import ──────────────────────
from config.logging_config import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

# ─── Configuración de página ──────────────────────────────────────────────────
st.set_page_config(
    page_title="Pulsar — BusinessOps Dashboard",
    page_icon="assets/pulsar_32x32.png",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "About": "Pulsar v1.3 — BusinessOps Dashboard · Powered by Anthropic",
    },
)


def _resolve_tenant_id() -> str:
    """
    Determina el tenant_id activo para la sesión.
    Prioridad: session_state → demo tenant.

    Seguridad: ?tenant=slug solo debe resolverse en contexto autenticado (JWT).
    Mientras no haya auth en Streamlit, no se resuelve por slug para evitar
    que cualquier visitante pruebe slugs; se usa siempre DEMO_TENANT_ID si no
    hay tenant_id en session_state.
    """
    from config.constants import DEMO_TENANT_ID

    if "tenant_id" in st.session_state:
        return st.session_state["tenant_id"]

    # Resolución por slug deshabilitada hasta tener Supabase Auth en la app.
    # Cuando exista JWT en sesión, aquí se podría resolver tenant por slug
    # solo para usuarios autenticados (app_metadata.tenant_id o get_tenant_by_slug).
    # query_params = st.query_params
    # tenant_slug = query_params.get("tenant")
    # if tenant_slug and st.session_state.get("user_jwt"): ...

    st.session_state["tenant_id"] = DEMO_TENANT_ID
    logger.info("tenant_defaulted_to_demo", extra={"tenant_id": DEMO_TENANT_ID})
    return DEMO_TENANT_ID


def _check_settings() -> bool:
    """
    Verifica que la configuración mínima esté cargada.
    Con Supabase desactivado (USE_SUPABASE=false o sin SUPABASE_URL) la app arranca
    y muestra instrucciones en lugar de fallar.
    """
    try:
        from config.settings import settings  # noqa: F401
        return True
    except ValueError as exc:
        st.error(
            f"⚠️ **Error de configuración**\n\n"
            f"Faltan variables de entorno necesarias:\n\n"
            f"```\n{exc}\n```\n\n"
            f"Revisá tu `.env` o Streamlit Secrets.",
            icon="⚠️",
        )
        return False


def main() -> None:
    """
    Landing page de Pulsar.
    Resuelve tenant y muestra estado + navegación.
    """
    # ── Validar configuración ──────────────────────────────────────────────────
    if not _check_settings():
        st.stop()

    from config.settings import settings

    # ── Supabase desactivado: mostrar instrucciones y no conectar ─────────────
    if not settings.use_supabase:
        st.info(
            "⚡ **Supabase desactivado**\n\n"
            "Para usar el dashboard configurá:\n\n"
            "- **SUPABASE_URL** y **SUPABASE_ANON_KEY** en `.env` o en "
            "Streamlit Secrets (`C:\\Users\\Francisco\\.streamlit\\secrets.toml` o "
            "`.streamlit/secrets.toml` en el proyecto).\n\n"
            "Para desactivar Supabase a propósito, no hace falta definir nada; "
            "si querés forzar el modo sin backend, podés setear `USE_SUPABASE=false` en `.env`.",
            icon="⚡",
        )
        st.caption(
            "Paths válidos para secrets: "
            "C:\\Users\\Francisco\\.streamlit\\secrets.toml — "
            "D:\\Developer\\1Proyectos\\Pulsar v1.0\\.streamlit\\secrets.toml"
        )
        st.stop()

    # ── Resolver tenant ────────────────────────────────────────────────────────
    tenant_id = _resolve_tenant_id()

    # ── Handle upgrade redirect ────────────────────────────────────────────────
    if st.query_params.get("upgrade") == "true":
        st.switch_page("pages/08_Upgrade.py")

    # ── Cargar datos del tenant ────────────────────────────────────────────────
    try:
        from core.crud import get_tenant
        from core.database import DatabaseError, get_anon_client
        from core.permisos import get_access_summary, get_demo_tenant_fallback
        from config.constants import VERTICALS
    except ImportError as exc:
        if "supabase" in str(exc).lower():
            st.error(
                "⚠️ **Falta el paquete Supabase**\n\n"
                "En la carpeta del proyecto, activá el venv y ejecutá:\n\n"
                "```bash\npip install supabase\n```\n\n"
                "O instalá todas las dependencias:\n\n"
                "```bash\npip install -r requirements.txt\n```",
                icon="⚠️",
            )
        else:
            st.error(f"Error al cargar módulos: {exc}")
        st.stop()

    try:
        db = get_anon_client()
        tenant = get_tenant(db, tenant_id)
    except DatabaseError as exc:
        st.error(f"Error de conexión: {exc}")
        st.stop()

    if not tenant:
        tenant = get_demo_tenant_fallback(tenant_id)
        st.info(
            "Tenant de ejemplo (sin conexión a la base de datos). "
            "Configurá SUPABASE_URL y SUPABASE_ANON_KEY para usar datos reales.",
            icon="ℹ️",
        )

    access = get_access_summary(tenant)
    demo = access["demo_mode"]
    vertical = tenant.get("vertical", "pyme_servicios")
    vertical_labels = VERTICALS.get(vertical, VERTICALS["pyme_servicios"])

    # ── Sidebar ────────────────────────────────────────────────────────────────
    from UI.sidebar import render_sidebar
    render_sidebar(
        tenant,
        active=access["subscription_active"],
        demo_mode=demo,
        vertical_labels=vertical_labels,
    )

    # ── Contenido landing ─────────────────────────────────────────────────────
    st.image("assets/pulsar_192x192.png", width=80)
    st.title(f"Pulsar — {tenant.get('name', '')}")
    st.caption(f"BusinessOps Dashboard · {vertical_labels['label']}")

    if demo:
        st.info(
            "⚡ Estás en **Modo Demo**. "
            "Explorá el dashboard con datos reales limitados o "
            "[activá tu cuenta completa](/?upgrade=true) para acceder a todo.",
            icon="⚡",
        )
    else:
        st.success(
            "✅ Cuenta activa. Accedé a todas las secciones desde el menú lateral.",
            icon="✅",
        )

    st.divider()

    # Accesos rápidos
    cols = st.columns(4)
    quick_links = [
        ("📊 Panel", "pages/01_Panel.py"),
        ("📅 Turnos", "pages/04_Turnos.py"),
        ("👥 Clientes", "pages/02_Clientes.py"),
        ("💡 Insights", "pages/07_Insights.py"),
    ]

    for col, (label, page) in zip(cols, quick_links):
        with col:
            if st.button(label, use_container_width=True):
                st.switch_page(page)

    logger.info(
        "app_landing_rendered",
        extra={"tenant_id": tenant_id, "demo_mode": demo},
    )


main()
