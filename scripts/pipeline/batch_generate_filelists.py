"""
Gera o filelist.txt para todos os personagens já preparados (que passaram
por preprocess/f0/features mas ainda não têm filelist.txt).

Uso:
    python batch_generate_filelists.py --rvc-dir "D:\\RVC (WebUI)\\rvc-webui" --version v2
"""

import argparse
import random
from pathlib import Path


def generate_for_character(exp_dir: Path, version: str, if_f0: bool, spk_id: int) -> bool:
    gt_wavs_dir = exp_dir / "0_gt_wavs"
    feature_dir = exp_dir / ("3_feature256" if version == "v1" else "3_feature768")
    f0_dir = exp_dir / "2a_f0"
    f0nsf_dir = exp_dir / "2b-f0nsf"

    if not gt_wavs_dir.exists() or not feature_dir.exists():
        return False

    names_gt = {p.stem for p in gt_wavs_dir.glob("*.wav")}
    names_feat = {p.stem for p in feature_dir.glob("*.npy")}

    if if_f0:
        if not f0_dir.exists() or not f0nsf_dir.exists():
            return False
        names_f0 = {p.stem.replace(".wav", "") for p in f0_dir.glob("*.npy")}
        names_f0nsf = {p.stem.replace(".wav", "") for p in f0nsf_dir.glob("*.npy")}
        names = names_gt & names_feat & names_f0 & names_f0nsf
    else:
        names = names_gt & names_feat

    if not names:
        return False

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

    with open(exp_dir / "filelist.txt", "w", encoding="utf8") as f:
        f.write("\n".join(lines))

    return True


def main(rvc_dir: Path, version: str):
    logs_dir = rvc_dir / "logs"
    char_dirs = sorted([p for p in logs_dir.iterdir() if p.is_dir()])

    print(f"Verificando {len(char_dirs)} pastas em logs/...\n")

    generated = 0
    already_had = 0
    skipped_incomplete = 0

    for char_dir in char_dirs:
        if (char_dir / "filelist.txt").exists():
            already_had += 1
            continue

        ok = generate_for_character(char_dir, version, if_f0=True, spk_id=0)
        if ok:
            generated += 1
            print(f"  [{char_dir.name}] filelist.txt gerado")
        else:
            skipped_incomplete += 1
            print(f"  [{char_dir.name}] incompleto (faltam pastas de preprocess/f0/features), pulado")

    print(f"\n=== RESUMO ===")
    print(f"Já tinham filelist: {already_had}")
    print(f"Gerados agora: {generated}")
    print(f"Incompletos (pulados): {skipped_incomplete}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--rvc-dir", required=True)
    parser.add_argument("--version", default="v2", choices=["v1", "v2"])

    args = parser.parse_args()
    main(Path(args.rvc_dir), args.version)