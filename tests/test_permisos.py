"""
tests/unit/test_permisos.py
============================
Tests para el sistema de control de acceso en core/permisos.py.

Objetivo: verificar que get_access_summary() toma decisiones correctas
para CADA estado de suscripción, y que require_full_access() bloquea
correctamente el acceso a features premium en modo demo.

Cobertura:
  ✅ Estado 'active': todas las features habilitadas, sin límites
  ✅ Estados inactivos (inactive, past_due, cancelled, demo): demo_mode=True
  ✅ Cada feature individual bloqueada/desbloqueada correctamente
  ✅ Límites cuantitativos: max_kpis_visible, max_records_per_table
  ✅ require_full_access(): bloqueo y paso correcto por feature
  ✅ Robustez: None, tipo incorrecto, campo faltante
  ✅ Consistencia: demo_mode ↔ subscription_active son siempre inversos
"""

import pytest

from core.permisos import (
    AccessSummary,
    get_access_summary,
    require_full_access,
    DEMO_MAX_KPI_VISIBLE,
    FULL_MAX_KPI_VISIBLE,
    _NO_LIMIT_SENTINEL,
)


# ═══════════════════════════════════════════════════════════════════════════════
# SECCIÓN 1 — Tenant activo: acceso completo
# ═══════════════════════════════════════════════════════════════════════════════

class TestTenantActivo:
    """Estado 'active': todas las features deben estar disponibles."""

    def test_demo_mode_es_false(self, tenant_active):
        summary = get_access_summary(tenant_active)
        assert summary["demo_mode"] is False

    def test_subscription_active_es_true(self, tenant_active):
        summary = get_access_summary(tenant_active)
        assert summary["subscription_active"] is True

    def test_subscription_status_preservado(self, tenant_active):
        summary = get_access_summary(tenant_active)
        assert summary["subscription_status"] == "active"

    def test_puede_exportar_csv(self, tenant_active):
        summary = get_access_summary(tenant_active)
        assert summary["can_export_csv"] is True

    def test_puede_exportar_pdf(self, tenant_active):
        summary = get_access_summary(tenant_active)
        assert summary["can_export_pdf"] is True

    def test_puede_ver_historial_completo(self, tenant_active):
        summary = get_access_summary(tenant_active)
        assert summary["can_view_full_history"] is True

    def test_puede_recibir_reporte_mensual(self, tenant_active):
        summary = get_access_summary(tenant_active)
        assert summary["can_receive_monthly_report"] is True

    def test_puede_acceder_analiticas_avanzadas(self, tenant_active):
        summary = get_access_summary(tenant_active)
        assert summary["can_access_advanced_analytics"] is True

    def test_max_kpis_es_8(self, tenant_active):
        """Tenant activo debe ver los 8 KPIs del dashboard completo."""
        summary = get_access_summary(tenant_active)
        assert summary["max_kpis_visible"] == FULL_MAX_KPI_VISIBLE
        assert summary["max_kpis_visible"] == 8

    def test_max_records_es_sin_limite(self, tenant_active):
        """Tenant activo no tiene restricción de registros por tabla."""
        summary = get_access_summary(tenant_active)
        assert summary["max_records_per_table"] == _NO_LIMIT_SENTINEL

    def test_demo_y_active_son_inversos(self, tenant_active):
        """demo_mode y subscription_active nunca pueden ser iguales."""
        summary = get_access_summary(tenant_active)
        assert summary["demo_mode"] is not summary["subscription_active"]


# ═══════════════════════════════════════════════════════════════════════════════
# SECCIÓN 2 — Tenant inactivo (sin pago): modo demo
# ═══════════════════════════════════════════════════════════════════════════════

class TestTenantInactivo:
    """Estado 'inactive': recién creado, nunca pagó. Debe ser demo_mode=True."""

    def test_demo_mode_es_true(self, tenant_inactive):
        summary = get_access_summary(tenant_inactive)
        assert summary["demo_mode"] is True

    def test_subscription_active_es_false(self, tenant_inactive):
        summary = get_access_summary(tenant_inactive)
        assert summary["subscription_active"] is False

    def test_no_puede_exportar_csv(self, tenant_inactive):
        summary = get_access_summary(tenant_inactive)
        assert summary["can_export_csv"] is False

    def test_no_puede_exportar_pdf(self, tenant_inactive):
        summary = get_access_summary(tenant_inactive)
        assert summary["can_export_pdf"] is False

    def test_no_puede_ver_historial(self, tenant_inactive):
        summary = get_access_summary(tenant_inactive)
        assert summary["can_view_full_history"] is False

    def test_no_recibe_reporte_mensual(self, tenant_inactive):
        summary = get_access_summary(tenant_inactive)
        assert summary["can_receive_monthly_report"] is False

    def test_no_accede_analiticas_avanzadas(self, tenant_inactive):
        summary = get_access_summary(tenant_inactive)
        assert summary["can_access_advanced_analytics"] is False

    def test_max_kpis_es_3(self, tenant_inactive):
        """Tenant en demo solo ve 3 de los 8 KPIs."""
        summary = get_access_summary(tenant_inactive)
        assert summary["max_kpis_visible"] == DEMO_MAX_KPI_VISIBLE
        assert summary["max_kpis_visible"] == 3

    def test_max_records_es_10(self, tenant_inactive):
        """Tenant en demo está limitado a 10 registros por tabla."""
        summary = get_access_summary(tenant_inactive)
        assert summary["max_records_per_table"] == 10


# ═══════════════════════════════════════════════════════════════════════════════
# SECCIÓN 3 — Todos los estados inactivos producen demo_mode=True
# ═══════════════════════════════════════════════════════════════════════════════

class TestTodosLosEstadosInactivos:
    """
    inactive, past_due, cancelled y demo deben producir EXACTAMENTE
    el mismo resultado: demo_mode=True, todas las features bloqueadas.

    Usa la fixture parametrizada tenant_any_inactive de conftest.py.
    """

    def test_demo_mode_true_para_cualquier_estado_inactivo(self, tenant_any_inactive):
        summary = get_access_summary(tenant_any_inactive)
        assert summary["demo_mode"] is True, (
            f"Estado '{tenant_any_inactive['subscription_status']}' "
            f"debería producir demo_mode=True"
        )

    def test_subscription_active_false_para_cualquier_estado_inactivo(self, tenant_any_inactive):
        summary = get_access_summary(tenant_any_inactive)
        assert summary["subscription_active"] is False

    def test_todas_las_features_bloqueadas_en_cualquier_estado_inactivo(self, tenant_any_inactive):
        summary = get_access_summary(tenant_any_inactive)
        features = [
            "can_export_csv",
            "can_export_pdf",
            "can_view_full_history",
            "can_receive_monthly_report",
            "can_access_advanced_analytics",
        ]
        for feature in features:
            assert summary[feature] is False, (
                f"Feature '{feature}' debería estar bloqueada "
                f"para estado '{tenant_any_inactive['subscription_status']}'"
            )

    def test_max_kpis_es_3_para_cualquier_estado_inactivo(self, tenant_any_inactive):
        summary = get_access_summary(tenant_any_inactive)
        assert summary["max_kpis_visible"] == 3

    def test_max_records_es_10_para_cualquier_estado_inactivo(self, tenant_any_inactive):
        summary = get_access_summary(tenant_any_inactive)
        assert summary["max_records_per_table"] == 10


# ═══════════════════════════════════════════════════════════════════════════════
# SECCIÓN 4 — Estados específicos
# ═══════════════════════════════════════════════════════════════════════════════

class TestEstadosEspecificos:

    def test_past_due_es_demo_mode(self, tenant_past_due):
        """Pago fallido = modo demo hasta que regularice."""
        summary = get_access_summary(tenant_past_due)
        assert summary["demo_mode"] is True
        assert summary["subscription_status"] == "past_due"

    def test_cancelled_es_demo_mode(self, tenant_cancelled):
        """Suscripción cancelada = modo demo."""
        summary = get_access_summary(tenant_cancelled)
        assert summary["demo_mode"] is True
        assert summary["subscription_status"] == "cancelled"

    def test_demo_tenant_es_demo_mode(self, tenant_demo):
        """Tenant demo explícito = modo demo."""
        summary = get_access_summary(tenant_demo)
        assert summary["demo_mode"] is True
        assert summary["subscription_status"] == "demo"

    def test_subscription_status_se_preserva_exacto(self, tenant_past_due):
        """El status original se retorna sin modificar para trazabilidad."""
        summary = get_access_summary(tenant_past_due)
        assert summary["subscription_status"] == tenant_past_due["subscription_status"]


# ═══════════════════════════════════════════════════════════════════════════════
# SECCIÓN 5 — require_full_access()
# ═══════════════════════════════════════════════════════════════════════════════

class TestRequireFullAccess:
    """require_full_access() bloquea features en demo y permite en full."""

    def test_no_lanza_error_con_tenant_activo(self, tenant_active):
        summary = get_access_summary(tenant_active)
        # No debe lanzar ninguna excepción
        require_full_access(summary, "exportar CSV")

    def test_lanza_permission_error_en_demo(self, tenant_inactive):
        summary = get_access_summary(tenant_inactive)
        with pytest.raises(PermissionError):
            require_full_access(summary, "exportar CSV")

    def test_mensaje_incluye_nombre_del_feature(self, tenant_inactive):
        summary = get_access_summary(tenant_inactive)
        with pytest.raises(PermissionError, match="exportar PDF"):
            require_full_access(summary, "exportar PDF")

    def test_mensaje_incluye_estado_actual(self, tenant_inactive):
        summary = get_access_summary(tenant_inactive)
        with pytest.raises(PermissionError, match="inactive"):
            require_full_access(summary, "reporte mensual")

    def test_todos_los_estados_inactivos_lanzan_permission_error(self, tenant_any_inactive):
        summary = get_access_summary(tenant_any_inactive)
        with pytest.raises(PermissionError):
            require_full_access(summary, "feature de prueba")

    def test_require_full_access_para_exportar_csv(self, tenant_active, tenant_inactive):
        """Verificación directa por feature: CSV."""
        summary_full = get_access_summary(tenant_active)
        summary_demo = get_access_summary(tenant_inactive)

        require_full_access(summary_full, "exportar CSV")  # no lanza

        with pytest.raises(PermissionError):
            require_full_access(summary_demo, "exportar CSV")

    def test_require_full_access_para_reporte_mensual(self, tenant_active, tenant_inactive):
        """Verificación directa por feature: reporte mensual."""
        summary_full = get_access_summary(tenant_active)
        summary_demo = get_access_summary(tenant_inactive)

        require_full_access(summary_full, "reporte mensual")  # no lanza

        with pytest.raises(PermissionError):
            require_full_access(summary_demo, "reporte mensual")

    def test_require_full_access_para_analiticas(self, tenant_active, tenant_inactive):
        """Verificación directa por feature: analíticas avanzadas."""
        summary_full = get_access_summary(tenant_active)
        summary_demo = get_access_summary(tenant_inactive)

        require_full_access(summary_full, "analíticas avanzadas")  # no lanza

        with pytest.raises(PermissionError):
            require_full_access(summary_demo, "analíticas avanzadas")


# ═══════════════════════════════════════════════════════════════════════════════
# SECCIÓN 6 — Robustez: inputs inválidos a get_access_summary
# ═══════════════════════════════════════════════════════════════════════════════

class TestGetAccessSummaryRobustez:
    """
    get_access_summary() debe fallar explícitamente ante inputs inválidos.
    Falla rápida con mensaje claro previene bugs silenciosos.
    """

    def test_none_lanza_value_error(self):
        with pytest.raises(ValueError):
            get_access_summary(None)

    def test_tipo_incorrecto_lanza_value_error(self):
        with pytest.raises(ValueError):
            get_access_summary("no-soy-un-dict")

    def test_lista_lanza_value_error(self):
        with pytest.raises(ValueError):
            get_access_summary([{"subscription_status": "active"}])

    def test_dict_sin_subscription_status_lanza_value_error(self):
        """El campo subscription_status es obligatorio."""
        tenant_incompleto = {"id": "uuid-cualquiera", "name": "Test"}
        with pytest.raises(ValueError, match="subscription_status"):
            get_access_summary(tenant_incompleto)

    def test_mensaje_de_error_es_informativo(self):
        with pytest.raises(ValueError) as exc_info:
            get_access_summary(None)
        assert str(exc_info.value), "El mensaje de ValueError no puede estar vacío"

    def test_dict_vacio_lanza_value_error(self):
        with pytest.raises(ValueError):
            get_access_summary({})

    def test_subscription_status_desconocido_resulta_en_demo(self):
        """
        Un status desconocido (ej. 'suspended', 'trial') debe tratarse
        como demo por defecto — principio de menor privilegio.
        """
        tenant_status_raro = {
            "id": "550e8400-e29b-41d4-a716-446655440001",
            "subscription_status": "suspended_por_fraude",
        }
        summary = get_access_summary(tenant_status_raro)
        assert summary["demo_mode"] is True, (
            "Status desconocido debe resultar en demo_mode=True (menor privilegio)"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# SECCIÓN 7 — Consistencia interna del AccessSummary
# ═══════════════════════════════════════════════════════════════════════════════

class TestConsistenciaInterna:
    """
    Las claves del AccessSummary deben ser internamente consistentes.
    Si demo_mode=True, TODAS las features deben estar bloqueadas.
    Si demo_mode=False, TODAS las features deben estar habilitadas.
    """

    def test_tenant_activo_todas_las_features_habilitadas(self, tenant_active):
        summary = get_access_summary(tenant_active)
        features = [
            "can_export_csv",
            "can_export_pdf",
            "can_view_full_history",
            "can_receive_monthly_report",
            "can_access_advanced_analytics",
        ]
        for feature in features:
            assert summary[feature] is True, (
                f"Feature '{feature}' debe ser True para tenant activo"
            )

    def test_demo_mode_y_subscription_active_siempre_opuestos(self, tenant_active, tenant_inactive):
        for tenant in [tenant_active, tenant_inactive]:
            summary = get_access_summary(tenant)
            assert summary["demo_mode"] is not summary["subscription_active"], (
                f"demo_mode y subscription_active deben ser opuestos. "
                f"Status: {tenant['subscription_status']}"
            )

    def test_max_kpis_nunca_excede_8(self, tenant_active):
        summary = get_access_summary(tenant_active)
        assert summary["max_kpis_visible"] <= 8

    def test_max_kpis_demo_menor_que_full(self, tenant_active, tenant_inactive):
        summary_full = get_access_summary(tenant_active)
        summary_demo = get_access_summary(tenant_inactive)
        assert summary_demo["max_kpis_visible"] < summary_full["max_kpis_visible"]

    def test_summary_contiene_todas_las_claves_requeridas(self, tenant_active):
        """El AccessSummary debe tener exactamente las claves definidas en el TypedDict."""
        summary = get_access_summary(tenant_active)
        claves_requeridas = {
            "demo_mode",
            "subscription_active",
            "subscription_status",
            "can_export_csv",
            "can_export_pdf",
            "can_view_full_history",
            "can_receive_monthly_report",
            "can_access_advanced_analytics",
            "max_kpis_visible",
            "max_records_per_table",
        }
        for clave in claves_requeridas:
            assert clave in summary, f"Clave '{clave}' faltante en AccessSummary"

    def test_get_access_summary_es_pura(self, tenant_active):
        """
        La función es pura: el mismo input produce el mismo output.
        No debe haber estado interno que cambie entre llamadas.
        """
        summary_1 = get_access_summary(tenant_active)
        summary_2 = get_access_summary(tenant_active)
        assert summary_1 == summary_2

    def test_get_access_summary_no_modifica_el_tenant(self, tenant_active):
        """La función no debe mutar el dict del tenant que recibe."""
        status_original = tenant_active["subscription_status"]
        get_access_summary(tenant_active)
        assert tenant_active["subscription_status"] == status_original


# ═══════════════════════════════════════════════════════════════════════════════
# SECCIÓN 8 — Constantes de configuración
# ═══════════════════════════════════════════════════════════════════════════════

class TestConstantesDeConfiguracion:
    """Las constantes del módulo deben cumplir las invariantes del blueprint."""

    def test_demo_max_kpi_es_3(self):
        """El blueprint especifica exactamente 3 KPIs en modo demo."""
        assert DEMO_MAX_KPI_VISIBLE == 3

    def test_full_max_kpi_es_8(self):
        """El blueprint especifica exactamente 8 KPIs en modo full."""
        assert FULL_MAX_KPI_VISIBLE == 8

    def test_demo_kpi_menor_que_full_kpi(self):
        assert DEMO_MAX_KPI_VISIBLE < FULL_MAX_KPI_VISIBLE

    def test_no_limit_sentinel_es_negativo(self):
        """El centinela de 'sin límite' debe ser negativo para distinguirse de límites reales."""
        assert _NO_LIMIT_SENTINEL < 0
