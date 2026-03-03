"""
Tests unitarios para analytics/revenue_metrics.py.
Funciones puras: sin mocks de DB.
"""
from __future__ import annotations

import pytest

from analytics.revenue_metrics import (
    compute_ingresos_mensuales,
    compute_ticket_promedio,
    compute_ocupacion,
    compute_servicios_mas_vendidos,
    compute_horas_pico,
    compute_comparacion_mes_anterior,
)
# ─── compute_ingresos_mensuales ───────────────────────────────────────────────

def test_ingresos_mensuales_vacio() -> None:
    assert compute_ingresos_mensuales([], {}) == 0.0


def test_ingresos_mensuales_solo_billables() -> None:
    turnos = [
        {"servicio_id": "s1", "estado": "completado"},
        {"servicio_id": "s2", "estado": "confirmado"},
    ]
    servicios = {"s1": 1000.0, "s2": 500.0}
    assert compute_ingresos_mensuales(turnos, servicios) == 1500.0


def test_ingresos_mensuales_ignora_no_billables() -> None:
    turnos = [
        {"servicio_id": "s1", "estado": "completado"},
        {"servicio_id": "s2", "estado": "cancelado"},
    ]
    servicios = {"s1": 1000.0, "s2": 500.0}
    assert compute_ingresos_mensuales(turnos, servicios) == 1000.0


# ─── compute_ticket_promedio ──────────────────────────────────────────────────

def test_ticket_promedio_cero_turnos() -> None:
    assert compute_ticket_promedio(0.0, 0) == 0.0


def test_ticket_promedio_ok() -> None:
    assert compute_ticket_promedio(3000.0, 10) == 300.0


# ─── compute_ocupacion ────────────────────────────────────────────────────────

def test_ocupacion_capacidad_cero() -> None:
    assert compute_ocupacion(5, 0) == 0.0


def test_ocupacion_ok() -> None:
    assert compute_ocupacion(8, 32) == 0.25


def test_ocupacion_max_uno() -> None:
    assert compute_ocupacion(50, 32) == 1.0


# ─── compute_servicios_mas_vendidos ───────────────────────────────────────────

def test_servicios_mas_vendidos_vacio() -> None:
    assert compute_servicios_mas_vendidos([], {}) == []


def test_servicios_mas_vendidos_ranking() -> None:
    turnos = [
        {"servicio_id": "s1", "estado": "completado"},
        {"servicio_id": "s1", "estado": "completado"},
        {"servicio_id": "s2", "estado": "completado"},
    ]
    servicios = {"s1": "Corte", "s2": "Barba"}
    result = compute_servicios_mas_vendidos(turnos, servicios, top_n=5)
    assert len(result) == 2
    assert result[0]["nombre"] == "Corte" and result[0]["cantidad"] == 2
    assert result[1]["nombre"] == "Barba" and result[1]["cantidad"] == 1


# ─── compute_comparacion_mes_anterior ─────────────────────────────────────────

def test_comparacion_mes_anterior_sin_base() -> None:
    assert compute_comparacion_mes_anterior(100.0, 0.0) == 0.0


def test_comparacion_mes_anterior_positiva() -> None:
    assert compute_comparacion_mes_anterior(115.0, 100.0) == 0.15


def test_comparacion_mes_anterior_negativa() -> None:
    assert compute_comparacion_mes_anterior(90.0, 100.0) == -0.1


# ─── compute_horas_pico ───────────────────────────────────────────────────────

def test_horas_pico_vacio() -> None:
    assert compute_horas_pico([]) == []


def test_horas_pico_con_horas() -> None:
    turnos = [
        {"hora": "10:00"},
        {"hora": "10:00"},
        {"hora": "14:00"},
    ]
    result = compute_horas_pico(turnos)
    assert len(result) >= 1
    horas = {r["hora"]: r["cantidad"] for r in result}
    assert horas.get("10:00") == 2 or "10:00" in [r["hora"] for r in result]
