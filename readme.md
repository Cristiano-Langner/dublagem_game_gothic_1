# Dublagem PT-BR — Gothic 1 (Projeto Fan-Made com IA)

Projeto pessoal de documentação e experimentação: gerar uma dublagem em
português brasileiro para o Gothic 1 (2001, Piranha Bytes) usando
ferramentas de modding da comunidade + IA de voz (voice cloning).

Este repositório documenta todo o processo, do ambiente de mods até o
reempacotamento no jogo, como referência pra quem quiser reproduzir ou
adaptar pra outros jogos da série.

> ⚠️ Projeto sem fins lucrativos, feito por fã. Não redistribui assets
> originais do jogo (áudio, texto, modelos). Veja a seção **Licença e
> Direitos Autorais** abaixo.

## Status atual

- [x] Ambiente configurado (Union, Ninja, Toolkit, G1CP, GD3D11)
- [x] Extração dos áudios de fala (`speech.VDF`) via GothicVDFS
- [x] Organização automática dos áudios por personagem
- [x] Decompilação dos scripts do jogo (Gothic Sourcer)
- [x] Extração dos textos de diálogo (`AI_Output` → JSON)
- [x] Tradução PT-BR (via API Anthropic/Claude), com controle de tamanho
- [x] Correção de contaminação de vozes (falas do Herói misturadas nos NPCs)
- [x] Pipeline de geração de voz: XTTS v2 com voice cloning zero-shot
- [x] Dublagem completa dos diálogos (192/193 personagens, 5.508 falas)
- [x] **Extração e dublagem das mensagens padrão (SVM)** — falas de
      reação/combate genéricas (`svm.d`), 1.726 falas em 17 vozes
      (`VOZ_PADRAO_1` a `17`)
- [x] Correção de falas com ênfase excessiva (gritos/letras repetidas)
- [x] **Reempacotamento no jogo — dublagem funcionando in-game**
- [ ] Legendas em PT-BR (investigado, não concluído — ver seção abaixo)
- [ ] **Conversas ambiente entre NPCs (sem envolver o Herói) ainda em
      inglês** — fonte ainda não identificada, ver seção abaixo

**Números finais do dataset:**
- 7.351 arquivos de áudio de diálogo/SVM extraídos do `speech.VDF`,
  organizados por personagem
- 5.508 falas de diálogo dubladas em PT-BR
- 1.726 falas de mensagens padrão (SVM) dubladas em PT-BR, incluindo a
  `VOZ_PADRAO_16`, encontrada num VDF separado (`speech_babe_speech_engl.VDF`)
  não coberto pela extração inicial
- Total: ~7.234 falas dubladas no `speech.VDF` final

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

Reconhece os padrões `DIA_`, `<CARGO>_<ID>_`, `INFO_`, `PC_`, `SVM_`, `B_GRAVO_`.

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

**Problema descoberto:** cada arquivo `.d` de diálogo contém falas de
dois personagens (NPC dono do arquivo e Herói respondendo). 1.910 de
5.594 falas (34%) estavam mal classificadas.

```bash
python scripts/dataset/check_speaker_contamination.py --json "dialogue_dataset.json" --character DIEGO
python scripts/dataset/fix_speaker_contamination.py --json "dialogue_dataset.json" --dataset "<pasta dataset>" --dry-run
python scripts/pipeline/consolidate_translations.py --dataset "<pasta dataset>" --out "translations_index.json"
python scripts/dataset/rebuild_metadata.py --dataset "<pasta dataset>" --dialogue-json "dialogue_dataset.json" --translations "translations_index.json"
```

### 6. Mensagens padrão (SVM)

Falas de reação/combate genéricas ("Pare com a magia!", "Socorro!")
não vêm de `AI_Output` em diálogos, mas de uma classe `C_SVM` separada
(`Story/svm.d`), com uma instância por "conjunto de voz" (`SVM_1` a
`SVM_17`, ligadas às pastas `VOZ_PADRAO_*` já identificadas na extração
de áudio):

```bash
python scripts/dataset/extract_svm_text.py --src "svm.d" --out "svm_dataset.json"
python scripts/dataset/merge_svm_audio_text.py --dataset "<pasta dataset>" --json "svm_dataset.json"
```

**Nota:** a `SVM_16` não estava no `speech.VDF` principal — seus 6
arquivos ficam num VDF separado, `Data/speech_babe_speech_engl.VDF`
(precisa ser extraído e adicionado manualmente à pasta `VOZ_PADRAO_16`
antes de traduzir/dublar).

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

### Geração da dublagem

```bash
python scripts/pipeline/dub_with_xtts.py --dataset "<pasta dataset>" --references "<pasta references>" --out "<pasta de saída>" --samples 0
```

Modelo carregado uma única vez, reaproveitado para todos os
personagens/falas. Retomável — pula arquivos já gerados.

### Correção de falas com gritos

```bash
python scripts/pipeline/find_repeated_letters.py --dataset "<dataset>" --out "falas_flagged.json"
python scripts/pipeline/regenerate_flagged.py --flagged "falas_flagged.json" --references "<references>" --out "<pasta dublagem>"
```

## Reempacotamento no jogo

Conversão para **IMA_ADPCM 4-bit** (formato original) via `ffmpeg`:

```bash
python scripts/pipeline/prepare_repack.py --dubbed "<pasta dublagem>" --out "<pasta repack>"
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

**Nota:** carregar via `Data/ModVDF/` (prioridade sobre o original) não
funcionou neste ambiente (motivo não diagnosticado). Solução funcional:
**substituir diretamente o `speech.VDF` original** (com backup preservado).

## Pendências conhecidas

**Conversas ambiente entre NPCs (sem envolver o Herói) continuam em
inglês.** Essas falas usam a função nativa `AI_OutputSVM` (chamada via
`B_Say`, no sistema `ZS_Smalltalk`), que referencia os mesmos campos
`Smalltalk01`-`24` do `C_SVM` já extraídos, traduzidos e dublados no
pipeline (confirmado: o arquivo de áudio correto, em português, existe
no `speech.VDF` ativo). Mesmo assim, o jogo continua reproduzindo a
versão em inglês nessas falas específicas — diálogo direto com o Herói
usa o mesmo sistema SVM e funciona normalmente dublado.

Investigado sem sucesso: VDFs concorrentes na pasta `Data` (nenhum
outro contém `SPEECH`), cache do Union/GD3D11 (nenhuma pasta de cache
encontrada), hash do arquivo (confirmado idêntico ao dublado), reinício
completo do jogo e novo save. A causa provável está em como o motor
resolve `AI_OutputSVM` para falas "Noise" (ambiente) internamente —
possivelmente um mecanismo diferente de carregamento não capturável por
inspeção de arquivos. Ferramentas como Process Monitor (captura de
acesso a disco em tempo real) poderiam confirmar a causa raiz, mas não
foram usadas nesta investigação. Documentado como limitação conhecida.

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
propriedade de **Piranha Bytes / THQ Nordic**. Este repositório **não**
inclui, distribui ou hospeda nenhum arquivo extraído do jogo original
(áudios, dataset, scripts de diálogo do jogo). Qualquer pessoa que queira
reproduzir o processo precisa possuir uma cópia legítima do jogo.

Este é um projeto de fã, não afiliado à Piranha Bytes ou THQ Nordic.