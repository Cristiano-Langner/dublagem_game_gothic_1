"""
Verifica propriedades dos áudios e converte para WAV PCM 16-bit padrão,
formato esperado pela maioria das ferramentas de treino de voz (RVC, etc).

Uso:
    python prepare_audio_for_training.py --src "D:\\Meus Projetos\\dataset\\DIEGO" --dst "D:\\Meus Projetos\\dataset_rvc_ready\\DIEGO"
    python prepare_audio_for_training.py --src "D:\\Meus Projetos\\dataset" --dst "D:\\Meus Projetos\\dataset_rvc_ready" --all
"""

import argparse
import soundfile as sf
from pathlib import Path
from collections import Counter


def inspect_and_convert(src: Path, dst: Path, quiet: bool = False):
    dst.mkdir(parents=True, exist_ok=True)

    wav_files = sorted({p.resolve() for p in src.glob("*.wav")}, key=lambda p: p.name)
    if not wav_files:
        return 0, 0, Counter()

    formats = Counter()
    errors = []
    converted = 0

    for wav_path in wav_files:
        try:
            info = sf.info(str(wav_path))
            fmt_key = f"{info.samplerate}Hz, {info.subtype}, {info.channels}ch"
            formats[fmt_key] += 1

            data, samplerate = sf.read(str(wav_path))
            out_path = dst / wav_path.name
            sf.write(str(out_path), data, samplerate, subtype="PCM_16")
            converted += 1

        except Exception as e:
            errors.append((wav_path.name, str(e)))

    if not quiet:
        print(f"  [{src.name}] {converted}/{len(wav_files)} convertidos")
        if errors:
            print(f"    Erros: {len(errors)}")
            for name, err in errors[:5]:
                print(f"      {name}: {err}")

    return converted, len(wav_files), formats


def main(src: Path, dst: Path, do_all: bool):
    if do_all:
        char_dirs = sorted([p for p in src.iterdir() if p.is_dir()])
        print(f"Processando {len(char_dirs)} personagens...\n")

        total_converted = 0
        total_files = 0
        all_formats = Counter()

        for char_dir in char_dirs:
            char_dst = dst / char_dir.name
            converted, total, formats = inspect_and_convert(char_dir, char_dst)
            total_converted += converted
            total_files += total
            all_formats.update(formats)

        print(f"\n=== RESUMO GERAL ===")
        print(f"Total convertido: {total_converted}/{total_files}")
        print(f"\nFormatos originais encontrados (todos os personagens):")
        for fmt, count in all_formats.most_common():
            print(f"  {fmt:40s} {count}")
    else:
        converted, total, formats = inspect_and_convert(src, dst)
        print(f"Encontrados {total} arquivos em {src.name}")
        print("Formatos originais encontrados:")
        for fmt, count in formats.most_common():
            print(f"  {fmt:40s} {count}")
        print(f"Convertidos com sucesso: {converted}/{total}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Inspeciona e converte áudios para PCM 16-bit.")
    parser.add_argument("--src", required=True, help="Pasta com os .wav (de um personagem, ou raiz do dataset com --all)")
    parser.add_argument("--dst", required=True, help="Pasta de saída para os .wav convertidos")
    parser.add_argument("--all", action="store_true", help="Processa todas as subpastas de personagens")

    args = parser.parse_args()
    main(Path(args.src), Path(args.dst), do_all=args.all)