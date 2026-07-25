"""
Reconstrói metadata.csv (EN) e metadata_pt.csv (EN+PT) de cada pasta de
personagem após a correção de contaminação de speaker, reaproveitando o
dialogue_dataset.json (texto original) e translations_index.json
(traduções já pagas, sem chamar a API de novo).

Uso:
    python rebuild_metadata.py --dataset "D:\\Meus Projetos\\dataset" --dialogue-json "dialogue_dataset.json" --translations "translations_index.json"
"""

import argparse
import csv
import json
from pathlib import Path
from collections import defaultdict


def main(dataset_dir: Path, dialogue_json: Path, translations_json: Path):
    with open(dialogue_json, encoding="utf-8") as f:
        entries = json.load(f)

    with open(translations_json, encoding="utf-8") as f:
        translations = json.load(f)

    # Indexa texto em inglês por nome de arquivo (fonte da verdade pro texto original)
    text_by_filename = {e["audio_filename"].strip().upper(): e["text_en"] for e in entries if e.get("text_en")}

    char_dirs = sorted([p for p in dataset_dir.iterdir() if p.is_dir()])
    print(f"Reconstruindo metadata para {len(char_dirs)} pastas...\n")

    total_with_text = 0
    total_with_translation = 0
    total_missing_translation = []

    for char_dir in char_dirs:
        wav_files = sorted({p.resolve() for p in char_dir.glob("*.wav")}, key=lambda p: p.name)
        if not wav_files:
            continue

        rows_en = []
        rows_pt = []

        for wav_path in wav_files:
            key = wav_path.name.strip().upper()
            text_en = text_by_filename.get(key)

            if not text_en:
                continue

            rows_en.append((wav_path.name, text_en))
            total_with_text += 1

            translation = translations.get(key)
            if translation:
                rows_pt.append((wav_path.name, translation["text_en"], translation["text_pt"]))
                total_with_translation += 1
            else:
                total_missing_translation.append((char_dir.name, wav_path.name))

        if rows_en:
            with open(char_dir / "metadata.csv", "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f, delimiter="|")
                writer.writerows(rows_en)

        if rows_pt:
            with open(char_dir / "metadata_pt.csv", "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f, delimiter="|")
                writer.writerows(rows_pt)

        print(f"  [{char_dir.name}] {len(rows_en)} com texto | {len(rows_pt)} com tradução")

    print(f"\n=== RESUMO ===")
    print(f"Total com texto EN: {total_with_text}")
    print(f"Total com tradução PT (reaproveitada): {total_with_translation}")
    print(f"Faltando tradução (precisará traduzir): {len(total_missing_translation)}")

    if total_missing_translation:
        out_path = dataset_dir.parent / "missing_translations.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(total_missing_translation, f, ensure_ascii=False, indent=2)
        print(f"Lista de faltantes salva em: {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--dialogue-json", required=True)
    parser.add_argument("--translations", required=True)

    args = parser.parse_args()
    main(Path(args.dataset), Path(args.dialogue_json), Path(args.translations))