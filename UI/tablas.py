"""
Pulsar v1.0 — UI/tablas.py
============================
Componentes de tablas de datos y el uploader de importación CSV/XLSX.
Solo presentación. Sin lógica de negocio ni acceso directo a DB.

Exports públicos:
    render_data_table(rows, height)
    render_appointments_table(turnos, demo_mode, servicios_label)
    render_clients_table(clientes, demo_mode)
    render_services_table(servicios, demo_mode)
    render_import_uploader(tenant_id, demo_mode, vertical_labels)
"""

import logging
from typing import Any

import pandas as pd
import streamlit as st

from services.import_services import (
    ENTITY_SCHEMA,
    ImportResult,
    detect_column_mapping,
    get_file_preview,
    process_import,
    validate_columns,
)

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# TABLAS GENÉRICAS
# ─────────────────────────────────────────────────────────────────────────────


def render_data_table(
    rows: list[dict] | pd.DataFrame,
    height: int = 400,
    hide_index: bool = True,
) -> None:
    """
    Tabla genérica para cualquier lista de dicts o DataFrame.
    Muestra estado vacío si no hay datos.
    """
    if rows is None or (isinstance(rows, list) and len(rows) == 0):
        st.info("Sin datos para mostrar.", icon="📭")
        return

    df = pd.DataFrame(rows) if isinstance(rows, list) else rows
    st.dataframe(df, use_container_width=True, height=height, hide_index=hide_index)


def render_appointments_table(
    turnos: list[dict],
    demo_mode: bool = False,
    servicios_label: str = "Servicio",
) -> None:
    """
    Tabla de turnos/citas con columnas formateadas.
    En demo_mode limita a 10 registros.
    """
    if not turnos:
        st.info("No hay turnos en el período seleccionado.", icon="📅")
        return

    data = turnos[:10] if demo_mode else turnos

    rows = []
    for t in data:
        rows.append(
            {
                "Fecha": t.get("fecha", "—"),
                "Hora": t.get("hora", "—"),
                servicios_label: t.get("servicio_nombre") or t.get("servicio", "—"),
                "Cliente": t.get("cliente_nombre") or t.get("cliente", "—"),
                "Estado": t.get("estado", "—"),
                "Precio ($)": t.get("precio_cobrado") or t.get("precio", 0),
            }
        )

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, height=380, hide_index=True)

    if demo_mode and len(turnos) > 10:
        st.caption(
            f"🔒 Mostrando 10 de {len(turnos)} registros. Activá tu suscripción para ver todos."
        )


def render_clients_table(
    clientes: list[dict],
    demo_mode: bool = False,
) -> None:
    """Tabla de clientes/pacientes."""
    if not clientes:
        st.info("No hay clientes registrados.", icon="👥")
        return

    data = clientes[:10] if demo_mode else clientes

    rows = []
    for c in data:
        nombre = f"{c.get('nombre', '')} {c.get('apellido', '')}".strip() or c.get(
            "name", "—"
        )
        rows.append(
            {
                "Nombre": nombre,
                "Email": c.get("email", "—"),
                "Teléfono": c.get("telefono") or c.get("phone", "—"),
                "Alta": c.get("created_at", "—"),
            }
        )

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, height=380, hide_index=True)

    if demo_mode and len(clientes) > 10:
        st.caption(f"🔒 Mostrando 10 de {len(clientes)} registros.")


def render_services_table(
    servicios: list[dict],
    demo_mode: bool = False,
    servicios_label: str = "Servicio",
) -> None:
    """Tabla de servicios/productos."""
    if not servicios:
        st.info(f"No hay {servicios_label.lower()}s registrados.", icon="🛠️")
        return

    rows = []
    for s in servicios:
        rows.append(
            {
                servicios_label: s.get("nombre") or s.get("name", "—"),
                "Precio ($)": float(s.get("precio") or s.get("price", 0)),
                "Categoría": s.get("categoria") or s.get("category", "General"),
                "Duración (min)": s.get("duracion_minutos", "—"),
            }
        )

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, height=380, hide_index=True)


# ─────────────────────────────────────────────────────────────────────────────
# IMPORT UPLOADER — Drag & Drop CSV/XLSX
# ─────────────────────────────────────────────────────────────────────────────

_ENTITY_LABELS = {
    "clients": "Clientes / Pacientes",
    "services": "Servicios / Productos",
    "appointments": "Turnos / Citas",
}

_FIELD_HELP = {
    "nombre": "Nombre del registro. Requerido.",
    "apellido": "Apellido. Opcional.",
    "email": "Correo electrónico válido. Opcional.",
    "telefono": "Teléfono o celular. Opcional.",
    "notas": "Notas u observaciones. Opcional.",
    "precio": "Precio numérico. Ej: 1500 o 1500.00. Requerido.",
    "categoria": "Categoría del servicio. Opcional.",
    "duracion_minutos": "Duración en minutos. Ej: 30. Opcional.",
    "descripcion": "Descripción del servicio. Opcional.",
    "cliente_nombre": "Nombre del cliente. Requerido.",
    "servicio_nombre": "Nombre del servicio. Requerido.",
    "fecha": "Fecha del turno. Ej: 2025-03-15. Requerido.",
    "hora": "Hora del turno. Ej: 14:30. Opcional.",
    "estado": "Estado del turno. Ej: completado. Opcional.",
    "precio_cobrado": "Monto cobrado. Opcional.",
}

_KEY = "pulsar_import"


def _k(suffix: str) -> str:
    return f"{_KEY}_{suffix}"


def _reset_import_state() -> None:
    for key in [
        "stage",
        "file_bytes",
        "filename",
        "entity",
        "df_preview",
        "column_mapping",
        "result",
    ]:
        st.session_state.pop(_k(key), None)


def _stage() -> str:
    return st.session_state.get(_k("stage"), "IDLE")


def _set_stage(s: str) -> None:
    st.session_state[_k("stage")] = s


# ── Paso 1: selector + uploader ───────────────────────────────────────────────
def _render_idle(entity_options: dict[str, str]) -> None:
    col_entity, _ = st.columns([2, 4])
    with col_entity:
        entity_label = st.selectbox(
            "¿Qué vas a importar?",
            options=list(entity_options.keys()),
            key=_k("entity_select"),
        )
    entity = entity_options[entity_label]

    st.caption(
        "Arrastrá tu archivo o hacé clic para seleccionarlo. Formatos aceptados: CSV, XLSX, XLS."
    )

    uploaded = st.file_uploader(
        label="Subir archivo",
        type=["csv", "xlsx", "xls"],
        accept_multiple_files=False,
        label_visibility="collapsed",
        key=_k("file_uploader"),
    )

    if uploaded is not None:
        try:
            file_bytes = uploaded.read()
            df_preview = get_file_preview(file_bytes, uploaded.name, n_rows=5)
            mapping = detect_column_mapping(df_preview, entity)

            st.session_state[_k("file_bytes")] = file_bytes
            st.session_state[_k("filename")] = uploaded.name
            st.session_state[_k("entity")] = entity
            st.session_state[_k("df_preview")] = df_preview
            st.session_state[_k("column_mapping")] = mapping

            _set_stage("PREVIEW")
            st.rerun()

        except ValueError as exc:
            st.error(f"**Error al leer el archivo:** {exc}")
        except Exception as exc:
            logger.exception("import_file_read_error")
            st.error(f"Error inesperado al procesar el archivo: {exc}")


# ── Paso 2: preview + mapeador de columnas ────────────────────────────────────
def _render_column_mapper(
    df_preview: pd.DataFrame,
    entity: str,
    mapping: dict[str, str | None],
) -> dict[str, str | None]:
    schema = ENTITY_SCHEMA[entity]
    all_fields = schema["required"] + schema["optional"]
    options = ["— sin mapear —"] + list(df_preview.columns)
    updated: dict[str, str | None] = {}

    st.markdown("**Mapeo de columnas**")
    st.caption(
        "Revisá que cada campo interno esté asignado a la columna correcta de tu archivo. "
        "Los campos con ✱ son requeridos."
    )

    for field_name in all_fields:
        is_req = field_name in schema["required"]
        label = f"{'✱ ' if is_req else ''}`{field_name}`"

        detected = mapping.get(field_name)
        default_idx = 0
        if detected and detected in df_preview.columns:
            default_idx = list(df_preview.columns).index(detected) + 1

        selected = st.selectbox(
            label=label,
            options=options,
            index=default_idx,
            key=_k(f"map_{field_name}"),
            help=_FIELD_HELP.get(field_name, ""),
        )
        updated[field_name] = selected if selected != "— sin mapear —" else None

    return updated


def _render_preview(entity_label: str) -> None:
    entity: str = st.session_state[_k("entity")]
    df_preview: pd.DataFrame = st.session_state[_k("df_preview")]
    filename: str = st.session_state[_k("filename")]
    mapping: dict = st.session_state[_k("column_mapping")]

    col_info, col_cancel = st.columns([5, 1])
    with col_info:
        st.markdown(f"📄 **{filename}** · {entity_label} · vista previa de 5 filas")
    with col_cancel:
        if st.button("✕ Cancelar", key=_k("btn_cancel"), use_container_width=True):
            _reset_import_state()
            st.rerun()

    with st.container(border=True):
        st.dataframe(df_preview, use_container_width=True, hide_index=True)

    st.divider()

    col_mapper, col_cols = st.columns([3, 2])

    with col_mapper:
        updated_mapping = _render_column_mapper(df_preview, entity, mapping)
        st.session_state[_k("column_mapping")] = updated_mapping

    with col_cols:
        st.markdown("**Columnas en tu archivo**")
        for col in df_preview.columns:
            st.markdown(f"- `{col}`")

        missing = validate_columns(updated_mapping, entity)
        if missing:
            st.warning(f"Campos requeridos sin asignar: **{', '.join(missing)}**")

    st.divider()

    missing = validate_columns(updated_mapping, entity)
    col_btn, _ = st.columns([2, 4])
    with col_btn:
        if st.button(
            "✅ Confirmar e importar",
            key=_k("btn_confirm"),
            type="primary",
            disabled=len(missing) > 0,
            use_container_width=True,
        ):
            _set_stage("CONFIRMED")
            st.rerun()


# ── Paso 3: procesamiento ─────────────────────────────────────────────────────
def _render_processing(tenant_id: str) -> None:
    from core.database import get_anon_client  # noqa: PLC0415

    file_bytes: bytes = st.session_state[_k("file_bytes")]
    filename: str = st.session_state[_k("filename")]
    entity: str = st.session_state[_k("entity")]
    mapping: dict = st.session_state[_k("column_mapping")]

    with st.spinner("Procesando archivo…"):
        try:
            db = get_anon_client()
            result = process_import(
                tenant_id=tenant_id,
                file_bytes=file_bytes,
                filename=filename,
                entity=entity,
                column_mapping=mapping,
                db_client=db,
            )
            st.session_state[_k("result")] = result
            _set_stage("DONE")
            st.rerun()

        except ValueError as exc:
            st.error(f"**Error de validación:** {exc}")
            _set_stage("PREVIEW")
        except Exception as exc:
            logger.exception("import_processing_error")
            st.error(f"**Error inesperado:** {exc}")
            _set_stage("PREVIEW")


# ── Paso 4: resultado ─────────────────────────────────────────────────────────
def _render_done() -> None:
    result: ImportResult = st.session_state[_k("result")]
    entity_label = _ENTITY_LABELS.get(result.entity, result.entity)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total filas", result.total_rows)
    col2.metric("Importados", result.success_count, delta=f"{result.success_rate}%")
    col3.metric("Con errores", result.error_count, delta_color="inverse")
    col4.metric("Omitidos", result.skipped_count)

    if result.success_count == result.total_rows:
        st.success(
            f"✅ {result.success_count:,} {entity_label.lower()} importados correctamente."
        )
    elif result.success_count > 0:
        st.warning(
            f"⚠️ Importación parcial: {result.success_count:,} cargados, "
            f"{result.error_count:,} con errores."
        )
    else:
        st.error("❌ No se importó ningún registro. Revisá los errores.")

    if result.errors:
        with st.expander(f"Ver {len(result.errors)} error(es)", expanded=False):
            error_rows = [
                {
                    "Fila": e.row_number,
                    "Campo": e.column,
                    "Valor": str(e.value)[:60],
                    "Motivo": e.reason,
                }
                for e in result.errors[:100]
            ]
            st.dataframe(
                pd.DataFrame(error_rows), use_container_width=True, hide_index=True
            )
            if len(result.errors) > 100:
                st.caption(f"Mostrando primeros 100 de {len(result.errors)} errores.")

    st.divider()
    col_btn, _ = st.columns([2, 4])
    with col_btn:
        if st.button(
            "📂 Nueva importación", key=_k("btn_new"), use_container_width=True
        ):
            _reset_import_state()
            st.rerun()


# ── API pública ───────────────────────────────────────────────────────────────
def render_import_uploader(
    tenant_id: str,
    demo_mode: bool = False,
    vertical_labels: dict[str, Any] | None = None,
) -> None:
    """
    Componente drag & drop completo para importar CSV/XLSX.

    Flujo de estados: IDLE → PREVIEW → CONFIRMED → DONE
    Toda la lógica de negocio vive en services/import_services.py.

    Args:
        tenant_id:       UUID del tenant activo.
        demo_mode:       Si True, bloquea la importación con banner de upgrade.
        vertical_labels: Dict de labels del vertical para personalizar textos.
    """
    if not tenant_id:
        st.error("No se pudo identificar el tenant. Iniciá sesión nuevamente.")
        return

    if demo_mode:
        st.info(
            "🔒 **Importación disponible en la versión completa.** "
            "Cargá tu base de clientes, servicios y turnos históricos desde un archivo."
        )
        return

    vl = vertical_labels or {}
    entity_options = {
        vl.get("clientes_label", "Clientes / Pacientes"): "clients",
        vl.get("servicios_label", "Servicios / Productos"): "services",
        vl.get("turnos_label", "Turnos / Citas"): "appointments",
    }

    s = _stage()

    if s == "IDLE":
        _render_idle(entity_options)

    elif s == "PREVIEW":
        entity = st.session_state.get(_k("entity"), "clients")
        entity_label = _ENTITY_LABELS.get(entity, entity)
        _render_preview(entity_label)

    elif s == "CONFIRMED":
        _render_processing(tenant_id)

    elif s == "DONE":
        _render_done()
