"""
agents/agent_01_product_kpi.py
================================
Agente 01: Product & KPI Designer para Pulsar v1.0.

Scope estricto:
  - Definir KPIs mandatorios
  - Diseñar pantallas del dashboard
  - Definir reporte mensual
  - NO tocar Stripe, SQL schema, pricing ni deploy
"""
from __future__ import annotations
import logging
import os
from typing import Any

import anthropic  # type: ignore

from agents.config import StructuredLogger, MANDATORY_KPIS, AGENT_PROHIBITIONS, ANTHROPIC_MODEL, MAX_TOKENS

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Sos el Agente 01 de Pulsar v1.0 — Product & KPI Designer.

Tu único scope es:
1. Definir los KPIs del dashboard (los 8 obligatorios ya están fijos)
2. Especificar qué muestra cada pantalla del dashboard
3. Definir el contenido del reporte mensual automático

PROHIBICIONES ABSOLUTAS — No mencionés ni sugerís:
- Stripe, checkout, pagos, webhooks
- SQL, schema, migraciones, tablas
- Deploy, CI/CD, infraestructura
- Pricing o planes
- Features enterprise

Respondé SIEMPRE con JSON estructurado con estas claves:
{
  "kpis": {...},
  "pantallas": [...],
  "reporte_mensual": {...},
  "lo_que_hice": "string",
  "lo_que_no_toque": ["lista"]
}"""

USER_PROMPT = f"""Pulsar v1.0 es un SaaS multi-tenant para negocios de servicios.
Tenant inicial: Santa Barba (peluquería).
KPIs obligatorios: {list(MANDATORY_KPIS)}

Define:
1. Los 8 KPIs con su descripción, fórmula y visualización sugerida
2. Las 7 pantallas del dashboard y su contenido
3. El contenido del reporte mensual PDF

Adaptá los labels al vertical "peluqueria" (servicios → cortes).
Respondé solo con JSON válido."""


class Agent01ProductKPI:
    """Agente de definición de KPIs y pantallas."""

    def __init__(self) -> None:
        self.log = StructuredLogger("agent_01")
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY no configurada")
        self.client = anthropic.Anthropic(api_key=api_key)

    def run(self) -> dict[str, Any]:
        """
        Ejecuta el agente y retorna el output estructurado.

        Returns:
            dict con output, lo_que_hice, lo_que_no_toque, _meta.
        """
        self.log.info("agent_01_started")
        self.log.start_timer("llm_call")

        try:
            response = self.client.messages.create(
                model=ANTHROPIC_MODEL,
                max_tokens=MAX_TOKENS,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": USER_PROMPT}],
            )
            self.log.end_timer("llm_call")

            raw_text = response.content[0].text if response.content else ""

            import json
            try:
                output = json.loads(raw_text)
            except json.JSONDecodeError:
                import re
                match = re.search(r"\{[\s\S]+\}", raw_text)
                output = json.loads(match.group()) if match else {"raw": raw_text}

            result: dict[str, Any] = {
                "output": output,
                "lo_que_hice": output.get("lo_que_hice", "Definí KPIs y pantallas"),
                "lo_que_no_toque": output.get("lo_que_no_toque", AGENT_PROHIBITIONS["agent_01"]),
                "_meta": {
                    "model": ANTHROPIC_MODEL,
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                    "duration_s": self.log._timers.get("llm_call", 0),
                },
            }
            self.log.info("agent_01_completed", tokens=response.usage.output_tokens)
            return result

        except Exception as exc:
            self.log.error("agent_01_failed", error=str(exc))
            return {"error": str(exc), "output": {}}
