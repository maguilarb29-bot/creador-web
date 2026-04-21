"""
renombrar_quitar_prefijo_letra.py

Elimina la letra mayúscula de categoría que precede al número en los
nombres de los archivos de foto, en todas las carpetas del inventario.

Ejemplos:
  F1-aparador.jpg       →  1-aparador.jpg
  D7a-figurines.jpg     →  7a-figurines.jpg
  C163ab-vajilla.jpg    →  163ab-vajilla.jpg
  U49-ref-cubeta.jpg    →  49-ref-cubeta.jpg

También actualiza solaris_catalogo.json para reflejar los nuevos nombres.
"""
import os, re, json, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FOTOS_BASE   = PROJECT_ROOT / "Api_PG" / "images" / "fotos-Solaris-inventory"
CATALOGO     = PROJECT_ROOT / "Api_PG" / "data" / "solaris_catalogo.json"

OLD_PATTERN = re.compile(r'^([A-Z])(\d.*)$')   # letra mayúscula + dígito + resto

def build_rename_map(folder: Path) -> dict[str, str]:
    """Retorna {old_name: new_name} para todos los .jpg con prefijo letra."""
    rename_map = {}
    for f in folder.iterdir():
        if not f.is_file() or not f.suffix.lower() == ".jpg":
            continue
        m = OLD_PATTERN.match(f.name)
        if m:
            new_name = m.group(2)   # solo la parte sin la letra
            rename_map[f.name] = new_name
    return rename_map


def rename_files_in_folder(folder: Path, rename_map: dict) -> int:
    count = 0
    for old_name, new_name in rename_map.items():
        old_path = folder / old_name
        new_path = folder / new_name
        if old_path.exists() and not new_path.exists():
            old_path.rename(new_path)
            count += 1
        elif old_path.exists() and new_path.exists():
            print(f"  CONFLICTO (ya existe): {new_name} — omitido")
    return count


def main():
    # -------------------------------------------------------
    # 1. Recopilar todas las carpetas a procesar
    # -------------------------------------------------------
    folders = [d for d in FOTOS_BASE.iterdir() if d.is_dir()]
    print(f"Carpetas encontradas: {[d.name for d in folders]}")

    # -------------------------------------------------------
    # 2. Construir mapa global de renombrado (old → new)
    # -------------------------------------------------------
    global_map: dict[str, str] = {}
    for folder in folders:
        m = build_rename_map(folder)
        global_map.update(m)      # same mapping regardless of folder

    print(f"\nArchivos a renombrar (nombres únicos): {len(global_map)}")
    for old, new in sorted(global_map.items())[:10]:
        print(f"  {old}  →  {new}")
    print("  ...")

    # -------------------------------------------------------
    # 3. Renombrar en cada carpeta
    # -------------------------------------------------------
    total_renamed = 0
    for folder in folders:
        local_map = build_rename_map(folder)
        n = rename_files_in_folder(folder, local_map)
        print(f"  {folder.name}: {n} archivos renombrados")
        total_renamed += n

    print(f"\nTotal archivos renombrados: {total_renamed}")

    # -------------------------------------------------------
    # 4. Actualizar solaris_catalogo.json
    # -------------------------------------------------------
    print("\nActualizando solaris_catalogo.json...")
    with open(CATALOGO, encoding="utf-8") as f:
        cat = json.load(f)

    items = list(cat.values()) if isinstance(cat, dict) else cat
    keys  = list(cat.keys())   if isinstance(cat, dict) else None

    foto_updates = 0
    for it in items:
        new_fotos = []
        for foto in (it.get("fotos") or []):
            if foto in global_map:
                new_fotos.append(global_map[foto])
                foto_updates += 1
            else:
                new_fotos.append(foto)
        it["fotos"] = new_fotos

    # Guardar
    if isinstance(cat, dict):
        new_cat = dict(zip(keys, items))
        with open(CATALOGO, "w", encoding="utf-8") as f:
            json.dump(new_cat, f, ensure_ascii=False, indent=2)
    else:
        with open(CATALOGO, "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)

    print(f"  Referencias de foto actualizadas en catálogo: {foto_updates}")

    # -------------------------------------------------------
    # 5. Resumen final
    # -------------------------------------------------------
    print()
    print("=" * 55)
    print("RENOMBRADO COMPLETO")
    print("=" * 55)
    print(f"  Archivos renombrados en disco:  {total_renamed}")
    print(f"  Referencias en catálogo JSON:   {foto_updates}")
    print(f"  Patrón eliminado: [A-Z] inicial antes del dígito")


if __name__ == "__main__":
    main()
