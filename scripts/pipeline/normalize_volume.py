"""
Normaliza o volume (RMS) dos áudios dublados para bater com o nível do
áudio original correspondente, evitando que a dublagem soe mais alta
que o jogo original (comum em falas ambiente/SVM).

Uso:
    python normalize_volume.py --dubbed "D:\\Meus Projetos\\dublagem_completa_final" --originals "D:\\Meus Projetos\\dataset" --out "D:\\Meus Projetos\\dublagem_normalizada"
"""

import argparse
import shutil
from pathlib import Path

import numpy as np
import soundfile as sf


def rms(audio: np.ndarray) -> float:
    return np.sqrt(np.mean(audio.astype(np.float64) ** 2))


def normalize_to_match(dubbed_path: Path, original_path: Path, out_path: Path, max_gain: float = 3.0):
    dubbed, sr_d = sf.read(str(dubbed_path))
    original, sr_o = sf.read(str(original_path))

    rms_dubbed = rms(dubbed)
    rms_original = rms(original)

    if rms_dubbed <= 0 or rms_original <= 0:
        shutil.copy2(dubbed_path, out_path)
        return False

    gain = rms_original / rms_dubbed
    gain = min(gain, max_gain)  # evita amplificar demais se o original for muito mais alto

    adjusted = dubbed * gain
    adjusted = np.clip(adjusted, -1.0, 1.0)  # evita distorção por clipping

    sf.write(str(out_path), adjusted, sr_d)
    return True


def main(dubbed_dir: Path, originals_dir: Path, out_dir: Path):
    char_dirs = sorted([p for p in dubbed_dir.iterdir() if p.is_dir()])

    total = 0
    normalized = 0
    skipped = 0

    for char_dir in char_dirs:
        original_char_dir = originals_dir / char_dir.name
        out_char_dir = out_dir / char_dir.name
        out_char_dir.mkdir(parents=True, exist_ok=True)

        for dubbed_wav in char_dir.glob("*.wav"):
            total += 1
            original_wav = original_char_dir / dubbed_wav.name
            out_wav = out_char_dir / dubbed_wav.name

            if not original_wav.exists():
                shutil.copy2(dubbed_wav, out_wav)
                skipped += 1
                continue

            ok = normalize_to_match(dubbed_wav, original_wav, out_wav)
            if ok:
                normalized += 1
            else:
                skipped += 1

        print(f"  [{char_dir.name}] processado")

    print(f"\n=== RESUMO ===")
    print(f"Total: {total}")
    print(f"Normalizados: {normalized}")
    print(f"Copiados sem alteração (sem original ou erro): {skipped}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dubbed", required=True, help="Pasta com os áudios dublados")
    parser.add_argument("--originals", required=True, help="Pasta com os áudios originais (dataset)")
    parser.add_argument("--out", required=True, help="Pasta de saída (áudios normalizados)")

    args = parser.parse_args()
    main(Path(args.dubbed), Path(args.originals), Path(args.out))