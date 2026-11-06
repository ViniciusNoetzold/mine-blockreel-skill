#!/usr/bin/env python3
"""Replace the publishing placeholders (YOUR_USER, YOUR_NAME) everywhere in the repo, after showing what will change.

  python tools/set_placeholders.py --user octocat --name "Octo Cat"                         # dry run: lists every change
  python tools/set_placeholders.py --user octocat --name "Octo Cat" --repo my-repo --apply  # writes the files
YOUR_USER/blockreel becomes <user>/<repo> (default repo name: blockreel), then any remaining YOUR_USER becomes <user>.
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP = {".git", "node_modules", "out", "work", "films", "__pycache__", ".pytest_cache"}
TEXT = {".md", ".json", ".py", ".yml", ".yaml", ".txt", ".js", ".html"}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--user", required=True, help="GitHub user or organisation that will own the repo")
    ap.add_argument("--name", required=True, help="author name shown in the plugin manifests")
    ap.add_argument("--repo", default="blockreel", help="repository name on GitHub (default: blockreel)")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args(argv)
    if "/" in a.user or " " in a.user:
        print("--user must be just the GitHub user name (no slash or spaces)", file=sys.stderr)
        return 2
    n = 0
    for f in sorted(ROOT.rglob("*")):
        if not f.is_file() or f.suffix not in TEXT or any(part in SKIP for part in f.relative_to(ROOT).parts) or f.name == Path(__file__).name:
            continue
        try:
            s = f.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if "YOUR_USER" in s or "YOUR_NAME" in s:
            cnt = s.count("YOUR_USER") + s.count("YOUR_NAME")
            print(f"{'edit' if a.apply else 'would edit'} {f.relative_to(ROOT)} ({cnt})")
            n += cnt
            if a.apply:
                f.write_text(s.replace("YOUR_USER/blockreel", f"{a.user}/{a.repo}").replace("YOUR_USER", a.user).replace("YOUR_NAME", a.name), encoding="utf-8")
    print(f"{n} replacements" + ("" if a.apply else " (dry run; add --apply)"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
