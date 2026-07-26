"""
Gera dublagem de teste (TTS + conversão RVC) para todos os personagens
que já têm modelo treinado, usando algumas falas de amostra de cada um.

Uso:
    python dub_ready_characters.py --dataset "D:\\Meus Projetos\\dataset" --rvc-dir "D:\\RVC (WebUI)\\rvc-webui" --out "D:\\Meus Projetos\\dublagem_teste" --samples 3
"""

import argparse
import asyncio
import csv
import os
import subprocess
from pathlib import Path

import edge_tts

TTS_VOICE = "pt-BR-AntonioNeural"


def find_ready_characters(rvc_dir: Path) -> dict[str, Path]:
    weights_dir = rvc_dir / "assets" / "weights"
    if not weights_dir.exists():
        return {}

    ready = {}
    for pth_file in weights_dir.glob("*.pth"):
        name = pth_file.stem.split("_e")[0]
        if name not in ready or pth_file.stat().st_mtime > ready[name].stat().st_mtime:
            ready[name] = pth_file

    return ready


def load_sample_lines(dataset_dir: Path, character: str, n_samples: int) -> list[tuple[str, str]]:
    metadata_path = dataset_dir / character / "metadata_pt.csv"
    if not metadata_path.exists():
        return []

    rows = []
    with open(metadata_path, encoding="utf-8") as f:
        reader = csv.reader(f, delimiter="|")
        for row in reader:
            if len(row) == 3:
                rows.append((row[0], row[2]))

    return rows[:n_samples]


async def generate_tts(text: str, output_path: Path, voice: str = TTS_VOICE):
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(str(output_path))


def convert_with_rvc(rvc_python: Path, rvc_dir: Path, model_path: Path, input_wav: Path, output_wav: Path) -> tuple:
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"

    cmd = [
        str(rvc_python), "test_inference.py",
        "--model", str(model_path.relative_to(rvc_dir)).replace("\\", "/"),
        "--input", str(input_wav),
        "--output", str(output_wav),
    ]
    result = subprocess.run(cmd, cwd=str(rvc_dir), capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
    return result.returncode == 0, result.stdout, result.stderr


def main(dataset_dir: Path, rvc_dir: Path, out_dir: Path, n_samples: int):
    rvc_python = rvc_dir / ".venv" / "Scripts" / "python.exe"
    ready = find_ready_characters(rvc_dir)

    print(f"Personagens com modelo pronto: {len(ready)}\n")

    tts_temp_dir = out_dir / "_tts_temp"
    tts_temp_dir.mkdir(parents=True, exist_ok=True)

    for char_name, model_path in sorted(ready.items()):
        samples = load_sample_lines(dataset_dir, char_name, n_samples)
        if not samples:
            print(f"  [{char_name}] sem metadata_pt.csv ou sem falas, pulando")
            continue

        char_out_dir = out_dir / char_name
        char_out_dir.mkdir(parents=True, exist_ok=True)

        print(f"  [{char_name}] gerando {len(samples)} amostras...")

        for filename, text_pt in samples:
            tts_path = tts_temp_dir / f"{char_name}_{filename}"
            final_path = char_out_dir / filename

            if final_path.exists():
                continue

            try:
                asyncio.run(generate_tts(text_pt, tts_path))
            except Exception as e:
                print(f"    [{filename}] ERRO no TTS: {e}")
                continue

            ok, out, err = convert_with_rvc(rvc_python, rvc_dir, model_path, tts_path, final_path)
            if not ok:
                print(f"    [{filename}] ERRO no RVC: {err[-300:]}")
                continue

            print(f"    [{filename}] OK: \"{text_pt[:50]}\"")

    print(f"\nResultados salvos em: {out_dir.resolve()}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--rvc-dir", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--samples", type=int, default=3)

    args = parser.parse_args()
    main(Path(args.dataset), Path(args.rvc_dir), Path(args.out), args.samples)