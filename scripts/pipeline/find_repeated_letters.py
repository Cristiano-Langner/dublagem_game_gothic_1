"""
Identifica falas no metadata_pt.csv que têm sequências de letras repetidas
(padrão de grito/ênfase que confunde o XTTS), para regeneração posterior.

Uso:
    python find_repeated_letters.py --dataset "D:\\Meus Projetos\\dataset" --out "falas_com_gritos.json"
"""

import argparse
import csv
import json
import re
from pathlib import Path

PATTERN = re.compile(r'([A-Za-zÀ-ÿ])\1{2,}')  # 3+ letras repetidas seguidas


def main(dataset_dir: Path, out_path: Path):
    char_dirs = sorted([p for p in dataset_dir.iterdir() if p.is_dir()])

    flagged = []

    for char_dir in char_dirs:
        metadata_path = char_dir / "metadata_pt.csv"
        if not metadata_path.exists():
            continue

        with open(metadata_path, encoding="utf-8") as f:
            reader = csv.reader(f, delimiter="|")
            for row in reader:
                if len(row) != 3:
                    continue
                filename, text_en, text_pt = row
                if PATTERN.search(text_pt):
                    flagged.append({
                        "character": char_dir.name,
                        "filename": filename,
                        "text_pt": text_pt,
                    })

    print(f"Total de falas com letras repetidas encontradas: {len(flagged)}\n")
    for item in flagged[:20]:
        print(f"  [{item['character']}] {item['filename']}: \"{item['text_pt']}\"")
    if len(flagged) > 20:
        print(f"  ... e mais {len(flagged) - 20}")

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(flagged, f, ensure_ascii=False, indent=2)

    print(f"\nLista completa salva em: {out_path.resolve()}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--out", required=True)

    args = parser.parse_args()
    main(Path(args.dataset), Path(args.out))