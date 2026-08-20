#!/usr/bin/env python3
"""Serve the static prototype on loopback only."""

from __future__ import annotations

import argparse
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    handler = lambda *values, **kwargs: SimpleHTTPRequestHandler(  # noqa: E731
        *values, directory=str(ROOT / "prototype"), **kwargs
    )
    server = ThreadingHTTPServer(("127.0.0.1", args.port), handler)
    print(f"Local-only prototype: http://127.0.0.1:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
