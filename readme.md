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
- [x] **Dublagem completa de 192/193 personagens (5.508 falas)**
- [x] Correção de falas com ênfase excessiva (gritos/letras repetidas)
- [x] **Reempacotamento no jogo — dublagem funcionando in-game**
- [ ] Legendas em PT-BR (investigado, não concluído — ver seção abaixo)

**Números finais do dataset:**
- 7.351 arquivos de áudio extraídos, organizados por personagem
- 5.594 falas de diálogo com texto extraído dos scripts
- 5.508 falas traduzidas e dubladas em PT-BR (192 de 193 personagens;
  1 sem áudio suficiente para referência de voz)
- 1.843 falas sem tradução (SVMs/barks genéricos de combate) permanecem
  no áudio original em inglês no arquivo final

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

Reconhece os padrões `DIA_`, `<CARGO>_<ID>_`, `INFO_`, `PC_`, `SVM_`, `B_GRAVO_` no nome dos arquivos de áudio originais.

### 2. Decompilação dos scripts e extração de texto

```bash
python scripts/dataset/extract_dialogue_text.py --src "<pasta do projeto decompilado>" --out "dialogue_dataset.json"
```

Extrai o texto (comentário) e speaker/listener de cada `AI_Output`.

### 3. Cruzamento áudio + texto

```bash
python scripts/dataset/merge_audio_text.py --dataset "<pasta dataset>" --json "dialogue_dataset.json"
```

### 4. Tradução PT-BR

```bash
python scripts/pipeline/translate_dataset.py --dataset "<pasta dataset>" --all
```

Via API da Anthropic, com controle de tamanho (tradução limitada a ~20%
de expansão sobre o original) e salvamento incremental.

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

## Geração de voz — XTTS v2 com voice cloning

**Decisão de arquitetura:** testadas três abordagens — TTS genérico +
RVC treinado por personagem; RVC com índice de features e calibração de
pitch/pausas; XTTS v2 com voice cloning direto do áudio original. A mais
simples venceu: **XTTS v2 usando o próprio áudio original em inglês de
cada personagem como referência de voz**, sem RVC nem treino algum.

### Setup

```bash
pip install TTS
```

Requer Microsoft C++ Build Tools (Windows) e PyTorch com CUDA. Ajustes
de compatibilidade necessários (incluídos em `test_xtts.py` e
`dub_with_xtts.py`): `torch.load` com `weights_only=False` (PyTorch
2.6+ mudou o padrão) e substituição de `torchaudio.load` por
`soundfile` (evita dependência do `torchcodec`/FFmpeg externo).

**Correções de texto antes da síntese** (`clean_text_for_tts`):
- `split_sentences=False` — evita que o modelo verbalize pontuação na
  junção entre frases divididas automaticamente
- Reticências (`...`) viram vírgula
- Ponto final é removido — o XTTS ocasionalmente verbaliza "ponto" em
  frases curtas
- Sequências de 3+ letras repetidas colapsam para 1 (`AAAAARRRGHHHHH`
  → `ARGH`) — preserva duplas naturais do português (`carro`), corrige
  apenas exageros de grito/ênfase que geravam áudio distorcido

### Seleção da referência de voz

Para cada personagem, seleciona a fala mais longa do áudio original
(ideal: 6–20s), concatenando falas adicionais se necessário:

```bash
python scripts/pipeline/batch_select_xtts_references.py --dataset "<pasta dataset>" --out "<pasta references>"
```

### Geração da dublagem

```bash
python scripts/pipeline/dub_with_xtts.py --dataset "<pasta dataset>" --references "<pasta references>" --out "<pasta de saída>" --samples 0
```

Modelo carregado uma única vez, reaproveitado para todos os
personagens/falas. Processa em ordem crescente de quantidade de falas.
Retomável — pula arquivos já gerados.

### Correção de falas com gritos

```bash
python scripts/pipeline/find_repeated_letters.py --dataset "<dataset>" --out "falas_flagged.json"
python scripts/pipeline/regenerate_flagged.py --flagged "falas_flagged.json" --references "<references>" --out "<pasta dublagem>"
```

41 de 5.508 falas (0.7%) precisaram dessa correção pontual.

## Reempacotamento no jogo

Os áudios dublados (PCM, saída do XTTS) precisam ser convertidos para
**IMA_ADPCM 4-bit** (formato original do jogo) antes de empacotar:

```bash
python scripts/pipeline/prepare_repack.py --dubbed "<pasta dublagem>" --out "<pasta repack>"
```

Usa `ffmpeg` (`-acodec adpcm_ima_wav`). Como só 5.508 das 7.351 falas
originais foram dubladas, é necessário fazer merge com os áudios
originais em inglês (mesma pasta, sobrescrevendo apenas os arquivos
dublados) antes de empacotar — garante que personagens/falas sem
dublagem continuem funcionando normalmente:

```powershell
# copia todos os áudios originais primeiro
Copy-Item "<pasta audios originais>\*" -Destination "<pasta merge>" -Force
# sobrescreve com os dublados por cima
Copy-Item "<pasta dublagem convertida>\*" -Destination "<pasta merge>" -Force
```

O volume final (7.351 arquivos) é empacotado em um novo `speech.VDF`
usando o **GothicVDFS** (aba **Builder**, Root Path na pasta que contém
a estrutura `_WORK\DATA\SOUND\SPEECH\`, máscara `*.wav`).

**Nota:** tentativas de carregar o VDF de dublagem via `Data/ModVDF/`
(prioridade sobre o original) não funcionaram neste ambiente — o motivo
não foi diagnosticado. A solução funcional foi **substituir diretamente
o `speech.VDF` original** (com backup do original preservado antes).

## Legendas em PT-BR (não concluído)

As legendas do jogo não vêm dos scripts compilados (`Gothic.dat`) nem
do texto que o Gothic Sourcer mostra como comentário ao decompilar —
esse texto é só um índice de conveniência, lido do banco de dados
**Output Units (OU)**, armazenado em `OUINFO.INF`
(`_work/Data/Scripts/_compiled/`) e `OU.BIN`/`OU.CSL`. Relatos da
comunidade indicam que **editar o `OUINFO.INF` diretamente não altera
as legendas em jogo** — o dado real parece exigir regeneração via
**Spacer** (editor de níveis do Gothic, ferramenta separada do
Sourcer), através de uma função "Output-Units → Update → Save" cujo
mecanismo exato (fonte do texto durante a atualização) não foi
totalmente esclarecido nesta investigação. Retomar como projeto futuro,
começando pela instalação e exploração do Spacer.

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