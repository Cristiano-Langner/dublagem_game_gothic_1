"""
Converte os áudios dublados (PCM, gerados pelo XTTS) para IMA_ADPCM
(formato original do jogo) e organiza numa estrutura de pasta única,
pronta para empacotamento em VDF.

Uso:
    python prepare_repack.py --dubbed "D:\\Meus Projetos\\dublagem_completa_final" --out "D:\\Meus Projetos\\repack_build"
"""

import argparse
import subprocess
from pathlib import Path


def main(dubbed_dir: Path, out_dir: Path):
    target_dir = out_dir / "_WORK" / "DATA" / "SOUND" / "SPEECH"
    target_dir.mkdir(parents=True, exist_ok=True)

    wav_files = list(dubbed_dir.rglob("*.wav")) + list(dubbed_dir.rglob("*.WAV"))
    wav_files = [w for w in wav_files if "_tts_temp" not in str(w)]

    print(f"Encontrados {len(wav_files)} áudios dublados\n")

    converted = 0
    errors = 0

    for wav_path in wav_files:
        out_name = wav_path.name.upper()
        if not out_name.endswith(".WAV"):
            out_name += ".WAV"
        out_path = target_dir / out_name

        cmd = [
            "ffmpeg", "-y", "-i", str(wav_path),
            "-acodec", "adpcm_ima_wav",
            "-ar", "44100",
            "-ac", "1",
            str(out_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            converted += 1
        else:
            print(f"  ERRO em {wav_path.name}: {result.stderr[-300:]}")
            errors += 1

    print(f"\nConvertidos: {converted}")
    print(f"Erros: {errors}")
    print(f"\nEstrutura pronta em: {target_dir.resolve()}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dubbed", required=True)
    parser.add_argument("--out", required=True)

    args = parser.parse_args()
    main(Path(args.dubbed), Path(args.out))