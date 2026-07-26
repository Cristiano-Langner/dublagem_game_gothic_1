"""
Seleciona o(s) melhor(es) clipe(s) de áudio original para servir de
referência de voz no XTTS v2 (voice cloning zero-shot).

Uso:
    python select_xtts_reference.py --dataset "D:\\Meus Projetos\\dataset" --character DIEGO --out "D:\\Meus Projetos\\xtts_references"
"""

import argparse
import shutil
import soundfile as sf
from pathlib import Path

MIN_DURATION = 6.0   # segundos mínimos desejados
MAX_DURATION = 20.0  # teto, não precisa mais que isso


def get_duration(wav_path: Path) -> float:
    info = sf.info(str(wav_path))
    return info.frames / info.samplerate


def select_reference(char_dir: Path, out_dir: Path, character: str):
    wav_files = list(char_dir.glob("*.wav"))
    if not wav_files:
        print(f"  [{character}] nenhum áudio encontrado")
        return

    # Ordena do mais longo para o mais curto
    durations = [(w, get_duration(w)) for w in wav_files]
    durations.sort(key=lambda x: -x[1])

    longest_path, longest_dur = durations[0]

    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{character}_reference.wav"

    if longest_dur >= MIN_DURATION:
        # A fala mais longa já basta sozinha
        shutil.copy2(longest_path, out_path)
        print(f"  [{character}] referência: {longest_path.name} ({longest_dur:.1f}s)")
        return

    # Precisa concatenar algumas falas até atingir o mínimo
    import numpy as np
    chunks = []
    total_dur = 0.0
    used = []

    for wav_path, dur in durations:
        if total_dur >= MIN_DURATION:
            break
        data, sr = sf.read(str(wav_path))
        chunks.append(data)
        used.append(wav_path.name)
        total_dur += dur

    if not chunks:
        print(f"  [{character}] falha ao montar referência")
        return

    concatenated = np.concatenate(chunks)
    sf.write(str(out_path), concatenated, sr)
    print(f"  [{character}] referência concatenada de {len(used)} falas: {', '.join(used)} ({total_dur:.1f}s total)")


def main(dataset_dir: Path, character: str, out_dir: Path):
    char_dir = dataset_dir / character
    if not char_dir.exists():
        raise FileNotFoundError(f"Pasta não encontrada: {char_dir}")

    select_reference(char_dir, out_dir, character)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--character", required=True)
    parser.add_argument("--out", required=True)

    args = parser.parse_args()
    main(Path(args.dataset), args.character, Path(args.out))