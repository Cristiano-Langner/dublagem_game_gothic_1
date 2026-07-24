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
- [ ] Pipeline de geração de voz (TTS / RVC ou So-VITS-SVC)
- [ ] Reempacotamento no jogo

**Números atuais do dataset:**
- 7.351 arquivos de áudio extraídos, organizados em 192 pastas por personagem
- 5.594 falas de diálogo com texto extraído dos scripts
- 5.508 pares áudio+texto prontos para uso (taxa de acerto ~98% nos diálogos nomeados)
- **5.508 falas traduzidas para PT-BR**, custo total de **US$ 2,48** via API da Anthropic (Claude Sonnet)
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
`AI_Output`, junto com o ID do áudio correspondente:

O script `scripts/dataset/extract_dialogue_text.py` varre todos os `.d`
decompilados e gera um JSON com todas as falas encontradas:

```bash
python scripts/dataset/extract_dialogue_text.py --src "<pasta do projeto decompilado>" --out "dialogue_dataset.json"
```

### 3. Cruzamento áudio + texto

O script `scripts/dataset/merge_audio_text.py` casa os `.wav` já
organizados com o texto extraído no passo anterior, gerando um
`metadata.csv` (formato LJSpeech: `nome_arquivo|texto`) dentro de cada
pasta de personagem — pronto para uso em treino de TTS/voice cloning:

```bash
python scripts/dataset/merge_audio_text.py --dataset "<pasta dataset>" --json "dialogue_dataset.json"
```

## Estrutura do repositório

## Ferramentas de terceiros utilizadas

- [GothicVDFS](https://worldofplayers.ru/threads/42314/) — extração de pacotes `.vdf`
- [Gothic Sourcer](https://worldofplayers.ru/threads/38318/) — decompilação e leitura de scripts de diálogo
- Union / Ninja / Toolkit / G1CP / GD3D11 — via Steam Workshop

## Licença e Direitos Autorais

O **código deste repositório** (scripts, documentação) é distribuído sob
licença MIT — veja `LICENSE`.

Gothic 1 e todos os seus assets (áudio, texto, modelos, texturas) são
propriedade de **Piranha Bytes / THQ Nordic**. Este repositório **não**
inclui, distribui ou hospeda nenhum arquivo extraído do jogo original
(áudios, dataset, scripts de diálogo do jogo). Qualquer pessoa que queira
reproduzir o processo precisa possuir uma cópia legítima do jogo.

Este é um projeto de fã, não afiliado à Piranha Bytes ou THQ Nordic.