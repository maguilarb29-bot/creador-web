from pathlib import Path
import sys

import fitz


def main() -> int:
    base_dir = Path(__file__).resolve().parents[1]
    pdf_candidates = sorted(base_dir.glob("Valuation*.pdf"))
    if not pdf_candidates:
        raise FileNotFoundError("No se encontro el PDF de Sotheby's en Api_PG")

    pdf_path = pdf_candidates[0]
    out_dir = base_dir / "output" / "sothebys_pages_hi"
    out_dir.mkdir(parents=True, exist_ok=True)

    zoom = float(sys.argv[1]) if len(sys.argv) > 1 else 3.0
    doc = fitz.open(pdf_path)
    matrix = fitz.Matrix(zoom, zoom)

    for i, page in enumerate(doc, start=1):
        out_path = out_dir / f"page_{i:03d}.png"
        if out_path.exists():
            continue
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        pix.save(out_path)
        print(f"exported {out_path.name}")

    print(f"done: {len(doc)} paginas -> {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
