#!/usr/bin/env python3
"""Live preview in your own browser: a local server plus a time slider and play button.

  python tools/preview.py examples/hello-world/story.json            # opens http://127.0.0.1:<port>/...
  python tools/preview.py story.json --no-open                       # just print the URL

Edit story.json, reload the page, drag the slider. With a real GPU this runs in real time; the page uses the same
engine as the renderer, so what you see at time t is exactly what the final video shows at t.
"""
import argparse
import sys
import threading
import time
import webbrowser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from render import serve  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("story"); ap.add_argument("--no-open", action="store_true")
    a = ap.parse_args(argv)
    p = Path(a.story).resolve()
    srv, port = serve(p.parent)
    url = f"http://127.0.0.1:{port}/core/engine/index.html?project=/project/{p.name}&live=1"
    print("preview:", url, "(Ctrl+C to stop)")
    if not a.no_open:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
