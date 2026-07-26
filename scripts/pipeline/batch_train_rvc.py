"""
Orquestra o treino de múltiplos personagens no RVC, pulando quem já foi
treinado. Pode ser interrompido e retomado a qualquer momento — roda
aos poucos, ao longo de vários dias.

Épocas são calculadas automaticamente pela quantidade de áudio disponível
(datasets pequenos atingem o platô mais rápido), a menos que --total-epoch
seja passado explicitamente para forçar um valor fixo.

Uso:
    # Treina os 5 personagens com mais áudio, épocas automáticas por tamanho
    python batch_train_rvc.py --dataset "D:\\Meus Projetos\\dataset_rvc_ready" --rvc-dir "D:\\RVC (WebUI)\\rvc-webui" --top 5

    # Treina uma lista específica, forçando 100 épocas fixas para todos
    python batch_train_rvc.py --dataset "D:\\Meus Projetos\\dataset_rvc_ready" --rvc-dir "D:\\RVC (WebUI)\\rvc-webui" --characters DIEGO XARDAS --total-epoch 100
"""

import argparse
import subprocess
from pathlib import Path


def epochs_for_file_count(n_files: int) -> int:
    """Heurística: datasets menores platôam mais rápido, então usam menos épocas."""
    if n_files < 20:
        return 60
    elif n_files < 50:
        return 80
    else:
        return 100  # teto máximo, confirmado com o Diego (123 falas)


def already_trained(rvc_dir: Path, char_name: str) -> bool:
    weights_dir = rvc_dir / "assets" / "weights"
    if not weights_dir.exists():
        return False
    matches = list(weights_dir.glob(f"{char_name}_*.pth"))
    return len(matches) > 0


def is_prepared(rvc_dir: Path, char_name: str) -> bool:
    exp_dir = rvc_dir / "logs" / char_name
    return (exp_dir / "filelist.txt").exists()


def train_character(rvc_python: Path, rvc_dir: Path, char_name: str,
                     total_epoch: int, save_every: int, batch_size: int):
    args = [
        "-e", char_name,
        "-sr", "40k",
        "-f0", "1",
        "-bs", str(batch_size),
        "-te", str(total_epoch),
        "-se", str(save_every),
        "-pg", "assets/pretrained_v2/f0G40k.pth",
        "-pd", "assets/pretrained_v2/f0D40k.pth",
        "-g", "0",
        "-v", "v2",
        "-l", "0",
        "-c", "0",
        "-sw", "1",
    ]
    cmd = [str(rvc_python), "-m", "train.train"] + args

    print(f"\n{'='*60}")
    print(f"Treinando: {char_name} ({total_epoch} épocas)")
    print(f"{'='*60}\n")

    result = subprocess.run(cmd, cwd=str(rvc_dir))
    return result.returncode == 0


def main(dataset_dir: Path, rvc_dir: Path, top: int, characters: list[str],
          total_epoch: int, save_every_override: int, batch_size: int):
    rvc_python = rvc_dir / ".venv" / "Scripts" / "python.exe"
    if not rvc_python.exists():
        raise FileNotFoundError(f"Python do venv do RVC não encontrado em: {rvc_python}")

    char_dirs = {p.name: p for p in dataset_dir.iterdir() if p.is_dir()}

    if characters:
        candidates = characters
    else:
        counted = [(name, len(list(p.glob("*.wav")))) for name, p in char_dirs.items()]
        counted.sort(key=lambda x: x[1])
        candidates = [name for name, _ in counted[:top]] if top else [name for name, _ in counted]

    print(f"Candidatos a treinar (nesta ordem): {candidates}\n")

    to_train = []
    for name in candidates:
        if already_trained(rvc_dir, name):
            print(f"  [{name}] já treinado (modelo encontrado em assets/weights), pulando")
            continue
        if not is_prepared(rvc_dir, name):
            print(f"  [{name}] AINDA NÃO PREPARADO (rode batch_prepare_rvc.py primeiro), pulando")
            continue
        to_train.append(name)

    print(f"\nPersonagens a treinar nesta execução: {to_train}\n")

    for name in to_train:
        n_files = len(list(char_dirs[name].glob("*.wav"))) if name in char_dirs else 0

        epoch_count = total_epoch if total_epoch else epochs_for_file_count(n_files)
        save_every = save_every_override if save_every_override else max(25, epoch_count // 4)

        print(f"  [{name}] {n_files} áudios -> {epoch_count} épocas (checkpoint a cada {save_every})")

        ok = train_character(rvc_python, rvc_dir, name, epoch_count, save_every, batch_size)
        if ok:
            print(f"\n[{name}] treino concluído.")
        else:
            print(f"\n[{name}] treino terminou com erro ou foi interrompido.")
            print("Rode o script novamente para tentar retomar/pular para o próximo.")
            break


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True, help="Pasta dataset_rvc_ready")
    parser.add_argument("--rvc-dir", required=True, help="Pasta raiz do RVC WebUI")
    parser.add_argument("--top", type=int, default=0, help="Treina os N personagens com mais áudio (ignora --characters)")
    parser.add_argument("--characters", nargs="+", help="Lista específica de personagens a treinar")
    parser.add_argument("--total-epoch", type=int, default=0, help="Força um número fixo de épocas para todos (0 = automático por tamanho do dataset)")
    parser.add_argument("--save-every", type=int, default=0, help="Força intervalo de checkpoint (0 = automático, épocas/4)")
    parser.add_argument("--batch-size", type=int, default=4)

    args = parser.parse_args()
    main(Path(args.dataset), Path(args.rvc_dir), args.top, args.characters,
         args.total_epoch, args.save_every, args.batch_size)