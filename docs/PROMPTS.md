# Prompts prontos / Ready-made prompts

Cole no Claude Code dentro da pasta do repositório (ou com o plugin instalado). / Paste into Claude Code inside the repo folder (or with the plugin installed).
Os prompts funcionam em português ou inglês; a skill escreve código e docs em inglês. / Prompts work in Portuguese or English.

---

## 1. Super produção de 30 s: "O Cerco do Farol Negro" (PT-BR)

> Antes de colar: veja [COVERAGE.md](COVERAGE.md). O prompt foi escrito para ficar **dentro do que o motor faz hoje** (sem espadas/ferramentas na mão, sem escadas/cercas,
> mobs só creeper/porco/aranha/zumbi). Estimativa de tempo de render: 1080p30 com pós-processamento e 4 workers, algo entre 25 e 45 min (**estimativa, 1080p não foi medido**).

```text
Use a skill blockreel (siga o fluxo A→E inteiro, sem pular etapas) para produzir uma SUPER PRODUÇÃO de Minecraft de EXATAMENTE 30 segundos, 1920x1080, 30 fps,
com acabamento de cinema (letterbox 2.37:1, bloom, grão leve, color grade). Quero qualidade de lançamento, não de teste.

PREMISSA (uma frase): ao amanhecer de uma tempestade, uma guerreira solitária defende o último farol de uma costa de obsidiana contra uma horda de zumbis e o
vigia de olhos brilhantes que a comanda; ela vence usando uma armadilha de TNT e acende o farol, e a luz muda o mundo.
TOM: épico, sombrio no começo, quente e catártico no final. Energia em forma de onda: calmo → intenso → UM silêncio → calmo/quente.

ANTES DE CONSTRUIR
1. Leia docs/COVERAGE.md e me diga em 5 linhas o que NÃO dá para fazer hoje e como você vai contornar. Não use nenhum recurso marcado como missing.
2. Briefing: assuma as decisões que faltarem e declare-as (no máximo UMA pergunta curta, só se for indispensável).
3. Pesquisa na web COM LINKS em research.md: ritmo de montagem de ação e épico, antecipação/overshoot/follow-through em corpo rígido, composição de câmera
   para escala (revelação por pull-back), arquitetura de fortaleza/farol em blocos, e fontes de música e efeitos sonoros LIVRES com a licença de cada uma.
   Só liste, NÃO baixe nada. Registre princípios, não copie obras nem personagens existentes.
4. brief.md e shotlist.md (tabela do DIRECTOR.md com a coluna "intenção"), com 16 a 22 planos, planos de ação de 1 a 2 s, planos calmos de até 4 s,
   gancho nos primeiros 3 s (movimento + mudança de escala), uma revelação de escala (objeto em primeiro plano → pull-back mostrando a horda), um plano em
   primeira pessoa, um slow-motion (timeRemap) no golpe decisivo, flashes/whip pans cobrindo cortes de ação, e um cartão final de uma linha.

PERSONAGENS E ARTE (use as skills, nada de skins prontas do jogo)
- Use a skill blockreel-skins para criar 2 skins ORIGINAIS: a guerreira (slim) e o vigia (classic, olhos brilhantes no filme). Paleta com rampas de 4 tons,
  pintura em camadas, turntable de 4 ângulos e no mínimo 2 rodadas de revisão olhando a imagem. Guarde em films/farol-negro/skins/.
- Zumbis: use a skin humanoide de zumbi de exemplo (core/builtin/mobs/sample-zombie-layout.png) com o clipe "zombie", 8 a 12 zumbis no total (não passe disso: custo de render).
  Um creeper (core/builtin/mobs/sample-creeper-layout.png) como armadilha viva: clipe swell + explosão + hide.
- Opcional, se couber no tempo: skill blockreel-textures para um conjunto próprio de ~12 blocos (obsidiana, pedra molhada, madeira escura, tijolo, glowstone...)
  com tilecheck e pack_preview, aplicado ao filme pela pasta "blocks" + index.json.

DIREÇÃO TÉCNICA
- Cenário: costa de obsidiana, farol alto de pedra com um brasier vazio no topo (pilar + glowstone colocado por "changes"), portão de madeira (prop door),
  baú, TNT empilhado, água e lava. Duas locações no máximo (a costa e o topo do farol), cada uma com paleta própria.
- Luz: lighting em 3 atos (azul-tempestade → vermelho/laranja da explosão → ouro do amanhecer), chuva, relâmpago simulado com flashes brancos curtos.
- Atuação: use swing / hit / lunge / stance / shout, olhar (lookAt), faces (glow, wide, angry, shout, hurt, dead) e legendas curtas com lip-sync (no máximo 3 falas de até 6 palavras).
- Câmera: handheld em toda ação, dutch angle no auge, rack focus (post.dof) na revelação do vigia, plano em primeira pessoa, órbita no clímax.
- Partículas e mundo: poeira de passos, faíscas, fumaça, fogo, quebra de bloco com rachaduras, TNT com pavio, explosão que abre cratera, porta e baú animados.
- Som: NÃO invente arquivos. Deixe a faixa "audio" do story.json preparada (música, efeitos e diálogo com ducking) apontando para assets/audio/*.wav e me diga
  exatamente quais sons preciso colocar, com tempo de entrada, para eu soltar os arquivos livres que você listou.

PRODUÇÃO (obrigatória)
1. Quadros de teste de cada plano; prévia com --preset preview; só então o render final com --workers 4 em 1920x1080 (--scale 1.5 a partir de um story de 1280x720).
2. QA obrigatória ANTES de entregar: python tools/qa.py com pelo menos 12 quadros, olhe CADA imagem, corrija e rode de novo (mínimo 3 rodadas), e registre em qa.md
   o que olhou, achou, corrigiu e o que NÃO conseguiu verificar. Atenção especial a: câmera dentro de bloco, personagem flutuando sobre cratera, rosto de costas
   nos planos de fala, legenda cortada, pés cortados, plano longo demais, close-ups de rosto e mãos (proporções do jogo: ombro alinhado ao tronco, cabeça direto no corpo).
3. Entregue: o MP4 final, a pasta do projeto (story.json, skins, assets), research.md, brief.md, shotlist.md, qa.md, 6 quadros-chave em JPG e um GIF de 6 s.
4. Seja honesto no relatório final: o que foi testado e rodado, o que falhou, o que não foi verificado (áudio, jogo real, GPU) e quanto tempo o render levou.
```

---

## 2. Short film, quick (EN)

```text
Use the blockreel skill. Make a 30 s blocky comedy: a noob mines a diamond, a creeper-looking mob shows up, TNT is involved, the noob survives by accident.
Run the full flow (brief, research with links, shot list, build, QA with at least 8 frames you actually look at) and tell me what the engine cannot do before you start.
```

## 3. Skin

```text
Use the blockreel-skins skill. Design an original skin: a copper-haired alchemist with a leather apron and goggles pushed up on the forehead, slim arms, cartoon style.
Research palettes and shading first, plan 4-tone ramps, paint base layer then overlay, validate, and iterate at least twice on the 4-angle turntable (show me each round).
```

## 4. Texture pack

```text
Use the blockreel-textures skill. Make a 16x "autumn village" texture set (stone, cobblestone, dirt, grass top and side, planks, log, leaves, bricks, glass, water, lava, glowstone, TNT, wool).
Plan one palette for the whole set, make every tile seamless, run tilecheck and pack_preview and look at both, then build the pack for Java 1.21.4 with the format number cited from the Minecraft Wiki.
```

## 5. Skin from a screenshot

```text
Here is a screenshot of my skin (attached). Turn it into a clean 64x64 PNG, tell me if it is slim or classic, and show me a turntable. If rows are missing, say so instead of guessing.
```
