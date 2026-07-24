"""
Organiza os arquivos .wav extraídos do speech.VDF em pastas por personagem.

Padrões de nome reconhecidos:
  DIA_<PERSONAGEM>_...                       -> ex: DIA_AIDAN_HELLO_13_01.WAV
  <CARGO>_<ID_NUMERICO>_<PERSONAGEM>_...     -> ex: GRD_200_THORUS_TEACH_09_01.WAV
  INFO_<PERSONAGEM>_...                      -> ex: INFO_AARON_PISSED_09_01.WAV
  B_GRAVO_...                                -> barks genéricos (sem personagem fixo)

Uso:
    python organize_by_character.py --src "D:\\Meus Projetos\\audios_gothic_1_raw\\_WORK\\DATA\\SOUND\\SPEECH" --dst "D:\\Meus Projetos\\dataset"
    Adicione --dry-run pra só simular, sem copiar nada ainda.
"""

import argparse
import re
import shutil
from pathlib import Path
from collections import Counter

DIA_PATTERN = re.compile(r"^DIA_([A-Za-z0-9]+)_", re.IGNORECASE)
BARK_PREFIX = "B_GRAVO_"

# <CARGO>_<ID_NUMERICO>_<NOME_PERSONAGEM>_... -> ex: GRD_200_THORUS_...
ROLE_ID_NAME_PATTERN = re.compile(r"^[A-Za-z]+_\d+_([A-Za-z0-9]+)_", re.IGNORECASE)

# INFO_<NOME_PERSONAGEM>_... -> ex: INFO_AARON_PISSED_09_01.WAV
INFO_PATTERN = re.compile(r"^INFO_([A-Za-z0-9]+)_", re.IGNORECASE)

# PC_<VARIANTE>_... -> falas do próprio Herói/Nônimo, ex: PC_PSIONIC_FOLLOWME_INFO_05_01.WAV
PC_PATTERN = re.compile(r"^PC_([A-Za-z0-9]+)_", re.IGNORECASE)

# SVM_<VOICE_ID>_... -> falas padrão de combate/reação, agrupadas por conjunto de voz
SVM_PATTERN = re.compile(r"^SVM_(\d+)_", re.IGNORECASE)

UNKNOWN_FOLDER = "_nao_identificado"
BARKS_FOLDER = "_barks_genericos"


def get_character_folder(filename: str) -> str:
    upper = filename.upper()

    if upper.startswith(BARK_PREFIX):
        return BARKS_FOLDER

    match = DIA_PATTERN.match(upper)
    if match:
        return match.group(1)

    match = ROLE_ID_NAME_PATTERN.match(upper)
    if match:
        return match.group(1)

    match = INFO_PATTERN.match(upper)
    if match:
        return match.group(1)
    
    match = PC_PATTERN.match(upper)
    if match:
        return "HEROI_" + match.group(1)

    match = INFO_PATTERN.match(upper)
    if match:
        return match.group(1)
    
    match = SVM_PATTERN.match(upper)
    if match:
        return "VOZ_PADRAO_" + match.group(1)

    return UNKNOWN_FOLDER


def organize(src: Path, dst: Path, dry_run: bool = False):
    if not src.exists():
        raise FileNotFoundError(f"Pasta de origem não encontrada: {src}")

    # Evita contar duplicado no Windows (onde *.WAV e *.wav batem nos mesmos arquivos)
    wav_files = sorted({p.resolve() for p in src.glob("*.wav")}, key=lambda p: p.name)
    if not wav_files:
        print("Nenhum arquivo .wav encontrado na pasta de origem.")
        return

    counter = Counter()
    unidentified_examples = []

    for wav_path in wav_files:
        character_folder = get_character_folder(wav_path.name)
        counter[character_folder] += 1

        if character_folder == UNKNOWN_FOLDER and len(unidentified_examples) < 30:
            unidentified_examples.append(wav_path.name)

        dest_dir = dst / character_folder
        dest_file = dest_dir / wav_path.name

        if dry_run:
            continue

        dest_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(wav_path, dest_file)

    print(f"\nTotal de arquivos processados: {len(wav_files)}")
    print(f"Total de pastas/personagens distintos: {len(counter)}\n")

    print("Top 15 personagens por quantidade de falas:")
    for name, count in counter.most_common(15):
        print(f"  {name:30s} {count}")

    if unidentified_examples:
        print(f"\nExemplos de arquivos NÃO identificados ({counter[UNKNOWN_FOLDER]} no total):")
        for name in unidentified_examples:
            print(f"  {name}")

    if dry_run:
        print("\n[DRY-RUN] Nenhum arquivo foi copiado de verdade.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Organiza áudios do Gothic 1 por personagem.")
    parser.add_argument("--src", required=True, help="Pasta com os .wav extraídos (SPEECH)")
    parser.add_argument("--dst", required=True, help="Pasta de destino do dataset organizado")
    parser.add_argument("--dry-run", action="store_true", help="Só simula, não copia nada")

    args = parser.parse_args()
    organize(Path(args.src), Path(args.dst), dry_run=args.dry_run)