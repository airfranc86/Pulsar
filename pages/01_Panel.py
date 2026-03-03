"""
Pulsar v1.0 ? Panel de Métricas
==================================
P?gina principal: KPIs del período, gráficas de ingresos y operaciones.
Orquesta: carga de datos ? cálculo de KPIs ? rendering de UI.

Multi-tenant: tenant_id se obtiene de la sesión. Toda query lo incluye.
Demo mode: muestra KPIs limitados + banner de upgrade.
"""

import logging
from datetime import date, timedelta
from typing import Any

import streamlit as st

from UI.layout import init_page, render_connection_error, render_page_header
from UI.KPI_cards import (
    render_kpi_row_ingresos,
    render_kpi_row_operativo,
    render_demo_kpi_overlay,
    render_upgrade_banner,
)
from UI.graficas import (
    render_ingresos_timeline,
    render_servicios_bar,
    render_horas_pico_heatmap,
    render_clientes_donut,
)
from UI.sidebar import render_sidebar
from analytics.revenue_metrics import (
    compute_ingresos_mensuales,
    compute_ticket_promedio,
    compute_ocupacion,
    compute_servicios_mas_vendidos,
    compute_horas_pico,
    compute_comparacion_mes_anterior,
)
from analytics.retention_metrics import compute_clientes_nuevos_vs_recurrentes
from config.constants import (
    APPOINTMENT_STATES_BILLABLE,
    APPOINTMENT_STATES_NEGATIVE,
    CACHE_TTL_KPI,
    SLOTS_POR_DIA_DEFAULT,
    VERTICALS,
)
from core.crud import (
    list_appointments,
    list_services,
    get_tenant,
)
from core.database import DatabaseError, get_anon_client
from core.permisos import get_access_summary, is_demo_mode

logger = logging.getLogger(__name__)

# ??? Page config ??????????????????????????????????????????????????????????????
init_page("Panel de Métricas", "??")


def _get_session_tenant_id() -> str:
    """Obtiene tenant_id de la sesión. Falla limpiamente si no existe."""
    tenant_id = st.session_state.get("tenant_id")
    if not tenant_id:
        from config.constants import DEMO_TENANT_ID
        tenant_id = DEMO_TENANT_ID
        st.session_state["tenant_id"] = tenant_id
    return tenant_id


@st.cache_data(ttl=CACHE_TTL_KPI, show_spinner=False)
def _load_tenant_data(tenant_id: str) -> dict[str, Any]:
    """Carga datos del tenant con caché."""
    db = get_anon_client()
    return get_tenant(db, tenant_id) or {}


@st.cache_data(ttl=CACHE_TTL_KPI, show_spinner=False)
def _load_period_data(
    tenant_id: str,
    fecha_desde: str,
    fecha_hasta: str,
) -> dict[str, Any]:
    """Carga turnos y servicios del período con caché."""
    from datetime import date as date_cls
    db = get_anon_client()

    fd = date_cls.fromisoformat(fecha_desde)
    fh = date_cls.fromisoformat(fecha_hasta)

    turnos = list_appointments(
        db, tenant_id, fecha_desde=fd, fecha_hasta=fh, limit=500
    )
    services = list_services(db, tenant_id, activo=True)

    return {"turnos": turnos, "services": services}


def main() -> None:
    tenant_id = _get_session_tenant_id()

    # ?? Cargar tenant ?????????????????????????????????????????????????????????
    try:
        tenant = _load_tenant_data(tenant_id)
    except DatabaseError as exc:
        render_connection_error(str(exc))
        return

    if not tenant:
        st.error("Tenant no encontrado.")
        st.stop()

    access = get_access_summary(tenant)
    demo = access["demo_mode"]
    vertical = tenant.get("vertical", "pyme_servicios")
    vertical_labels = VERTICALS.get(vertical, VERTICALS["pyme_servicios"])

    # ?? Sidebar ???????????????????????????????????????????????????????????????
    render_sidebar(
        tenant,
        active=access["subscription_active"],
        demo_mode=demo,
        vertical_labels=vertical_labels,
    )

    # ?? Header ????????????????????????????????????????????????????????????????
    render_page_header(
        f"Panel ? {tenant.get('name', '')}",
        subtitle=f"{vertical_labels['label']} · Período actual",
        demo_mode=demo,
    )

    if demo:
        render_upgrade_banner()

    # ?? Filtro de período ??????????????????????????????????????????????????????
    hoy = date.today()
    col_f1, col_f2, _ = st.columns([2, 2, 6])
    with col_f1:
        fecha_desde = st.date_input(
            "Desde",
            value=hoy.replace(day=1),
            max_value=hoy,
        )
    with col_f2:
        fecha_hasta = st.date_input(
            "Hasta",
            value=hoy,
            max_value=hoy,
        )

    if fecha_desde > fecha_hasta:
        st.warning("La fecha de inicio debe ser anterior a la de fin.")
        return

    # ?? Cargar datos del período ???????????????????????????????????????????????
    try:
        with st.spinner("Cargando métricas..."):
            period_data = _load_period_data(
                tenant_id,
                fecha_desde.isoformat(),
                fecha_hasta.isoformat(),
            )
    except DatabaseError as exc:
        render_connection_error(str(exc))
        return

    turnos = period_data["turnos"]
    services = period_data["services"]
    servicios_precio = {s["id"]: float(s.get("precio", 0)) for s in services}
    servicios_nombre = {s["id"]: s.get("nombre", "") for s in services}

    # Cargar mes anterior para comparación
    prev_desde = (fecha_desde.replace(day=1) - timedelta(days=1)).replace(day=1)
    prev_hasta = fecha_desde.replace(day=1) - timedelta(days=1)

    try:
        prev_data = _load_period_data(
            tenant_id,
            prev_desde.isoformat(),
            prev_hasta.isoformat(),
        )
        prev_ingresos = compute_ingresos_mensuales(
            prev_data["turnos"],
            {s["id"]: float(s.get("precio", 0)) for s in prev_data["services"]},
        )
    except DatabaseError:
        prev_ingresos = 0.0

    # ?? Calcular KPIs ??????????????????????????????????????????????????????????
    billable = [t for t in turnos if t.get("estado") in APPOINTMENT_STATES_BILLABLE]
    negativos = [t for t in turnos if t.get("estado") in APPOINTMENT_STATES_NEGATIVE]
    cancelados = [t for t in turnos if t.get("estado") == "cancelado"]
    no_shows = [t for t in turnos if t.get("estado") == "no_show"]

    ingresos = compute_ingresos_mensuales(billable, servicios_precio)
    ticket = compute_ticket_promedio(ingresos, len(billable))
    # Ocupación contra slots disponibles reales del período (no contra total turnos).
    dias_periodo = (fecha_hasta - fecha_desde).days + 1
    capacidad_slots = max(dias_periodo * SLOTS_POR_DIA_DEFAULT, 1)
    ocupacion = compute_ocupacion(len(billable), capacidad_slots)
    comparacion = compute_comparacion_mes_anterior(ingresos, prev_ingresos)

    prev_client_ids = {t["client_id"] for t in prev_data.get("turnos", []) if t.get("client_id")}
    retencion = compute_clientes_nuevos_vs_recurrentes(
        [t for t in billable if t.get("client_id")],
        [{"client_id": cid} for cid in prev_client_ids],
    )

    # ?? KPI Rows ???????????????????????????????????????????????????????????????
    st.subheader("?? Financiero")
    render_kpi_row_ingresos(ingresos, ticket, len(billable), comparacion)

    st.divider()

    if demo:
        render_demo_kpi_overlay()
    else:
        st.subheader("?? Operativo")
        render_kpi_row_operativo(
            ocupacion,
            len(cancelados),
            len(no_shows),
            retencion["nuevos"],
            retencion["recurrentes"],
        )
        st.divider()

    # ?? Gráficas ???????????????????????????????????????????????????????????????
    col_left, col_right = st.columns(2)

    with col_left:
        top_services = compute_servicios_mas_vendidos(billable, servicios_nombre, top_n=5)
        render_servicios_bar(
            top_services,
            label_field="nombre",
            value_field="cantidad",
            title=f"{vertical_labels['servicios_label']} más frecuentes",
        )

    with col_right:
        if not demo:
            render_clientes_donut(
                retencion["nuevos"],
                retencion["recurrentes"],
                title="Nuevos vs Recurrentes",
            )

    if not demo:
        horas = compute_horas_pico(turnos)
        render_horas_pico_heatmap(horas, title="Horas pico del período")

    logger.info(
        "panel_rendered",
        extra={
            "tenant_id": tenant_id,
            "turnos": len(turnos),
            "demo_mode": demo,
        },
    )


main()
