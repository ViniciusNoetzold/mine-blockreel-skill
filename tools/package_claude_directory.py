"""Build a tagged-source candidate for the Claude directory from a Git commit."""

import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PLUGIN_MANIFEST = "plugin/.claude-plugin/plugin.json"
EXCLUDED_FILES = {".claude-plugin/marketplace.json", PLUGIN_MANIFEST, "CLAUDE.md"}
MEDIA_EXTENSIONS = {".mp4", ".webm", ".gif"}
MIB = 1024 * 1024


def git(*arguments, env=None, data=None):
    return subprocess.check_output(["git", *arguments], cwd=ROOT, env=env, input=data)


def make_tree(source):
    tracked = git("ls-tree", "-r", "--name-only", "-z", source).decode().rstrip("\0").split("\0")
    exclude = [
        name for name in tracked
        if name in EXCLUDED_FILES or name.startswith(".github/") or Path(name).suffix in MEDIA_EXTENSIONS
    ]
    manifest = json.loads(git("show", f"{source}:{PLUGIN_MANIFEST}"))
    manifest["skills"] = "./plugin/skills/"
    readme = git("show", f"{source}:plugin/README.md")
    readme += (
        b"\nThis snapshot packages the renderer, guides, and skills for the Claude directory. "
        b"[Project source and films](https://github.com/ViniciusNoetzold/mine-blockreel-skill/tree/main)\n"
    )
    with tempfile.TemporaryDirectory(prefix="blockreel-directory-") as scratch:
        env = {**os.environ, "GIT_INDEX_FILE": str(Path(scratch) / "index")}
        git("read-tree", source, env=env)
        git("update-index", "--force-remove", "-z", "--stdin", env=env,
            data=b"".join(name.encode() + b"\0" for name in exclude))
        for name, content in (
            (".claude-plugin/plugin.json", (json.dumps(manifest, indent=2) + "\n").encode()),
            ("README.md", readme),
        ):
            blob = git("hash-object", "-w", "--stdin", data=content).decode().strip()
            git("update-index", "--add", "--cacheinfo", f"100644,{blob},{name}", env=env)
        tree = git("write-tree", env=env).decode().strip()
    return tree, manifest["version"]


def validate(archive):
    with zipfile.ZipFile(archive) as package:
        entries = package.infolist()
        if len(entries) >= 10_000 or sum(entry.file_size for entry in entries) >= 256 * MIB:
            raise ValueError("The directory snapshot exceeds the unpacked size or entry limit.")
        if any(entry.file_size >= 5 * MIB for entry in entries):
            raise ValueError("A file in the plugin snapshot exceeds the 5 MiB limit.")
        if archive.stat().st_size >= 50 * MIB:
            raise ValueError("The archive exceeds the 50 MiB directory limit.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ref", default="HEAD", help="Committed BlockReel source to package")
    parser.add_argument("--out", type=Path, required=True, help="Output ZIP path")
    args = parser.parse_args()
    source = git("rev-parse", "--verify", "--end-of-options", f"{args.ref}^{{commit}}").decode().strip()
    tree, version = make_tree(source)
    message = f"Package BlockReel {version} for the Claude directory\n\nSource: {source}\n"
    commit = git("commit-tree", tree, "-p", source, data=message.encode()).decode().strip()
    output = args.out.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="blockreel-package-", dir=output.parent) as scratch:
        archive = Path(scratch) / "claude-directory.zip"
        git("archive", "--format=zip", "-9", f"--output={archive}", commit)
        validate(archive)
        archive.replace(output)
    print(f"Claude directory snapshot {commit}")
    print(f"{output} ({output.stat().st_size / MIB:.2f} MiB)")


if __name__ == "__main__":
    main()
