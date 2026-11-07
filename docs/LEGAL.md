# Legal notes (not legal advice)

- BlockReel is an independent, unofficial fan tool. It is **not** made by, affiliated with, or endorsed by Mojang or Microsoft.
  The name deliberately avoids the game's trademark.
- This repository ships **no game assets**: no textures, models, sounds, music or fonts from the game.
  The built-in block textures and skins in `core/builtin/` are procedurally generated originals, released under CC0.
- `tools/vanilla.py` downloads Mojang's own textures (from Mojang's official `bedrock-samples` repository, or the mirror
  `ZtechNetwork/MCBVanillaResourcePack`) and sound effects (from Mojang's official asset servers) into `work/vanilla/` on **your**
  machine, for rendering your own videos. `python tools/vanilla.py font` reads the game's bitmap font the same way (a few files of
  Mojang's `client.jar`, fetched with HTTP range requests from Mojang's servers) into `work/vanilla/font/`. `work/` is gitignored: never commit, upload or redistribute those files. Game music is not fetched.
- `core/persona.py preset herobrine --from-steve` (and the director's Herobrine when the cache exists) derives a skin from the cached
  default skin: it is written to your film folder, which is gitignored. Without the cache an original CC0 painting is used.
- Photos: turn a photo into a skin only for the user themself or someone who agreed. Photos are read locally and never uploaded by the tools.
- Tools that process your sheets, skins or textures work on files **you** provide. You are responsible for having the right
  to use them. Do not commit game assets to a public fork.
- Videos you publish may be subject to Mojang's current Usage Guidelines and the EULA. Read the current versions before monetising.
- Code: MIT (see `LICENSE`).
