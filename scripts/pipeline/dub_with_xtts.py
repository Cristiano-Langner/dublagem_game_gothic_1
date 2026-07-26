"""
Gera dublagem usando XTTS v2 com voice cloning a partir do áudio original
de cada personagem (voice cloning zero-shot, sem RVC como etapa final —
XTTS puro se mostrou superior a XTTS+RVC nos testes).

Requer que as referências de voz já tenham sido geradas com
select_xtts_reference.py para cada personagem.

Uso:
    python dub_with_xtts.py --dataset "D:\\Meus Projetos\\dataset" --references "D:\\Meus Projetos\\xtts_references" --out "D:\\Meus Projetos\\dublagem_xtts" --samples 5
"""

import argparse
import csv
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


def find_characters_with_reference(references_dir: Path) -> dict[str, Path]:
    """Retorna {nome_personagem: caminho_referencia} para quem já tem referência gerada."""
    if not references_dir.exists():
        return {}

    result = {}
    for ref_path in references_dir.glob("*_reference.wav"):
        char_name = ref_path.stem.replace("_reference", "")
        result[char_name] = ref_path

    return result


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

    if n_samples <= 0:
        return rows

    return rows[:n_samples]


def main(dataset_dir: Path, references_dir: Path, out_dir: Path, n_samples: int):
    characters = find_characters_with_reference(references_dir)
    print(f"Personagens com referência de voz pronta: {len(characters)}\n")

    print("Carregando modelo XTTS v2 (uma vez só, reaproveitado para todos os personagens)...")
    tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2", gpu=True)
    print("Modelo carregado.\n")

    for char_name, reference_path in sorted(characters.items()):
        samples = load_sample_lines(dataset_dir, char_name, n_samples)
        if not samples:
            print(f"  [{char_name}] sem metadata_pt.csv ou sem falas, pulando")
            continue

        char_out_dir = out_dir / char_name
        char_out_dir.mkdir(parents=True, exist_ok=True)

        print(f"  [{char_name}] gerando {len(samples)} amostras...")

        for filename, text_pt in samples:
            final_path = char_out_dir / filename

            if final_path.exists():
                continue

            try:
                tts.tts_to_file(
                    text=text_pt,
                    speaker_wav=str(reference_path),
                    language="pt",
                    file_path=str(final_path),
                    split_sentences=False,
                )
                print(f"    [{filename}] OK: \"{text_pt[:50]}\"")
            except Exception as e:
                print(f"    [{filename}] ERRO: {e}")
                continue

    print(f"\nResultados salvos em: {out_dir.resolve()}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--references", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--samples", type=int, default=5)

    args = parser.parse_args()
    main(Path(args.dataset), Path(args.references), Path(args.out), args.samples)