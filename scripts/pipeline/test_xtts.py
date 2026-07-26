"""
Testa geração de voz com XTTS v2, usando um áudio de referência para
clonar o timbre (voice cloning zero-shot).

Uso:
    python test_xtts.py --reference "D:\\Meus Projetos\\xtts_references\\DIEGO_reference.wav" --text "Texto em português aqui" --output "teste_xtts_diego.wav"
"""

import argparse
from pathlib import Path

import torch
import soundfile as sf

# PyTorch 2.6+ mudou o padrão de torch.load para weights_only=True, o que
# quebra o carregamento de checkpoints mais antigos como o do Coqui TTS.
_original_load = torch.load
def _patched_load(*args, **kwargs):
    kwargs.setdefault("weights_only", False)
    return _original_load(*args, **kwargs)
torch.load = _patched_load

import torchaudio

# torchaudio novo exige torchcodec (que exige FFmpeg instalado à parte no
# sistema) para carregar áudio. Substituímos por soundfile, que já
# temos funcionando, evitando essa dependência extra.
def _patched_torchaudio_load(filepath, **kwargs):
    data, samplerate = sf.read(str(filepath), dtype="float32", always_2d=True)
    waveform = torch.from_numpy(data.T)  # (channels, samples), formato esperado pelo torchaudio
    return waveform, samplerate
torchaudio.load = _patched_torchaudio_load

from TTS.api import TTS


def main(reference_path: str, text: str, output_path: str):
    print("Carregando modelo XTTS v2...")
    tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2", gpu=True)

    print("Gerando áudio...")
    tts.tts_to_file(
        text=text,
        speaker_wav=reference_path,
        language="pt",
        file_path=output_path,
        split_sentences=False,
    )

    print(f"Áudio salvo em: {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--reference", required=True, help="Caminho do áudio de referência (voz a clonar)")
    parser.add_argument("--text", required=True, help="Texto a ser sintetizado")
    parser.add_argument("--output", required=True, help="Caminho de saída do áudio gerado")

    args = parser.parse_args()
    main(args.reference, args.text, args.output)