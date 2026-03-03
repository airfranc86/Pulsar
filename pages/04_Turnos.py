"""
Pulsar v1.0 — Gestión de Turnos
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
from core.permisos import get_access_summary
from core.validators import validate_appointment_payload

logger = logging.getLogger(__name__)

init_page("Turnos", "📅")


def _get_tenant_id() -> str:
    tid = st.session_state.get("tenant_id")
    if not tid:
        from config.constants import DEMO_TENANT_ID
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
    return list_services(db, tenant_id, activo=True)


@st.cache_data(ttl=CACHE_TTL_CLIENTS, show_spinner=False)
def _load_clients(tenant_id: str, _cache_version: int = 0) -> list[dict[str, Any]]:
    db = get_anon_client()
    return list_clients(db, tenant_id, limit=200)


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
            turnos = list_appointments(
                db,
                tenant_id,
                fecha_desde=fecha_desde,
                fecha_hasta=fecha_hasta,
                estados=estados_filtro or None,
                limit=access["records_limit"] or 200,
            )
            render_appointments_table(
                turnos,
                demo_mode=demo,
                servicios_label=vertical_labels["servicios_label"],
            )
        except DatabaseError as exc:
            st.error(f"Error al cargar turnos: {exc}")

    # ─── Tab Nuevo Turno ───────────────────────────────────────────────────────
    with tab_nuevo:
        try:
            services = _load_services(tenant_id, cache_ver)
            clients = _load_clients(tenant_id, cache_ver)
        except DatabaseError as exc:
            st.error(f"Error al cargar datos: {exc}")
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
