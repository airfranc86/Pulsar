-- Pulsar v1.0 — Initial Schema + Multi-Tenant + RLS
-- Run in Supabase SQL Editor

-- ─── Tenants ──────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    vertical TEXT NOT NULL DEFAULT 'pyme_servicios',
    subscription_status TEXT NOT NULL DEFAULT 'inactive',
    current_period_end TIMESTAMPTZ,
    stripe_customer_id TEXT,
    stripe_subscription_id TEXT,
    report_day INTEGER NOT NULL DEFAULT 1 CHECK (report_day BETWEEN 1 AND 28),
    report_email TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ─── Clients ──────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS clients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    nombre TEXT NOT NULL,
    apellido TEXT,
    email TEXT,
    telefono TEXT,
    notas TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_clients_tenant ON clients(tenant_id);

-- ─── Services ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS services (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    nombre TEXT NOT NULL,
    descripcion TEXT,
    precio NUMERIC(10,2) NOT NULL DEFAULT 0,
    duracion_minutos INTEGER NOT NULL DEFAULT 60,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_services_tenant ON services(tenant_id);

-- ─── Appointments ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS appointments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    client_id UUID NOT NULL REFERENCES clients(id),
    servicio_id UUID NOT NULL REFERENCES services(id),
    fecha DATE NOT NULL,
    hora TIME NOT NULL,
    estado TEXT NOT NULL DEFAULT 'pendiente'
        CHECK (estado IN ('pendiente','confirmado','completado','cancelado','no_show')),
    notas TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_appointments_tenant ON appointments(tenant_id);
CREATE INDEX IF NOT EXISTS idx_appointments_fecha ON appointments(tenant_id, fecha);

-- ─── Report History ───────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS report_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    period_label TEXT NOT NULL,  -- "2025-01"
    storage_path TEXT NOT NULL,
    sent_to_email TEXT,
    sent_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_report_history_tenant ON report_history(tenant_id);

-- ─── RLS Policies ─────────────────────────────────────────────────────────────
ALTER TABLE clients ENABLE ROW LEVEL SECURITY;
ALTER TABLE services ENABLE ROW LEVEL SECURITY;
ALTER TABLE appointments ENABLE ROW LEVEL SECURITY;
ALTER TABLE report_history ENABLE ROW LEVEL SECURITY;

-- Política: usuario solo ve datos de su tenant
-- El tenant_id debe estar en el JWT claim: app_metadata.tenant_id

CREATE POLICY "tenant_isolation_clients" ON clients
    USING (tenant_id::text = (auth.jwt() -> 'app_metadata' ->> 'tenant_id'));

CREATE POLICY "tenant_isolation_services" ON services
    USING (tenant_id::text = (auth.jwt() -> 'app_metadata' ->> 'tenant_id'));

CREATE POLICY "tenant_isolation_appointments" ON appointments
    USING (tenant_id::text = (auth.jwt() -> 'app_metadata' ->> 'tenant_id'));

CREATE POLICY "tenant_isolation_report_history" ON report_history
    USING (tenant_id::text = (auth.jwt() -> 'app_metadata' ->> 'tenant_id'));

-- ─── Demo tenant (Tenant 001 — Santa Barba) ───────────────────────────────────
INSERT INTO tenants (id, slug, name, vertical, subscription_status)
VALUES (
    '00000000-0000-0000-0000-000000000001',
    'santa-barba',
    'Santa Barba',
    'peluqueria',
    'inactive'
) ON CONFLICT (id) DO NOTHING;
