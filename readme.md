# Dublagem PT-BR — Gothic 1 (Projeto Fan-Made com IA)

Projeto pessoal de documentação e experimentação: gerar uma dublagem em
português brasileiro para o Gothic 1 (2001, Piranha Bytes) usando
ferramentas de modding da comunidade + IA de voz (TTS / voice cloning).

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
- [x] Tradução PT-BR (via API Anthropic/Claude), com controle de tamanho
- [x] Correção de contaminação de vozes (falas do Herói misturadas nos NPCs)
- [x] **Pipeline de geração de voz definido: XTTS v2 com voice cloning zero-shot**
- [x] Validado em 6 personagens (qualidade superior a TTS genérico + RVC)
- [ ] Geração completa (todas as falas) de todos os personagens
- [ ] Reempacotamento no jogo

**Números atuais do dataset:**
- 7.351 arquivos de áudio extraídos, organizados por personagem
- 5.594 falas de diálogo com texto extraído dos scripts
- 5.508 pares áudio+texto traduzidos para PT-BR
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

### 2. Decompilação dos scripts e extração de texto

```bash
python scripts/dataset/extract_dialogue_text.py --src "<pasta do projeto decompilado>" --out "dialogue_dataset.json"
```

### 3. Cruzamento áudio + texto

```bash
python scripts/dataset/merge_audio_text.py --dataset "<pasta dataset>" --json "dialogue_dataset.json"
```

### 4. Tradução PT-BR

Tradução via API da Anthropic (Claude), em lotes por personagem, com
controle de tamanho (a tradução não deve ultrapassar ~20% do tamanho do
texto original, reduzindo a necessidade de ajustar duração do áudio
depois) e salvamento incremental (retomável):

```bash
python scripts/pipeline/translate_dataset.py --dataset "<pasta dataset>" --all
```

Requer `ANTHROPIC_API_KEY` em `.env`.

### 5. Correção de contaminação de vozes

**Problema descoberto:** cada arquivo `.d` de diálogo contém falas de
**dois** personagens — o NPC dono do arquivo (`self`) e o Herói/Nônimo
respondendo (`other`/`hero`). 1.910 de 5.594 falas (34%) estavam mal
classificadas.

```bash
python scripts/dataset/check_speaker_contamination.py --json "dialogue_dataset.json" --character DIEGO
python scripts/dataset/fix_speaker_contamination.py --json "dialogue_dataset.json" --dataset "<pasta dataset>" --dry-run
python scripts/pipeline/consolidate_translations.py --dataset "<pasta dataset>" --out "translations_index.json"
python scripts/dataset/rebuild_metadata.py --dataset "<pasta dataset>" --dialogue-json "dialogue_dataset.json" --translations "translations_index.json"
```

## Geração de voz — XTTS v2 com voice cloning (pipeline atual)

**Decisão de arquitetura:** depois de testar três abordagens (TTS
genérico + RVC treinado por personagem; RVC com índice de features e
calibração de pitch/pausas; XTTS v2 com voice cloning direto do áudio
original), a que se mostrou melhor foi a mais simples: **XTTS v2 usando
o próprio áudio original em inglês de cada personagem como referência
de voz** (voice cloning zero-shot), sem RVC como etapa adicional.

Isso elimina a necessidade de treinar um modelo por personagem — não é
mais preciso rodar o pipeline de treino RVC (`batch_prepare_rvc.py`,
`batch_train_rvc.py`) para novos personagens. Esses scripts continuam
no repositório como documentação do processo, mas não fazem mais parte
do fluxo ativo.

### Setup

```bash
pip install TTS
```

Requer Microsoft C++ Build Tools no Windows (compilação de extensão
nativa) e PyTorch com CUDA já configurado no ambiente.

**Ajustes de compatibilidade necessários** (PyTorch 2.6+ mudou o padrão
de `torch.load`; `torchaudio` novo exige `torchcodec`/FFmpeg externo
para carregar áudio): `test_xtts.py` e `dub_with_xtts.py` já incluem os
patches necessários (força `weights_only=False` no carregamento do
checkpoint; substitui `torchaudio.load` por `soundfile`, evitando a
dependência do FFmpeg).

**Importante:** usar `split_sentences=False` na chamada do XTTS — com o
split automático ativado, o modelo verbaliza a pontuação na junção
entre frases divididas (ex: fala "ponto" no meio do áudio).

### 6. Seleção da referência de voz

Para cada personagem, seleciona a fala mais longa do áudio original
(ideal: 6–20 segundos) como referência de clonagem. Se a mais longa for
curta demais, concatena as próximas até atingir o mínimo:

```bash
python scripts/pipeline/select_xtts_reference.py --dataset "<pasta dataset>" --character DIEGO --out "<pasta references>"
```

### 7. Geração da dublagem

```bash
python scripts/pipeline/dub_with_xtts.py --dataset "<pasta dataset>" --references "<pasta references>" --out "<pasta de saída>" --samples 5
```

O modelo XTTS é carregado uma única vez e reaproveitado para todos os
personagens/falas (mais rápido que recarregar por chamada, como era
necessário no fluxo antigo baseado em RVC).

## Ferramentas de terceiros utilizadas

- [GothicVDFS](https://worldofplayers.ru/threads/42314/) — extração de pacotes `.vdf`
- [Gothic Sourcer](https://worldofplayers.ru/threads/38318/) — decompilação e leitura de scripts de diálogo
- Union / Ninja / Toolkit / G1CP / GD3D11 — via Steam Workshop
- [Coqui TTS (XTTS v2)](https://github.com/coqui-ai/TTS) — geração de voz com voice cloning
- [RVC WebUI](https://github.com/RVC-Project/Retrieval-based-Voice-Conversion-WebUI) — usado experimentalmente; não faz mais parte do pipeline ativo

## Licença e Direitos Autorais

O **código deste repositório** (scripts, documentação) é distribuído sob
licença MIT — veja `LICENSE`.

Gothic 1 e todos os seus assets (áudio, texto, modelos, texturas) são
propriedade de **Piranha Bytes / THQ Nordic**. Este repositório **não**
inclui, distribui ou hospeda nenhum arquivo extraído do jogo original
(áudios, dataset, scripts de diálogo do jogo). Qualquer pessoa que queira
reproduzir o processo precisa possuir uma cópia legítima do jogo.

Este é um projeto de fã, não afiliado à Piranha Bytes ou THQ Nordic.