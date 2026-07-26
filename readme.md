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
- [x] Treino do primeiro modelo de voz (piloto: Diego) e validação de épocas ideais
- [x] Treino em lote de múltiplos personagens (6 concluídos até agora)
- [x] Pipeline de geração de dublagem de teste (TTS + RVC) funcional ponta a ponta
- [ ] Transferência de prosódia/emoção do áudio original (próximo passo, ver seção "Próximos passos")
- [ ] Dublagem completa de todos os personagens treinados
- [ ] Reempacotamento no jogo

**Números atuais do dataset:**
- 7.351 arquivos de áudio extraídos, organizados por personagem
- 5.594 falas de diálogo com texto extraído dos scripts
- 5.508 pares áudio+texto traduzidos para PT-BR, custo total de **US$ 2,48** via API da Anthropic (Claude Sonnet)
- Restante (SVMs/barks genéricos de combate) sem texto associado — tratamento futuro
- **6 personagens com modelo de voz treinado** até agora: ASGHAN, CAINE, DIEGO, GRIMES, HOMER, além da voz genérica `_barks_genericos`

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

`scripts/dataset/check_speaker_contamination.py` foi o script de
diagnóstico usado para confirmar e quantificar o problema num personagem
específico antes da correção em massa:

```bash
python scripts/dataset/check_speaker_contamination.py --json "dialogue_dataset.json" --character DIEGO
```

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
extração de f0, extração de features, treino, inferência) foi executado
com sucesso rodando os módulos manualmente via `python -m train.<script>`.

### Treino piloto (Diego) e escolha do número de épocas

Testado com checkpoints em 50, 100 e 150 épocas (config `v2`, `40k`, `f0`
ativado, `batch_size=4`, limitado pela VRAM). Resultado: 50 épocas soou
perceptivelmente inferior; 100 e 150 soaram equivalentes — sinal de que o
treino atinge o platô bem antes de 150. **100 épocas foi adotado como
teto padrão**, evitando overfitting e economizando tempo.

### Treino em lote

`scripts/pipeline/batch_prepare_rvc.py` prepara (preprocess + extração
de f0 + features + filelist) todos os personagens com áudio suficiente
de uma vez, pulando quem já está pronto:

```bash
python scripts/pipeline/batch_prepare_rvc.py --dataset "<dataset_rvc_ready>" --rvc-dir "<pasta RVC>" --min-files 10
python scripts/pipeline/batch_generate_filelists.py --rvc-dir "<pasta RVC>"  # gera filelist.txt para quem ficou faltando
```

`scripts/pipeline/batch_train_rvc.py` treina múltiplos personagens em
sequência, pulando quem já tem modelo pronto (retomável a qualquer
momento — interrompe e continua depois de onde parou). O número de
épocas é calculado automaticamente pela quantidade de áudio disponível
(datasets pequenos platôam mais rápido):

| Falas disponíveis | Épocas |
| --- | --- |
| < 20 | 60 |
| 20–50 | 80 |
| 50+ | 100 (teto) |

```bash
python scripts/pipeline/batch_train_rvc.py --dataset "<dataset_rvc_ready>" --rvc-dir "<pasta RVC>"
```

Por padrão treina do maior para o menor personagem; ordenar do menor
para o maior (mais rápido no início, útil para deixar rodando durante a
noite) é uma troca de uma linha (`counted.sort(key=lambda x: x[1])`).

## Geração de dublagem (TTS + RVC)

`scripts/pipeline/dub_ready_characters.py` gera falas de teste (TTS em
português via `edge-tts`, convertido para o timbre do personagem via
RVC) para todos os personagens que já têm modelo treinado:

```bash
python scripts/pipeline/dub_ready_characters.py --dataset "<dataset>" --rvc-dir "<pasta RVC>" --out "<pasta de saída>" --samples 3
```

Depende de `test_inference.py`, um script auxiliar criado dentro da
pasta do RVC (fora deste repositório) para chamar a classe `VC` do RVC
via linha de comando — a interface web não expôs essa função de forma
utilizável neste ambiente.

### Experimentos de calibração (resultado: não trouxe ganho)

Foram testados: (1) índice de features (`.index`) por personagem — só
ajudou em datasets pequenos, com `index_rate` baixo (~0.3), e piorou o
Diego, que já tinha dataset grande o suficiente para generalizar bem
sozinho; (2) calibração de pitch/velocidade de fala com base na média do
personagem — não trouxe diferença perceptível; (3) ajuste de duração via
`time-stretch` (phase vocoder) — introduziu artefatos audíveis
("reverberação") e foi descartado.

**Conclusão:** o timbre (o que o RVC aprende) já estava bom desde o
primeiro teste simples. O problema real é a **prosódia genérica do TTS**
— o RVC preserva fielmente a entonação/ritmo de quem entra, então uma
fala "neutra" do TTS sai neutra também na voz do personagem, mesmo que o
áudio original tivesse hesitação, medo, ênfase etc. Ajustar médias
(pitch médio, velocidade média) não resolve isso, porque emoção é uma
característica de cada fala individual, não do personagem como um todo.

## Próximos passos

Abordagem planejada para resolver a perda de prosódia/emoção: em vez de
deixar o TTS gerar uma entonação genérica, extrair a curva de pitch (F0)
do áudio original em inglês — que já carrega a emoção real da fala — e
transferir essa curva (redimensionada no tempo) para a síntese em
português. Também planejado: trocar o `time-stretch` por um método menos
artefactual (ex. `pyrubberband`/WSOLA) para os casos em que ajuste de
duração for necessário.

## Ferramentas de terceiros utilizadas

- [GothicVDFS](https://worldofplayers.ru/threads/42314/) — extração de pacotes `.vdf`
- [Gothic Sourcer](https://worldofplayers.ru/threads/38318/) — decompilação e leitura de scripts de diálogo
- Union / Ninja / Toolkit / G1CP / GD3D11 — via Steam Workshop
- [RVC WebUI](https://github.com/RVC-Project/Retrieval-based-Voice-Conversion-WebUI) — treino e inferência de voice conversion
- [edge-tts](https://github.com/rany2/edge-tts) — síntese de voz em português (base antes da conversão RVC)

## Licença e Direitos Autorais

O **código deste repositório** (scripts, documentação) é distribuído sob
licença MIT — veja `LICENSE`.

Gothic 1 e todos os seus assets (áudio, texto, modelos, texturas) são
propriedade de **Piranha Bytes / THQ Nordic**. Este repositório **não**
inclui, distribui ou hospeda nenhum arquivo extraído do jogo original
(áudios, dataset, scripts de diálogo do jogo). Qualquer pessoa que queira
reproduzir o processo precisa possuir uma cópia legítima do jogo.

Este é um projeto de fã, não afiliado à Piranha Bytes ou THQ Nordic.