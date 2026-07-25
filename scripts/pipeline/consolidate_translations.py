"""
Consolida todas as traduções já feitas (metadata_pt.csv espalhados pelas
pastas de personagem) num índice único, para reaproveitar após a correção
de contaminação de speaker (sem gastar API de novo).

Uso:
    python consolidate_translations.py --dataset "D:\\Meus Projetos\\dataset" --out "translations_index.json"
"""

import argparse
import csv
import json
from pathlib import Path


def main(dataset_dir: Path, out_path: Path):
    index = {}
    total_rows = 0

    for char_dir in dataset_dir.iterdir():
        if not char_dir.is_dir():
            continue
        metadata_pt = char_dir / "metadata_pt.csv"
        if not metadata_pt.exists():
            continue

        with open(metadata_pt, encoding="utf-8") as f:
            reader = csv.reader(f, delimiter="|")
            for row in reader:
                if len(row) != 3:
                    continue
                filename, text_en, text_pt = row
                index[filename.strip().upper()] = {
                    "text_en": text_en,
                    "text_pt": text_pt,
                }
                total_rows += 1

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    print(f"Total de traduções consolidadas: {total_rows}")
    print(f"Índice salvo em: {out_path.resolve()}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--out", required=True)

    args = parser.parse_args()
    main(Path(args.dataset), Path(args.out))