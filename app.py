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

import logging

import streamlit as st

# ─── Inicializar logging ANTES de cualquier otro import ──────────────────────
from config.logging_config import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

# ─── Configuración de página ──────────────────────────────────────────────────
st.set_page_config(
    page_title="Pulsar — BusinessOps Dashboard",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "About": "Pulsar v1.0 — BusinessOps Dashboard · Powered by Anthropic",
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
    Muestra error amigable si faltan variables de entorno.

    Returns:
        True si la configuración es válida.
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

    # ── Resolver tenant ────────────────────────────────────────────────────────
    tenant_id = _resolve_tenant_id()

    # ── Handle upgrade redirect ────────────────────────────────────────────────
    if st.query_params.get("upgrade") == "true":
        st.switch_page("pages/08_Upgrade.py")

    # ── Cargar datos del tenant ────────────────────────────────────────────────
    from core.crud import get_tenant
    from core.database import DatabaseError, get_anon_client
    from core.permisos import get_access_summary
    from config.constants import VERTICALS

    try:
        db = get_anon_client()
        tenant = get_tenant(db, tenant_id)
    except DatabaseError as exc:
        st.error(f"Error de conexión: {exc}")
        st.stop()

    if not tenant:
        st.error("Tenant no encontrado. Verificá la URL.")
        st.stop()

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
