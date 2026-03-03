"""
Pulsar v1.0 — Domain Models
==============================
Modelos Pydantic que representan las entidades del dominio.
Sin IO. Sin acceso a base de datos. Contratos entre capas.

Garantía multi-tenant: tenant_id es obligatorio en todos los modelos
que persisten en Supabase. Validado a nivel de tipo, no solo runtime.
"""

import uuid
from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator, model_validator


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _new_uuid() -> str:
    return str(uuid.uuid4())


# ─── Tenant ───────────────────────────────────────────────────────────────────

class Tenant(BaseModel):
    id: str = Field(default_factory=_new_uuid)
    slug: str
    name: str
    vertical: str = "pyme_servicios"
    subscription_status: str = "inactive"
    current_period_end: Optional[datetime] = None
    stripe_customer_id: Optional[str] = None
    stripe_subscription_id: Optional[str] = None
    report_day: int = Field(default=1, ge=1, le=28)
    report_email: Optional[str] = None
    created_at: Optional[datetime] = None

    @field_validator("vertical")
    @classmethod
    def validate_vertical(cls, v: str) -> str:
        allowed = {
            "peluqueria", "veterinaria", "taller_mecanico",
            "concesionaria", "clinica", "pyme_servicios",
        }
        if v not in allowed:
            raise ValueError(f"Vertical inválido: '{v}'. Permitidos: {allowed}")
        return v

    @field_validator("report_day")
    @classmethod
    def validate_report_day(cls, v: int) -> int:
        if not 1 <= v <= 28:
            raise ValueError("report_day debe estar entre 1 y 28.")
        return v


# ─── Client ───────────────────────────────────────────────────────────────────

class Client(BaseModel):
    id: str = Field(default_factory=_new_uuid)
    tenant_id: str
    nombre: str = Field(..., min_length=1, max_length=120)
    apellido: Optional[str] = None
    email: Optional[str] = None
    telefono: Optional[str] = None
    notas: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        if v and "@" not in v:
            raise ValueError("Email inválido.")
        return v


class ClientCreate(BaseModel):
    tenant_id: str
    nombre: str = Field(..., min_length=1, max_length=120)
    apellido: Optional[str] = None
    email: Optional[str] = None
    telefono: Optional[str] = None
    notas: Optional[str] = None


# ─── Service ──────────────────────────────────────────────────────────────────

class Service(BaseModel):
    id: str = Field(default_factory=_new_uuid)
    tenant_id: str
    nombre: str = Field(..., min_length=1, max_length=120)
    descripcion: Optional[str] = None
    precio: float = Field(..., ge=0)
    duracion_minutos: int = Field(default=60, ge=5, le=480)
    activo: bool = True
    created_at: Optional[datetime] = None


class ServiceCreate(BaseModel):
    tenant_id: str
    nombre: str = Field(..., min_length=1, max_length=120)
    descripcion: Optional[str] = None
    precio: float = Field(..., ge=0)
    duracion_minutos: int = Field(default=60, ge=5, le=480)
    activo: bool = True


# ─── Appointment ──────────────────────────────────────────────────────────────

VALID_APPOINTMENT_STATES = frozenset([
    "pendiente", "confirmado", "completado", "cancelado", "no_show",
])


class Appointment(BaseModel):
    id: str = Field(default_factory=_new_uuid)
    tenant_id: str
    client_id: str
    servicio_id: str
    fecha: date
    hora: str                           # HH:MM
    estado: str = "pendiente"
    notas: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @field_validator("estado")
    @classmethod
    def validate_estado(cls, v: str) -> str:
        if v not in VALID_APPOINTMENT_STATES:
            raise ValueError(f"Estado inválido: '{v}'.")
        return v

    @field_validator("hora")
    @classmethod
    def validate_hora(cls, v: str) -> str:
        parts = v.split(":")
        if len(parts) != 2:
            raise ValueError("hora debe ser HH:MM")
        h, m = int(parts[0]), int(parts[1])
        if not (0 <= h <= 23 and 0 <= m <= 59):
            raise ValueError("hora fuera de rango.")
        return v


class AppointmentCreate(BaseModel):
    tenant_id: str
    client_id: str
    servicio_id: str
    fecha: date
    hora: str
    estado: str = "pendiente"
    notas: Optional[str] = None


# ─── Subscription ─────────────────────────────────────────────────────────────

class Subscription(BaseModel):
    id: str = Field(default_factory=_new_uuid)
    tenant_id: str
    stripe_subscription_id: str
    stripe_customer_id: str
    status: str
    current_period_end: datetime
    price_id: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ─── Report History ───────────────────────────────────────────────────────────

class ReportHistory(BaseModel):
    id: str = Field(default_factory=_new_uuid)
    tenant_id: str
    period_label: str                   # "2025-01"
    storage_path: str
    sent_to_email: Optional[str] = None
    sent_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


# ─── KPI Snapshot (no persiste, se calcula al vuelo) ─────────────────────────

class KPISnapshot(BaseModel):
    tenant_id: str
    period_label: str
    ingresos_mensuales: float = 0.0
    ticket_promedio: float = 0.0
    total_turnos: int = 0
    ocupacion_turnos: float = 0.0       # 0.0 - 1.0
    cancelaciones: int = 0
    no_shows: int = 0
    clientes_nuevos: int = 0
    clientes_recurrentes: int = 0
    comparacion_mes_anterior: float = 0.0  # ratio vs mes anterior
    computed_at: datetime = Field(default_factory=datetime.utcnow)
