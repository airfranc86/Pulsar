"""
Tests unitarios para analytics/retention_metrics.py.
Funciones puras: compute_clientes_nuevos_vs_recurrentes y compute_retention_rate.
"""
from __future__ import annotations

import pytest

from analytics.retention_metrics import (
    compute_clientes_nuevos_vs_recurrentes,
    compute_retention_rate,
)


# ─── compute_clientes_nuevos_vs_recurrentes ──────────────────────────────────

def test_clientes_nuevos_vs_recurrentes_vacio() -> None:
    assert compute_clientes_nuevos_vs_recurrentes([], []) == {
        "nuevos": 0,
        "recurrentes": 0,
    }


def test_clientes_nuevos_todos_nuevos() -> None:
    turnos_periodo = [
        {"client_id": "c1"},
        {"client_id": "c2"},
    ]
    turnos_historicos: list[dict] = []
    assert compute_clientes_nuevos_vs_recurrentes(
        turnos_periodo, turnos_historicos
    ) == {"nuevos": 2, "recurrentes": 0}


def test_clientes_nuevos_y_recurrentes() -> None:
    turnos_periodo = [
        {"client_id": "c1"},
        {"client_id": "c2"},
        {"client_id": "c3"},
    ]
    turnos_historicos = [{"client_id": "c1"}, {"client_id": "c1"}]
    assert compute_clientes_nuevos_vs_recurrentes(
        turnos_periodo, turnos_historicos
    ) == {"nuevos": 2, "recurrentes": 1}


# ─── compute_retention_rate ───────────────────────────────────────────────────

def test_retention_rate_sin_mes_anterior() -> None:
    assert compute_retention_rate(set(), {"c1", "c2"}) == 0.0


def test_retention_rate_parcial() -> None:
    anterior = {"c1", "c2", "c3"}
    actual = {"c1", "c3"}
    assert compute_retention_rate(anterior, actual) == pytest.approx(2 / 3, rel=1e-3)


def test_retention_rate_total() -> None:
    anterior = {"c1", "c2"}
    actual = {"c1", "c2", "c3"}
    assert compute_retention_rate(anterior, actual) == 1.0
