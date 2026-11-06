# Research: The Last Torch

Searched with WebSearch/WebFetch on the day this film was built. The search results were thin in places (noted below);
nothing here is copied from any work. All items are principles or links.

## 1. Animation language (epic / suspense)
- **Pace follows the story, and varies.** Shorter shots intensify action, longer shots invite contemplation, and varying shot
  length creates rhythm. I use calm 3 s shots at both ends and 0.8–1.8 s shots in the charge. — [Fiveable: pacing and rhythm in animated narratives](https://fiveable.me/2d-animation/unit-16/pacing-rhythm-animated-narratives/study-guide/RxEvXQNY0PYmJArB)
- **Fast cutting can still be clear.** An average shot length around 2 s does not have to be chaotic if the shots are planned. — [The Fastest Cut](https://vashivisuals.com/?p=5689)
- **Ask whether pacing is uniform.** Does the action speed up and slow down in ways that serve the story? — [animatic critique checklist](https://people.willamette.edu/~gorr/classes/ids252Sp13/lectures/animaticCritique.doc)
- **Low angles make a figure imposing; silhouettes and unseen figures build unease; Dutch angles disorient.** Warden is introduced from a low angle (shot 4). — [The Secrets of Horror Movie Cinematography](https://blog.thefilmfund.co/?p=902), [Grammar of Dread](https://blog.indiecinema.co/?p=892229)
- **Alternating calm and threat is the engine of suspense.** The standoff (shot 5) holds still before the charge. — [Hitchcock suspense storyboarding](https://www.thepromptindex.com/skill/1281-storyboard-hitchcock-suspense)
- **Plan the rhythm of the whole before the shots.** I wrote the energy shape in `brief.md` first. — same source
- *Gap:* the searches did not cover rain as a visual device or epic-climax escalation techniques; I rely on `DIRECTOR.md` §10 for those.

## 2. Rigid-body character animation
- Anticipation and ease-in/out live in the frames around the start of an action: more "drawings" near the pose, fewer between. In BlockReel
  that is the `swing` and `lunge` clips (wind-up, strike, overshoot, settle) and `outBack` movement easing. — [Fiveable pacing guide](https://fiveable.me/2d-animation/unit-16/pacing-rhythm-animated-narratives/study-guide/RxEvXQNY0PYmJArB)
- *Gap:* no source found that ties follow-through and overlapping action to cut length. I treat them as clip design (arms lag the torso) and
  keep a longer 1.8 s shot after the blast so the settle is visible. For depth, the classic reference is Williams' *The Animator's Survival Kit* (a book; not consulted here).

## 3. Setting references
- A weathered look comes from mixing cobblestone, stone and mossy variants; avoid a perfectly blocky silhouette by breaking the walls and the roofline. — [Diamond Lobby: how to build a watchtower](https://diamondlobby.com/minecraft/how-to-build-watchtower-in-minecraft/), [Beebom: castle blueprint](https://beebom.com/how-build-castle-in-minecraft/amp/)
- What I build: a hollow cobblestone tower with a door gap, holes in two walls, a missing roof corner, four obsidian brazier blocks and rubble. BlockReel has no
  mossy variant, so the ruin comes from holes and rubble. Several pages in that search looked like low-quality rewrites; I used only the build guides.

## 4. Music and sound sources (free to use). **Do not download; the user decides.**
| Source | What | License (as stated by the source) | Link | Where it would go |
|---|---|---|---|---|
| OpenGameArt | "CC0 cinematic music" collection | CC0 per the search result. **Not verified**: the page blocked an automated fetch (HTTP 403), so check the license on the page | [link](https://opengameart.org/content/cc0-cinematic-music) | low drone under shots 1–3, swell at 14 s |
| Mixkit | free thunder / rain / explosion effects | "Mixkit License" (free to use in video projects; the page did not state the terms, read the license text first) | [link](https://mixkit.co/free-sound-effects/thunder/), [license](https://mixkit.co/license/#sfxFree) | rain bed, the blast at 14.6 s |
| 99Sounds | free pack of cinematic effects (impacts, risers) | royalty-free per the result; **read the pack's license** | [link](https://99sounds.org/cinematic-sound-effects/comment-page-14/) | riser into the charge, impact on the blast |
Not checked (not returned by the search): Pixabay, Kevin MacLeod. Do not assume their terms.

## 5. Principles to apply
1. Quiet → loud → one silent beat → quiet; the film earns its loud middle (brief).
2. Hook with motion and scale in 3 s: a rain tilt up the tower (shot 1).
3. Low angle for the threat (shot 4), eye level for the human (shot 3).
4. Action shots 0.8–1.8 s, with a whip pan and a flash covering the cuts (shots 6–8).
5. Slow motion only on the blast, as a speed ramp that catches up (`timeRemap`).
6. One palette per act: cold dusk blue → warm dawn when the beacon lights (`lighting` keyframes).
7. Light the thing to look at: glowing eyes, then the glowstone beacon, with bloom.
8. Hold the emotional beat: after the blast, 3.7 s in the smoke with no action.
9. End quiet: a pull-back and a one-line card.
