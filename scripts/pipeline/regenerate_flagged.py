"""
Regenera apenas as falas identificadas com letras repetidas (gritos),
usando texto normalizado, sobrescrevendo os arquivos já dublados.

Uso:
    python regenerate_flagged.py --flagged "D:\\Meus Projetos\\falas_com_gritos.json" --references "D:\\Meus Projetos\\xtts_references" --out "D:\\Meus Projetos\\dublagem_completa_final"
"""

import argparse
import json
import re
from pathlib import Path

import torch
import soundfile as sf

_original_load = torch.load
def _patched_load(*args, **kwargs):
    kwargs.setdefault("weights_only", False)
    return _original_load(*args, **kwargs)
torch.load = _patched_load

import torchaudio

def _patched_torchaudio_load(filepath, **kwargs):
    data, samplerate = sf.read(str(filepath), dtype="float32", always_2d=True)
    waveform = torch.from_numpy(data.T)
    return waveform, samplerate
torchaudio.load = _patched_torchaudio_load

from TTS.api import TTS


def clean_text_for_tts(text: str) -> str:
    """Remove artefatos que o XTTS pode verbalizar ou distorcer."""
    text = text.strip()
    # Colapsa 3+ letras repetidas para 1 só (só pega exageros de grito, preserva duplas naturais do PT como "carro")
    text = re.sub(r'([A-Za-zÀ-ÿ])\1{2,}', r'\1', text)
    text = re.sub(r'([!?]){2,}', r'\1\1', text)
    text = re.sub(r'\.{2,}', ',', text)
    if text.endswith('.'):
        text = text[:-1]
    return text


def main(flagged_path: Path, references_dir: Path, out_dir: Path):
    with open(flagged_path, encoding="utf-8") as f:
        flagged = json.load(f)

    print(f"Regenerando {len(flagged)} falas sinalizadas...\n")

    print("Carregando modelo XTTS v2...")
    tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2", gpu=True)
    print("Modelo carregado.\n")

    success = 0
    errors = 0

    for item in flagged:
        character = item["character"]
        filename = item["filename"]
        text_pt = item["text_pt"]

        reference_path = references_dir / f"{character}_reference.wav"
        if not reference_path.exists():
            print(f"  [{character}] {filename}: SEM REFERÊNCIA, pulando")
            errors += 1
            continue

        output_path = out_dir / character / filename
        cleaned_text = clean_text_for_tts(text_pt)

        try:
            tts.tts_to_file(
                text=cleaned_text,
                speaker_wav=str(reference_path),
                language="pt",
                file_path=str(output_path),
                split_sentences=False,
            )
            print(f"  [{character}] {filename}: \"{text_pt}\" -> \"{cleaned_text}\"")
            success += 1
        except Exception as e:
            print(f"  [{character}] {filename}: ERRO: {e}")
            errors += 1

    print(f"\n=== RESUMO ===")
    print(f"Regeneradas com sucesso: {success}")
    print(f"Erros: {errors}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--flagged", required=True)
    parser.add_argument("--references", required=True)
    parser.add_argument("--out", required=True)

    args = parser.parse_args()
    main(Path(args.flagged), Path(args.references), Path(args.out))