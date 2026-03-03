"""
Pulsar v1.0 — Layout y estructura de página
============================================
Inicialización de página, cabecera y mensajes de error de conexión.
Solo presentación; sin lógica de negocio.
"""

from typing import Optional

import streamlit as st


def init_page(page_title: str, icon: str) -> None:
    """
    Registra título e ícono de la página actual en session_state.
    No llama a set_page_config (ya se hace en app.py).
    """
    st.session_state["page_title"] = page_title
    st.session_state["page_icon"] = icon


def render_connection_error(message: str) -> None:
    """Muestra mensaje de error cuando falla la conexión a BD o servicios."""
    st.error(f"⚠️ Error de conexión: {message}")
    st.info("Verificá tu conexión y que las variables de entorno (ej. SUPABASE_URL) estén configuradas.")


def render_page_header(
    title: str,
    subtitle: Optional[str] = None,
    demo_mode: bool = False,
) -> None:
    """
    Renderiza la cabecera de la página: título, subtítulo opcional y banner demo si aplica.
    """
    st.title(f"{title}")
    if subtitle:
        st.caption(subtitle)
    if demo_mode:
        st.warning("🔒 Modo demo — datos limitados. Activá tu cuenta para acceso completo.")
