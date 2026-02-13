"""Case 2: Variable conveyor width selection and optimization."""

from typing import Dict, List, Tuple

from .models import GlassType, Layout, generate_variants
from .solver import solve, extract_top_n, get_max_used_width


def run_case2(
    types: List[GlassType],
    W_min: int = 5200,
    W_max: int = 5500,
    H: int = None,
    top_n: int = 10,
    delta: int = 5,
    dp_k: int = 20
) -> Tuple[int, Dict[int, List[Layout]], Dict[int, float]]:
    """Run Case 2 optimization with variable conveyor width.

    1. For each W in [W_min, W_max], compute average waste ratio across all mandatory types
    2. Select W* with minimum average waste ratio (tie-break: smaller W)
    3. Run full extraction at W* for all mandatory types

    Args:
        types: list of glass types
        W_min: minimum conveyor width to consider
        W_max: maximum conveyor width to consider
        H: conveyor height in mm (perpendicular), None = no constraint
        top_n: number of top layouts to return per mandatory type
        delta: width tolerance from optimal (mm)
        dp_k: max layouts per DP cell

    Returns:
        Tuple of:
        - W*: selected optimal width
        - results: dict mapping mandatory_type_id -> list of top layouts
        - score_by_W: dict mapping W -> average waste ratio
    """
    variants = generate_variants(types)
    score_by_W: Dict[int, float] = {}

    # Phase 1: Evaluate each W
    for W in range(W_min, W_max + 1):
        waste_ratios = []
        for gt in types:
            dp = solve(W, gt.type_id, variants, dp_k, H=H)
            u_star = get_max_used_width(dp)

            if u_star is None:
                # Infeasible - assign worst ratio
                waste_ratios.append(1.0)
            else:
                waste = W - u_star
                waste_ratios.append(waste / W)

        avg_ratio = sum(waste_ratios) / len(waste_ratios)
        score_by_W[W] = avg_ratio

    # Phase 2: Select W* (min avg ratio, tie-break smaller W)
    W_star = min(score_by_W.keys(), key=lambda w: (score_by_W[w], w))

    # Phase 3: Full extraction at W*
    results: Dict[int, List[Layout]] = {}
    for gt in types:
        dp = solve(W_star, gt.type_id, variants, dp_k, H=H)
        layouts = extract_top_n(dp, W_star, top_n, delta)
        results[gt.type_id] = layouts

    return W_star, results, score_by_W
