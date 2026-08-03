"""
Gera a mesma frase de teste usando 10 referências de voz diferentes,
todas extraídas do próprio pool de falas do Herói, para comparar e
escolher a mais impactante.

Uso:
    python generate_hero_voice_options.py --dataset "D:\\Meus Projetos\\dataset" --out "D:\\Meus Projetos\\teste_audio\\hero_options"
"""

import argparse
import random
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

TEST_TEXT = "Eu não vim até aqui pra desistir agora. Vamos terminar o que começamos, de uma vez por todas."
N_OPTIONS = 10
MIN_DURATION = 5.0
MAX_DURATION = 15.0


def get_duration(wav_path: Path) -> float:
    info = sf.info(str(wav_path))
    return info.frames / info.samplerate


def pick_candidate_references(hero_dir: Path, n: int, seed: int = 42) -> list[Path]:
    wav_files = list(hero_dir.glob("*.wav"))
    candidates = [w for w in wav_files if MIN_DURATION <= get_duration(w) <= MAX_DURATION]

    if len(candidates) < n:
        candidates = wav_files  # relaxa o filtro se não tiver o suficiente

    random.seed(seed)
    return random.sample(candidates, min(n, len(candidates)))


def main(dataset_dir: Path, out_dir: Path):
    hero_dir = dataset_dir / "HEROI"
    out_dir.mkdir(parents=True, exist_ok=True)

    references = pick_candidate_references(hero_dir, N_OPTIONS)
    print(f"Selecionadas {len(references)} referências candidatas:\n")
    for r in references:
        print(f"  {r.name} ({get_duration(r):.1f}s)")

    print("\nCarregando modelo XTTS v2...")
    tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2", gpu=True)

    for i, ref_path in enumerate(references, 1):
        out_path = out_dir / f"hero_option_{i:02d}_{ref_path.stem}.wav"
        print(f"[{i}/{len(references)}] gerando com referência: {ref_path.name}")

        tts.tts_to_file(
            text=TEST_TEXT,
            speaker_wav=str(ref_path),
            language="pt",
            file_path=str(out_path),
            split_sentences=False,
        )

    print(f"\nOpções salvas em: {out_dir.resolve()}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--out", required=True)

    args = parser.parse_args()
    main(Path(args.dataset), Path(args.out))