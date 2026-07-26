"""
Reaproveita as traduções já feitas (metadata_pt_v1.csv) e retraduz APENAS
as falas que ficaram acima do limite de expansão de tamanho, economizando
custo de API. Gera o metadata_pt.csv final combinando traduções antigas
(as que já estavam ok) com as novas (só as que precisaram de ajuste).

Uso:
    python retranslate_oversized.py --dataset "D:\\Meus Projetos\\dataset" --backup-suffix v1 --character DIEGO
    python retranslate_oversized.py --dataset "D:\\Meus Projetos\\dataset" --backup-suffix v1 --all
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
MAX_EXPANSION_RATIO = 1.20

SYSTEM_PROMPT = """Você é um tradutor especializado em localização de jogos RPG medievais de fantasia, traduzindo do inglês para português brasileiro, PARA DUBLAGEM (o áudio final precisa caber numa janela de tempo parecida com a fala original).

Contexto: Gothic (2001), RPG alemão de fantasia sombria/medieval. Tom rude, direto, às vezes grosseiro (é um mundo de prisioneiros numa colônia penal).

Regras:
- Mantenha nomes próprios de personagens e lugares SEM tradução (ex: Xardas, Diego, Nônimo, Old Camp pode virar "Velho Acampamento" mas nomes de personagem NUNCA mudam)
- Mantenha o registro/tom: se for grosseiro no original, mantenha grosseiro em português
- Não traduza literalmente expressões idiomáticas; use o equivalente natural em português
- IMPORTANTE - RESTRIÇÃO DE TAMANHO: cada tradução tem um limite MÁXIMO de caracteres informado entre colchetes antes do texto original (ex: "[max: 45 caracteres] Text here"). A tradução anterior desta mesma linha ficou longa demais - reescreva de forma mais concisa, usando contrações naturais da fala (tá, pra, cê) e frases mais diretas, mantendo o sentido e o tom.
- Cada linha de entrada deve gerar exatamente uma linha de saída, na mesma ordem
- Responda APENAS com as traduções, uma por linha, numeradas exatamente como a entrada, sem nenhum texto adicional, sem repetir o limite de caracteres na resposta"""


def translate_batch(client, texts: list[str]) -> list[str]:
    numbered_input = "\n".join(
        f"{i+1}. [max: {int(len(t) * MAX_EXPANSION_RATIO)} caracteres] {t}"
        for i, t in enumerate(texts)
    )

    message = client.messages.create(
        model=MODEL,
        max_tokens=4000,
        system=SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": f"Retraduza estas falas de forma mais concisa, respeitando os limites de caracteres:\n\n{numbered_input}"
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


def process_character(client, char_dir: Path, backup_suffix: str):
    backup_path = char_dir / f"metadata_pt_{backup_suffix}.csv"
    if not backup_path.exists():
        return None

    with open(backup_path, encoding="utf-8") as f:
        reader = csv.reader(f, delimiter="|")
        rows = [row for row in reader if len(row) == 3]

    if not rows:
        return None

    good_rows = []
    bad_rows = []  # (index, filename, text_en, text_pt_antigo)

    for idx, (filename, text_en, text_pt) in enumerate(rows):
        max_allowed = int(len(text_en) * MAX_EXPANSION_RATIO)
        if len(text_pt) > max_allowed:
            bad_rows.append((idx, filename, text_en, text_pt))
        else:
            good_rows.append(idx)

    total = len(rows)
    n_bad = len(bad_rows)

    if n_bad == 0:
        print(f"  [{char_dir.name}] 0/{total} precisam retradução, copiando backup direto")
        final_rows = [(r[0], r[1], r[2]) for r in rows]
    else:
        print(f"  [{char_dir.name}] {n_bad}/{total} precisam retradução ({100*n_bad/total:.1f}%)")

        new_translations = {}
        texts_to_retranslate = [b[2] for b in bad_rows]

        for i in range(0, len(texts_to_retranslate), BATCH_SIZE):
            batch = texts_to_retranslate[i:i + BATCH_SIZE]
            try:
                translated = translate_batch(client, batch)
            except Exception as e:
                print(f"    [ERRO] lote {i}: {e}")
                translated = [None] * len(batch)

            if len(translated) != len(batch):
                print(f"    [AVISO] lote {i} retornou {len(translated)}, esperado {len(batch)}")
                while len(translated) < len(batch):
                    translated.append(None)

            for offset, new_text in enumerate(translated):
                global_idx = bad_rows[i + offset][0]
                new_translations[global_idx] = new_text

            time.sleep(0.5)

        final_rows = []
        for idx, (filename, text_en, text_pt) in enumerate(rows):
            if idx in new_translations and new_translations[idx]:
                final_rows.append((filename, text_en, new_translations[idx]))
            else:
                final_rows.append((filename, text_en, text_pt))  # mantém antiga se falhou ou já estava boa

    output_path = char_dir / "metadata_pt.csv"
    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="|")
        writer.writerows(final_rows)

    print(f"  [{char_dir.name}] metadata_pt.csv atualizado")
    return n_bad


def main(dataset_dir: Path, backup_suffix: str, character: str = None, do_all: bool = False):
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError("ANTHROPIC_API_KEY não encontrada (verifique o .env).")

    client = anthropic.Anthropic(api_key=api_key)

    if character:
        char_dir = dataset_dir / character
        if not char_dir.exists():
            raise FileNotFoundError(f"Pasta não encontrada: {char_dir}")
        process_character(client, char_dir, backup_suffix)
    elif do_all:
        char_dirs = sorted([p for p in dataset_dir.iterdir() if p.is_dir()])
        print(f"Processando {len(char_dirs)} personagens...\n")
        total_bad = 0
        for char_dir in char_dirs:
            result = process_character(client, char_dir, backup_suffix)
            if result:
                total_bad += result
        print(f"\nTotal de falas retraduzidas em todo o dataset: {total_bad}")
    else:
        raise ValueError("Especifique --character NOME ou --all")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--backup-suffix", default="v1", help="Sufixo do backup a usar como base (ex: v1)")
    parser.add_argument("--character", help="Nome de um personagem específico")
    parser.add_argument("--all", action="store_true")

    args = parser.parse_args()
    main(Path(args.dataset), args.backup_suffix, character=args.character, do_all=args.all)