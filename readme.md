# Dublagem PT-BR — Gothic 1 (Projeto Fan-Made com IA)

Projeto pessoal de documentação e experimentação: gerar uma dublagem em
português brasileiro para o Gothic 1 (2001, Piranha Bytes) usando
ferramentas de modding da comunidade + IA de voz (TTS / voice conversion).

Este repositório documenta todo o processo, do ambiente de mods até o
pipeline de geração de voz, como referência pra quem quiser reproduzir
ou adaptar pra outros jogos da série.

> ⚠️ Projeto sem fins lucrativos, feito por fã. Não redistribui assets
> originais do jogo (áudio, texto, modelos). Veja a seção **Licença e
> Direitos Autorais** abaixo.

## Status atual

- [x] Ambiente configurado (Union, Ninja, Toolkit, G1CP, GD3D11)
- [x] Extração dos áudios de fala (`speech.VDF`) via GothicVDFS
- [x] Organização automática dos áudios por personagem (script Python)
- [x] Decompilação dos scripts do jogo (Gothic Sourcer)
- [x] Extração dos textos de diálogo (`AI_Output` → JSON)
- [x] Cruzamento áudio + texto em `metadata.csv` por personagem (formato LJSpeech)
- [x] Tradução PT-BR (via API Anthropic/Claude)
- [x] Correção de contaminação de vozes (falas do Herói misturadas nos NPCs)
- [x] Ambiente de treino de voz configurado (RVC WebUI, RTX 3050 4GB)
- [ ] Treino do primeiro modelo de voz (piloto: Diego)
- [ ] Pipeline de geração de voz completo (TTS + RVC)
- [ ] Reempacotamento no jogo

**Números atuais do dataset:**
- 7.351 arquivos de áudio extraídos, organizados por personagem
- 5.594 falas de diálogo com texto extraído dos scripts
- 5.508 pares áudio+texto traduzidos para PT-BR, custo total de **US$ 2,48** via API da Anthropic (Claude Sonnet)
- Restante (SVMs/barks genéricos de combate) sem texto associado — tratamento futuro

## Setup do ambiente de jogo (Gothic 1 Classic — Steam)

1. Ativar a branch **workshop** (Propriedades → Betas)
2. Inscrever-se nos itens do Workshop:
   - Union - patch for Gothic 1
   - Ninja
   - Toolkit
   - Gothic 1 Community Patch
   - GD3D11 Render (corrige renderização/flickering em GPUs modernas)
3. Sempre abrir pelo **Mod Launcher**, com a ordem: Union → Ninja → Toolkit → G1CP → GD3D11

Detalhes de troubleshooting (crashes, tela preta na intro, flickering) em `docs/`.

## Pipeline do dataset

### 1. Extração de áudio

Os arquivos de fala ficam em `Data/speech.VDF`, extraídos com o
**GothicVDFS**. O script `scripts/dataset/organize_by_character.py`
organiza os `.wav` em pastas por personagem, reconhecendo os seguintes
padrões de nome de arquivo:

| Padrão                           | Exemplo                            | Significado                         |
| --------------------------------- | ---------------------------------- | ------------------------------------ |
| `DIA_<PERSONAGEM>_...`          | `DIA_AIDAN_HELLO_13_01.WAV`      | Diálogo de NPC nomeado               |
| `<CARGO>_<ID>_<PERSONAGEM>_...` | `GRD_200_THORUS_TEACH_09_01.WAV` | NPC com cargo (guarda, etc.)         |
| `INFO_<PERSONAGEM>_...`         | `INFO_AARON_PISSED_09_01.WAV`    | Diálogo de NPC (variante)            |
| `PC_<VARIANTE>_...`             | `PC_PSIONIC_FOLLOWME_...`        | Falas do próprio Herói/Nônimo        |
| `SVM_<ID_VOZ>_...`              | `SVM_10_ALARM.WAV`               | Voz padrão compartilhada (combate)   |
| `B_GRAVO_...`                   | `B_GRAVO_HELPATTITUDE_ANGRY_...` | Barks genéricos de reação             |

```bash
python scripts/dataset/organize_by_character.py --src "<pasta SPEECH extraída>" --dst "<pasta destino>" --dry-run
```

Remova `--dry-run` pra copiar de fato.

### 2. Decompilação dos scripts e extração de texto

Os scripts do jogo (`_work/Data/Scripts/_compiled/Gothic.dat`) são
decompilados com o **Gothic Sourcer** (File → New Project → "First
decompile action"), gerando os arquivos-fonte `.d` em formato Daedalus.

O texto de cada fala aparece como comentário logo após a chamada
`AI_Output`, junto com o ID do áudio e os campos de quem fala (`self`)
e quem escuta (`other`):

```bash
python scripts/dataset/extract_dialogue_text.py --src "<pasta do projeto decompilado>" --out "dialogue_dataset.json"
```

### 3. Cruzamento áudio + texto

```bash
python scripts/dataset/merge_audio_text.py --dataset "<pasta dataset>" --json "dialogue_dataset.json"
```

Gera `metadata.csv` (formato LJSpeech: `nome_arquivo|texto`) em cada pasta.

### 4. Tradução PT-BR

Tradução via API da Anthropic (Claude), em lotes por personagem, com
salvamento incremental (pode ser interrompida e retomada):

```bash
python scripts/pipeline/translate_dataset.py --dataset "<pasta dataset>" --all
```

Requer `ANTHROPIC_API_KEY` em `.env`. Gera `metadata_pt.csv`
(`arquivo|texto_en|texto_pt`) em cada pasta.

### 5. Correção de contaminação de vozes

**Problema descoberto:** cada arquivo `.d` de diálogo contém falas de
**dois** personagens — o NPC dono do arquivo (`self`) e o Herói/Nônimo
respondendo (`other`/`hero`). A organização inicial (baseada só no nome
do arquivo de áudio) atribuía **todas** as falas de um diálogo ao NPC
dono do arquivo, contaminando cada pasta de personagem com ~30% de falas
do Herói — o que corromperia qualquer modelo de voz treinado em cima.

O script `scripts/dataset/fix_speaker_contamination.py` usa o campo
`speaker` (já capturado no `dialogue_dataset.json`) para mover as falas
do Herói para uma pasta `HEROI` dedicada:

```bash
python scripts/dataset/fix_speaker_contamination.py --json "dialogue_dataset.json" --dataset "<pasta dataset>" --dry-run
```

Remova `--dry-run` para mover de fato. **Resultado:** 1.910 de 5.594
falas (34%) estavam mal classificadas e foram corrigidas — a maior parte
foi parar corretamente na pasta `HEROI`, que passou a ser o personagem
com mais dados de voz do dataset (esperado, já que é o protagonista).

As traduções já pagas não se perdem: `consolidate_translations.py` gera
um índice `nome_arquivo → tradução` antes da correção, e
`rebuild_metadata.py` reconstrói os `metadata.csv`/`metadata_pt.csv` de
cada pasta reaproveitando 100% das traduções já feitas, sem custo
adicional de API.

```bash
python scripts/pipeline/consolidate_translations.py --dataset "<pasta dataset>" --out "translations_index.json"
# (rodar fix_speaker_contamination.py sem --dry-run aqui)
python scripts/dataset/rebuild_metadata.py --dataset "<pasta dataset>" --dialogue-json "dialogue_dataset.json" --translations "translations_index.json"
```

### 6. Preparo de áudio para treino

Os `.wav` originais do jogo estão em **IMA_ADPCM 4-bit**, formato não
suportado pelas ferramentas de ML. O script converte para PCM 16-bit:

```bash
python scripts/pipeline/prepare_audio_for_training.py --src "<dataset>" --dst "<dataset_rvc_ready>" --all
```

## Geração de voz (RVC)

**Hardware:** notebook com RTX 3050 (4GB VRAM), 16GB RAM. Com essa
VRAM, RVC (voice conversion) é viável; treinar TTS do zero (XTTS
fine-tuning) não é.

**Setup:** [RVC-Project WebUI](https://github.com/RVC-Project/Retrieval-based-Voice-Conversion-WebUI)
instalado separadamente (fora deste repositório, é uma ferramenta de
terceiros), com PyTorch CUDA 12.8 (`torch==2.7.1+cu128`).

Modelos base necessários (baixados do Hugging Face `lj1995/VoiceConversionWebUI`):
```bash
hf download lj1995/VoiceConversionWebUI --include "hubert_base/*" --local-dir assets
hf download lj1995/VoiceConversionWebUI rmvpe.pt --local-dir assets/rmvpe
hf download lj1995/VoiceConversionWebUI --include "pretrained/*" --local-dir assets
hf download lj1995/VoiceConversionWebUI --include "pretrained_v2/*" --local-dir assets
```

**Nota:** a interface web do RVC apresentou bugs de subprocesso nesse
ambiente (PYTHONPATH/caminhos relativos). O pipeline completo (preprocess,
extração de f0, extração de features, treino) foi executado com sucesso
rodando os módulos manualmente via `python -m train.<script>` — ver
histórico de comandos para reprodução.

Configuração de treino usada (piloto: Diego, 123 falas após correção de
contaminação): `v2`, `40k`, `f0` ativado, `batch_size=4` (limitado pela
VRAM), `total_epoch=200`, `save_every_epoch=50`.

## Estrutura do repositório