"""
Pulsar v1.0 — Facturación
===========================
Vista de ingresos y resumen de facturación del período.
Exportación disponible solo en FULL_MODE.
"""

import logging
from datetime import date
from typing import Any

import pandas as pd
import streamlit as st

from UI.layout import init_page, render_connection_error, render_page_header
from UI.sidebar import render_sidebar
from config.constants import APPOINTMENT_STATES_BILLABLE, VERTICALS, CACHE_TTL_KPI
from core.crud import list_appointments, list_services, get_tenant
from core.database import DatabaseError, get_anon_client
from core.permisos import get_access_summary
from services.export_services import export_to_csv, export_to_excel, get_export_filename

logger = logging.getLogger(__name__)

init_page("Facturación", "💰")


def _get_tenant_id() -> str:
    tid = st.session_state.get("tenant_id")
    if not tid:
        from config.constants import DEMO_TENANT_ID
        return DEMO_TENANT_ID
    return tid


@st.cache_data(ttl=CACHE_TTL_KPI, show_spinner=False)
def _load_tenant(tenant_id: str) -> dict[str, Any]:
    db = get_anon_client()
    return get_tenant(db, tenant_id) or {}


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
    render_page_header("Facturación", subtitle="Resumen de ingresos por período", demo_mode=demo)

    col_f1, col_f2, _ = st.columns([2, 2, 6])
    with col_f1:
        fecha_desde = st.date_input("Desde", value=date.today().replace(day=1))
    with col_f2:
        fecha_hasta = st.date_input("Hasta", value=date.today())

    try:
        db = get_anon_client()
        turnos = list_appointments(
            db, tenant_id,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            estados=list(APPOINTMENT_STATES_BILLABLE),
            limit=500,
        )
        services = list_services(db, tenant_id)
    except DatabaseError as exc:
        st.error(str(exc))
        return

    servicios_info = {s["id"]: s for s in services}

    rows = []
    for t in turnos:
        svc = servicios_info.get(t.get("servicio_id", ""), {})
        rows.append({
            "Fecha": t.get("fecha"),
            "Hora": t.get("hora"),
            vertical_labels["servicios_label"]: svc.get("nombre", "—"),
            "Precio ($)": float(svc.get("precio", 0)),
            "Estado": t.get("estado"),
        })

    if rows:
        df = pd.DataFrame(rows)
        total = df["Precio ($)"].sum()
        st.metric("Total del período", f"$ {total:,.0f}")
        st.dataframe(df, use_container_width=True, hide_index=True)

        if not demo:
            col_csv, col_xlsx = st.columns(2)
            with col_csv:
                csv_bytes = export_to_csv(rows)
                st.download_button(
                    "⬇️ Exportar CSV",
                    data=csv_bytes,
                    file_name=get_export_filename(
                        "facturacion", tenant.get("slug", "tenant"), "csv"
                    ),
                    mime="text/csv",
                )
            with col_xlsx:
                xlsx_bytes = export_to_excel(rows, sheet_name="Facturación")
                st.download_button(
                    "⬇️ Exportar Excel",
                    data=xlsx_bytes,
                    file_name=get_export_filename(
                        "facturacion", tenant.get("slug", "tenant"), "xlsx"
                    ),
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
        else:
            st.info("🔒 Exportación disponible en la versión completa.")
    else:
        st.info("Sin turnos facturables en el período seleccionado.")


main()
