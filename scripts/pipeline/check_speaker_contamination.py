"""
Verifica se falas de outro personagem (tipicamente o Herói/"other") estão
misturadas dentro da pasta de um personagem específico, usando os campos
speaker/listener capturados no dialogue_dataset.json.

Uso:
    python check_speaker_contamination.py --json "D:\\Meus Projetos\\dialogue_dataset.json" --character DIEGO
"""

import argparse
import json
from pathlib import Path
from collections import Counter


def main(json_path: Path, character: str):
    with open(json_path, encoding="utf-8") as f:
        entries = json.load(f)

    char_entries = [e for e in entries if e["character_folder"].upper() == character.upper()]
    print(f"Total de falas na pasta '{character}': {len(char_entries)}\n")

    speaker_counter = Counter(e["speaker"] for e in char_entries)
    print("Distribuição do campo 'speaker' (quem fala):")
    for speaker, count in speaker_counter.most_common():
        print(f"  {speaker:20s} {count}")

    print("\nExemplos de cada valor de speaker encontrado:")
    seen = set()
    for e in char_entries:
        if e["speaker"] not in seen:
            seen.add(e["speaker"])
            print(f"  [{e['speaker']}] {e['audio_filename']}: \"{e['text_en']}\"")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", required=True)
    parser.add_argument("--character", required=True)

    args = parser.parse_args()
    main(Path(args.json), args.character)