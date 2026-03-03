"""
agents/config.py
=================
Configuración compartida del sistema multi-agente de Pulsar v1.0.

Compatible con el config.py raíz existente.
Este archivo centraliza constantes específicas de los agentes.
"""
from __future__ import annotations
import json
import os
import time
import uuid
from datetime import datetime
from typing import Any

# ─── Modelo Anthropic ─────────────────────────────────────────────────────────
ANTHROPIC_MODEL: str = "claude-sonnet-4-20250514"
MAX_TOKENS: int = 4096

# ─── Tenant inicial ───────────────────────────────────────────────────────────
INITIAL_TENANT: dict[str, str] = {
    "id": "001",
    "slug": "santa-barba",
    "name": "Santa Barba Dashboard",
}

# ─── KPIs obligatorios ────────────────────────────────────────────────────────
MANDATORY_KPIS: tuple[str, ...] = (
    "ingresos_mensuales", "ticket_promedio", "servicios_mas_vendidos",
    "clientes_nuevos_vs_recurrentes", "ocupacion_turnos",
    "cancelaciones_no_shows", "horas_pico", "comparacion_mes_anterior",
)

# ─── Guardarraíles por agente ─────────────────────────────────────────────────
AGENT_PROHIBITIONS: dict[str, list[str]] = {
    "agent_01": [
        "tocar Stripe", "tocar Supabase schema", "tocar deploy o CI/CD",
        "redefinir pricing", "inventar features enterprise",
    ],
    "agent_02": [
        "diseñar pantallas", "escribir schema SQL", "proponer arquitectura técnica",
        "modificar KPIs", "tocar código",
    ],
    "agent_03": [
        "redefinir KPIs", "inventar pricing", "agregar features fuera del MVP",
        "crear otro repositorio", "duplicar código demo/full",
        "migrar fuera de Supabase", "introducir Render o infraestructura innecesaria",
    ],
}


class StructuredLogger:
    """Logger JSON trazable por run_id para agentes."""

    def __init__(self, agent_name: str, log_dir: str = "logs") -> None:
        self.agent_name = agent_name
        self.run_id = str(uuid.uuid4())[:8]
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)
        self.log_file = os.path.join(
            log_dir,
            f"{agent_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
        )
        self._timers: dict[str, float] = {}

    def _write(self, level: str, event: str, **kwargs: Any) -> None:
        record = {
            "ts": datetime.utcnow().isoformat() + "Z",
            "run_id": self.run_id,
            "agent": self.agent_name,
            "level": level,
            "event": event,
            **kwargs,
        }
        line = json.dumps(record, ensure_ascii=False)
        print(line)
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(line + "\n")

    def info(self, event: str, **kwargs: Any) -> None:
        self._write("INFO", event, **kwargs)

    def warning(self, event: str, **kwargs: Any) -> None:
        self._write("WARNING", event, **kwargs)

    def error(self, event: str, **kwargs: Any) -> None:
        self._write("ERROR", event, **kwargs)

    def start_timer(self, stage: str) -> None:
        self._timers[stage] = time.time()

    def end_timer(self, stage: str) -> float:
        elapsed = round(time.time() - self._timers.get(stage, time.time()), 3)
        self.info("stage_complete", stage=stage, duration_s=elapsed)
        return elapsed
