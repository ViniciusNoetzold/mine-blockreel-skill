# Publishing checklist (v0.1.0)

Nothing in this file has been run for you: git and GitHub actions publish your work, so you (or the assistant, after you say so) run them.

## 1. Placeholders (done for this repo)

The publishing placeholders were replaced with the owner `ViniciusNoetzold` and the repo `mine-blockreel-skill` using `tools/set_placeholders.py`
(it replaces `YOUR_USER/blockreel` with `<user>/<repo>` and any leftover `YOUR_USER` / `YOUR_NAME`). To publish a fork under another name:

```bash
python tools/set_placeholders.py --user <github-user> --name "<Your Name>" --repo <repo-name>          # dry run
```
(The placeholders no longer exist in this repo; the script is only useful on a fresh copy of the template.)

## 2. Validate and test

```bash
python -m pytest tests -q && node tests/anim_check.mjs
claude plugin validate .            # the marketplace (.claude-plugin/marketplace.json)
claude plugin validate ./plugin     # the plugin (manifest + 3 skills)
```
(`claude plugin validate` could not be run where this repo was prepared; the manifests were checked by reading the official docs, which say `name` is the only required
plugin field and that marketplace entries need `name` and `source`.)

## 3. First commit and tag

The folder was not a git repository when this was prepared.

```bash
git init -b main && git add -A && git status        # check that out/, work/, films/ and node_modules/ are NOT listed
git commit -m "BlockReel v0.1.0"
git tag -a v0.1.0 -m "v0.1.0"
```
Never commit game assets or reference videos (`work/` and `films/` are gitignored). `docs/media/demo.gif` (2.8 MB) and `docs/media/poster.png` are original renders and are meant to be committed.

## 4. Create the repo and push

```bash
gh repo create ViniciusNoetzold/mine-blockreel-skill --public --source . --remote origin --description "Make Minecraft-style animations, skins and texture packs from a prompt. Rendered in code, no video model. A Claude Code plugin." --push
git push origin v0.1.0
```

## 5. Topics, about box, social preview

Suggested **topics**: `minecraft`, `animation`, `claude-code`, `claude-code-plugin`, `claude-skills`, `threejs`, `procedural-generation`, `pixel-art`, `minecraft-skins`,
`resource-pack`, `texture-pack`, `video-generation`, `python`, `ffmpeg`, `playwright`.

```bash
gh repo edit ViniciusNoetzold/mine-blockreel-skill --add-topic minecraft --add-topic animation --add-topic claude-code --add-topic claude-code-plugin \
  --add-topic claude-skills --add-topic threejs --add-topic procedural-generation --add-topic pixel-art --add-topic minecraft-skins \
  --add-topic resource-pack --add-topic texture-pack --add-topic video-generation --add-topic python --add-topic ffmpeg --add-topic playwright
```
**Social preview:** Settings → General → Social preview → upload an image (1280x640 is the recommended size); `docs/media/poster.png` is a 960x540 frame you can crop or extend.

## 6. Release v0.1.0

Draft notes are in [RELEASE-NOTES-v0.1.0.md](RELEASE-NOTES-v0.1.0.md).

```bash
gh release create v0.1.0 --title "BlockReel v0.1.0" --notes-file docs/RELEASE-NOTES-v0.1.0.md
```
Optionally attach a rendered film (`examples/last-torch`, 25 MB at 960x540; render it yourself with `python tools/render.py examples/last-torch/story.json --workers 4 --out last-torch.mp4`).

## 7. Good first issues

Ready to paste or create with `gh`: [GOOD-FIRST-ISSUES.md](GOOD-FIRST-ISSUES.md). Create the `good first issue` label first (GitHub has it by default).

## 8. After publishing

- Install the plugin from GitHub on a clean machine: `claude plugin marketplace add ViniciusNoetzold/mine-blockreel-skill` then `claude plugin install blockreel@blockreel-market`, and run `/blockreel:blockreel`.
- Look at the Actions tab: CI installs Chromium with software GL, so the real-render tests run there too. If a render test fails only on CI, check the Chromium launch flags in `tools/render.py`.
