"""
config/constants.py
===================
Constantes inmutables del sistema Pulsar v1.0.
No dependen de variables de entorno.
"""
from __future__ import annotations
from typing import Final

# ─── Tenant demo ──────────────────────────────────────────────────────────────
DEMO_TENANT_ID: Final[str] = "00000000-0000-0000-0000-000000000001"
DEMO_TENANT_SLUG: Final[str] = "santa-barba"
DEMO_TENANT_NAME: Final[str] = "Santa Barba"

# ─── Subscription states ──────────────────────────────────────────────────────
SUBSCRIPTION_ACTIVE: Final[str] = "active"
SUBSCRIPTION_INACTIVE: Final[str] = "inactive"
SUBSCRIPTION_TRIALING: Final[str] = "trialing"
SUBSCRIPTION_PAST_DUE: Final[str] = "past_due"
SUBSCRIPTION_CANCELED: Final[str] = "canceled"
ACTIVE_SUBSCRIPTION_STATES: Final[frozenset[str]] = frozenset(
    {SUBSCRIPTION_ACTIVE, SUBSCRIPTION_TRIALING}
)

# ─── Verticales ───────────────────────────────────────────────────────────────
VERTICAL_PELUQUERIA: Final[str] = "peluqueria"
VERTICAL_VETERINARIA: Final[str] = "veterinaria"
VERTICAL_TALLER: Final[str] = "taller"
VERTICAL_CONCESIONARIA: Final[str] = "concesionaria"
VERTICAL_CLINICA: Final[str] = "clinica"
VERTICAL_PYME: Final[str] = "pyme"
SUPPORTED_VERTICALS: Final[frozenset[str]] = frozenset(
    {VERTICAL_PELUQUERIA, VERTICAL_VETERINARIA, VERTICAL_TALLER,
     VERTICAL_CONCESIONARIA, VERTICAL_CLINICA, VERTICAL_PYME}
)
VERTICAL_SERVICE_LABEL: Final[dict[str, str]] = {
    VERTICAL_PELUQUERIA: "Cortes",
    VERTICAL_VETERINARIA: "Procedimientos",
    VERTICAL_TALLER: "Reparaciones",
    VERTICAL_CONCESIONARIA: "Servicios de venta",
    VERTICAL_CLINICA: "Consultas",
    VERTICAL_PYME: "Servicios",
}

# Labels por vertical (plural y singular para UI). Evita manipulación frágil tipo svc_label[:-1].
VERTICALS: Final[dict[str, dict[str, str]]] = {
    "pyme_servicios": {
        "label": "Pyme",
        "clientes_label": "Clientes",
        "servicios_label": "Servicios",
        "servicios_label_singular": "Servicio",
        "turnos_label": "Turnos",
    },
    VERTICAL_PELUQUERIA: {
        "label": "Peluquería",
        "clientes_label": "Clientes",
        "servicios_label": "Cortes",
        "servicios_label_singular": "Corte",
        "turnos_label": "Turnos",
    },
    VERTICAL_VETERINARIA: {
        "label": "Veterinaria",
        "clientes_label": "Dueños / Pacientes",
        "servicios_label": "Procedimientos",
        "servicios_label_singular": "Procedimiento",
        "turnos_label": "Citas",
    },
    VERTICAL_TALLER: {
        "label": "Taller",
        "clientes_label": "Clientes",
        "servicios_label": "Reparaciones",
        "servicios_label_singular": "Reparación",
        "turnos_label": "Órdenes de trabajo",
    },
    VERTICAL_CONCESIONARIA: {
        "label": "Concesionaria",
        "clientes_label": "Clientes",
        "servicios_label": "Servicios de venta",
        "servicios_label_singular": "Servicio de venta",
        "turnos_label": "Turnos",
    },
    VERTICAL_CLINICA: {
        "label": "Clínica",
        "clientes_label": "Pacientes",
        "servicios_label": "Consultas",
        "servicios_label_singular": "Consulta",
        "turnos_label": "Turnos",
    },
    VERTICAL_PYME: {
        "label": "Pyme",
        "clientes_label": "Clientes",
        "servicios_label": "Servicios",
        "servicios_label_singular": "Servicio",
        "turnos_label": "Reservas",
    },
}

# ─── KPIs obligatorios ────────────────────────────────────────────────────────
MANDATORY_KPIS: Final[tuple[str, ...]] = (
    "ingresos_mensuales", "ticket_promedio", "servicios_mas_vendidos",
    "clientes_nuevos_vs_recurrentes", "ocupacion_turnos",
    "cancelaciones_no_shows", "horas_pico", "comparacion_mes_anterior",
)

# ─── Estados de turno ─────────────────────────────────────────────────────────
APPOINTMENT_PENDING: Final[str] = "pendiente"
APPOINTMENT_CONFIRMED: Final[str] = "confirmado"
APPOINTMENT_COMPLETED: Final[str] = "completado"
APPOINTMENT_CANCELLED: Final[str] = "cancelado"
APPOINTMENT_NO_SHOW: Final[str] = "no_show"
APPOINTMENT_STATES: Final[frozenset[str]] = frozenset(
    {APPOINTMENT_PENDING, APPOINTMENT_CONFIRMED, APPOINTMENT_COMPLETED,
     APPOINTMENT_CANCELLED, APPOINTMENT_NO_SHOW}
)
BILLABLE_APPOINTMENT_STATES: Final[frozenset[str]] = frozenset(
    {APPOINTMENT_COMPLETED, APPOINTMENT_CONFIRMED}
)
# Alias usado en analytics y pages
APPOINTMENT_STATES_BILLABLE: Final[frozenset[str]] = BILLABLE_APPOINTMENT_STATES

# ─── Ocupación (capacidad real para métrica) ───────────────────────────────────
# Slots por día asumidos cuando el tenant no tiene configuración. Ajustar por vertical si hace falta.
SLOTS_POR_DIA_DEFAULT: Final[int] = 32

# ─── Límites demo ─────────────────────────────────────────────────────────────
DEMO_MAX_CLIENTS_VISIBLE: Final[int] = 10
DEMO_MAX_SERVICES_VISIBLE: Final[int] = 5
DEMO_MAX_APPOINTMENTS_VISIBLE: Final[int] = 20

# ─── Paginación ───────────────────────────────────────────────────────────────
DEFAULT_PAGE_SIZE: Final[int] = 50
MAX_PAGE_SIZE: Final[int] = 500

# ─── Stripe ───────────────────────────────────────────────────────────────────
STRIPE_WEBHOOK_EVENTS: Final[frozenset[str]] = frozenset(
    {"checkout.session.completed", "customer.subscription.updated",
     "customer.subscription.deleted", "invoice.payment_failed"}
)

# ─── Storage ──────────────────────────────────────────────────────────────────
STORAGE_BUCKET_REPORTS: Final[str] = "monthly-reports"
STORAGE_PATH_TEMPLATE: Final[str] = "{tenant_id}/{year}/{month:02d}/report.pdf"

# ─── Retry ────────────────────────────────────────────────────────────────────
MAX_RETRY_ATTEMPTS: Final[int] = 3
RETRY_BACKOFF_BASE_SECONDS: Final[float] = 1.5

# ─── Formatos de fecha ────────────────────────────────────────────────────────
DATE_FORMAT: Final[str] = "%Y-%m-%d"
DATETIME_FORMAT: Final[str] = "%Y-%m-%dT%H:%M:%SZ"
DISPLAY_DATE_FORMAT: Final[str] = "%d/%m/%Y"
DISPLAY_DATETIME_FORMAT: Final[str] = "%d/%m/%Y %H:%M"
