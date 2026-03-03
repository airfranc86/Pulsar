"""
Pulsar v1.0 — Upgrade / Checkout
===================================
Pantalla de upgrade para tenants en demo mode.
Crea Stripe Checkout Session y redirige.
"""

import logging
from typing import Any

import streamlit as st

from UI.layout import init_page, render_page_header
from core.crud import get_tenant
from core.database import DatabaseError, get_anon_client
from core.permisos import is_subscription_active

logger = logging.getLogger(__name__)

init_page("Activar cuenta", "⚡")


def _get_tenant_id() -> str:
    tid = st.session_state.get("tenant_id")
    if not tid:
        from config.constants import DEMO_TENANT_ID
        return DEMO_TENANT_ID
    return tid


def main() -> None:
    tenant_id = _get_tenant_id()

    try:
        db = get_anon_client()
        tenant = get_tenant(db, tenant_id)
    except DatabaseError as exc:
        st.error(str(exc))
        return

    if not tenant:
        st.error("Tenant no encontrado.")
        return

    if is_subscription_active(tenant):
        st.success("✅ Tu cuenta ya está activa. Tenés acceso completo a Pulsar.")
        if st.button("Ir al Panel"):
            st.switch_page("pages/01_Panel.py")
        return

    render_page_header(
        "⚡ Activá tu cuenta completa",
        subtitle="Accedé a todas las funciones de Pulsar v1.0",
    )

    col_info, col_cta = st.columns([2, 1])

    with col_info:
        st.markdown("""
        ### ¿Qué incluye el plan completo?

        ✅ **Todos los KPIs** — Ingresos, ocupación, retención y más  
        ✅ **Exportación PDF y Excel** — Descargá tus datos cuando quieras  
        ✅ **Historial completo** — Sin límite de registros  
        ✅ **Reporte mensual automático** — Llega a tu email el día que elijas  
        ✅ **Sin límites de clientes ni turnos**

        Sin contratos. Cancelá cuando quieras.
        """)

    with col_cta:
        st.markdown("### Plan mensual")
        st.markdown("---")
        st.markdown("## ~~USD 29~~ **USD 19/mes**")
        st.caption("Precio de lanzamiento · Primeros 10 clientes")
        st.caption("Sin contratos · Cancelá cuando quieras")
        st.info(
            "Con 2 turnos recuperados por mes la herramienta se paga sola."
        )

        if st.button("Activar ahora →", type="primary", use_container_width=True):
            from services.payment_services import create_checkout_session

            try:
                checkout_url = create_checkout_session(
                    tenant_id=tenant_id,
                    user_email=tenant.get("report_email") or "",
                )
                st.markdown(
                    f'<meta http-equiv="refresh" content="0; url={checkout_url}">',
                    unsafe_allow_html=True,
                )
                st.info(f"Redirigiendo a Stripe... [Click aquí si no redirecciona]({checkout_url})")
            except Exception as exc:
                st.error(f"Error al iniciar el pago: {exc}")
                logger.error(
                    "checkout_redirect_failed",
                    extra={"tenant_id": tenant_id, "error": str(exc)},
                )


main()
