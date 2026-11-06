# Pre-production (steps A–C)

A film is decided here, before any JSON. Four files per film in `films/<name>/`:
`brief.md`, `research.md`, `shotlist.md`, and later `qa.md`.

## A. brief.md

```markdown
# <Film title>
- **Premise** (one sentence):
- **Tone**: comedy | horror | epic | wholesome | ...
- **Length**: 45 s
- **Characters**: name — skin file — role
- **Setting**: where, time of day
- **Style**: classic-2012 | golden-hour | nightfall | void-arena | ember-haze
- **Defaults I chose** (the user can change any): ...
- **Beats**: setup / escalation / turn / payoff in one line each
- **Energy shape**: quiet → ... → quiet
```

Ask the user at most one short question; otherwise decide and declare the choices.

## B. research.md

Search the web for each item, read at least the top result of each (WebFetch), and write down what you *use*, not
what you read. Every bullet has a link.

```markdown
# Research: <Film title>
## 1. Animation language (<tone>)
- <principle> — <link>
## 2. Rigid-body character animation
- anticipation / overshoot / follow-through / impact frames: <how I use it in shot N> — <link>
## 3. Setting references
- block architecture / palette / landmarks: <what I build> — <link>
## 4. Music and sound sources (free to use)
| Source | Track / pack | License | Link | Where it would go |
|---|---|---|---|---|
(Do not download. The user decides and supplies the files.)
## 5. Principles to apply
1. ...
```

Rules:
- **Principles, not copies.** Do not reproduce scenes, characters, dialogue or music from any work.
- Reference videos live in `work/` (gitignored). Only your written conclusions go in the repo.
- Search queries that work: "<tone> animation pacing shot length", "12 principles of animation anticipation
  follow through", "minecraft <setting> build palette", "royalty free <mood> music CC0", "free sound effects
  <explosion|footsteps> license". Prefer sources that state a license (CC0, CC-BY, Pixabay/YouTube Audio Library terms).
- For a reference video analysis, follow `references/video-analysis/673z48KEXy0.md` as the model.

## C. shotlist.md

```markdown
| # | t | dur | shot | camera | action / clip | line | intent |
|---|---|---|---|---|---|---|---|
| 1 | 0.0 | 3.5 | establishing wide | dolly in, low | hero walks | — | where are we, what is the mood |
```

Checks before building:
- One idea; the premise fits one sentence.
- Total duration matches the brief; no shot longer than the tone allows (comedy 2–4 s, action 1–2 s, calm holds
  up to 5 s with movement).
- A hook in the first 3 s; a quiet beat before the payoff; a button after it.
- Every shot has an *intent*. If you cannot write it, cut the shot.
- Lines ≤ 10 words, ≤ 2 s on screen.
- List which engine features each shot needs and confirm they exist in `docs/STORYBOARD.md`.
