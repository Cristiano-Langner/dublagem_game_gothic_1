"""
Gera a referência de voz XTTS para todos os personagens do dataset de uma vez.

Uso:
    python batch_select_xtts_references.py --dataset "D:\\Meus Projetos\\dataset" --out "D:\\Meus Projetos\\xtts_references"
"""

import argparse
import shutil
import soundfile as sf
import numpy as np
from pathlib import Path

MIN_DURATION = 6.0
MAX_DURATION = 20.0


def get_duration(wav_path: Path) -> float:
    info = sf.info(str(wav_path))
    return info.frames / info.samplerate


def select_reference(char_dir: Path, out_dir: Path, character: str) -> bool:
    wav_files = list(char_dir.glob("*.wav"))
    if not wav_files:
        return False

    durations = [(w, get_duration(w)) for w in wav_files]
    durations.sort(key=lambda x: -x[1])

    longest_path, longest_dur = durations[0]
    out_path = out_dir / f"{character}_reference.wav"

    if out_path.exists():
        return True  # já existe, pula

    if longest_dur >= MIN_DURATION:
        shutil.copy2(longest_path, out_path)
        return True

    chunks = []
    total_dur = 0.0
    for wav_path, dur in durations:
        if total_dur >= MIN_DURATION:
            break
        data, sr = sf.read(str(wav_path))
        chunks.append(data)
        total_dur += dur

    if not chunks:
        return False

    concatenated = np.concatenate(chunks)
    sf.write(str(out_path), concatenated, sr)
    return True


def main(dataset_dir: Path, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    char_dirs = sorted([p for p in dataset_dir.iterdir() if p.is_dir()])

    print(f"Processando {len(char_dirs)} personagens...\n")

    success = 0
    failed = []

    for char_dir in char_dirs:
        ok = select_reference(char_dir, out_dir, char_dir.name)
        if ok:
            success += 1
        else:
            failed.append(char_dir.name)

    print(f"Referências geradas: {success}")
    print(f"Falharam (sem áudio): {len(failed)}")
    if failed:
        print("Personagens sem referência:", ", ".join(failed))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--out", required=True)

    args = parser.parse_args()
    main(Path(args.dataset), Path(args.out))