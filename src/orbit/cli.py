"""Small CLI entrypoints for ORBIT (development placeholder).

This file provides minimal entrypoints while the codebase grows. Keep it lightweight
so it doesn't introduce heavy runtime deps.
"""

import argparse
import sys


def main(argv=None):
    argv = argv or sys.argv[1:]
    p = argparse.ArgumentParser(prog="orbit")
    p.add_argument("command", nargs="?", default="help", help="subcommand: ingest|features|run")
    args = p.parse_args(argv)

    if args.command in ("help", "", None):
        p.print_help()
        return 0

    print(f"Called orbit {args.command} (placeholder). Replace with real entrypoints.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
