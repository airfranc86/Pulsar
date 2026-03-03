"""
Pulsar v1.0 — Analíticas Avanzadas
=====================================
Gráficas de profitability y lifecycle.
Solo disponible en FULL_MODE.
"""

import logging
from datetime import date
from typing import Any

import streamlit as st

from UI.layout import init_page, render_connection_error, render_page_header
from UI.graficas import render_servicios_bar
from UI.sidebar import render_sidebar
from config.constants import VERTICALS, CACHE_TTL_KPI
from core.crud import list_appointments, list_services, get_tenant
from core.database import DatabaseError, get_anon_client
from core.permisos import get_access_summary
from analytics.profitability import compute_revenue_by_service

logger = logging.getLogger(__name__)

init_page("Analíticas", "📈")


def _get_tenant_id() -> str:
    tid = st.session_state.get("tenant_id")
    if not tid:
        from config.constants import DEMO_TENANT_ID
        return DEMO_TENANT_ID
    return tid


@st.cache_data(ttl=CACHE_TTL_KPI, show_spinner=False)
def _load_tenant(tenant_id: str) -> dict[str, Any]:
    return get_tenant(get_anon_client(), tenant_id) or {}


def main() -> None:
    tenant_id = _get_tenant_id()

    try:
        tenant = _load_tenant(tenant_id)
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
    render_page_header("Analíticas", subtitle="Profitability y tendencias", demo_mode=demo)

    if demo:
        st.info(
            "📊 **Analíticas avanzadas** disponibles en la versión completa. "
            "Incluye rentabilidad por servicio, LTV y tendencias mensuales."
        )
        return

    col_f1, col_f2 = st.columns(2)
    with col_f1:
        fecha_desde = st.date_input("Desde", value=date.today().replace(day=1))
    with col_f2:
        fecha_hasta = st.date_input("Hasta", value=date.today())

    try:
        db = get_anon_client()
        turnos = list_appointments(db, tenant_id, fecha_desde=fecha_desde, fecha_hasta=fecha_hasta, limit=500)
        services = list_services(db, tenant_id)
    except DatabaseError as exc:
        st.error(str(exc))
        return

    servicios_map = {s["id"]: s for s in services}
    revenue_by_svc = compute_revenue_by_service(turnos, servicios_map)

    st.subheader(f"Ingresos por {vertical_labels['servicios_label']}")
    render_servicios_bar(
        revenue_by_svc,
        label_field="nombre",
        value_field="ingresos",
        title=f"Ingresos por {vertical_labels['servicios_label']}",
    )

    if revenue_by_svc:
        import pandas as pd
        df = pd.DataFrame(revenue_by_svc)
        df["ingresos"] = df["ingresos"].apply(lambda x: f"$ {x:,.0f}")
        df["precio_promedio"] = df["precio_promedio"].apply(lambda x: f"$ {x:,.0f}")
        df = df.rename(columns={
            "nombre": vertical_labels["servicios_label"],
            "cantidad": "Turnos",
            "ingresos": "Ingresos",
            "precio_promedio": "Ticket Prom.",
        })
        st.dataframe(df, use_container_width=True, hide_index=True)


main()
