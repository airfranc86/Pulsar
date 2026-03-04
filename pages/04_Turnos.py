"""
Pulsar — Gestión de Turnos
==================================
CRUD de turnos con filtros operativos.
Multi-tenant obligatorio en todas las operaciones.
"""

import logging
from datetime import date, timedelta
from typing import Any

import streamlit as st

from UI.layout import init_page, render_connection_error, render_page_header
from UI.tablas import render_appointments_table
from UI.sidebar import render_sidebar
from config.constants import (
    APPOINTMENT_STATES,
    DEMO_TENANT_ID,
    VERTICALS,
    CACHE_TTL_CLIENTS,
)
from core.crud import (
    list_appointments,
    list_services,
    list_clients,
    create_appointment,
    update_appointment_status,
    get_tenant,
)
from core.database import DatabaseError, get_anon_client
from core.permisos import get_access_summary, get_demo_tenant_fallback
from core.validators import validate_appointment_payload
from data.demo_data import get_demo_appointments, get_demo_clients, get_demo_services

logger = logging.getLogger(__name__)

init_page("Turnos", "📅")


def _get_tenant_id() -> str:
    tid = st.session_state.get("tenant_id")
    if not tid:
        st.session_state["tenant_id"] = DEMO_TENANT_ID
        return DEMO_TENANT_ID
    return tid


def _bust_cache() -> None:
    """Invalida caché del tenant actual sin borrar toda la caché global."""
    st.session_state["cache_version"] = st.session_state.get("cache_version", 0) + 1


@st.cache_data(ttl=CACHE_TTL_CLIENTS, show_spinner=False)
def _load_tenant(tenant_id: str, _cache_version: int = 0) -> dict[str, Any]:
    db = get_anon_client()
    return get_tenant(db, tenant_id) or {}


@st.cache_data(ttl=CACHE_TTL_CLIENTS, show_spinner=False)
def _load_services(tenant_id: str, _cache_version: int = 0) -> list[dict[str, Any]]:
    db = get_anon_client()
    return list_services(db, tenant_id, active_only=True)


@st.cache_data(ttl=CACHE_TTL_CLIENTS, show_spinner=False)
def _load_clients(tenant_id: str, _cache_version: int = 0) -> list[dict[str, Any]]:
    db = get_anon_client()
    return list_clients(db, tenant_id, page=1, page_size=200)


def main() -> None:
    tenant_id = _get_tenant_id()
    cache_ver = st.session_state.get("cache_version", 0)

    try:
        tenant = _load_tenant(tenant_id, cache_ver)
    except DatabaseError:
        tenant = get_demo_tenant_fallback(tenant_id)

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
    render_page_header(
        f"{vertical_labels['turnos_label']}",
        subtitle="Gestión operativa de agenda",
        demo_mode=demo,
    )

    tab_lista, tab_nuevo, tab_estado = st.tabs([
        "📋 Lista",
        "➕ Nuevo turno",
        "✏️ Cambiar estado",
    ])

    # ─── Tab Lista ─────────────────────────────────────────────────────────────
    with tab_lista:
        col_f1, col_f2, col_f3 = st.columns([2, 2, 3])
        with col_f1:
            fecha_desde = st.date_input("Desde", value=date.today().replace(day=1))
        with col_f2:
            fecha_hasta = st.date_input("Hasta", value=date.today() + timedelta(days=7))
        with col_f3:
            estados_filtro = st.multiselect(
                "Estados",
                options=APPOINTMENT_STATES,
                default=["pendiente", "confirmado"],
            )

        try:
            db = get_anon_client()
            page_size = access.get("max_records_per_table") or 200
            if page_size == -1:
                page_size = 500
            turnos_raw = list_appointments(
                db,
                tenant_id,
                fecha_desde=fecha_desde,
                fecha_hasta=fecha_hasta,
                page=1,
                page_size=page_size,
            )
            if estados_filtro:
                turnos = [t for t in turnos_raw if t.get("estado") in estados_filtro]
            else:
                turnos = turnos_raw
            render_appointments_table(
                turnos,
                demo_mode=demo,
                servicios_label=vertical_labels["servicios_label"],
            )
        except DatabaseError:
            if tenant_id == DEMO_TENANT_ID:
                turnos_raw = get_demo_appointments(
                    tenant_id,
                    fecha_desde=fecha_desde,
                    fecha_hasta=fecha_hasta,
                )
                if estados_filtro:
                    turnos = [t for t in turnos_raw if t.get("estado") in estados_filtro]
                else:
                    turnos = turnos_raw
                render_appointments_table(
                    turnos,
                    demo_mode=demo,
                    servicios_label=vertical_labels["servicios_label"],
                )
            else:
                st.error("Error al cargar turnos. Sin conexión a la base de datos.")

    # ─── Tab Nuevo Turno ───────────────────────────────────────────────────────
    with tab_nuevo:
        try:
            services = _load_services(tenant_id, cache_ver)
            clients = _load_clients(tenant_id, cache_ver)
        except DatabaseError:
            if tenant_id == DEMO_TENANT_ID:
                services = get_demo_services(tenant_id)
                clients = get_demo_clients(tenant_id)
            else:
                st.error("Error al cargar datos. Sin conexión a la base de datos.")
                return

        if not services:
            st.warning(f"No hay {vertical_labels['servicios_label'].lower()} activos. Creá uno primero en la sección Servicios.")
            return

        service_options = {s["nombre"]: s["id"] for s in services}
        client_options = {
            f"{c.get('nombre', '')} {c.get('apellido', '')}".strip(): c["id"]
            for c in clients
        }

        with st.form("form_nuevo_turno"):
            servicio_sel = st.selectbox(
                vertical_labels["servicios_label"],
                options=list(service_options.keys()),
            )
            cliente_sel = st.selectbox(
                vertical_labels["clientes_label"],
                options=list(client_options.keys()) if client_options else ["Sin clientes"],
            )
            col_fecha, col_hora = st.columns(2)
            with col_fecha:
                fecha = st.date_input("Fecha", min_value=date.today())
            with col_hora:
                hora = st.time_input("Hora")
            notas = st.text_area("Notas", max_chars=500)

            submitted = st.form_submit_button("Crear turno", type="primary")

            if submitted:
                if not client_options:
                    st.error("No hay clientes registrados.")
                    return
                try:
                    payload = validate_appointment_payload({
                        "client_id": client_options.get(cliente_sel, ""),
                        "servicio_id": service_options.get(servicio_sel, ""),
                        "fecha": fecha,
                        "hora": hora.strftime("%H:%M"),
                        "estado": "pendiente",
                        "notas": notas or None,
                    })
                    db = get_anon_client()
                    create_appointment(db, tenant_id, payload)
                    st.success("✅ Turno creado exitosamente.")
                    _bust_cache()
                    logger.info(
                        "appointment_created_from_ui",
                        extra={"tenant_id": tenant_id},
                    )
                except (ValueError, DatabaseError) as exc:
                    st.error(f"Error: {exc}")

    # ─── Tab Cambiar Estado ────────────────────────────────────────────────────
    with tab_estado:
        st.caption("Actualizá el estado de un turno existente.")

        appointment_id = st.text_input("ID del turno (UUID)")
        nuevo_estado = st.selectbox("Nuevo estado", options=APPOINTMENT_STATES)

        if st.button("Actualizar estado", type="primary"):
            if not appointment_id:
                st.warning("Ingresá el ID del turno.")
            else:
                try:
                    db = get_anon_client()
                    update_appointment_status(
                        db, tenant_id, appointment_id.strip(), nuevo_estado
                    )
                    st.success(f"✅ Estado actualizado a '{nuevo_estado}'.")
                    _bust_cache()
                except (ValueError, DatabaseError) as exc:
                    st.error(f"Error: {exc}")


main()
