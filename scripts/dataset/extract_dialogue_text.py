"""
Extrai os textos de diálogo dos arquivos .d decompilados pelo Gothic Sourcer
e gera um JSON mapeando: nome_do_audio -> texto, personagem, etc.

Uso:
    python extract_dialogue_text.py --src "D:\\SteamLibrary\\steamapps\\common\\Gothic\\Gothic Projects\\gothic1_decompile\\GOTHIC" --out "dialogue_dataset.json"
"""

import argparse
import json
import re
from pathlib import Path
from collections import Counter

# Captura: AI_Output(quem_fala, quem_ouve, "ID_DO_AUDIO");  //texto opcional
AI_OUTPUT_PATTERN = re.compile(
    r'AI_Output\s*\(\s*([A-Za-z0-9_]+)\s*,\s*([A-Za-z0-9_]+)\s*,\s*"([^"]+)"\s*\)\s*;'
    r'(?:\s*//\s*(.*))?'
)

# Reaproveita a mesma lógica usada na organização dos áudios
DIA_PATTERN = re.compile(r"^DIA_([A-Za-z0-9]+)_", re.IGNORECASE)
ROLE_ID_NAME_PATTERN = re.compile(r"^[A-Za-z]+_\d+_([A-Za-z0-9]+)_", re.IGNORECASE)
INFO_PATTERN = re.compile(r"^INFO_([A-Za-z0-9]+)_", re.IGNORECASE)
PC_PATTERN = re.compile(r"^PC_([A-Za-z0-9]+)_", re.IGNORECASE)
SVM_PATTERN = re.compile(r"^SVM_(\d+)_", re.IGNORECASE)
BARK_PREFIX = "B_GRAVO_"

UNKNOWN_FOLDER = "_nao_identificado"
BARKS_FOLDER = "_barks_genericos"


def get_character_folder(audio_id: str) -> str:
    upper = audio_id.upper()

    if upper.startswith(BARK_PREFIX):
        return BARKS_FOLDER

    match = DIA_PATTERN.match(upper)
    if match:
        return match.group(1)

    match = ROLE_ID_NAME_PATTERN.match(upper)
    if match:
        return match.group(1)

    match = SVM_PATTERN.match(upper)
    if match:
        return "VOZ_PADRAO_" + match.group(1)

    match = PC_PATTERN.match(upper)
    if match:
        return "HEROI_" + match.group(1)

    match = INFO_PATTERN.match(upper)
    if match:
        return match.group(1)

    return UNKNOWN_FOLDER


def extract_from_file(file_path: Path):
    entries = []
    try:
        text = file_path.read_text(encoding="latin-1")
    except Exception as e:
        print(f"  [erro ao ler {file_path.name}]: {e}")
        return entries

    for match in AI_OUTPUT_PATTERN.finditer(text):
        speaker, listener, audio_id, comment = match.groups()
        entries.append({
            "audio_id": audio_id,
            "audio_filename": audio_id.upper() + ".WAV",
            "character_folder": get_character_folder(audio_id),
            "speaker": speaker,
            "listener": listener,
            "text_en": comment.strip() if comment else None,
            "source_file": str(file_path.name),
        })
    return entries


def main(src: Path, out: Path):
    if not src.exists():
        raise FileNotFoundError(f"Pasta não encontrada: {src}")

    d_files = list(src.rglob("*.d"))
    print(f"Encontrados {len(d_files)} arquivos .d para processar...")

    all_entries = []
    for d_file in d_files:
        all_entries.extend(extract_from_file(d_file))

    print(f"\nTotal de falas extraídas: {len(all_entries)}")

    with_text = sum(1 for e in all_entries if e["text_en"])
    print(f"Falas com texto (comentário) encontrado: {with_text}")
    print(f"Falas SEM texto (só o AI_Output, sem comentário): {len(all_entries) - with_text}")

    char_counter = Counter(e["character_folder"] for e in all_entries)
    print(f"\nPersonagens distintos encontrados: {len(char_counter)}")
    print("Top 10:")
    for name, count in char_counter.most_common(10):
        print(f"  {name:30s} {count}")

    out.write_text(json.dumps(all_entries, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nJSON salvo em: {out.resolve()}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extrai texto de diálogo dos .d decompilados.")
    parser.add_argument("--src", required=True, help="Pasta raiz com os .d decompilados (ex: .../GOTHIC)")
    parser.add_argument("--out", required=True, help="Caminho do JSON de saída")

    args = parser.parse_args()
    main(Path(args.src), Path(args.out))