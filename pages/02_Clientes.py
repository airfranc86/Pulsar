"""
Pulsar v1.0 — Gestión de Clientes
====================================
CRUD de clientes con búsqueda y paginación.
Demo mode: limita registros visibles.
"""

import logging
from typing import Any

import streamlit as st

from UI.layout import init_page, render_connection_error, render_page_header
from UI.tablas import render_clients_table
from UI.sidebar import render_sidebar
from config.constants import VERTICALS, CACHE_TTL_CLIENTS
from core.crud import list_clients, create_client_record, get_tenant
from core.database import DatabaseError, get_anon_client
from core.permisos import get_access_summary
from core.validators import validate_client_payload

logger = logging.getLogger(__name__)

init_page("Clientes", "👥")


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


def main() -> None:
    tenant_id = _get_tenant_id()

    try:
        tenant = _load_tenant(tenant_id, st.session_state.get("cache_version", 0))
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
        vertical_labels["clientes_label"],
        subtitle="Registro y gestión de clientes",
        demo_mode=demo,
    )

    tab_lista, tab_nuevo = st.tabs(["📋 Lista", "➕ Nuevo"])

    with tab_lista:
        search = st.text_input("🔍 Buscar por nombre", placeholder="Ingresá un nombre...")
        try:
            db = get_anon_client()
            clientes = list_clients(
                db,
                tenant_id,
                limit=access["records_limit"] or 100,
                search=search or None,
            )
            render_clients_table(clientes, demo_mode=demo)
        except DatabaseError as exc:
            st.error(f"Error al cargar clientes: {exc}")

    with tab_nuevo:
        with st.form("form_nuevo_cliente"):
            col1, col2 = st.columns(2)
            with col1:
                nombre = st.text_input("Nombre *", max_chars=120)
            with col2:
                apellido = st.text_input("Apellido", max_chars=120)
            col3, col4 = st.columns(2)
            with col3:
                email = st.text_input("Email")
            with col4:
                telefono = st.text_input("Teléfono")
            notas = st.text_area("Notas", max_chars=500)

            submitted = st.form_submit_button("Registrar cliente", type="primary")
            if submitted:
                try:
                    payload = validate_client_payload({
                        "nombre": nombre,
                        "apellido": apellido or None,
                        "email": email or None,
                        "telefono": telefono or None,
                        "notas": notas or None,
                    })
                    db = get_anon_client()
                    create_client_record(db, tenant_id, payload)
                    st.success("✅ Cliente registrado.")
                    _bust_cache()
                    logger.info("client_created_from_ui", extra={"tenant_id": tenant_id})
                except (ValueError, DatabaseError) as exc:
                    st.error(f"Error: {exc}")


main()
