# Legal notes (not legal advice)

- BlockReel is an independent, unofficial fan tool. It is **not** made by, affiliated with, or endorsed by Mojang or Microsoft.
  The name deliberately avoids the game's trademark.
- This repository ships **no game assets**: no textures, models, sounds, music or fonts from the game.
  The built-in block textures and skins in `core/builtin/` are procedurally generated originals, released under CC0.
- `tools/vanilla.py` downloads Mojang's own textures (from Mojang's official `bedrock-samples` repository, or the mirror
  `ZtechNetwork/MCBVanillaResourcePack`) and sound effects (from Mojang's official asset servers) into `work/vanilla/` on **your**
  machine, for rendering your own videos. `work/` is gitignored: never commit, upload or redistribute those files. Game music is not fetched.
- Tools that process your sheets, skins or textures work on files **you** provide. You are responsible for having the right
  to use them. Do not commit game assets to a public fork.
- Videos you publish may be subject to Mojang's current Usage Guidelines and the EULA. Read the current versions before monetising.
- Code: MIT (see `LICENSE`).
