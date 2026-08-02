"""
Cruza os áudios das pastas VOZ_PADRAO_* (SVM) com o texto extraído do
svm.d, gerando metadata.csv em cada pasta.

Uso:
    python merge_svm_audio_text.py --dataset "D:\\Meus Projetos\\dataset" --json "svm_dataset.json"
"""

import argparse
import json
import csv
from pathlib import Path


def main(dataset_dir: Path, json_path: Path):
    with open(json_path, encoding="utf-8") as f:
        entries = json.load(f)

    text_by_filename = {e["audio_filename"].strip().upper(): e["text_en"] for e in entries}
    print(f"Textos SVM carregados: {len(text_by_filename)}\n")

    char_dirs = sorted([p for p in dataset_dir.iterdir() if p.is_dir() and p.name.startswith("VOZ_PADRAO_")])
    print(f"Pastas VOZ_PADRAO encontradas: {len(char_dirs)}\n")

    total_matched = 0
    total_unmatched = 0

    for char_dir in char_dirs:
        wav_files = sorted({p.resolve() for p in char_dir.glob("*.wav")}, key=lambda p: p.name)

        rows = []
        unmatched = 0

        for wav_path in wav_files:
            key = wav_path.name.strip().upper()
            text_en = text_by_filename.get(key)

            if text_en:
                rows.append((wav_path.name, text_en))
                total_matched += 1
            else:
                unmatched += 1
                total_unmatched += 1

        if rows:
            metadata_path = char_dir / "metadata.csv"
            with open(metadata_path, "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f, delimiter="|")
                writer.writerows(rows)

        print(f"  [{char_dir.name}] {len(rows)} com texto | sem texto: {unmatched}")

    print(f"\nTOTAL casado: {total_matched}")
    print(f"TOTAL sem texto: {total_unmatched}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--json", required=True)

    args = parser.parse_args()
    main(Path(args.dataset), Path(args.json))