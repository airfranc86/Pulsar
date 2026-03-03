"""
Pulsar v1.0 — Import Services
================================
Procesamiento de archivos CSV y XLSX subidos por el tenant.
Soporta tres entidades: clients, services, appointments.

Capas:
  parse_file()        → ingesta raw → DataFrame
  validate_columns()  → detecta columnas disponibles vs requeridas
  map_columns()       → renombra columnas del usuario al schema interno
  validate_rows()     → validación fila por fila, produce ImportResult
  persist_batch()     → escribe en Supabase con tenant_id inyectado

Restricciones:
  - tenant_id siempre como primer argumento en persist
  - Nunca opera sin tenant_id (lanza ValueError)
  - Máximo FILE_SIZE_LIMIT_MB por archivo
  - XLSX: solo primera hoja, máximo MAX_ROWS_PER_IMPORT filas
"""

import io
import logging
from dataclasses import dataclass, field
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)

# ── Constantes ────────────────────────────────────────────────────────────────
FILE_SIZE_LIMIT_MB = 5
MAX_ROWS_PER_IMPORT = 2_000

# Columnas requeridas y opcionales por entidad.
# "aliases" permite detectar nombres alternativos que los usuarios usan en sus propios archivos.
ENTITY_SCHEMA: dict[str, dict] = {
    "clients": {
        "required": ["nombre"],
        "optional": ["apellido", "email", "telefono", "notas"],
        "aliases": {
            "nombre": [
                "name",
                "cliente",
                "paciente",
                "titular",
                "razón social",
                "razon social",
            ],
            "apellido": ["last_name", "surname", "apellidos"],
            "email": ["correo", "mail", "e-mail", "e_mail"],
            "telefono": ["phone", "tel", "celular", "móvil", "movil", "whatsapp"],
            "notas": ["notes", "observaciones", "comentarios", "obs"],
        },
    },
    "services": {
        "required": ["nombre", "precio"],
        "optional": ["categoria", "duracion_minutos", "descripcion"],
        "aliases": {
            "nombre": ["name", "servicio", "producto", "descripción corta"],
            "precio": ["price", "costo", "importe", "valor", "tarifa"],
            "categoria": ["category", "tipo", "rubro", "área", "area"],
            "duracion_minutos": ["duracion", "duration", "tiempo", "minutes", "mins"],
            "descripcion": ["description", "detalle", "info"],
        },
    },
    "appointments": {
        "required": ["cliente_nombre", "servicio_nombre", "fecha"],
        "optional": ["hora", "estado", "notas", "precio_cobrado"],
        "aliases": {
            "cliente_nombre": [
                "cliente",
                "paciente",
                "client",
                "nombre_cliente",
                "titular",
            ],
            "servicio_nombre": [
                "servicio",
                "service",
                "tratamiento",
                "procedimiento",
                "consulta",
            ],
            "fecha": ["date", "fecha_turno", "dia", "appointment_date"],
            "hora": ["time", "hora_turno", "horario"],
            "estado": ["status", "estado_turno", "result", "resultado"],
            "notas": ["notes", "observaciones", "comentarios"],
            "precio_cobrado": ["precio", "monto", "importe", "cobrado", "amount"],
        },
    },
}


# ── Data classes ──────────────────────────────────────────────────────────────
@dataclass
class ImportError:
    row_number: int
    column: str
    value: Any
    reason: str


@dataclass
class ImportResult:
    entity: str
    total_rows: int
    success_count: int = 0
    error_count: int = 0
    skipped_count: int = 0
    errors: list[ImportError] = field(default_factory=list)
    inserted_ids: list[str] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        if self.total_rows == 0:
            return 0.0
        return round(self.success_count / self.total_rows * 100, 1)

    def to_summary(self) -> dict[str, Any]:
        return {
            "entity": self.entity,
            "total": self.total_rows,
            "success": self.success_count,
            "errors": self.error_count,
            "skipped": self.skipped_count,
            "success_rate": f"{self.success_rate}%",
        }


# ── Capa 1: Ingesta ───────────────────────────────────────────────────────────
def parse_file(file_bytes: bytes, filename: str) -> pd.DataFrame:
    """
    Convierte bytes de un archivo CSV o XLSX a DataFrame.
    Normaliza nombres de columnas (lowercase + strip).

    Raises:
        ValueError: si el formato no es soportado, el archivo está vacío,
                    o supera los límites de tamaño/filas.
    """
    size_mb = len(file_bytes) / (1024 * 1024)
    if size_mb > FILE_SIZE_LIMIT_MB:
        raise ValueError(
            f"El archivo supera el límite de {FILE_SIZE_LIMIT_MB} MB "
            f"({size_mb:.1f} MB recibido)."
        )

    lower_name = filename.lower().strip()

    if lower_name.endswith(".csv"):
        # Intentar detección automática de encoding y separador
        for encoding in ("utf-8", "latin-1", "utf-8-sig"):
            try:
                df = pd.read_csv(
                    io.BytesIO(file_bytes),
                    encoding=encoding,
                    sep=None,  # motor Python detecta separador
                    engine="python",
                    dtype=str,  # todo como string: validamos nosotros
                    skipinitialspace=True,
                )
                break
            except UnicodeDecodeError:
                continue
        else:
            raise ValueError(
                "No se pudo decodificar el archivo CSV. Intentar guardarlo como UTF-8."
            )

    elif lower_name.endswith((".xlsx", ".xls")):
        df = pd.read_excel(
            io.BytesIO(file_bytes),
            sheet_name=0,  # solo primera hoja
            dtype=str,
        )
    else:
        raise ValueError(
            f"Formato no soportado: '{filename}'. "
            "Solo se aceptan archivos .csv, .xlsx o .xls."
        )

    if df.empty:
        raise ValueError("El archivo está vacío o no contiene filas de datos.")

    if len(df) > MAX_ROWS_PER_IMPORT:
        raise ValueError(
            f"El archivo tiene {len(df):,} filas. "
            f"El límite es {MAX_ROWS_PER_IMPORT:,} filas por importación."
        )

    # Normalizar columnas
    df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
    df = df.dropna(how="all")  # eliminar filas completamente vacías

    logger.info(
        "file_parsed",
        extra={"filename": filename, "rows": len(df), "columns": list(df.columns)},
    )
    return df


# ── Capa 2: Detección de columnas ─────────────────────────────────────────────
def detect_column_mapping(df: pd.DataFrame, entity: str) -> dict[str, str | None]:
    """
    Detecta automáticamente qué columna del DataFrame corresponde
    a cada campo interno del schema.

    Retorna dict: {campo_interno: columna_df | None}
    La UI puede usar este dict para mostrar un mapper al usuario y corregirlo.
    """
    if entity not in ENTITY_SCHEMA:
        raise ValueError(
            f"Entidad desconocida: '{entity}'. Opciones: {list(ENTITY_SCHEMA)}"
        )

    schema = ENTITY_SCHEMA[entity]
    all_fields = schema["required"] + schema["optional"]
    aliases = schema["aliases"]
    available_cols = set(df.columns)

    mapping: dict[str, str | None] = {}

    for field_name in all_fields:
        # Coincidencia exacta primero
        if field_name in available_cols:
            mapping[field_name] = field_name
            continue

        # Buscar por alias
        matched = None
        for alias in aliases.get(field_name, []):
            alias_normalized = alias.strip().lower().replace(" ", "_")
            if alias_normalized in available_cols:
                matched = alias_normalized
                break

        mapping[field_name] = matched

    return mapping


def validate_columns(
    mapping: dict[str, str | None],
    entity: str,
) -> list[str]:
    """
    Verifica que todos los campos requeridos tengan una columna mapeada.
    Retorna lista de campos requeridos sin mapear (vacío = OK).
    """
    required = ENTITY_SCHEMA[entity]["required"]
    return [f for f in required if mapping.get(f) is None]


# ── Capa 3: Validación por fila ───────────────────────────────────────────────
def _clean_price(value: str) -> float | None:
    """Limpia strings de precio: '$1.500,00' → 1500.0"""
    if not value or str(value).strip() in ("", "nan", "None"):
        return None
    cleaned = (
        str(value)
        .replace("$", "")
        .replace(" ", "")
        .replace(".", "")
        .replace(",", ".")
        .strip()
    )
    try:
        return float(cleaned)
    except ValueError:
        return None


def _clean_string(value: Any) -> str:
    if value is None or str(value).strip().lower() in ("nan", "none", ""):
        return ""
    return str(value).strip()


def _validate_and_transform_rows(
    df: pd.DataFrame,
    mapping: dict[str, str | None],
    entity: str,
) -> tuple[list[dict], list[ImportError]]:
    """
    Itera el DataFrame y transforma cada fila al schema interno.
    Retorna (filas_validas, errores).
    """
    valid_rows: list[dict] = []
    errors: list[ImportError] = []

    for idx, row in df.iterrows():
        row_num = int(idx) + 2  # +2: encabezado + base-1
        record: dict[str, Any] = {}
        row_has_error = False

        for field_name, col_name in mapping.items():
            if col_name is None:
                # campo opcional sin mapear → omitir
                continue

            raw_value = row.get(col_name, "")
            cleaned = _clean_string(raw_value)

            # Validaciones por campo
            if field_name in ENTITY_SCHEMA[entity]["required"] and not cleaned:
                errors.append(
                    ImportError(
                        row_number=row_num,
                        column=field_name,
                        value=raw_value,
                        reason=f"El campo '{field_name}' es requerido y está vacío.",
                    )
                )
                row_has_error = True
                continue

            if field_name == "precio":
                price = _clean_price(cleaned)
                if price is None and cleaned:
                    errors.append(
                        ImportError(
                            row_number=row_num,
                            column="precio",
                            value=raw_value,
                            reason=f"Valor de precio inválido: '{raw_value}'.",
                        )
                    )
                    row_has_error = True
                    continue
                record[field_name] = price or 0.0

            elif field_name == "precio_cobrado":
                record[field_name] = _clean_price(cleaned) or 0.0

            elif field_name == "duracion_minutos":
                try:
                    record[field_name] = int(float(cleaned)) if cleaned else None
                except ValueError:
                    errors.append(
                        ImportError(
                            row_number=row_num,
                            column="duracion_minutos",
                            value=raw_value,
                            reason=f"Duración debe ser un número entero: '{raw_value}'.",
                        )
                    )
                    row_has_error = True
                    continue

            elif field_name == "email" and cleaned:
                if "@" not in cleaned or "." not in cleaned.split("@")[-1]:
                    errors.append(
                        ImportError(
                            row_number=row_num,
                            column="email",
                            value=raw_value,
                            reason=f"Email con formato inválido: '{raw_value}'.",
                        )
                    )
                    row_has_error = True
                    continue
                record[field_name] = cleaned.lower()

            else:
                record[field_name] = cleaned if cleaned else None

        if not row_has_error and record:
            valid_rows.append(record)

    return valid_rows, errors


# ── Capa 4: Persistencia ──────────────────────────────────────────────────────
def _persist_batch(
    tenant_id: str,
    entity: str,
    valid_rows: list[dict],
    db_client: Any,
) -> tuple[int, int, list[ImportError]]:
    """
    Escribe filas válidas en Supabase en lotes de 100.
    Inyecta tenant_id en cada fila.

    Retorna (success_count, error_count, persist_errors).
    """
    if not tenant_id:
        raise ValueError("tenant_id es requerido para persistir datos.")

    success = 0
    error_count = 0
    persist_errors: list[ImportError] = []
    batch_size = 100
    table_map = {
        "clients": "clients",
        "services": "services",
        "appointments": "appointments",
    }
    table = table_map[entity]

    for i in range(0, len(valid_rows), batch_size):
        batch = valid_rows[i : i + batch_size]
        # Inyectar tenant_id en cada fila del batch
        batch_with_tenant = [{**row, "tenant_id": tenant_id} for row in batch]

        try:
            response = db_client.table(table).insert(batch_with_tenant).execute()
            if hasattr(response, "data") and response.data:
                success += len(response.data)
            else:
                # Supabase retorna error en response.error
                error_msg = getattr(response, "error", "Error desconocido de Supabase")
                logger.error(
                    "batch_insert_failed",
                    extra={"entity": entity, "batch_start": i, "error": str(error_msg)},
                )
                error_count += len(batch)
                persist_errors.append(
                    ImportError(
                        row_number=i + 2,
                        column="batch",
                        value=f"Filas {i + 2} a {i + len(batch) + 1}",
                        reason=f"Error de base de datos: {error_msg}",
                    )
                )
        except Exception as exc:
            logger.exception(
                "batch_insert_exception",
                extra={"entity": entity, "batch_start": i},
            )
            error_count += len(batch)
            persist_errors.append(
                ImportError(
                    row_number=i + 2,
                    column="batch",
                    value=f"Filas {i + 2} a {i + len(batch) + 1}",
                    reason=str(exc),
                )
            )

    return success, error_count, persist_errors


# ── API Pública ───────────────────────────────────────────────────────────────
def process_import(
    tenant_id: str,
    file_bytes: bytes,
    filename: str,
    entity: str,
    column_mapping: dict[str, str | None],
    db_client: Any,
) -> ImportResult:
    """
    Pipeline completo de importación.

    Args:
        tenant_id:      UUID del tenant. Requerido.
        file_bytes:     Contenido binario del archivo subido.
        filename:       Nombre original del archivo (para detectar extensión).
        entity:         'clients' | 'services' | 'appointments'
        column_mapping: Mapeo {campo_interno: columna_df} confirmado por el usuario.
        db_client:      Cliente Supabase (anon o service_role según contexto).

    Returns:
        ImportResult con resumen completo de la operación.
    """
    if not tenant_id:
        raise ValueError("tenant_id es requerido para importar datos.")

    if entity not in ENTITY_SCHEMA:
        raise ValueError(f"Entidad desconocida: '{entity}'.")

    logger.info(
        "import_started",
        extra={"tenant_id": tenant_id, "entity": entity, "filename": filename},
    )

    # 1. Parsear archivo
    df = parse_file(file_bytes, filename)
    result = ImportResult(entity=entity, total_rows=len(df))

    # 2. Validar que campos requeridos estén mapeados
    missing = validate_columns(column_mapping, entity)
    if missing:
        raise ValueError(
            f"Campos requeridos sin mapear: {missing}. "
            "Asignalos en el mapeador de columnas antes de continuar."
        )

    # 3. Validar y transformar filas
    valid_rows, row_errors = _validate_and_transform_rows(df, column_mapping, entity)
    result.errors.extend(row_errors)
    result.error_count += len(row_errors)
    result.skipped_count = len(df) - len(valid_rows) - len(row_errors)

    if not valid_rows:
        logger.warning(
            "import_no_valid_rows",
            extra={"tenant_id": tenant_id, "entity": entity, "errors": len(row_errors)},
        )
        return result

    # 4. Persistir en Supabase
    success, persist_errors_count, persist_errors = _persist_batch(
        tenant_id, entity, valid_rows, db_client
    )
    result.success_count = success
    result.error_count += persist_errors_count
    result.errors.extend(persist_errors)

    logger.info(
        "import_completed",
        extra={
            "tenant_id": tenant_id,
            "entity": entity,
            "success": result.success_count,
            "errors": result.error_count,
        },
    )
    return result


def get_file_preview(file_bytes: bytes, filename: str, n_rows: int = 5) -> pd.DataFrame:
    """
    Retorna las primeras n_rows filas del archivo para preview en UI.
    No persiste nada. Solo para mostrar al usuario antes de confirmar.
    """
    df = parse_file(file_bytes, filename)
    return df.head(n_rows)
