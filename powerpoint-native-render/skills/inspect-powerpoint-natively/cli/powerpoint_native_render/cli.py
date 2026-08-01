from __future__ import annotations

import argparse
import json
from typing import Optional, Sequence

from .doctor import diagnose


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="powerpoint-native-render")
    subcommands = parser.add_subparsers(dest="command", required=True)
    subcommands.add_parser(
        "doctor",
        help="Check native PowerPoint render prerequisites without opening a presentation.",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "doctor":
        payload = diagnose()
        print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
        return 0 if payload["status"] == "ok" else 1
    raise AssertionError(f"Unhandled command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
