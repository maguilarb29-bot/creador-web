from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from google.oauth2 import service_account
from googleapiclient.discovery import build


SCRIPT_PATH = Path(__file__).resolve()
PROJECT_ROOT = SCRIPT_PATH.parents[2]
ENV_PATH = PROJECT_ROOT / "pignatelli-app" / ".env.local"
JSON_PATH = PROJECT_ROOT / "Api_PG" / "data" / "solaris_catalogo.json"

SHEET_NAME = "INVENTARIO_MAESTRO"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

HEADERS = [
    "codigoItem",
    "nombreES",
    "descripcionES",
    "categoria",
    "catCodigo",
    "ubicacion",
    "precioUSD",
    "tieneSothebys",
    "refSothebys",
    "cantidad",
    "materiales",
    "estilo",
    "estado",
    "foto1",
    "foto2",
    "foto3",
    "esRef",
    "notas",
]

CAT_ORDER = {
    "C": 0,
    "D": 1,
    "E": 2,
    "F": 3,
    "G": 4,
    "J": 5,
    "M": 6,
    "P": 7,
    "S": 8,
    "U": 9,
}


def load_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        raise FileNotFoundError(f"No se encontro .env.local en: {path}")

    env: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if value.startswith('"') and value.endswith('"'):
            value = value[1:-1]
        env[key] = value
    return env


def get_sheets_service() -> tuple[Any, str]:
    env = load_env_file(ENV_PATH)
    sheet_id = env.get("GOOGLE_SHEETS_ID", "").strip()
    service_account_email = env.get("GOOGLE_SERVICE_ACCOUNT_EMAIL", "").strip()
    private_key = env.get("GOOGLE_PRIVATE_KEY", "").replace("\\n", "\n").strip()

    if not sheet_id or not service_account_email or not private_key:
        raise RuntimeError(
            "Faltan GOOGLE_SHEETS_ID, GOOGLE_SERVICE_ACCOUNT_EMAIL o GOOGLE_PRIVATE_KEY en .env.local"
        )

    credentials_info = {
        "type": "service_account",
        "project_id": "inventario-pignatelli",
        "private_key_id": "",
        "private_key": private_key,
        "client_email": service_account_email,
        "client_id": "",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": (
            "https://www.googleapis.com/robot/v1/metadata/x509/"
            + service_account_email.replace("@", "%40")
        ),
    }

    credentials = service_account.Credentials.from_service_account_info(
        credentials_info,
        scopes=SCOPES,
    )
    service = build("sheets", "v4", credentials=credentials, cache_discovery=False)
    return service, sheet_id


def load_catalog(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as fh:
        raw = json.load(fh)

    if isinstance(raw, dict):
        items = list(raw.values())
    elif isinstance(raw, list):
        items = raw
    else:
        raise TypeError("solaris_catalogo.json debe ser una lista o un objeto")

    normalized: list[dict[str, Any]] = []
    for item in items:
        if isinstance(item, dict):
            normalized.append(item)
    return normalized


def is_ref_photo_name(name: str) -> bool:
    if not name:
        return False
    return bool(re.search(r"(^|[-_\s])ref([-. _]|$)", name, re.IGNORECASE))


def es_ref_item(item: dict[str, Any]) -> bool:
    fotos = [str(f).strip() for f in item.get("fotos", []) if str(f).strip()]
    notas = str(item.get("notas", "") or "")
    if "Ref del set" in notas:
        return True
    if len(fotos) == 1 and is_ref_photo_name(fotos[0]):
        return True
    return False


def es_nodo_estructural(item: dict[str, Any]) -> bool:
    tipo = str(item.get("tipoEstructural", "") or "").strip().upper()
    return tipo in {"GRUPO", "SUBSET", "REF"}


def normalize_notes(item: dict[str, Any], nombre_fallback: bool) -> str:
    notas = str(item.get("notas", "") or "").strip()
    extras: list[str] = []
    if notas:
        extras.append(notas)
    if nombre_fallback:
        extras.append("PENDIENTE NOMBRE")
    return " | ".join(extras)


def compact_null(value: Any) -> str | int | float:
    if value is None:
        return ""
    if isinstance(value, str):
        text = value.strip()
        if text.lower() in {"none", "null"}:
            return ""
        return text
    return value


def split_photos(fotos: list[str]) -> tuple[str, str, str]:
    clean = [f.strip() for f in fotos if str(f).strip()]
    foto1 = clean[0] if len(clean) > 0 else ""
    foto2 = clean[1] if len(clean) > 1 else ""
    if len(clean) <= 2:
        foto3 = clean[2] if len(clean) > 2 else ""
    else:
        foto3 = clean[2] if len(clean) == 3 else " | ".join(clean[2:])
    return foto1, foto2, foto3


def build_row(item: dict[str, Any]) -> list[Any]:
    fotos = [str(f).strip() for f in item.get("fotos", []) if str(f).strip()]
    foto1, foto2, foto3 = split_photos(fotos)
    nombre_original = compact_null(item.get("nombreES"))
    descripcion_original = compact_null(item.get("descripcionOriginal"))
    nombre_fallback = not bool(nombre_original)
    precio = item.get("precioUSD")
    if precio in (None, 0, 0.0, "0", "0.0"):
        precio = ""

    return [
        compact_null(item.get("codigoItem")),
        nombre_original or descripcion_original,
        compact_null(item.get("descripcionES")),
        compact_null(item.get("categoria")),
        compact_null(item.get("catCodigo")),
        compact_null(item.get("ubicacion")),
        precio,
        "TRUE" if item.get("tieneSothebys") else "FALSE",
        compact_null(item.get("refSothebys")),
        item.get("cantidad") if item.get("cantidad") not in (None, "") else 1,
        compact_null(item.get("materiales")),
        compact_null(item.get("estilo")),
        compact_null(item.get("estado")),
        foto1,
        foto2,
        foto3,
        "TRUE" if any(is_ref_photo_name(f) for f in fotos) else "FALSE",
        normalize_notes(item, nombre_fallback),
    ]


def sort_key(item: dict[str, Any]) -> tuple[int, int, str]:
    cat_codigo = str(item.get("catCodigo", "") or "").strip()
    num_item = item.get("numItem")
    try:
        num_item_value = int(num_item)
    except (TypeError, ValueError):
        num_item_value = 10**9
    codigo_item = str(item.get("codigoItem", "") or "").strip()
    return (CAT_ORDER.get(cat_codigo, 999), num_item_value, codigo_item)


def clear_sheet_body(service: Any, sheet_id: str) -> None:
    service.spreadsheets().values().clear(
        spreadsheetId=sheet_id,
        range=f"{SHEET_NAME}!A2:R",
        body={},
    ).execute()


def write_headers(service: Any, sheet_id: str) -> None:
    service.spreadsheets().values().update(
        spreadsheetId=sheet_id,
        range=f"{SHEET_NAME}!A1:R1",
        valueInputOption="RAW",
        body={"values": [HEADERS]},
    ).execute()


def write_rows(service: Any, sheet_id: str, rows: list[list[Any]]) -> None:
    service.spreadsheets().values().batchUpdate(
        spreadsheetId=sheet_id,
        body={
            "valueInputOption": "USER_ENTERED",
            "data": [
                {
                    "range": f"{SHEET_NAME}!A2:R{len(rows) + 1}",
                    "values": rows,
                }
            ],
        },
    ).execute()


def read_back_rows(service: Any, sheet_id: str) -> list[list[str]]:
    response = service.spreadsheets().values().get(
        spreadsheetId=sheet_id,
        range=f"{SHEET_NAME}!A2:R",
        valueRenderOption="UNFORMATTED_VALUE",
    ).execute()
    return response.get("values", [])


def validate_rows(rows: list[list[Any]], written_rows: list[list[Any]]) -> None:
    if len(written_rows) != len(rows):
        raise RuntimeError(
            f"Validacion fallida: filas escritas {len(written_rows)} != filas esperadas {len(rows)}"
        )

    expected_codes = [str(row[0]) for row in rows]
    written_codes = [str(row[0]) for row in written_rows]
    if written_codes != expected_codes:
        raise RuntimeError("Validacion fallida: los codigos no quedaron ordenados correctamente")

    for row in written_rows:
        for cell in row:
            if str(cell).strip().lower() in {"none", "null"}:
                raise RuntimeError('Validacion fallida: se detecto "None" o "null" como texto')


def build_rows(items: list[dict[str, Any]]) -> list[list[Any]]:
    filtered = [item for item in items if not es_ref_item(item) and not es_nodo_estructural(item)]
    ordered = sorted(filtered, key=sort_key)
    return [build_row(item) for item in ordered]


def print_summary(rows: list[list[Any]]) -> None:
    con_sothebys = sum(1 for row in rows if row[7] == "TRUE")
    sin_precio = sum(1 for row in rows if row[6] == "")
    sin_descripcion = sum(1 for row in rows if not str(row[2]).strip())

    print(f"Filas escritas: {len(rows)}")
    print(f"Articulos con Sotheby's: {con_sothebys}")
    print(f"Articulos sin precio: {sin_precio}")
    print(f"Articulos sin descripcionES: {sin_descripcion}")


def main() -> None:
    catalog = load_catalog(JSON_PATH)
    rows = build_rows(catalog)

    service, sheet_id = get_sheets_service()
    clear_sheet_body(service, sheet_id)
    write_headers(service, sheet_id)
    write_rows(service, sheet_id, rows)

    written_rows = read_back_rows(service, sheet_id)
    validate_rows(rows, written_rows)
    print_summary(rows)


if __name__ == "__main__":
    main()
