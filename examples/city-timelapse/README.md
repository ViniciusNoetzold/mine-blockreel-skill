# Praça do Horizonte

Timelapse de 14 segundos em que duas avenidas cruzam um terreno vazio e ligam quatro bairros. A construção ocupa uma área de 81 × 67 blocos. A torre do relógio marca a silhueta acima dos telhados.

[Assista ao timelapse](https://viniciusnoetzold.github.io/mine-blockreel-skill/#city-timelapse) · [Layout editável](layout.json) · [Guia de timelapses](../../docs/BUILD-TIMELAPSE.md)

| Etapa | O que aparece |
| --- | --- |
| Avenidas | Piso escuro, faixas brancas, calçadas de pedra e luminárias |
| Feira | Praça de pedra e quatro bancas com toldos listrados |
| Jardim | Caminhos de arenito, bétulas, canteiros e um espelho azul de vidro sobre lã |
| Residências | Quatro casas com fachadas distintas, janelas e telhados inclinados |
| Centro cívico | Prédio de arenito com colunas, bandeira e torre de tijolos |

O layout reúne 5.553 colocações com materiais incluídos no BlockReel. Cada arquivo em `districts/` usa coordenadas locais. O layout decide a posição e a ordem dos bairros. Para reutilizar uma quadra, referencie o mesmo arquivo com outro `id` e `origin`. Ajuste as ligações com as avenidas. O compilador valida sobreposições antes do render.

## Reproduza o vídeo

Rode da raiz do repositório depois de [instalar as dependências](../../README.pt-BR.md#rode-as-ferramentas-diretamente).

```sh
python tools/city_timelapse.py examples/city-timelapse/layout.json --out work/city-timelapse
python tools/render.py work/city-timelapse/story.json --preset preview --out work/city-timelapse/preview.mp4
python tools/qa.py work/city-timelapse/story.json --out work/city-timelapse/qa
python tools/render.py work/city-timelapse/story.json --out work/city-timelapse/film.mp4
python tools/check_media.py work/city-timelapse/film.mp4 --duration 14 --size 1280x720 --fps 24 --require-audio
```

O compilador gera o storyboard, a planta expandida, o relatório com os tempos de cada etapa e a mixagem original. Confira se os caminhos continuam conectados, se os toldos e telhados se distinguem na prévia e se a torre cabe no quadro final.

## Revisão do exemplo

Conferimos as avenidas antes dos bairros, a construção dos telhados e a cidade completa. Ajustamos a altura das nuvens para que a câmera aérea enxergasse as etapas e estendemos o terreno visual para a borda da cena ficar fora da vista. A checagem de trajetórias ficou sem colisões. O aviso sobre o plano longo foi aceito para preservar a visão geral durante a montagem. A revelação também foi conferida em um quadro 9:16. O MP4 horizontal final decodificou por completo, com 336 quadros e áudio AAC estéreo.
