"""
Extrai o texto das mensagens padrão (SVM) do arquivo svm.d, gerando um
JSON no mesmo formato do dialogue_dataset.json, para reaproveitar o
pipeline de tradução e dublagem já existente.

Uso:
    python extract_svm_text.py --src "svm.d" --out "svm_dataset.json"
"""

import argparse
import json
import re
from pathlib import Path

# Field = "AUDIO_ID"; //texto
PATTERN = re.compile(r'(\w+)\s*=\s*"([^"]+)"\s*;\s*(?://(.*))?')


def main(src_path: Path, out_path: Path):
    text = src_path.read_text(encoding="latin-1")

    entries = []
    for match in PATTERN.finditer(text):
        field_name, audio_id, comment = match.groups()
        text_en = comment.strip() if comment else None

        if not text_en:
            continue  # pula entradas sem texto (ex: sons de orc sem legenda)

        entries.append({
            "audio_id": audio_id,
            "audio_filename": audio_id.upper() + ".WAV",
            "text_en": text_en,
            "field_name": field_name,
        })

    print(f"Total de mensagens SVM extraídas: {len(entries)}")

    out_path.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Salvo em: {out_path.resolve()}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--src", required=True)
    parser.add_argument("--out", required=True)

    args = parser.parse_args()
    main(Path(args.src), Path(args.out))