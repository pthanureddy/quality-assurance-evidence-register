import argparse
import json
from pathlib import Path

from .exporter import export_register
from .loader import load_register
from .metrics import calculate_kpis


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate and export a quality assurance evidence register."
    )
    parser.add_argument(
        "command", choices=("validate", "generate"), help="operation to perform"
    )
    parser.add_argument("--input", required=True, type=Path, help="register JSON file")
    parser.add_argument("--output", type=Path, help="export directory for generate")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    register = load_register(args.input)
    kpis = calculate_kpis(register)
    if args.command == "generate":
        if args.output is None:
            raise SystemExit("--output is required for generate")
        manifest = export_register(register, args.output)
        print(json.dumps({"kpis": kpis, "rows": manifest}, indent=2, sort_keys=True))
    else:
        print(json.dumps(kpis, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

