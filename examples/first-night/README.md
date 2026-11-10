# Primeira Noite

Um jogador corre contra o pôr do sol, se fecha numa encosta e descobre o que a luz da tocha estava escondendo. Curta de 60 segundos em 1280 × 720 a 24 fps, com trilha e efeitos sonoros originais.

[Assista com som no navegador](https://viniciusnoetzold.github.io/mine-blockreel-skill-/#first-night) · [Storyboard editável](story.json) · [Registro de revisão](qa.md)

| Tempo | Direção |
| --- | --- |
| 00–10 s | Olhos, mãos em primeira pessoa e uma órbita completa que revela a clareira e a ravina. |
| 10–25 s | Três troncos, bancada, picareta de madeira e coleta de pedregulho. Cada receita segue o inventário mostrado. |
| 25–40 s | Olhos da aranha entre os troncos. A corrida termina com três blocos escavados e o fechamento da entrada. |
| 40–52 s | Respiração no abrigo, carvão e receita da tocha na grade pessoal de 2 × 2. |
| 52–60 s | Luz quente e alívio. A câmera revela o Creeper, o som some por um segundo e o estouro corta para preto. |

O cenário usa texturas originais do BlockReel e dois sprites do projeto para o carvão. A trilha é sintetizada por `make_audio.py` a partir de `audio-cues.json`. A névoa, o bloom e as partículas dão profundidade à luz da floresta. O plano final usa uma tocha acionada pela timeline.

## Reproduza o render

Rode da raiz do repositório depois da [instalação](../../README.pt-BR.md#rode-as-ferramentas-diretamente).

```sh
python examples/first-night/make_audio.py
python tools/qa.py examples/first-night/story.json --out work/first-night/qa --no-md
python tools/render.py examples/first-night/story.json --workers 2 --crf 21 --out work/first-night.mp4
python tools/check_media.py work/first-night.mp4 --duration 60 --size 1280x720 --fps 24 --require-audio
```

O gerador grava a mixagem em `generated/mix.wav`. A revisão de áudio tem uma pausa de 56,25 a 57,25 s, seguida pelo estopim. A explosão coincide com a entrada do quadro preto em 59,25 s.
