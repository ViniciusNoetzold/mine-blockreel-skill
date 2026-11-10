# A Casa Nova · Timelapse de construção

A cabana usa como referência a construção de *A Casa Nova*. A fachada preserva a faixa de pedregulho, os postes de carvalho, o vão central e as duas janelas de vidro na mesma altura. A planta de 7 × 6 blocos e a cobertura de duas águas foram recuperadas do projeto original e do filme publicado. [Assista ao timelapse de 12 segundos](https://viniciusnoetzold.github.io/mine-blockreel-skill-/#house-timelapse) · [Assista ao filme original](https://viniciusnoetzold.github.io/mine-blockreel-skill-/#creeper-surprise) · [Plano original](../creeper-surprise/plan.json)

O print mostra a casa durante a obra. Para a versão pronta, fechamos os frontões e levantamos o piso interno um bloco acima do terreno, mantendo o vão da fachada livre. A sequência começa na clareira e monta o piso, a estrutura, as paredes, as janelas e o telhado em ordem. No final, a câmera deixa a construção inteira em quadro. [Blueprint editável](blueprint.json)

## Reproduza o timelapse

Rode na raiz do repositório após [instalar as dependências](../../README.pt-BR.md#rode-as-ferramentas-diretamente).

```sh
python tools/build_timelapse.py examples/house-timelapse/blueprint.json --out films/house-timelapse
python tools/qa.py films/house-timelapse/story.json --out films/house-timelapse/qa --no-md
python tools/render.py films/house-timelapse/story.json --out films/house-timelapse/timelapse.mp4
python tools/check_media.py films/house-timelapse/timelapse.mp4 --duration 12 --size 1280x720 --fps 24 --require-audio
```

Compare os quadros da fachada com a referência durante a subida das paredes e na vista final. Confira se os vãos continuam visíveis, se a cumeeira está inteira no quadro e se os sons acompanham a construção.

## Revisão do exemplo

Conferimos a clareira vazia, as paredes antes do telhado e a vista final. Abrimos um corredor na vegetação para preservar a entrada e as duas janelas no plano final. A revisão automática apontou zero colisões e um aviso de duração do plano de construção, mantido para acompanhar as etapas no mesmo enquadramento. Um quadro da revelação também foi conferido em 9:16. O MP4 final decodificou por completo, com 288 quadros e AAC estéreo.
