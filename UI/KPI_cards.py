"""
Pulsar v1.0 — UI/KPI_cards.py
================================
Componentes de tarjetas KPI para el Panel y otras pages.
Solo presentación. Los valores ya deben venir calculados.

Exports públicos:
    render_kpi_row_ingresos(ingresos, ticket, turnos, comparacion)
    render_kpi_row_operativo(ocupacion, cancelados, no_shows, nuevos, recurrentes)
    render_demo_kpi_overlay()
    render_upgrade_banner(message)
    render_kpi_single(label, value, delta, delta_color, help_text)
"""

import streamlit as st


# ── Helpers internos ──────────────────────────────────────────────────────────


def _fmt_money(value: float) -> str:
    """Formatea número como moneda argentina. Ej: 1245000 → '$ 1.245.000'"""
    return f"$ {value:,.0f}".replace(",", ".")


def _fmt_pct(value: float, decimals: int = 1) -> str:
    return f"{value:.{decimals}f}%"


def _delta_color_for_delta(delta: float) -> str:
    """Retorna 'normal' si positivo (verde = bueno), 'inverse' si negativo."""
    return "normal" if delta >= 0 else "inverse"


# ── Rows de KPIs ─────────────────────────────────────────────────────────────


def render_kpi_row_ingresos(
    ingresos: float,
    ticket: float,
    n_turnos: int,
    comparacion: dict,
) -> None:
    """
    Fila de 4 métricas financieras principales.

    Args:
        ingresos:    Total facturado en el período.
        ticket:      Ticket promedio.
        n_turnos:    Cantidad de turnos/servicios facturados.
        comparacion: Dict con {'delta_abs': float, 'delta_pct': float}
                     comparando vs período anterior.
    """
    delta_pct: float = comparacion.get("delta_pct", 0.0)
    delta_label = f"{'+' if delta_pct >= 0 else ''}{delta_pct:.1f}% vs mes ant."

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="Ingresos del período",
            value=_fmt_money(ingresos),
            delta=delta_label,
            delta_color=_delta_color_for_delta(delta_pct),
            help="Total facturado en el período seleccionado.",
        )
    with col2:
        st.metric(
            label="Ticket promedio",
            value=_fmt_money(ticket),
            help="Ingreso promedio por turno/servicio completado.",
        )
    with col3:
        st.metric(
            label="Servicios facturados",
            value=f"{n_turnos:,}",
            help="Cantidad de turnos o servicios en estado completado.",
        )
    with col4:
        delta_abs: float = comparacion.get("delta_abs", 0.0)
        abs_label = f"{'+' if delta_abs >= 0 else ''}{_fmt_money(abs(delta_abs))}"
        st.metric(
            label="Diferencia vs mes ant.",
            value=abs_label,
            delta=delta_label,
            delta_color=_delta_color_for_delta(delta_pct),
            help="Diferencia absoluta de ingresos respecto al período anterior.",
        )


def render_kpi_row_operativo(
    ocupacion: float,
    cancelados: int,
    no_shows: int,
    nuevos: int,
    recurrentes: int,
) -> None:
    """
    Fila de 5 métricas operativas.

    Args:
        ocupacion:   Tasa de ocupación 0-100.
        cancelados:  Cantidad de turnos cancelados.
        no_shows:    Cantidad de no-shows.
        nuevos:      Clientes nuevos en el período.
        recurrentes: Clientes recurrentes en el período.
    """
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        color = "normal" if ocupacion >= 70 else "off"
        st.metric(
            label="Ocupación",
            value=_fmt_pct(ocupacion),
            delta="≥70% objetivo" if ocupacion >= 70 else "<70% objetivo",
            delta_color=color,
            help="Turnos completados sobre el total de turnos registrados.",
        )
    with col2:
        st.metric(
            label="Cancelaciones",
            value=f"{cancelados:,}",
            delta_color="inverse",
            help="Cantidad de turnos cancelados en el período.",
        )
    with col3:
        st.metric(
            label="No-shows",
            value=f"{no_shows:,}",
            delta_color="inverse",
            help="Clientes que no se presentaron sin cancelar.",
        )
    with col4:
        st.metric(
            label="Clientes nuevos",
            value=f"{nuevos:,}",
            help="Clientes con su primera visita en el período.",
        )
    with col5:
        total = nuevos + recurrentes
        pct_ret = (recurrentes / total * 100) if total > 0 else 0.0
        st.metric(
            label="Recurrentes",
            value=f"{recurrentes:,}",
            delta=f"{_fmt_pct(pct_ret)} del total",
            help="Clientes con más de una visita histórica.",
        )


# ── Overlays de demo y upgrade ────────────────────────────────────────────────


def render_demo_kpi_overlay() -> None:
    """
    Bloque que reemplaza KPIs bloqueados en demo mode.
    Muestra métricas ocultas con un CTA de upgrade.
    """
    with st.container(border=True):
        col_msg, col_cta = st.columns([4, 1])
        with col_msg:
            st.markdown(
                "🔒 **Métricas operativas disponibles en la versión completa:** "
                "ocupación, cancelaciones, no-shows y retención de clientes."
            )
        with col_cta:
            st.page_link("pages/08_Upgrade.py", label="Activar →", icon="⚡")


def render_upgrade_banner(
    message: str = "Activá tu suscripción para acceder a esta función.",
) -> None:
    """Banner de upgrade inline, para usar dentro de secciones bloqueadas."""
    st.info(f"🔒 {message}", icon=None)
    col_btn, _ = st.columns([2, 4])
    with col_btn:
        st.page_link("pages/08_Upgrade.py", label="Ver planes y precios →", icon="⚡")


# ── KPI individual (uso genérico) ─────────────────────────────────────────────


def render_kpi_single(
    label: str,
    value: str,
    delta: str | None = None,
    delta_color: str = "normal",
    help_text: str = "",
) -> None:
    """
    Métrica individual. Wrapper delgado sobre st.metric para
    mantener consistencia visual en todo el proyecto.
    """
    st.metric(
        label=label,
        value=value,
        delta=delta,
        delta_color=delta_color,
        help=help_text or None,
    )
