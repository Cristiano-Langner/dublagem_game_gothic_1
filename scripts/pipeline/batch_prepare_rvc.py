"""
Automatiza a preparação (preprocess + extração de f0 + features + filelist)
de todos os personagens do dataset para o RVC WebUI, pulando quem já foi
preparado e quem tem áudio insuficiente.

Uso:
    python batch_prepare_rvc.py --dataset "D:\\Meus Projetos\\dataset_rvc_ready" --rvc-dir "D:\\RVC (WebUI)\\rvc-webui" --min-files 10
"""

import argparse
import subprocess
import shutil
from pathlib import Path

MIN_FILES_DEFAULT = 10


def run_rvc_module(rvc_python: Path, rvc_dir: Path, module: str, args: list[str]):
    cmd = [str(rvc_python), "-m", module] + args
    result = subprocess.run(cmd, cwd=str(rvc_dir), capture_output=True, text=True, encoding="utf-8", errors="replace")
    return result.returncode, result.stdout, result.stderr


def prepare_character(char_name: str, char_audio_dir: Path, rvc_python: Path, rvc_dir: Path):
    exp_dir_rel = f"logs/{char_name}"
    exp_dir_abs = rvc_dir / "logs" / char_name

    if (exp_dir_abs / "filelist.txt").exists():
        print(f"  [{char_name}] já preparado, pulando")
        return True

    exp_dir_abs.mkdir(parents=True, exist_ok=True)

    # 1. Preprocess
    rc, out, err = run_rvc_module(
        rvc_python, rvc_dir, "train.preprocess",
        [str(char_audio_dir), "40000", "8", exp_dir_rel, "False", "3.0"]
    )
    if rc != 0:
        print(f"  [{char_name}] ERRO no preprocess: {err[-500:]}")
        return False

    # 2. Extract F0
    rc, out, err = run_rvc_module(
        rvc_python, rvc_dir, "train.dataset.extract_f0",
        ["cuda", "1", "0", "0", exp_dir_rel, "True"]
    )
    if rc != 0:
        print(f"  [{char_name}] ERRO no extract_f0: {err[-500:]}")
        return False

    # 3. Extract HuBERT features
    rc, out, err = run_rvc_module(
        rvc_python, rvc_dir, "train.dataset.extract_hubert_feature",
        ["cuda", "1", "0", "0", exp_dir_rel, "v2", "True"]
    )
    if rc != 0:
        print(f"  [{char_name}] ERRO no extract_hubert_feature: {err[-500:]}")
        return False

    # 4. Copy config
    config_src = rvc_dir / "configs" / "v1" / "40k.json"
    shutil.copy(config_src, exp_dir_abs / "config.json")

    print(f"  [{char_name}] preparado com sucesso")
    return True


def main(dataset_dir: Path, rvc_dir: Path, min_files: int):
    rvc_python = rvc_dir / ".venv" / "Scripts" / "python.exe"
    if not rvc_python.exists():
        raise FileNotFoundError(f"Python do venv do RVC não encontrado em: {rvc_python}")

    char_dirs = sorted([p for p in dataset_dir.iterdir() if p.is_dir()])
    print(f"Encontrados {len(char_dirs)} pastas de personagem\n")

    eligible = []
    skipped_few_files = []

    for char_dir in char_dirs:
        wav_count = len(list(char_dir.glob("*.wav")))
        if wav_count < min_files:
            skipped_few_files.append((char_dir.name, wav_count))
            continue
        eligible.append(char_dir)

    print(f"Elegíveis para preparação (>= {min_files} áudios): {len(eligible)}")
    print(f"Pulados por poucos áudios: {len(skipped_few_files)}\n")

    success = []
    failed = []

    for char_dir in eligible:
        ok = prepare_character(char_dir.name, char_dir, rvc_python, rvc_dir)
        if ok:
            success.append(char_dir.name)
        else:
            failed.append(char_dir.name)

    print(f"\n=== RESUMO ===")
    print(f"Preparados com sucesso: {len(success)}")
    print(f"Falharam: {len(failed)}")
    if failed:
        print("Personagens com falha:", ", ".join(failed))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True, help="Pasta com dataset_rvc_ready (áudios PCM 16-bit)")
    parser.add_argument("--rvc-dir", required=True, help="Pasta raiz do RVC WebUI")
    parser.add_argument("--min-files", type=int, default=MIN_FILES_DEFAULT, help="Mínimo de áudios pra preparar o personagem")

    args = parser.parse_args()
    main(Path(args.dataset), Path(args.rvc_dir), args.min_files)