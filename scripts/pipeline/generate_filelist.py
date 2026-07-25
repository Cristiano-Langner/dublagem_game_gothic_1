"""
Gera o filelist.txt necessário pro treino do RVC, replicando a lógica
que a interface web faz automaticamente (mas que pulamos ao rodar manual).

Uso:
    python generate_filelist.py --exp-dir "D:\\RVC (WebUI)\\rvc-webui\\logs\\diego_gothic1" --version v2 --if-f0 --spk-id 0
"""

import argparse
import os
import random
from pathlib import Path


def generate(exp_dir: Path, version: str, if_f0: bool, spk_id: int):
    gt_wavs_dir = exp_dir / "0_gt_wavs"
    feature_dir = exp_dir / ("3_feature256" if version == "v1" else "3_feature768")
    f0_dir = exp_dir / "2a_f0"
    f0nsf_dir = exp_dir / "2b-f0nsf"

    names_gt = {p.stem for p in gt_wavs_dir.glob("*.wav")}
    names_feat = {p.stem for p in feature_dir.glob("*.npy")}

    if if_f0:
        names_f0 = {p.stem.replace(".wav", "") for p in f0_dir.glob("*.npy")}
        names_f0nsf = {p.stem.replace(".wav", "") for p in f0nsf_dir.glob("*.npy")}
        names = names_gt & names_feat & names_f0 & names_f0nsf
    else:
        names = names_gt & names_feat

    if not names:
        raise RuntimeError("Nenhum áudio válido encontrado. Confira se todas as etapas anteriores rodaram.")

    print(f"Nomes válidos encontrados (interseção de todas as pastas): {len(names)}")

    lines = []
    for name in names:
        if if_f0:
            line = "%s/%s.wav|%s/%s.npy|%s/%s.wav.npy|%s/%s.wav.npy|%s" % (
                str(gt_wavs_dir).replace("\\", "\\\\"), name,
                str(feature_dir).replace("\\", "\\\\"), name,
                str(f0_dir).replace("\\", "\\\\"), name,
                str(f0nsf_dir).replace("\\", "\\\\"), name,
                spk_id,
            )
        else:
            line = "%s/%s.wav|%s/%s.npy|%s" % (
                str(gt_wavs_dir).replace("\\", "\\\\"), name,
                str(feature_dir).replace("\\", "\\\\"), name,
                spk_id,
            )
        lines.append(line)

    random.shuffle(lines)

    out_path = exp_dir / "filelist.txt"
    with open(out_path, "w", encoding="utf8") as f:
        f.write("\n".join(lines))

    print(f"filelist.txt gerado com {len(lines)} linhas em: {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--exp-dir", required=True, help="Pasta do experimento (ex: logs/diego_gothic1)")
    parser.add_argument("--version", required=True, choices=["v1", "v2"])
    parser.add_argument("--if-f0", action="store_true", help="Inclui f0 (necessário se treinar com tom)")
    parser.add_argument("--spk-id", type=int, default=0)

    args = parser.parse_args()
    generate(Path(args.exp_dir), args.version, args.if_f0, args.spk_id)