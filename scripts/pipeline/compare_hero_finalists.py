"""
Compara duas referências de voz específicas em várias frases de tons
diferentes, para decisão final da voz do Herói.

Uso:
    python compare_hero_finalists.py --dataset "D:\\Meus Projetos\\dataset" --out "D:\\Meus Projetos\\teste_audio\\hero_finalists"
"""

import argparse
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

FINALISTS = {
    "opcao6_gornakosh": "TPL_1401_GORNAKOSH_SUGGEST_INFO_15_01.WAV",
    "opcao7_viran": "DIA_VIRAN_RIPOFF_15_02.WAV",
}

TEST_PHRASES = {
    "calmo": "Acho que é melhor a gente conversar antes de fazer alguma bobagem.",
    "tenso": "Fica onde está! Um passo a mais e você vai se arrepender.",
    "esforco": "Ainda não... preciso de mais um pouco de tempo... quase lá!",
    "irritado": "Já cansei dessa conversa. Ou você me ajuda, ou sai da minha frente.",
    "curto": "Vamos embora.",
}


def main(dataset_dir: Path, out_dir: Path):
    hero_dir = dataset_dir / "HEROI"
    out_dir.mkdir(parents=True, exist_ok=True)

    print("Carregando modelo XTTS v2...")
    tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2", gpu=True)

    for opt_name, ref_filename in FINALISTS.items():
        ref_path = hero_dir / ref_filename

        for tone, text in TEST_PHRASES.items():
            out_path = out_dir / f"{opt_name}_{tone}.wav"
            print(f"[{opt_name}] [{tone}] \"{text[:40]}...\"")

            tts.tts_to_file(
                text=text,
                speaker_wav=str(ref_path),
                language="pt",
                file_path=str(out_path),
                split_sentences=False,
            )

    print(f"\nArquivos salvos em: {out_dir.resolve()}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--out", required=True)

    args = parser.parse_args()
    main(Path(args.dataset), Path(args.out))