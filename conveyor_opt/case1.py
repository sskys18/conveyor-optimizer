"""Case 1: Fixed conveyor width optimization."""

from typing import Dict, List

from .models import GlassType, Layout, generate_variants
from .solver import solve, extract_top_n


def run_case1(
    types: List[GlassType],
    W: int = 5500,
    H: int = None,
    top_n: int = 10,
    delta: int = 5,
    dp_k: int = 20
) -> Dict[int, List[Layout]]:
    """Run Case 1 optimization with fixed conveyor width.

    For each glass type as mandatory, find the top-N near-optimal layouts.

    Args:
        types: list of glass types
        W: conveyor width in mm
        H: conveyor height in mm (perpendicular), None = no constraint
        top_n: number of top layouts to return per mandatory type
        delta: width tolerance from optimal (mm)
        dp_k: max layouts per DP cell

    Returns:
        Dict mapping mandatory_type_id -> list of top layouts
    """
    variants = generate_variants(types)
    results: Dict[int, List[Layout]] = {}

    for gt in types:
        dp = solve(W, gt.type_id, variants, dp_k, H=H)
        layouts = extract_top_n(dp, W, top_n, delta)
        results[gt.type_id] = layouts

    return results
