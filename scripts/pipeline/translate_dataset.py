"""
Traduz o metadata.csv de cada personagem (inglês -> português) usando a
API da Anthropic, mantendo contexto entre falas do mesmo personagem.

Salva incrementalmente (a cada lote), então pode ser interrompido e
retomado sem perder progresso.

Requer ANTHROPIC_API_KEY no arquivo .env ou variável de ambiente.

Uso:
    python translate_dataset.py --dataset "D:\\Meus Projetos\\dataset" --character DIEGO
    python translate_dataset.py --dataset "D:\\Meus Projetos\\dataset" --all
"""

import argparse
import csv
import os
import time
from pathlib import Path

import anthropic
from dotenv import load_dotenv

load_dotenv()

MODEL = "claude-sonnet-4-6"
BATCH_SIZE = 25

SYSTEM_PROMPT = """Você é um tradutor especializado em localização de jogos RPG medievais de fantasia, traduzindo do inglês para português brasileiro.

Contexto: Gothic (2001), RPG alemão de fantasia sombria/medieval. Tom rude, direto, às vezes grosseiro (é um mundo de prisioneiros numa colônia penal).

Regras:
- Mantenha nomes próprios de personagens e lugares SEM tradução (ex: Xardas, Diego, Nônimo, Old Camp pode virar "Velho Acampamento" mas nomes de personagem NUNCA mudam)
- Mantenha o registro/tom: se for grosseiro no original, mantenha grosseiro em português
- Não traduza literalmente expressões idiomáticas; use o equivalente natural em português
- Cada linha de entrada deve gerar exatamente uma linha de saída, na mesma ordem
- Responda APENAS com as traduções, uma por linha, numeradas exatamente como a entrada, sem nenhum texto adicional"""


def translate_batch(client, texts: list[str]) -> list[str]:
    numbered_input = "\n".join(f"{i+1}. {t}" for i, t in enumerate(texts))

    message = client.messages.create(
        model=MODEL,
        max_tokens=4000,
        system=SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": f"Traduza estas falas para português brasileiro:\n\n{numbered_input}"
        }]
    )

    response_text = message.content[0].text.strip()
    lines = response_text.split("\n")

    translations = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if ". " in line[:5]:
            line = line.split(". ", 1)[1]
        translations.append(line)

    return translations


def load_progress(output_path: Path):
    """Retorna quantas linhas já foram traduzidas (pra retomar de onde parou)."""
    if not output_path.exists():
        return 0
    with open(output_path, encoding="utf-8") as f:
        return sum(1 for _ in csv.reader(f, delimiter="|"))


def process_character(client, char_dir: Path):
    metadata_path = char_dir / "metadata.csv"
    if not metadata_path.exists():
        return

    output_path = char_dir / "metadata_pt.csv"

    with open(metadata_path, encoding="utf-8") as f:
        reader = csv.reader(f, delimiter="|")
        rows = [row for row in reader if len(row) == 2]

    if not rows:
        return

    already_done = load_progress(output_path)
    if already_done >= len(rows):
        print(f"  [{char_dir.name}] já completo ({already_done}/{len(rows)}), pulando")
        return

    if already_done > 0:
        print(f"  [{char_dir.name}] retomando do item {already_done}/{len(rows)}")

    # abre em modo append para não perder o que já foi salvo
    with open(output_path, "a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="|")

        for i in range(already_done, len(rows), BATCH_SIZE):
            batch_rows = rows[i:i + BATCH_SIZE]
            filenames = [r[0] for r in batch_rows]
            texts_en = [r[1] for r in batch_rows]

            try:
                translated = translate_batch(client, texts_en)
            except Exception as e:
                print(f"  [ERRO] {char_dir.name} no lote {i}: {e}")
                print(f"  Progresso salvo até o item {i}. Rode o script de novo para retomar.")
                return

            if len(translated) != len(batch_rows):
                print(f"  [AVISO] {char_dir.name}: lote {i} retornou {len(translated)}, esperado {len(batch_rows)}")
                while len(translated) < len(batch_rows):
                    translated.append("")

            for filename, text_en, text_pt in zip(filenames, texts_en, translated):
                writer.writerow([filename, text_en, text_pt])
            f.flush()  # garante que grava em disco imediatamente

            print(f"  [{char_dir.name}] {min(i + BATCH_SIZE, len(rows))}/{len(rows)} traduzidas")
            time.sleep(0.5)

    print(f"  [{char_dir.name}] concluído -> {output_path.name}")


def main(dataset_dir: Path, character: str = None, do_all: bool = False):
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError("ANTHROPIC_API_KEY não encontrada (verifique o .env).")

    client = anthropic.Anthropic(api_key=api_key)

    if character:
        char_dir = dataset_dir / character
        if not char_dir.exists():
            raise FileNotFoundError(f"Pasta não encontrada: {char_dir}")
        process_character(client, char_dir)
    elif do_all:
        char_dirs = sorted([p for p in dataset_dir.iterdir() if p.is_dir()])
        print(f"Processando {len(char_dirs)} personagens...\n")
        for char_dir in char_dirs:
            process_character(client, char_dir)
    else:
        raise ValueError("Especifique --character NOME ou --all")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Traduz metadata.csv (EN->PT) usando a API da Anthropic.")
    parser.add_argument("--dataset", required=True, help="Pasta raiz do dataset organizado por personagem")
    parser.add_argument("--character", help="Nome da pasta de um personagem específico (ex: DIEGO)")
    parser.add_argument("--all", action="store_true", help="Processa todos os personagens")

    args = parser.parse_args()
    main(Path(args.dataset), character=args.character, do_all=args.all)