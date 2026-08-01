from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Optional, Sequence

from .doctor import diagnose
from .render import RenderFailure, RenderOptions, render_presentation


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="powerpoint-native-render")
    subcommands = parser.add_subparsers(dest="command", required=True)
    subcommands.add_parser(
        "doctor",
        help="Check native PowerPoint render prerequisites without opening a presentation.",
    )
    render = subcommands.add_parser(
        "render",
        help="Render a saved .pptx through desktop Microsoft PowerPoint.",
    )
    render.add_argument("source", type=Path, help="Saved and closed .pptx source")
    render.add_argument(
        "--workspace",
        type=Path,
        required=True,
        help="Project Workspace that owns the render artifacts",
    )
    render.add_argument(
        "--settle-seconds",
        type=float,
        default=3.0,
        help="Seconds to wait after PowerPoint opens the snapshot (0-30; default: 3)",
    )
    render.add_argument(
        "--timeout",
        type=int,
        default=180,
        help="Per-attempt export and PDF stability timeout (30-900; default: 180)",
    )
    render.add_argument(
        "--dpi",
        type=int,
        default=180,
        help="Inspection PNG resolution (72-600; default: 180)",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "doctor":
        payload = diagnose()
        print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
        return 0 if payload["status"] == "ok" else 1
    if args.command == "render":
        try:
            payload = render_presentation(
                RenderOptions(
                    source=args.source,
                    workspace=args.workspace,
                    settle_seconds=args.settle_seconds,
                    timeout=args.timeout,
                    dpi=args.dpi,
                )
            )
        except RenderFailure as error:
            payload = error.as_payload()
            print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
            return 1
        print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
        return 0
    raise AssertionError(f"Unhandled command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
