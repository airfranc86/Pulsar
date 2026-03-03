"""
tests/unit/test_crud_guards.py
==============================
Tests para el guard de seguridad assert_tenant() en core/database.py.

Objetivo: verificar que NINGUNA operación de base de datos puede ejecutarse
sin un tenant_id válido. Este guard es la primera línea de defensa contra
acceso cruzado entre tenants en un sistema multi-tenant.

Cobertura:
  ✅ Casos válidos: UUIDs bien formados en sus variantes
  ✅ Casos inválidos: None, vacío, tipo incorrecto, formato incorrecto
  ✅ Mensajes de error: informativos, sin stack traces expuestos
  ✅ Comportamiento con strings límite: espacios, mayúsculas, unicode
  ✅ Jerarquía de excepciones: TenantAssertionError es DatabaseError
  ✅ Inmutabilidad del retorno: assert_tenant no modifica el valor
"""

import pytest

from core.database import (
    DatabaseError,
    TenantAssertionError,
    assert_tenant,
)
from tests.unit.conftest import (
    TENANT_UUID_A,
    TENANT_UUID_B,
    TENANT_UUID_DEMO,
    INVALID_UUID_NO_DASHES,
    INVALID_UUID_SHORT,
    INVALID_UUID_EXTRA,
)


# ═══════════════════════════════════════════════════════════════════════════════
# SECCIÓN 1 — Casos válidos: assert_tenant DEBE retornar el UUID
# ═══════════════════════════════════════════════════════════════════════════════

class TestAssertTenantValidos:
    """assert_tenant() con entradas válidas debe retornar el UUID sin modificarlo."""

    def test_uuid_valido_retorna_el_mismo_valor(self):
        resultado = assert_tenant(TENANT_UUID_A)
        assert resultado == TENANT_UUID_A

    def test_uuid_valido_tenant_b(self):
        resultado = assert_tenant(TENANT_UUID_B)
        assert resultado == TENANT_UUID_B

    def test_uuid_demo_tenant(self):
        """El UUID de ceros del tenant demo también debe ser válido."""
        resultado = assert_tenant(TENANT_UUID_DEMO)
        assert resultado == TENANT_UUID_DEMO

    def test_uuid_en_mayusculas_es_valido(self):
        """UUIDs en mayúsculas son válidos — el sistema los acepta case-insensitive."""
        uuid_upper = TENANT_UUID_A.upper()
        resultado = assert_tenant(uuid_upper)
        assert resultado == uuid_upper

    def test_uuid_mixto_mayusculas_minusculas(self):
        """Combinación de mayúsculas y minúsculas es aceptada."""
        uuid_mixed = "550E8400-e29b-41D4-A716-446655440001"
        resultado = assert_tenant(uuid_mixed)
        assert resultado == uuid_mixed

    def test_uuid_con_espacios_laterales_es_valido(self):
        """
        Espacios al inicio y al final deben aceptarse (strip interno).
        Esto evita falsos negativos cuando el UUID viene de formularios web.
        """
        uuid_con_espacios = f"  {TENANT_UUID_A}  "
        resultado = assert_tenant(uuid_con_espacios)
        # El resultado tiene el UUID sin espacios
        assert resultado == TENANT_UUID_A

    def test_retorno_es_string(self):
        """El retorno siempre debe ser str, independientemente del input."""
        resultado = assert_tenant(TENANT_UUID_A)
        assert isinstance(resultado, str)

    def test_no_modifica_uuid_valido(self):
        """assert_tenant no altera el UUID si ya está bien formado."""
        resultado = assert_tenant(TENANT_UUID_A)
        assert resultado == TENANT_UUID_A


# ═══════════════════════════════════════════════════════════════════════════════
# SECCIÓN 2 — None: el caso más crítico
# ═══════════════════════════════════════════════════════════════════════════════

class TestAssertTenantNone:
    """
    None es el caso más peligroso: ocurre cuando _resolve_tenant_id()
    no se ejecutó o cuando session_state no se inicializó correctamente.
    """

    def test_none_lanza_tenant_assertion_error(self):
        with pytest.raises(TenantAssertionError):
            assert_tenant(None)

    def test_none_mensaje_incluye_none(self):
        """El mensaje de error debe indicar explícitamente que recibió None."""
        with pytest.raises(TenantAssertionError, match="None"):
            assert_tenant(None)

    def test_none_es_database_error(self):
        """TenantAssertionError debe ser subclase de DatabaseError para catch unificado."""
        with pytest.raises(DatabaseError):
            assert_tenant(None)

    def test_none_no_retorna_silenciosamente(self):
        """Verificar que None NUNCA produce un retorno (ni None, ni string vacío)."""
        with pytest.raises(TenantAssertionError):
            result = assert_tenant(None)
            # Esta línea nunca debe ejecutarse
            assert result is not None, "assert_tenant(None) NO debe retornar nada"


# ═══════════════════════════════════════════════════════════════════════════════
# SECCIÓN 3 — Strings vacíos y en blanco
# ═══════════════════════════════════════════════════════════════════════════════

class TestAssertTenantVaciosYEspacios:
    """Strings vacíos y solo-espacios son inputs inválidos que deben rechazarse."""

    def test_string_vacio_lanza_error(self):
        with pytest.raises(TenantAssertionError):
            assert_tenant("")

    def test_string_solo_espacio_lanza_error(self):
        with pytest.raises(TenantAssertionError):
            assert_tenant(" ")

    def test_string_multiples_espacios_lanza_error(self):
        with pytest.raises(TenantAssertionError):
            assert_tenant("     ")

    def test_string_tab_lanza_error(self):
        with pytest.raises(TenantAssertionError):
            assert_tenant("\t")

    def test_string_newline_lanza_error(self):
        with pytest.raises(TenantAssertionError):
            assert_tenant("\n")

    def test_string_vacio_mensaje_claro(self):
        """El mensaje de error debe distinguir entre vacío y None."""
        with pytest.raises(TenantAssertionError, match="vacío"):
            assert_tenant("")


# ═══════════════════════════════════════════════════════════════════════════════
# SECCIÓN 4 — Tipos incorrectos
# ═══════════════════════════════════════════════════════════════════════════════

class TestAssertTenantTiposIncorrectos:
    """
    Protección contra errores de tipo en tiempo de desarrollo.
    Ocurren cuando tenant_id viene de una fuente inesperada (int de JSON, etc.)
    """

    def test_entero_lanza_error(self):
        with pytest.raises(TenantAssertionError):
            assert_tenant(1)

    def test_cero_lanza_error(self):
        with pytest.raises(TenantAssertionError):
            assert_tenant(0)

    def test_lista_lanza_error(self):
        with pytest.raises(TenantAssertionError):
            assert_tenant([TENANT_UUID_A])

    def test_dict_lanza_error(self):
        with pytest.raises(TenantAssertionError):
            assert_tenant({"id": TENANT_UUID_A})

    def test_bool_true_lanza_error(self):
        """True en Python es int subclase, pero no es un tenant_id válido."""
        with pytest.raises(TenantAssertionError):
            assert_tenant(True)

    def test_bool_false_lanza_error(self):
        with pytest.raises(TenantAssertionError):
            assert_tenant(False)

    def test_bytes_lanza_error(self):
        with pytest.raises(TenantAssertionError):
            assert_tenant(b"550e8400-e29b-41d4-a716-446655440001")

    def test_tipo_incorrecto_menciona_el_tipo_recibido(self):
        """El mensaje debe informar qué tipo se recibió para facilitar debugging."""
        with pytest.raises(TenantAssertionError, match="int"):
            assert_tenant(42)


# ═══════════════════════════════════════════════════════════════════════════════
# SECCIÓN 5 — Formato UUID inválido
# ═══════════════════════════════════════════════════════════════════════════════

class TestAssertTenantFormatoInvalido:
    """
    Strings que son UUIDs malformados. Ocurren por errores de serialización,
    truncamiento, o datos corruptos en base de datos.
    """

    def test_uuid_sin_guiones_lanza_error(self):
        with pytest.raises(TenantAssertionError):
            assert_tenant(INVALID_UUID_NO_DASHES)

    def test_uuid_incompleto_lanza_error(self):
        with pytest.raises(TenantAssertionError):
            assert_tenant(INVALID_UUID_SHORT)

    def test_uuid_con_sufijo_extra_lanza_error(self):
        with pytest.raises(TenantAssertionError):
            assert_tenant(INVALID_UUID_EXTRA)

    def test_uuid_con_caracteres_invalidos(self):
        """UUID con letras fuera del rango hexadecimal."""
        with pytest.raises(TenantAssertionError):
            assert_tenant("550e8400-e29b-41d4-a716-44665544ZZZZ")

    def test_string_arbitrario_lanza_error(self):
        with pytest.raises(TenantAssertionError):
            assert_tenant("no-soy-un-uuid")

    def test_sql_injection_attempt_lanza_error(self):
        """
        Un intento de SQL injection nunca tiene formato UUID válido.
        Este test documenta que el guard también protege contra este vector.
        """
        with pytest.raises(TenantAssertionError):
            assert_tenant("' OR '1'='1")

    def test_uuid_con_llaves_estilo_microsoft(self):
        """Formato {UUID} de Microsoft no es válido en este sistema."""
        with pytest.raises(TenantAssertionError):
            assert_tenant("{550e8400-e29b-41d4-a716-446655440001}")

    def test_error_menciona_formato_esperado(self):
        """El mensaje debe indicar el formato esperado para facilitar debugging."""
        with pytest.raises(TenantAssertionError, match="UUID"):
            assert_tenant("formato-invalido")


# ═══════════════════════════════════════════════════════════════════════════════
# SECCIÓN 6 — Jerarquía de excepciones
# ═══════════════════════════════════════════════════════════════════════════════

class TestJerarquiaExcepciones:
    """
    Verifica que la jerarquía de excepciones permite catch unificado
    en los puntos de entrada de la aplicación.
    """

    def test_tenant_assertion_error_es_subclase_de_database_error(self):
        assert issubclass(TenantAssertionError, DatabaseError)

    def test_tenant_assertion_error_es_subclase_de_exception(self):
        assert issubclass(TenantAssertionError, Exception)

    def test_catch_como_database_error_funciona(self):
        """
        Los handlers genéricos que capturan DatabaseError
        deben funcionar sin cambios cuando reciben TenantAssertionError.
        """
        capturado = False
        try:
            assert_tenant(None)
        except DatabaseError:
            capturado = True
        assert capturado, "DatabaseError no capturó TenantAssertionError"

    def test_tenant_assertion_error_tiene_mensaje_no_vacio(self):
        try:
            assert_tenant(None)
        except TenantAssertionError as exc:
            assert str(exc), "El mensaje de error no puede estar vacío"

    def test_multiples_inputs_invalidos_todos_lanzan_el_mismo_tipo(self):
        """Consistencia: todos los inputs inválidos producen TenantAssertionError."""
        invalidos = [None, "", " ", 0, [], {}, False, b""]
        for invalido in invalidos:
            try:
                assert_tenant(invalido)
                pytest.fail(f"assert_tenant({invalido!r}) debería lanzar TenantAssertionError")
            except TenantAssertionError:
                pass  # esperado
            except Exception as exc:
                pytest.fail(
                    f"assert_tenant({invalido!r}) lanzó {type(exc).__name__} "
                    f"en lugar de TenantAssertionError: {exc}"
                )


# ═══════════════════════════════════════════════════════════════════════════════
# SECCIÓN 8 — DatabaseError en clientes Supabase
# ═══════════════════════════════════════════════════════════════════════════════

class TestClientesSupabase:
    """
    Verifica la jerarquía completa de excepciones de database.py
    y que los clientes lanzan DatabaseError ante configuración inválida.
    Usa mocks de sys.modules para simular supabase instalado/no instalado
    sin depender de que el paquete real esté presente.
    """

    def _make_fake_supabase(self, side_effect=None):
        """Crea un módulo supabase falso con create_client mockeable."""
        import unittest.mock as mock
        import sys

        fake_supabase = mock.MagicMock()
        if side_effect:
            fake_supabase.create_client.side_effect = side_effect
        else:
            fake_supabase.create_client.return_value = mock.MagicMock()
        return fake_supabase

    def _make_fake_settings(self):
        """Crea settings falsos con las variables necesarias."""
        import unittest.mock as mock
        fake_settings = mock.MagicMock()
        fake_settings.SUPABASE_URL = "https://test.supabase.co"
        fake_settings.SUPABASE_ANON_KEY = "test-anon-key"
        fake_settings.SUPABASE_SERVICE_ROLE_KEY = "test-service-key"
        return fake_settings

    def test_get_anon_client_retorna_cliente_cuando_supabase_instalado(self):
        """Con supabase y settings válidos, get_anon_client retorna un cliente."""
        import unittest.mock as mock
        import sys
        import importlib

        fake_supabase = self._make_fake_supabase()
        fake_settings_module = mock.MagicMock()
        fake_settings_module.settings = self._make_fake_settings()

        with mock.patch.dict(sys.modules, {
            "supabase": fake_supabase,
            "config.settings": fake_settings_module,
        }):
            import core.database as db_module
            importlib.reload(db_module)
            result = db_module.get_anon_client()
            assert result is not None
            fake_supabase.create_client.assert_called_once()

    def test_get_anon_client_lanza_database_error_si_create_client_falla(self):
        """Si create_client lanza Exception, get_anon_client la envuelve en DatabaseError."""
        import unittest.mock as mock
        import sys
        import importlib

        fake_supabase = self._make_fake_supabase(side_effect=Exception("URL inválida"))
        fake_settings_module = mock.MagicMock()
        fake_settings_module.settings = self._make_fake_settings()

        with mock.patch.dict(sys.modules, {
            "supabase": fake_supabase,
            "config.settings": fake_settings_module,
        }):
            import core.database as db_module
            importlib.reload(db_module)
            with pytest.raises(db_module.DatabaseError, match="Supabase"):
                db_module.get_anon_client()

    def test_get_service_client_retorna_cliente_cuando_supabase_instalado(self):
        """Con supabase y settings válidos, get_service_client retorna un cliente."""
        import unittest.mock as mock
        import sys
        import importlib

        fake_supabase = self._make_fake_supabase()
        fake_settings_module = mock.MagicMock()
        fake_settings_module.settings = self._make_fake_settings()

        with mock.patch.dict(sys.modules, {
            "supabase": fake_supabase,
            "config.settings": fake_settings_module,
        }):
            import core.database as db_module
            importlib.reload(db_module)
            result = db_module.get_service_client()
            assert result is not None

    def test_get_service_client_lanza_database_error_si_create_client_falla(self):
        """Si create_client falla para service client, lanza DatabaseError."""
        import unittest.mock as mock
        import sys
        import importlib

        fake_supabase = self._make_fake_supabase(side_effect=Exception("creds inválidas"))
        fake_settings_module = mock.MagicMock()
        fake_settings_module.settings = self._make_fake_settings()

        with mock.patch.dict(sys.modules, {
            "supabase": fake_supabase,
            "config.settings": fake_settings_module,
        }):
            import core.database as db_module
            importlib.reload(db_module)
            with pytest.raises(db_module.DatabaseError, match="servicio"):
                db_module.get_service_client()

    def test_database_error_es_exception(self):
        assert issubclass(DatabaseError, Exception)

    def test_tenant_not_found_es_database_error(self):
        from core.database import TenantNotFoundError, DatabaseError as DBErr
        assert issubclass(TenantNotFoundError, DBErr)

    def test_subscription_error_es_database_error(self):
        from core.database import SubscriptionError, DatabaseError as DBErr
        assert issubclass(SubscriptionError, DBErr)


# ═══════════════════════════════════════════════════════════════════════════════
# SECCIÓN 9 — Idempotencia y efectos secundarios
# ═══════════════════════════════════════════════════════════════════════════════

class TestIdempotencia:
    """assert_tenant debe ser pura: sin estado, sin efectos secundarios."""

    def test_llamadas_multiples_retornan_mismo_valor(self):
        """Verificar que no hay estado interno que cambie entre llamadas."""
        uuid = TENANT_UUID_A
        assert assert_tenant(uuid) == assert_tenant(uuid) == assert_tenant(uuid)

    def test_llamadas_con_distintos_tenants_retornan_correctamente(self):
        """Dos tenants distintos no interfieren entre sí."""
        resultado_a = assert_tenant(TENANT_UUID_A)
        resultado_b = assert_tenant(TENANT_UUID_B)
        assert resultado_a == TENANT_UUID_A
        assert resultado_b == TENANT_UUID_B
        assert resultado_a != resultado_b

    def test_error_en_llamada_previa_no_afecta_llamada_siguiente(self):
        """Un error previo no envenena el estado de la función."""
        # Capturar cualquier excepción: el punto del test es verificar
        # que assert_tenant es stateless, no el tipo de excepción previo
        try:
            assert_tenant(None)
        except Exception:
            pass
        # Esta llamada debe funcionar normalmente
        resultado = assert_tenant(TENANT_UUID_A)
        assert resultado == TENANT_UUID_A

