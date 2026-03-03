"""
config/logging_config.py
========================
Logging estructurado en JSON para Pulsar v1.0.

Uso en cada módulo:
    import logging
    logger = logging.getLogger(__name__)
"""
from __future__ import annotations
import json
import logging
import sys
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Optional


class JSONFormatter(logging.Formatter):
    """Serializa cada LogRecord como una línea JSON con campos estándar."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key in ("tenant_id", "run_id", "user_id", "duration_ms", "event", "error"):
            val = getattr(record, key, None)
            if val is not None:
                payload[key] = val
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


class PulsarLogger:
    """
    Logger contextual que inyecta tenant_id y run_id en cada registro.
    Instanciar por operación/request; no usar como singleton global.
    """

    def __init__(
        self,
        name: str,
        tenant_id: Optional[str] = None,
        run_id: Optional[str] = None,
    ) -> None:
        self._logger = logging.getLogger(name)
        self.tenant_id = tenant_id
        self.run_id = run_id or str(uuid.uuid4())[:8]
        self._timers: dict[str, float] = {}

    def _extra(self, **kwargs: Any) -> dict[str, Any]:
        base: dict[str, Any] = {"run_id": self.run_id}
        if self.tenant_id:
            base["tenant_id"] = self.tenant_id
        base.update(kwargs)
        return base

    def info(self, event: str, **kwargs: Any) -> None:
        self._logger.info(event, extra=self._extra(event=event, **kwargs))

    def warning(self, event: str, **kwargs: Any) -> None:
        self._logger.warning(event, extra=self._extra(event=event, **kwargs))

    def error(self, event: str, **kwargs: Any) -> None:
        self._logger.error(event, extra=self._extra(event=event, **kwargs))

    def debug(self, event: str, **kwargs: Any) -> None:
        self._logger.debug(event, extra=self._extra(event=event, **kwargs))

    def start_timer(self, stage: str) -> None:
        self._timers[stage] = time.monotonic()

    def end_timer(self, stage: str) -> float:
        """Finaliza cronómetro y loggea duración en ms."""
        elapsed_ms = round(
            (time.monotonic() - self._timers.get(stage, time.monotonic())) * 1000, 2
        )
        self.info("stage_complete", stage=stage, duration_ms=elapsed_ms)
        return elapsed_ms


def setup_logging(level: str = "INFO") -> None:
    """
    Configura el sistema de logging global.
    Llamar una sola vez al iniciar la app (app.py).

    Args:
        level: Nivel de log (DEBUG, INFO, WARNING, ERROR).
    """
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    root_logger.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    handler.setLevel(numeric_level)
    root_logger.addHandler(handler)

    for noisy in ("httpx", "httpcore", "urllib3", "supabase", "gotrue", "postgrest"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    logging.getLogger(__name__).info(
        "logging_initialized",
        extra={"event": "logging_initialized", "log_level": level},
    )


def get_logger(name: str, tenant_id: Optional[str] = None) -> PulsarLogger:
    """
    Factory para PulsarLogger contextual.

    Args:
        name: Nombre del módulo (usar __name__).
        tenant_id: UUID del tenant activo.

    Returns:
        PulsarLogger listo con contexto inyectado.
    """
    return PulsarLogger(name=name, tenant_id=tenant_id)
