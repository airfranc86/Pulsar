"""
agents/agent_03_saas_architect.py
===================================
Agente 03: SaaS Implementation Architect para Pulsar v1.0.

Scope estricto:
  - Arquitectura técnica de multi-tenant
  - Flujo exacto de Stripe
  - Esquema de reporte mensual
  - NO redefinir KPIs, pricing ni crear infraestructura extra
"""
from __future__ import annotations
import json
import logging
import os
import re
from typing import Any

import anthropic  # type: ignore

from agents.config import StructuredLogger, AGENT_PROHIBITIONS, ANTHROPIC_MODEL, MAX_TOKENS

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Sos el Agente 03 de Pulsar v1.0 — SaaS Implementation Architect.

Tu único scope es:
1. Diseñar la arquitectura técnica de multi-tenant en Supabase existente
2. Definir el flujo exacto de Stripe (Checkout → Webhook → Edge Function → DB)
3. Especificar el cron de reporte mensual automático
4. Definir RLS policies para Supabase

PROHIBICIONES ABSOLUTAS — No mencionés ni sugerís:
- Cambiar los KPIs ya definidos
- Proponer precios o planes
- Crear microservicios o infraestructura externa innecesaria
- Crear otro repositorio o rama separada para demo
- Migrar fuera de Supabase

Respondé SIEMPRE con JSON estructurado:
{
  "multitenant_schema": {...},
  "rls_policies": [...],
  "stripe_integration": {...},
  "cron_report_flow": {...},
  "repo_structure": {...},
  "lo_que_hice": "string",
  "lo_que_no_toque": ["lista"]
}"""


class Agent03SaaSArchitect:
    """Agente de arquitectura técnica SaaS."""

    def __init__(self) -> None:
        self.log = StructuredLogger("agent_03")
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY no configurada")
        self.client = anthropic.Anthropic(api_key=api_key)

    def run(
        self,
        agent_01_output: dict[str, Any],
        agent_02_output: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Ejecuta el agente recibiendo outputs de los Agentes 01 y 02.

        Args:
            agent_01_output: KPIs y pantallas del Agente 01.
            agent_02_output: Pricing del Agente 02.

        Returns:
            dict con arquitectura técnica completa.
        """
        self.log.info("agent_03_started")

        pricing = json.dumps(
            agent_02_output.get("output", {}).get("pricing", {}),
            ensure_ascii=False
        )[:500]

        user_prompt = f"""Pulsar v1.0 ya existe en producción con Supabase + Streamlit.

Contexto técnico:
- Stack: Python + Streamlit + Supabase (PostgreSQL + Auth + Storage + Edge Functions)
- Tenant inicial: santa-barba (peluquería)
- Plan único activo en Stripe
- Pricing aprobado: {pricing}

Diseñá:
1. Schema multi-tenant: qué columnas agregar (tenant_id UUID en cada tabla)
2. RLS policies exactas para Supabase
3. Flujo Stripe completo: Checkout Session → Webhook → Edge Function → update subscription_status
4. Cron de reporte mensual: pg_cron o Edge Function scheduler
5. Estructura del repo (ya definida, solo confirmar)

Respondé solo con JSON válido."""

        self.log.start_timer("llm_call")
        try:
            response = self.client.messages.create(
                model=ANTHROPIC_MODEL,
                max_tokens=MAX_TOKENS,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}],
            )
            self.log.end_timer("llm_call")

            raw_text = response.content[0].text if response.content else ""
            try:
                output = json.loads(raw_text)
            except json.JSONDecodeError:
                match = re.search(r"\{[\s\S]+\}", raw_text)
                output = json.loads(match.group()) if match else {"raw": raw_text}

            return {
                "output": output,
                "lo_que_hice": output.get("lo_que_hice", "Diseñé arquitectura técnica"),
                "lo_que_no_toque": output.get("lo_que_no_toque", AGENT_PROHIBITIONS["agent_03"]),
                "_meta": {
                    "model": ANTHROPIC_MODEL,
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                },
            }
        except Exception as exc:
            self.log.error("agent_03_failed", error=str(exc))
            return {"error": str(exc), "output": {}}
