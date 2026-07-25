"""
Corrige a organização por personagem usando o campo 'speaker' do
dialogue_dataset.json como fonte da verdade (em vez de assumir que todo
áudio de um arquivo .d pertence ao NPC "dono" do arquivo).

Quando speaker == "self", o áudio pertence ao personagem original
(character_folder já identificado). Quando speaker indica o Herói
(other/hero/pc/player), o áudio é movido para a pasta HEROI.

Uso:
    python fix_speaker_contamination.py --json "dialogue_dataset.json" --dataset "D:\\Meus Projetos\\dataset" --dry-run
"""

import argparse
import json
import shutil
from pathlib import Path
from collections import Counter

HERO_SPEAKER_VALUES = {"hero", "other", "pc", "player", "pc_hero"}


def classify_true_owner(entry: dict) -> str:
    speaker = (entry.get("speaker") or "").strip().lower()

    if speaker == "self":
        return entry["character_folder"]

    if speaker in HERO_SPEAKER_VALUES:
        return "HEROI"

    # Fallback: nomes explícitos que não sejam "self"/"other" (raro, mas possível)
    return entry["character_folder"]


def main(json_path: Path, dataset_dir: Path, dry_run: bool):
    with open(json_path, encoding="utf-8") as f:
        entries = json.load(f)

    print(f"Total de falas no JSON: {len(entries)}\n")

    moves = []
    stats = Counter()

    for e in entries:
        original_folder = e["character_folder"]
        true_folder = classify_true_owner(e)

        if true_folder != original_folder:
            src_path = dataset_dir / original_folder / e["audio_filename"]
            dst_path = dataset_dir / true_folder / e["audio_filename"]
            moves.append((src_path, dst_path, original_folder, true_folder))
            stats[f"{original_folder} -> {true_folder}"] += 1

    print(f"Arquivos que precisam ser movidos: {len(moves)}\n")
    print("Resumo dos movimentos (top 20):")
    for change, count in stats.most_common(20):
        print(f"  {change:40s} {count}")

    if dry_run:
        print("\n[DRY-RUN] Nenhum arquivo foi movido.")
        return

    moved = 0
    not_found = 0
    for src_path, dst_path, orig, true in moves:
        if not src_path.exists():
            not_found += 1
            continue
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src_path), str(dst_path))
        moved += 1

    print(f"\nMovidos com sucesso: {moved}")
    print(f"Não encontrados (já haviam sido movidos ou não existem): {not_found}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", required=True)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--dry-run", action="store_true")

    args = parser.parse_args()
    main(Path(args.json), Path(args.dataset), args.dry_run)