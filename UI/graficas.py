"""
Pulsar v1.0 — UI/graficas.py
==============================
Componentes de visualización. Todas las gráficas usan Altair.
Solo presentación. Los datos ya deben venir calculados y limpios.

Paleta Pulsar definida en PULSAR_PALETTE.
Alturas fijas por tipo de gráfica para consistencia visual entre pages.

Exports públicos:
    render_servicios_bar(data, label_field, value_field, title)
    render_clientes_donut(nuevos, recurrentes, title)
    render_horas_pico_heatmap(horas, title)
    render_ingresos_timeline(data, date_field, value_field, title)
"""

import altair as alt
import pandas as pd
import streamlit as st

# ── Paleta de marca ───────────────────────────────────────────────────────────
PULSAR_PALETTE = {
    "primary": "#6366F1",  # Indigo
    "secondary": "#8B5CF6",  # Violeta
    "accent": "#06B6D4",  # Cyan
    "neutral": "#E2E8F0",  # Gris claro
    "success": "#10B981",  # Verde
    "warning": "#F59E0B",  # Amarillo
    "danger": "#EF4444",  # Rojo
    "text": "#1E293B",  # Texto oscuro
    "muted": "#94A3B8",  # Texto secundario
}

# Alturas fijas por tipo
_H_BAR = 280
_H_DONUT = 260
_H_HEATMAP = 220
_H_TIMELINE = 300


# ── Config base reutilizable ──────────────────────────────────────────────────
def _base_props(height: int, title: str = "") -> dict:
    """Propiedades comunes para todos los charts."""
    props: dict = {
        "background": "transparent",
        "height": height,
        "padding": {"left": 4, "right": 4, "top": 8, "bottom": 4},
    }
    if title:
        props["title"] = alt.TitleParams(
            text=title,
            fontSize=14,
            fontWeight="normal",
            color=PULSAR_PALETTE["text"],
            anchor="start",
        )
    return props


def _no_data_notice(message: str = "Sin datos para el período seleccionado.") -> None:
    st.info(message, icon="📭")


# ── 1. Barras horizontales — Servicios más frecuentes ────────────────────────
def render_servicios_bar(
    data: list[dict] | None,
    label_field: str,
    value_field: str,
    title: str = "Servicios más frecuentes",
) -> None:
    """
    Barras horizontales ordenadas descendente.

    Args:
        data:        Lista de dicts. Cada dict debe tener label_field y value_field.
        label_field: Nombre de la clave con la etiqueta (eje Y).
        value_field: Nombre de la clave con el valor numérico (eje X).
        title:       Título del chart.
    """
    if not data:
        _no_data_notice()
        return

    df = pd.DataFrame(data)

    if label_field not in df.columns or value_field not in df.columns:
        _no_data_notice(f"Columnas esperadas: '{label_field}', '{value_field}'.")
        return

    df = df[[label_field, value_field]].dropna()
    df[value_field] = pd.to_numeric(df[value_field], errors="coerce").fillna(0)

    chart = (
        alt.Chart(df)
        .mark_bar(
            color=PULSAR_PALETTE["primary"],
            cornerRadiusTopRight=4,
            cornerRadiusBottomRight=4,
        )
        .encode(
            y=alt.Y(
                f"{label_field}:N",
                sort=alt.EncodingSortField(field=value_field, order="descending"),
                axis=alt.Axis(
                    labelFontSize=12,
                    labelColor=PULSAR_PALETTE["text"],
                    labelLimit=180,
                    ticks=False,
                    domain=False,
                    title=None,
                ),
            ),
            x=alt.X(
                f"{value_field}:Q",
                axis=alt.Axis(
                    grid=False,
                    labelFontSize=11,
                    labelColor=PULSAR_PALETTE["muted"],
                    title=None,
                ),
            ),
            tooltip=[
                alt.Tooltip(f"{label_field}:N", title="Servicio"),
                alt.Tooltip(f"{value_field}:Q", title="Cantidad", format=","),
            ],
        )
        .properties(**_base_props(_H_BAR, title))
        .configure_view(strokeWidth=0)
        .configure_axis(labelFontSize=12)
    )

    st.altair_chart(chart, use_container_width=True)


# ── 2. Donut — Nuevos vs Recurrentes ─────────────────────────────────────────
def render_clientes_donut(
    nuevos: int,
    recurrentes: int,
    title: str = "Nuevos vs Recurrentes",
) -> None:
    """
    Donut chart con dos segmentos: clientes nuevos y recurrentes.

    Args:
        nuevos:      Cantidad de clientes nuevos.
        recurrentes: Cantidad de clientes recurrentes.
        title:       Título del chart.
    """
    total = nuevos + recurrentes
    if total == 0:
        _no_data_notice("Sin clientes en el período.")
        return

    df = pd.DataFrame(
        [
            {
                "tipo": "Nuevos",
                "cantidad": nuevos,
                "porcentaje": f"{nuevos / total * 100:.1f}%",
            },
            {
                "tipo": "Recurrentes",
                "cantidad": recurrentes,
                "porcentaje": f"{recurrentes / total * 100:.1f}%",
            },
        ]
    )

    chart = (
        alt.Chart(df)
        .mark_arc(innerRadius=65, outerRadius=105, stroke="white", strokeWidth=2)
        .encode(
            theta=alt.Theta("cantidad:Q"),
            color=alt.Color(
                "tipo:N",
                scale=alt.Scale(
                    domain=["Nuevos", "Recurrentes"],
                    range=[PULSAR_PALETTE["primary"], PULSAR_PALETTE["neutral"]],
                ),
                legend=alt.Legend(
                    orient="bottom",
                    labelFontSize=12,
                    labelColor=PULSAR_PALETTE["text"],
                    symbolSize=80,
                    title=None,
                ),
            ),
            tooltip=[
                alt.Tooltip("tipo:N", title="Tipo"),
                alt.Tooltip("cantidad:Q", title="Clientes", format=","),
                alt.Tooltip("porcentaje:N", title="% del total"),
            ],
        )
        .properties(**_base_props(_H_DONUT, title))
        .configure_view(strokeWidth=0)
    )

    st.altair_chart(chart, use_container_width=True)


# ── 3. Heatmap — Horas pico ───────────────────────────────────────────────────
def render_horas_pico_heatmap(
    horas: dict | list | None,
    title: str = "Horas pico del período",
) -> None:
    """
    Heatmap de calor: eje X = hora (0-23), eje Y = día de semana.

    Args:
        horas: Dict {dia: {hora: count}} o lista de dicts {dia, hora, count}.
        title: Título del chart.
    """
    if not horas:
        _no_data_notice("Sin datos de horas pico para el período.")
        return

    # Normalizar a lista de dicts
    if isinstance(horas, dict):
        rows = []
        for dia, horas_dict in horas.items():
            if isinstance(horas_dict, dict):
                for hora, count in horas_dict.items():
                    rows.append(
                        {"dia": str(dia), "hora": int(hora), "cantidad": int(count)}
                    )
            else:
                # Formato alternativo: {hora: count} sin día
                rows.append(
                    {"dia": "General", "hora": int(dia), "cantidad": int(horas_dict)}
                )
        df = pd.DataFrame(rows)
    else:
        df = pd.DataFrame(horas)

    if df.empty or "hora" not in df.columns or "cantidad" not in df.columns:
        _no_data_notice()
        return

    if "dia" not in df.columns:
        df["dia"] = "General"

    _DIAS_ORDER = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom", "General"]
    dias_presentes = [d for d in _DIAS_ORDER if d in df["dia"].unique()]

    chart = (
        alt.Chart(df)
        .mark_rect(cornerRadius=3)
        .encode(
            x=alt.X(
                "hora:O",
                title="hora del día",
                axis=alt.Axis(labelFontSize=11, labelColor=PULSAR_PALETTE["muted"]),
            ),
            y=alt.Y(
                "dia:O",
                sort=dias_presentes if dias_presentes else alt.Undefined,
                title=None,
                axis=alt.Axis(
                    labelFontSize=12, labelColor=PULSAR_PALETTE["text"], ticks=False
                ),
            ),
            color=alt.Color(
                "cantidad:Q",
                scale=alt.Scale(
                    scheme="purples",
                    domain=[0, df["cantidad"].max()],
                ),
                legend=alt.Legend(
                    title="turnos",
                    labelFontSize=11,
                    orient="right",
                ),
            ),
            tooltip=[
                alt.Tooltip("dia:O", title="Día"),
                alt.Tooltip("hora:O", title="Hora"),
                alt.Tooltip("cantidad:Q", title="Turnos", format=","),
            ],
        )
        .properties(**_base_props(_H_HEATMAP, title))
        .configure_view(strokeWidth=0)
    )

    st.altair_chart(chart, use_container_width=True)


# ── 4. Timeline — Evolución de ingresos ──────────────────────────────────────
def render_ingresos_timeline(
    data: list[dict] | None,
    date_field: str,
    value_field: str,
    title: str = "Evolución de ingresos",
) -> None:
    """
    Línea de tiempo con área rellena y punto interactivo en hover.

    Args:
        data:        Lista de dicts con date_field y value_field.
        date_field:  Clave de fecha (str ISO o date).
        value_field: Clave de valor numérico.
        title:       Título del chart.
    """
    if not data:
        _no_data_notice()
        return

    df = pd.DataFrame(data)

    if date_field not in df.columns or value_field not in df.columns:
        _no_data_notice(f"Columnas esperadas: '{date_field}', '{value_field}'.")
        return

    df[date_field] = pd.to_datetime(df[date_field], errors="coerce")
    df[value_field] = pd.to_numeric(df[value_field], errors="coerce").fillna(0)
    df = df.dropna(subset=[date_field]).sort_values(date_field)

    if df.empty:
        _no_data_notice()
        return

    # Selector para hover interactivo
    nearest = alt.selection_point(
        nearest=True,
        on="mouseover",
        fields=[date_field],
        empty=False,
    )

    base = alt.Chart(df).encode(
        x=alt.X(
            f"{date_field}:T",
            title=None,
            axis=alt.Axis(
                format="%d %b",
                labelFontSize=11,
                labelColor=PULSAR_PALETTE["muted"],
                grid=False,
                ticks=False,
            ),
        )
    )

    # Área rellena
    area = base.mark_area(
        color=alt.Gradient(
            gradient="linear",
            stops=[
                alt.GradientStop(color=PULSAR_PALETTE["primary"] + "55", offset=0),
                alt.GradientStop(color=PULSAR_PALETTE["primary"] + "08", offset=1),
            ],
            x1=1,
            x2=1,
            y1=1,
            y2=0,
        ),
        interpolate="monotone",
    ).encode(
        y=alt.Y(
            f"{value_field}:Q",
            title=None,
            axis=alt.Axis(
                format="$,.0f",
                labelFontSize=11,
                labelColor=PULSAR_PALETTE["muted"],
                grid=True,
                gridColor="#F1F5F9",
                ticks=False,
                domain=False,
            ),
        )
    )

    # Línea principal
    line = base.mark_line(
        color=PULSAR_PALETTE["primary"],
        strokeWidth=2,
        interpolate="monotone",
    ).encode(y=alt.Y(f"{value_field}:Q"))

    # Regla vertical en hover
    rule = (
        base.mark_rule(color=PULSAR_PALETTE["muted"], strokeDash=[4, 4], strokeWidth=1)
        .encode(
            opacity=alt.condition(nearest, alt.value(1), alt.value(0)),
            tooltip=[
                alt.Tooltip(f"{date_field}:T", title="Fecha", format="%d %b %Y"),
                alt.Tooltip(f"{value_field}:Q", title="Ingresos", format="$,.0f"),
            ],
        )
        .add_params(nearest)
    )

    # Punto en hover
    points = base.mark_point(
        color=PULSAR_PALETTE["primary"],
        size=60,
        filled=True,
    ).encode(
        y=alt.Y(f"{value_field}:Q"),
        opacity=alt.condition(nearest, alt.value(1), alt.value(0)),
    )

    chart = (
        alt.layer(area, line, rule, points)
        .properties(**_base_props(_H_TIMELINE, title))
        .configure_view(strokeWidth=0)
    )

    st.altair_chart(chart, use_container_width=True)
