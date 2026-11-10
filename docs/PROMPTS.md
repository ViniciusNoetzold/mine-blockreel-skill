# Prompts prontos / Ready-made prompts

No Codex, abra a raiz do repositório e peça para ler `plugin/skills/blockreel/SKILL.md`. No Claude Code, use o plugin ou abra a raiz do repositório. Os prompts funcionam em português ou inglês.

In Codex, open the repository root and ask it to read `plugin/skills/blockreel/SKILL.md`. In Claude Code, use the plugin or open the repository root.

---

## Terror cinematográfico em primeira pessoa (PT-BR)

```text
Use a skill BlockReel e siga docs/CINEMATIC-WORKFLOW.md para criar um curta de terror em primeira pessoa de 45 segundos, em 1280 × 720 a 24 fps, com som. Use Primeira Noite como referência de ritmo, luz e revisão.

Um mineiro encontra um trilho interrompido e ouve um carrinho vindo do escuro. Mantenha o ponto de vista do mineiro. Faça a primeira tocha revelar o trilho partido, aproxime o olhar de uma pista perto dos pés e use o som do carrinho para puxar a atenção de volta ao túnel. Mude a composição ou a luz quando mudar o que ele sabe. Deixe um silêncio curto antes da revelação final.

Defina os planos e os sons juntos. Confira os assets usados e gere uma prévia com a mixagem. Revise enquadramento, leitura da pista, ritmo e sincronia dos efeitos. Ajuste os trechos que ficaram repetitivos e confira o MP4 codificado com som antes de entregar. Inclua o storyboard, os assets de produção e o qa.md.
```

## 1. Super produção de 30 s: "O Cerco do Farol Negro" (PT-BR)

> Veja a [cobertura do motor](COVERAGE.md) antes de escolher os rigs e efeitos. Renderize um trecho na resolução final para medir o custo na sua máquina.

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
- Som: gere trilha e efeitos originais ou use os arquivos que eu fornecer. Sincronize os impactos, o pavio e a explosão aos planos. Monte e confira a mixagem com
  a prévia. Se faltar um áudio indispensável, registre qual arquivo ou cue está pendente e sinalize a exportação como prévia.

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

## Fights, reveals and you in the film (v0.2, the director)

- *"Me faça no Minecraft e crie uma batalha minha contra o Herobrine."* (attach a photo of yourself or your skin)
  → persona skin from the photo, `preset: herobrine`, night, shrine, lightning reveal, duel, teleport, lightning power, finisher,
  silence, ending card. Start: `python tools/compose.py --example`.
- *"Uma luta de espadas entre meu personagem e um cavaleiro numa arena de pedra ao pôr do sol, câmera lenta no golpe final."*
  → `golden-hour`, `world.arenaFloor: "stone_bricks"`, `preset: knight`, `faceoff` + `duel` + `finisher`.
- *"Herobrine aparece atrás de mim numa caverna escura com tochas."* → hand-built cave (`hollow` + torches), `reveal` with `fx: portal`,
  `teleport` to `behind:me`, `line` with `emotion: scared`.
- *"Um vídeo calmo: eu e meu cachorro vendo o pôr do sol numa colina, sem ação."* → `walk`, `act` (`sit`, hold), `wait`, `ending`; music
  `calm`/`dawn` only.
