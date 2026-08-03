# Dublagem PT-BR — Gothic 1 (Projeto Fan-Made com IA)

Projeto pessoal, sem fins lucrativos: dublagem completa do Gothic 1
Classic (2001, Piranha Bytes) em português brasileiro, usando
ferramentas de modding da comunidade + IA de voz (voice cloning).

Este repositório documenta todo o processo, do ambiente de mods até o
reempacotamento no jogo, como referência pra quem quiser reproduzir ou
adaptar pra outros jogos da série.

> ⚠️ Não redistribui assets originais do jogo neste repositório (áudio,
> texto, modelos). O arquivo final para instalação está disponível
> separadamente — veja **Download** abaixo.

## Download (jogar com a dublagem)

**[📥 Baixar speech.vdf + instruções (Google Drive)](https://drive.google.com/drive/folders/1OVqThsQe7lBnR4KGxA0QLnH2i-uBK-8O?usp=sharing)**

Requer uma cópia legítima do Gothic 1 Classic (Steam). Instruções de
instalação e reversão incluídas no arquivo `LEIA-ME` dentro da pasta.

## Status atual — Projeto concluído

- [x] Ambiente configurado (Union, Ninja, Toolkit, G1CP, GD3D11)
- [x] Extração dos áudios de fala (`speech.VDF`) via GothicVDFS
- [x] Organização automática dos áudios por personagem
- [x] Decompilação dos scripts do jogo (Gothic Sourcer)
- [x] Extração dos textos de diálogo (`AI_Output` → JSON)
- [x] Tradução PT-BR (via API Anthropic/Claude), com controle de tamanho
- [x] Correção de contaminação de vozes (falas do Herói misturadas nos NPCs)
- [x] Pipeline de geração de voz: XTTS v2 com voice cloning zero-shot
- [x] Dublagem completa dos diálogos (192/193 personagens, 5.508 falas)
- [x] Extração e dublagem das mensagens padrão/SVM (1.726 falas, 17 vozes)
- [x] Correção de falas com ênfase excessiva (gritos/letras repetidas)
- [x] Reempacotamento no jogo — dublagem funcionando in-game, incluindo
      diálogos diretos, mensagens de combate/reação e conversas
      ambiente entre NPCs
- [x] Refinamento da voz do Herói (comparação de 10 referências
      candidatas + teste em 5 tons diferentes, nova voz redublada)
- [x] **Normalização de volume** — falas ambiente/SVM dubladas soavam
      mais altas que o áudio original, corrigido por RMS matching
- [x] **Disponibilizado para a comunidade** (Google Drive)
- [ ] Legendas em PT-BR (investigado, não concluído — ver seção abaixo)

**Números finais do dataset:**
- 7.351 arquivos de áudio de diálogo/SVM dublados em PT-BR
- ~7.234 falas com tradução real; o restante (barks sem texto capturável)
  permanece no áudio original em inglês
- 17 vozes padrão (SVM) + 192 personagens únicos com voz clonada do
  próprio áudio original

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

```bash
python scripts/pipeline/translate_dataset.py --dataset "<pasta dataset>" --all
```

Via API da Anthropic, controle de tamanho, salvamento incremental.

### 5. Correção de contaminação de vozes

Cada `.d` de diálogo contém falas de dois personagens (NPC dono do
arquivo e Herói respondendo); 34% das falas estavam mal classificadas.

```bash
python scripts/dataset/check_speaker_contamination.py --json "dialogue_dataset.json" --character DIEGO
python scripts/dataset/fix_speaker_contamination.py --json "dialogue_dataset.json" --dataset "<pasta dataset>" --dry-run
python scripts/pipeline/consolidate_translations.py --dataset "<pasta dataset>" --out "translations_index.json"
python scripts/dataset/rebuild_metadata.py --dataset "<pasta dataset>" --dialogue-json "dialogue_dataset.json" --translations "translations_index.json"
```

### 6. Mensagens padrão (SVM)

Falas de reação/combate genéricas vêm de uma classe `C_SVM` separada
(`Story/svm.d`), incluindo o campo `Smalltalk01`-`24` usado pelas
conversas ambiente entre NPCs (via função nativa `AI_OutputSVM`,
chamada por `B_Say`/`ZS_Smalltalk`):

```bash
python scripts/dataset/extract_svm_text.py --src "svm.d" --out "svm_dataset.json"
python scripts/dataset/merge_svm_audio_text.py --dataset "<pasta dataset>" --json "svm_dataset.json"
```

**Nota:** a `SVM_16` não estava no `speech.VDF` principal — seus 6
arquivos ficam num VDF separado, `Data/speech_babe_speech_engl.VDF`.

## Geração de voz — XTTS v2 com voice cloning

**Decisão de arquitetura:** testadas três abordagens — TTS genérico +
RVC treinado por personagem; RVC com índice de features e calibração de
pitch/pausas; XTTS v2 com voice cloning direto do áudio original. A mais
simples venceu: **XTTS v2 usando o próprio áudio original em inglês de
cada personagem/voz como referência**, sem RVC nem treino algum.

### Setup

```bash
pip install TTS
```

Requer Microsoft C++ Build Tools (Windows) e PyTorch com CUDA. Ajustes
de compatibilidade (incluídos em `test_xtts.py` e `dub_with_xtts.py`):
`torch.load` com `weights_only=False`; `torchaudio.load` substituído por
`soundfile` (evita dependência do `torchcodec`/FFmpeg externo).

**Correções de texto antes da síntese** (`clean_text_for_tts`):
- `split_sentences=False` — evita verbalização de pontuação na junção
  entre frases divididas automaticamente
- Reticências (`...`) viram vírgula; ponto final é removido
- Sequências de 3+ letras repetidas colapsam para 1 (`AAAAARRRGHHHHH`
  → `ARGH`) — preserva duplas naturais do português

### Seleção da referência de voz

```bash
python scripts/pipeline/batch_select_xtts_references.py --dataset "<pasta dataset>" --out "<pasta references>"
```

Usa a fala mais longa disponível (ideal 6–20s), concatenando se necessário.

**Refinamento manual (Herói):** como o Herói é a voz mais ouvida do
jogo, foram testadas 10 referências candidatas (amostras aleatórias do
próprio pool de falas dele) com uma frase de teste, seguido de teste
mais aprofundado das 2 melhores em 5 tons diferentes (calmo, tenso,
esforço, irritado, curto) antes da escolha final.

### Geração da dublagem

```bash
python scripts/pipeline/dub_with_xtts.py --dataset "<pasta dataset>" --references "<pasta references>" --out "<pasta de saída>" --samples 0
```

Modelo carregado uma única vez, reaproveitado para todos os
personagens/falas. Retomável — pula arquivos já gerados (para redublar
um personagem específico com nova referência, apagar seus áudios da
pasta de saída antes de rodar novamente).

### Correção de falas com gritos

```bash
python scripts/pipeline/find_repeated_letters.py --dataset "<dataset>" --out "falas_flagged.json"
python scripts/pipeline/regenerate_flagged.py --flagged "falas_flagged.json" --references "<references>" --out "<pasta dublagem>"
```

### Normalização de volume

Falas ambiente/SVM dubladas ficaram audivelmente mais altas que o
áudio original (o XTTS normaliza para volume de fala isolada; o jogo
mixa falas ambiente mais discretas). Corrigido por RMS matching contra
o áudio original correspondente, com teto de ganho (3x) para evitar
distorção em casos extremos:

```bash
python scripts/pipeline/normalize_volume.py --dubbed "<pasta dublagem>" --originals "<pasta dataset>" --out "<pasta normalizada>"
```

7.225 de 7.243 áudios normalizados com sucesso.

## Reempacotamento no jogo

Conversão para **IMA_ADPCM 4-bit** (formato original) via `ffmpeg`:

```bash
python scripts/pipeline/prepare_repack.py --dubbed "<pasta dublagem normalizada>" --out "<pasta repack>"
```

Merge com os áudios originais em inglês (garante que falas sem
dublagem continuem funcionando):

```powershell
Copy-Item "<pasta audios originais>\*" -Destination "<pasta merge>" -Force
Copy-Item "<pasta dublagem convertida>\*" -Destination "<pasta merge>" -Force
```

Empacotamento em novo `speech.VDF` via **GothicVDFS** (aba **Builder**,
Root Path na pasta com a estrutura `_WORK\DATA\SOUND\SPEECH\`, máscara
`*.wav`).

**Notas:**
- Carregar via `Data/ModVDF/` (prioridade sobre o original) não
  funcionou neste ambiente. Solução: **substituir diretamente o
  `speech.VDF` original** (com backup preservado fora da pasta `Data`,
  já que mantê-lo dentro causa conflito de carregamento entre VDFs).
- As conversas ambiente entre NPCs pareceram continuar em inglês por
  várias sessões mesmo com o áudio correto confirmado no VDF — resolvido
  após reempacotamentos/reinícios subsequentes, provavelmente cache em
  algum nível do sistema que se dissipou com o tempo.

## Pendências conhecidas

**Legendas em PT-BR não concluídas.** As legendas não vêm dos scripts
compilados (`Gothic.dat`) nem do texto mostrado como comentário pelo
Gothic Sourcer — vêm de um banco de dados separado, **Output Units
(OU)**, em `OUINFO.INF` (`_work/Data/Scripts/_compiled/`) e
`OU.BIN`/`OU.CSL`. Relatos da comunidade indicam que editar o
`OUINFO.INF` diretamente não altera as legendas — a regeneração real
parece exigir o **Spacer** (editor de níveis, ferramenta separada do
Sourcer), cujo mecanismo exato não foi esclarecido nesta investigação.

## Ferramentas de terceiros utilizadas

- [GothicVDFS](https://worldofplayers.ru/threads/42314/) — extração e empacotamento de pacotes `.vdf`
- [Gothic Sourcer](https://worldofplayers.ru/threads/38318/) — decompilação e leitura de scripts de diálogo
- Union / Ninja / Toolkit / G1CP / GD3D11 — via Steam Workshop
- [Coqui TTS (XTTS v2)](https://github.com/coqui-ai/TTS) — geração de voz com voice cloning
- [FFmpeg](https://ffmpeg.org/) — conversão de áudio para IMA_ADPCM
- [RVC WebUI](https://github.com/RVC-Project/Retrieval-based-Voice-Conversion-WebUI) — usado experimentalmente; não faz parte do pipeline final

## Licença e Direitos Autorais

O **código deste repositório** (scripts, documentação) é distribuído sob
licença MIT — veja `LICENSE`.

Gothic 1 e todos os seus assets (áudio, texto, modelos, texturas) são
propriedade de **Piranha Bytes / THQ Nordic**. O código aqui não inclui
nenhum arquivo extraído do jogo original. O arquivo `speech.vdf`
disponibilizado para download contém o áudio original do jogo mesclado
com a dublagem gerada — requer posse legítima do jogo para uso.

Este é um projeto de fã, não afiliado à Piranha Bytes ou THQ Nordic.