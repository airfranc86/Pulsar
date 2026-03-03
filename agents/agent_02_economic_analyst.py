"""
agents/agent_02_economic_analyst.py
=====================================
Agente 02: Economic & Trend Analyst para Pulsar v1.0.

Scope estricto:
  - Análisis de mercado y pricing para el SaaS
  - Proponer plan de precios
  - NO tocar pantallas, SQL, arquitectura ni código
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

SYSTEM_PROMPT = """Sos el Agente 02 de Pulsar v1.0 — Economic & Trend Analyst.

Tu único scope es:
1. Analizar el mercado de SaaS para pymes de servicios en Argentina/LATAM
2. Proponer un precio mensual para el plan único de Pulsar v1.0
3. Identificar features premium para versiones futuras (sin implementarlas)

PROHIBICIONES ABSOLUTAS — No mencionés ni sugerís:
- Diseño de pantallas o UI
- SQL, schema, tablas, migraciones
- Arquitectura técnica o código
- Modificaciones a los KPIs ya definidos

Respondé SIEMPRE con JSON estructurado:
{
  "pricing": {"precio_mensual_usd": N, "precio_mensual_ars": N, "justificacion": "..."},
  "mercado": {"tam": "...", "competidores": [...], "diferenciadores": [...]},
  "features_premium_v2": [...],
  "lo_que_hice": "string",
  "lo_que_no_toque": ["lista"]
}"""


class Agent02EconomicAnalyst:
    """Agente de análisis económico y pricing."""

    def __init__(self) -> None:
        self.log = StructuredLogger("agent_02")
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY no configurada")
        self.client = anthropic.Anthropic(api_key=api_key)

    def run(self, agent_01_output: dict[str, Any]) -> dict[str, Any]:
        """
        Ejecuta el agente recibiendo el output del Agente 01.

        Args:
            agent_01_output: Output del Agente 01 (KPIs definidos).

        Returns:
            dict con pricing, mercado, features_premium_v2, _meta.
        """
        self.log.info("agent_02_started")

        kpis_ref = json.dumps(
            agent_01_output.get("output", {}).get("kpis", {}),
            ensure_ascii=False
        )[:1000]

        user_prompt = f"""Pulsar v1.0: SaaS multi-tenant para negocios de servicios (peluquerías, veterinarias, talleres, clínicas).

KPIs ya definidos por el equipo de producto: {kpis_ref}

Analizá el mercado y proponé:
1. Precio mensual en USD y ARS para el plan único
2. Análisis de mercado y competidores
3. 3-5 features para versiones futuras (no para v1.0)

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
                "lo_que_hice": output.get("lo_que_hice", "Analicé mercado y pricing"),
                "lo_que_no_toque": output.get("lo_que_no_toque", AGENT_PROHIBITIONS["agent_02"]),
                "_meta": {
                    "model": ANTHROPIC_MODEL,
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                },
            }
        except Exception as exc:
            self.log.error("agent_02_failed", error=str(exc))
            return {"error": str(exc), "output": {}}
