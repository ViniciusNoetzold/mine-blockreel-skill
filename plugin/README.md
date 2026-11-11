# BlockReel

BlockReel helps you make Minecraft-style animated films from prompts, storyboards, and reference images. It renders editable scenes frame by frame with a local Three.js renderer. The four skills guide distinct tasks.

- `blockreel` directs characters, cameras, lighting, and audio and exports landscape or vertical video.
- `blockreel-builds` converts building references into editable blueprints and construction timelapses.
- `blockreel-skins` paints and validates player skins and previews them in a turntable.
- `blockreel-textures` designs and validates block and item textures and packages them for Minecraft Java Edition.

Try asking for a 15-second timelapse of a wooden cabin from a reference image, with a portrait camera and an editable blueprint. [Watch the film gallery](https://viniciusnoetzold.github.io/mine-blockreel-skill/)

## Runtime and data

The skills use a local BlockReel checkout, Node.js 20+, Python 3.11+, FFmpeg, FFprobe, and Chrome or Chromium for rendering. Setup clones the public source from GitHub, installs the locked JavaScript dependencies and Python packages, and can download Chromium through Playwright. An installed compatible browser can be selected through `CHROME_PATH`. [Runtime setup](https://github.com/ViniciusNoetzold/mine-blockreel-skill#run-the-tools-directly)

The renderer processes supplied images, storyboards, and audio in the workspace. Its bundled art and generated audio can be used for renders. Optional Minecraft asset downloads go into an ignored local cache, and the optional Piper voice workflow downloads voice models for local synthesis. The skills may use the host agent's research capabilities for reference work and version-specific formats. [Asset policy](https://github.com/ViniciusNoetzold/mine-blockreel-skill/blob/main/docs/LEGAL.md)

BlockReel is an independent fan project. Code and documentation use the MIT license. Bundled original textures and skins use CC0. [License](https://github.com/ViniciusNoetzold/mine-blockreel-skill/blob/main/LICENSE)
