"""
Pulsar v1.0 — UI/sidebar.py
=============================
Sidebar persistente de la aplicación.
Muestra: logo, info del tenant, estado de suscripción,
         labels adaptados al vertical, y CTA de upgrade.

Exports públicos:
    render_sidebar(tenant, active, demo_mode, vertical_labels)
"""

import streamlit as st


# ── Paleta interna ────────────────────────────────────────────────────────────
_COLOR_ACTIVE = "#10B981"  # verde
_COLOR_INACTIVE = "#EF4444"  # rojo
_COLOR_DEMO = "#F59E0B"  # amarillo


def render_sidebar(
    tenant: dict | None = None,
    active: bool = False,
    demo_mode: bool = True,
    vertical_labels: dict | None = None,
) -> None:
    """
    Renderiza el sidebar completo.

    Args:
        tenant:          Dict de datos del tenant (name, slug, vertical, etc.)
        active:          True si la suscripción está activa.
        demo_mode:       True si está en modo demo.
        vertical_labels: Dict de labels del vertical para personalizar textos.
    """
    t = tenant or {}
    vl = vertical_labels or {}

    with st.sidebar:
        _render_logo()
        st.divider()
        _render_tenant_info(t, active, demo_mode)

        if demo_mode or not active:
            st.divider()
            _render_upgrade_cta()

        st.divider()
        _render_footer()


# ── Sub-componentes ───────────────────────────────────────────────────────────


def _render_logo() -> None:
    col_logo, col_name = st.columns([1, 3])
    with col_logo:
        st.image("assets/pulsar_192x192.png", use_container_width=True)
    with col_name:
        st.markdown("**Pulsar**")
        st.caption("BusinessOps v1.3")


def _render_tenant_info(tenant: dict, active: bool, demo_mode: bool) -> None:
    name = tenant.get("name") or tenant.get("nombre") or "Mi negocio"
    vertical = tenant.get("vertical", "pyme_servicios")

    st.markdown(f"**{name}**")
    st.caption(f"Vertical: `{vertical}`")

    if demo_mode:
        st.markdown(
            f'<span style="color:{_COLOR_DEMO}; font-size:0.8rem;">● Modo demo</span>',
            unsafe_allow_html=True,
        )
    elif active:
        st.markdown(
            f'<span style="color:{_COLOR_ACTIVE}; font-size:0.8rem;">● Suscripción activa</span>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f'<span style="color:{_COLOR_INACTIVE}; font-size:0.8rem;">● Sin suscripción</span>',
            unsafe_allow_html=True,
        )


def _render_upgrade_cta() -> None:
    st.markdown("**Activá tu cuenta**")
    st.caption("Accedé a todos los datos, reportes y funciones.")
    st.page_link("pages/08_Upgrade.py", label="Ver planes →", icon="⚡")


def _render_footer() -> None:
    st.caption("Pulsar · v1.3")
