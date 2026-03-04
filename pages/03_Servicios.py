"""
Pulsar — Gestión de Servicios
=====================================
CRUD de servicios con adaptación de labels por vertical.
Multi-tenant obligatorio.
"""

import logging
from typing import Any

import streamlit as st

from UI.layout import init_page, render_connection_error, render_page_header
from UI.tablas import render_services_table
from UI.sidebar import render_sidebar
from config.constants import DEMO_TENANT_ID, VERTICALS, CACHE_TTL_SERVICES
from core.crud import list_services, create_service, update_service, get_tenant
from core.database import DatabaseError, get_anon_client
from core.permisos import get_access_summary, get_demo_tenant_fallback
from core.validators import validate_service_payload
from data.demo_data import get_demo_services

logger = logging.getLogger(__name__)

init_page("Servicios", "⚙️")


def _get_tenant_id() -> str:
    tid = st.session_state.get("tenant_id")
    if not tid:
        st.session_state["tenant_id"] = DEMO_TENANT_ID
        return DEMO_TENANT_ID
    return tid


def _bust_cache() -> None:
    """Invalida caché del tenant actual sin borrar toda la caché global."""
    st.session_state["cache_version"] = st.session_state.get("cache_version", 0) + 1


@st.cache_data(ttl=CACHE_TTL_SERVICES, show_spinner=False)
def _load_tenant(tenant_id: str, _cache_version: int = 0) -> dict[str, Any]:
    db = get_anon_client()
    return get_tenant(db, tenant_id) or {}


@st.cache_data(ttl=CACHE_TTL_SERVICES, show_spinner=False)
def _load_services(tenant_id: str, _cache_version: int = 0) -> list[dict[str, Any]]:
    db = get_anon_client()
    return list_services(db, tenant_id)


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
    svc_label = vertical_labels["servicios_label"]
    svc_label_singular = vertical_labels.get("servicios_label_singular", svc_label)

    render_sidebar(
        tenant,
        active=access["subscription_active"],
        demo_mode=demo,
        vertical_labels=vertical_labels,
    )
    render_page_header(
        svc_label,
        subtitle=f"Gestión de {svc_label.lower()} del negocio",
        demo_mode=demo,
    )

    tab_lista, tab_nuevo, tab_editar = st.tabs([
        f"📋 Lista de {svc_label}",
        f"➕ Nuevo {svc_label_singular}",
        "✏️ Editar",
    ])

    with tab_lista:
        try:
            services = _load_services(tenant_id, cache_ver)
        except DatabaseError:
            if tenant_id == DEMO_TENANT_ID:
                services = get_demo_services(tenant_id)
            else:
                st.error("Error al cargar servicios. Sin conexión a la base de datos.")
                services = []
        render_services_table(services, servicios_label=svc_label)

    with tab_nuevo:
        with st.form("form_nuevo_servicio"):
            nombre = st.text_input(f"Nombre del {svc_label_singular}", max_chars=120)
            descripcion = st.text_area("Descripción", max_chars=500)
            col_precio, col_dur = st.columns(2)
            with col_precio:
                precio = st.number_input("Precio ($)", min_value=0.0, step=100.0)
            with col_dur:
                duracion = st.number_input("Duración (min)", min_value=5, max_value=480, value=60, step=5)
            activo = st.checkbox("Activo", value=True)

            submitted = st.form_submit_button("Crear", type="primary")
            if submitted:
                try:
                    payload = validate_service_payload({
                        "nombre": nombre,
                        "descripcion": descripcion or None,
                        "precio": precio,
                        "duracion_minutos": int(duracion),
                        "activo": activo,
                    })
                    db = get_anon_client()
                    create_service(db, tenant_id, payload)
                    st.success(f"✅ {svc_label_singular} creado.")
                    _bust_cache()
                    logger.info("service_created_from_ui", extra={"tenant_id": tenant_id})
                except (ValueError, DatabaseError) as exc:
                    st.error(f"Error: {exc}")

    with tab_editar:
        try:
            services = _load_services(tenant_id, cache_ver)
        except DatabaseError:
            if tenant_id == DEMO_TENANT_ID:
                services = get_demo_services(tenant_id)
            else:
                st.error("Error al cargar servicios. Sin conexión a la base de datos.")
                return

        if not services:
            st.info(f"No hay {svc_label.lower()} para editar.")
            return

        service_map = {s["nombre"]: s for s in services}
        sel_nombre = st.selectbox(f"Seleccionar {svc_label_singular}", list(service_map.keys()))
        svc = service_map[sel_nombre]

        with st.form("form_editar_servicio"):
            nuevo_precio = st.number_input("Precio ($)", value=float(svc.get("precio", 0)), step=100.0)
            nueva_duracion = st.number_input("Duración (min)", value=int(svc.get("duracion_minutos", 60)), min_value=5, max_value=480)
            nuevo_activo = st.checkbox("Activo", value=bool(svc.get("activo", True)))

            submitted = st.form_submit_button("Guardar cambios", type="primary")
            if submitted:
                try:
                    payload = validate_service_payload({
                        "nombre": svc["nombre"],
                        "precio": nuevo_precio,
                        "duracion_minutos": int(nueva_duracion),
                        "activo": nuevo_activo,
                    })
                    db = get_anon_client()
                    update_service(db, tenant_id, svc["id"], payload)
                    st.success("✅ Servicio actualizado.")
                    _bust_cache()
                except (ValueError, DatabaseError) as exc:
                    st.error(f"Error: {exc}")


main()
