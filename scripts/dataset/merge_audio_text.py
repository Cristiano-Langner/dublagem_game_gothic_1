"""
Cruza os áudios já organizados por personagem (dataset/<personagem>/*.wav)
com os textos extraídos dos scripts (dialogue_dataset.json), gerando um
metadata.csv por personagem no formato LJSpeech: nome_arquivo|texto

Uso:
    python merge_audio_text.py --dataset "D:\\Meus Projetos\\dataset" --json "D:\\Meus Projetos\\dialogue_dataset.json"
"""

import argparse
import json
import csv
from pathlib import Path
from collections import defaultdict


def load_text_entries(json_path: Path):
    with open(json_path, encoding="utf-8") as f:
        entries = json.load(f)

    # Indexa por nome de arquivo (upper, sem espaços) para casar com o que está no disco
    by_filename = {}
    for e in entries:
        key = e["audio_filename"].strip().upper()
        by_filename[key] = e

    return by_filename


def merge(dataset_dir: Path, json_path: Path):
    text_by_filename = load_text_entries(json_path)
    print(f"Textos carregados do JSON: {len(text_by_filename)}")

    character_folders = [p for p in dataset_dir.iterdir() if p.is_dir()]
    print(f"Pastas de personagem encontradas: {len(character_folders)}\n")

    total_matched = 0
    total_unmatched = 0
    summary = []

    for char_folder in character_folders:
        wav_files = list(char_folder.glob("*.wav")) + list(char_folder.glob("*.WAV"))
        wav_files = sorted({p.resolve() for p in wav_files}, key=lambda p: p.name)

        rows = []
        unmatched_here = 0

        for wav_path in wav_files:
            key = wav_path.name.strip().upper()
            entry = text_by_filename.get(key)

            if entry and entry.get("text_en"):
                rows.append((wav_path.name, entry["text_en"]))
                total_matched += 1
            else:
                unmatched_here += 1
                total_unmatched += 1

        if rows:
            metadata_path = char_folder / "metadata.csv"
            with open(metadata_path, "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f, delimiter="|")
                for filename, text in rows:
                    writer.writerow([filename, text])

        summary.append((char_folder.name, len(rows), unmatched_here))

    print("Resumo por personagem (falas com texto | falas sem texto):")
    for name, matched, unmatched in sorted(summary, key=lambda x: -x[1])[:20]:
        print(f"  {name:30s} {matched:5d} | sem texto: {unmatched}")

    print(f"\nTOTAL casado (áudio + texto): {total_matched}")
    print(f"TOTAL sem texto correspondente: {total_unmatched}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Junta áudio organizado com texto extraído em metadata.csv por personagem.")
    parser.add_argument("--dataset", required=True, help="Pasta raiz do dataset organizado por personagem")
    parser.add_argument("--json", required=True, help="Caminho do dialogue_dataset.json")

    args = parser.parse_args()
    merge(Path(args.dataset), Path(args.json))