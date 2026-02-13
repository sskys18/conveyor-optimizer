"""CLI entry point for the glass layout optimizer."""

import argparse
import os
import sys

import yaml

from .case1 import run_case1
from .case2 import run_case2
from .io import (
    load_csv,
    export_json,
    export_summary_csv,
    export_details_csv,
    export_score_by_W_csv
)


def load_config(config_path: str) -> dict:
    """Load configuration from YAML file."""
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            return yaml.safe_load(f) or {}
    return {}


def main():
    parser = argparse.ArgumentParser(
        prog='conveyor_opt',
        description='Optimize glass panel layouts on a conveyor belt'
    )
    parser.add_argument(
        '--config', '-c',
        default='config.yml',
        help='Path to config file (default: config.yml)'
    )

    subparsers = parser.add_subparsers(dest='command', required=True)

    # Case 1 subcommand
    case1_parser = subparsers.add_parser(
        'case1',
        help='Fixed conveyor width optimization'
    )
    case1_parser.add_argument('--input', '-i', required=True, help='Input CSV file')
    case1_parser.add_argument('--output', '-o', default='output', help='Output directory')
    case1_parser.add_argument('--W', type=int, help='Conveyor width (mm)')
    case1_parser.add_argument('--top-n', type=int, help='Number of top layouts per type')
    case1_parser.add_argument('--delta', type=int, help='Width tolerance (mm)')
    case1_parser.add_argument('--dp-k', type=int, help='Max layouts per DP cell')

    # Case 2 subcommand
    case2_parser = subparsers.add_parser(
        'case2',
        help='Variable conveyor width selection and optimization'
    )
    case2_parser.add_argument('--input', '-i', required=True, help='Input CSV file')
    case2_parser.add_argument('--output', '-o', default='output', help='Output directory')
    case2_parser.add_argument('--W-min', type=int, help='Minimum conveyor width (mm)')
    case2_parser.add_argument('--W-max', type=int, help='Maximum conveyor width (mm)')
    case2_parser.add_argument('--top-n', type=int, help='Number of top layouts per type')
    case2_parser.add_argument('--delta', type=int, help='Width tolerance (mm)')
    case2_parser.add_argument('--dp-k', type=int, help='Max layouts per DP cell')

    args = parser.parse_args()

    # Load config
    config = load_config(args.config)

    if args.command == 'case1':
        run_case1_cmd(args, config)
    elif args.command == 'case2':
        run_case2_cmd(args, config)


def run_case1_cmd(args, config: dict):
    """Execute Case 1 command."""
    # Get parameters (CLI args override config)
    W = args.W or config.get('W', 5500)
    top_n = getattr(args, 'top_n', None) or config.get('top_n', 10)
    delta = args.delta or config.get('delta', 5)
    dp_k = getattr(args, 'dp_k', None) or config.get('dp_k', 20)

    print(f"Loading glass types from {args.input}...")
    types = load_csv(args.input)
    print(f"Loaded {len(types)} glass types")

    print(f"Running Case 1 optimization (W={W}, top_n={top_n}, delta={delta})...")
    results = run_case1(types, W=W, top_n=top_n, delta=delta, dp_k=dp_k)

    # Export results
    os.makedirs(args.output, exist_ok=True)

    print(f"Exporting results to {args.output}/...")
    export_json(results, types, W, args.output)
    export_summary_csv(results, types, W, os.path.join(args.output, 'summary.csv'))
    export_details_csv(results, types, W, os.path.join(args.output, 'details.csv'))

    print("Done!")
    print_summary(results, types, W)


def run_case2_cmd(args, config: dict):
    """Execute Case 2 command."""
    # Get parameters (CLI args override config)
    W_min = getattr(args, 'W_min', None) or config.get('W_min', 5200)
    W_max = getattr(args, 'W_max', None) or config.get('W_max', 5500)
    top_n = getattr(args, 'top_n', None) or config.get('top_n', 10)
    delta = args.delta or config.get('delta', 5)
    dp_k = getattr(args, 'dp_k', None) or config.get('dp_k', 20)

    print(f"Loading glass types from {args.input}...")
    types = load_csv(args.input)
    print(f"Loaded {len(types)} glass types")

    print(f"Running Case 2 optimization (W_min={W_min}, W_max={W_max}, top_n={top_n}, delta={delta})...")
    W_star, results, score_by_W = run_case2(
        types, W_min=W_min, W_max=W_max, top_n=top_n, delta=delta, dp_k=dp_k
    )

    print(f"Selected optimal width: W* = {W_star} (avg waste ratio: {score_by_W[W_star]:.4f})")

    # Export results
    os.makedirs(args.output, exist_ok=True)

    print(f"Exporting results to {args.output}/...")
    export_json(results, types, W_star, args.output)
    export_summary_csv(results, types, W_star, os.path.join(args.output, 'summary.csv'))
    export_details_csv(results, types, W_star, os.path.join(args.output, 'details.csv'))
    export_score_by_W_csv(score_by_W, os.path.join(args.output, 'score_by_W.csv'))

    print("Done!")
    print_summary(results, types, W_star)


def print_summary(results: dict, types: list, W: int):
    """Print summary to console."""
    type_map = {gt.type_id: gt for gt in types}

    print(f"\n{'='*60}")
    print(f"Summary (W={W})")
    print(f"{'='*60}")

    for type_id in sorted(results.keys()):
        layouts = results[type_id]
        gt = type_map[type_id]

        if layouts:
            best = layouts[0]
            waste = W - best.used_width
            print(f"  {gt.name}: best waste={waste}mm, {best.num_panels} panels, {len(layouts)} layouts found")
        else:
            print(f"  {gt.name}: no feasible layout found")


if __name__ == '__main__':
    main()
