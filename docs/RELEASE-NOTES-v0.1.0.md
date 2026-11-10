# BlockReel v0.1.0

**Make Minecraft-style animations, skins and texture packs from a prompt. Rendered in code, no video model.** A Claude Code plugin with three skills.

## What is in it

- **`blockreel` (films):** pre-production flow (briefing, web research with links, shot list), a Three.js engine, and a mandatory visual QA (`tools/qa.py`).
  Clips with anticipation and overshoot, face states and lip-sync, seeded particles, block break/place/TNT/explosions, doors and chests, four mob rigs, handheld/Dutch/first-person/rack-focus
  cameras, flash/whip/fade transitions, speed ramps, day-night lighting, rain and snow, bloom/grain/grade, music + sfx + dialogue with ducking.
  Parallel workers, resolution scale, live browser preview.
- **`blockreel-skins`:** research → palette plan → layered painting → validate → 4-angle turntable you iterate on. Original demo skin in classic and slim.
- **`blockreel-textures`:** palette plan for a whole set → tileable tiles → tiling/seam and palette checker → in-scene preview → resource-pack zip with a researched, cited pack format
  (`pack_format`, or `min_format`/`max_format` for 1.21.9+). Original 16x demo set with animated water and lava.
- **Demo film:** [`examples/last-torch`](../examples/last-torch), 34 s, made with the full flow; its research, shot list and QA log are in the folder.
- 34 automated tests (plus a node check of the animation math), including real renders of every example.

## Honest limits

- Not complete: no held tools, no stairs/fences/torches, only four mob shapes, no sneak/swim/ride clips, no armor, no sun/moon/stars, no motion blur. See [COVERAGE.md](COVERAGE.md).
- Mob texture layouts are **unverified** against sources ([MOBS.md](MOBS.md)).
- Skins and resource packs were **not tested in the game**; they are validated and previewed in the BlockReel engine.
- Software GL is slow (the 34 s demo took 7.5 min with 4 workers). `--gpu` exists and is untested.
- `claude plugin validate` was not run by the author; run it before relying on the install commands.
- Unofficial fan tool. Not affiliated with Mojang or Microsoft. Ships no game assets ([LEGAL.md](LEGAL.md)).

## Install

```bash
claude plugin marketplace add ViniciusNoetzold/mine-blockreel-skill
claude plugin install blockreel@blockreel-market
```
Needs Node 20+, Python 3.11+, ffmpeg and Chrome/Chromium (`python -m playwright install chromium`).
