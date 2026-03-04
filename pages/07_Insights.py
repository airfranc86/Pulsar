"""
Pulsar — Insights & Reportes
=====================================
Historial de reportes mensuales y trigger manual.
Solo disponible en FULL_MODE.
"""

import logging
from datetime import date
from typing import Any

import streamlit as st

from UI.layout import init_page, render_connection_error, render_page_header
from UI.tablas import render_report_history_table
from UI.sidebar import render_sidebar
from config.constants import VERTICALS
from core.crud import list_report_history, get_tenant
from core.database import DatabaseError, get_anon_client
from core.permisos import get_access_summary

logger = logging.getLogger(__name__)

init_page("Insights", "💡")


def _get_tenant_id() -> str:
    tid = st.session_state.get("tenant_id")
    if not tid:
        from config.constants import DEMO_TENANT_ID
        return DEMO_TENANT_ID
    return tid


def _bust_cache() -> None:
    """Invalida caché del tenant actual sin borrar toda la caché global."""
    st.session_state["cache_version"] = st.session_state.get("cache_version", 0) + 1


@st.cache_data(ttl=60, show_spinner=False)
def _load_tenant(tenant_id: str, _cache_version: int = 0) -> dict[str, Any]:
    return get_tenant(get_anon_client(), tenant_id) or {}


def main() -> None:
    tenant_id = _get_tenant_id()
    cache_ver = st.session_state.get("cache_version", 0)

    try:
        tenant = _load_tenant(tenant_id, cache_ver)
    except DatabaseError as exc:
        render_connection_error(str(exc))
        return

    access = get_access_summary(tenant)
    demo = access["demo_mode"]
    vertical = tenant.get("vertical", "pyme_servicios")
    vertical_labels = VERTICALS.get(vertical, VERTICALS["pyme_servicios"])

    render_sidebar(
        tenant,
        active=access["subscription_active"],
        demo_mode=demo,
        vertical_labels=vertical_labels,
    )
    render_page_header("Insights y Reportes", subtitle="Historial de reportes mensuales", demo_mode=demo)

    if demo:
        st.info(
            "📄 **Reportes mensuales automáticos** disponibles en la versión completa. "
            "El sistema genera y envía el resumen por email el día que vos elijas."
        )
        return

    # Historial de reportes
    st.subheader("📋 Historial de reportes")
    try:
        db_anon = get_anon_client()
        history = list_report_history(db_anon, tenant_id, limit=12)
        render_report_history_table(history)
    except DatabaseError as exc:
        st.error(str(exc))

    st.divider()

    # Trigger manual de reporte
    st.subheader("▶️ Generar reporte manualmente")
    st.caption("Útil para re-generar un reporte o generar uno fuera de ciclo.")

    col_period, col_force = st.columns([3, 2])
    with col_period:
        period_sel = st.date_input(
            "Período (usar primer día del mes)",
            value=date.today().replace(day=1),
        )
    with col_force:
        force = st.checkbox("Forzar regeneración si ya existe")

    if st.button("Generar reporte", type="primary"):
        from services.scheduler_service import run_monthly_report_for_tenant
        with st.spinner("Generando reporte..."):
            try:
                result = run_monthly_report_for_tenant(
                    tenant_id,
                    period=period_sel.replace(day=1),
                    force=force,
                )
                if result["status"] == "success":
                    st.success(
                        f"✅ Reporte generado para {result['period_label']}. "
                        f"Email enviado: {'sí' if result['email_sent'] else 'no'}."
                    )
                    _bust_cache()
                elif result["status"] == "skipped":
                    st.warning("El reporte ya existe para este período. Marcá 'Forzar' para regenerarlo.")
            except Exception as exc:
                st.error(f"Error al generar reporte: {exc}")
                logger.error(
                    "manual_report_trigger_failed",
                    extra={"tenant_id": tenant_id, "error": str(exc)},
                )


main()
