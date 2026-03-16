"""
Orquestador principal del pipeline de calidad de datos abiertos NL.

Uso:
  python run_pipeline.py
  python run_pipeline.py --fast
  python run_pipeline.py --module 1
  python run_pipeline.py --module 2
  python run_pipeline.py --module 3
  python run_pipeline.py --with-standards
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).parent


def run_cmd(command: list[str]) -> None:
    result = subprocess.run(command, cwd=ROOT)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def run_module_1(fast: bool) -> None:
    cmd = [sys.executable, "01_extract.py"]
    if fast:
        cmd.append("--no-download-csv")
    run_cmd(cmd)


def run_module_2(with_standards: bool) -> None:
    cmd = [sys.executable, "02_evaluate.py"]
    if with_standards:
        cmd.append("--with-standards")
    run_cmd(cmd)


def run_module_3() -> None:
    run_cmd([sys.executable, "03_longitudinal.py"])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Pipeline NL 2024-2026")
    parser.add_argument(
        "--fast",
        action="store_true",
        help="Solo metadata en modulo 1 (sin descarga CSV)",
    )
    parser.add_argument(
        "--module",
        type=int,
        choices=[1, 2, 3],
        help="Ejecuta solo un modulo especifico",
    )
    parser.add_argument(
        "--with-standards",
        action="store_true",
        help="Activa evaluacion de estandares via OpenAI en modulo 2",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.module == 1:
        run_module_1(fast=args.fast)
        return
    if args.module == 2:
        run_module_2(with_standards=args.with_standards)
        return
    if args.module == 3:
        run_module_3()
        return

    run_module_1(fast=args.fast)
    run_module_2(with_standards=args.with_standards)
    run_module_3()


if __name__ == "__main__":
    main()
