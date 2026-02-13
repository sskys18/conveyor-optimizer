"""DP solver for glass layout optimization."""

from typing import Dict, List, Optional, Tuple

from .models import GlassType, Variant, Layout, empty_layout, add_variant_to_layout, generate_variants


# Type alias for DP cell: canonical_key -> Layout
DPCell = Dict[Tuple, Layout]


def solve(
    W: int,
    mandatory_type_id: int,
    variants: List[Variant],
    dp_k: int = 20,
    H: Optional[int] = None
) -> Dict[int, Dict[int, DPCell]]:
    """Run DP solver to find layouts.

    DP state: DP[s][u] where
      - s ∈ {0, 1}: whether mandatory type has been used
      - u ∈ [0, W]: used width

    Args:
        W: maximum conveyor width
        mandatory_type_id: type that must be included
        variants: list of all variants
        dp_k: max layouts to keep per (s, u) cell
        H: maximum conveyor height (perpendicular), None = no constraint

    Returns:
        DP table: {s: {u: {key: Layout}}}
    """
    # Initialize DP table
    # dp[s][u] = dict of canonical_key -> Layout
    dp: Dict[int, Dict[int, DPCell]] = {
        0: {},  # mandatory not used
        1: {}   # mandatory used
    }

    # Base case: empty layout at (s=0, u=0)
    dp[0][0] = {(): empty_layout()}

    # Process each used_width from 0 to W
    for u in range(W + 1):
        for s in [0, 1]:
            if u not in dp[s]:
                continue

            cell = dp[s][u]
            if not cell:
                continue

            # Try adding each variant
            for variant in variants:
                new_u = u + variant.width
                if new_u > W:
                    continue

                # Determine new state s
                new_s = s
                if variant.type_id == mandatory_type_id:
                    new_s = 1

                # Generate new layouts
                for layout in cell.values():
                    new_layout = add_variant_to_layout(layout, variant)

                    # Skip if exceeds height constraint
                    if H is not None and new_layout.max_height > H:
                        continue

                    # Insert into dp[new_s][new_u]
                    if new_u not in dp[new_s]:
                        dp[new_s][new_u] = {}

                    target_cell = dp[new_s][new_u]

                    # Dedup by canonical key - keep only if better or new
                    key = new_layout.key
                    if key not in target_cell:
                        target_cell[key] = new_layout

                    # Trim to dp_k if needed
                    if len(target_cell) > dp_k * 2:
                        _trim_cell(target_cell, dp_k)

        # Final trim after processing all variants for this u
        for s in [0, 1]:
            if u in dp[s] and len(dp[s][u]) > dp_k:
                _trim_cell(dp[s][u], dp_k)

    return dp


def _trim_cell(cell: DPCell, k: int) -> None:
    """Trim cell to keep only top k layouts.

    Sorting criteria: (num_panels ASC, num_distinct_types ASC, key ASC)
    Fewer panels = better (less handling), fewer types = simpler
    """
    if len(cell) <= k:
        return

    layouts = list(cell.values())
    layouts.sort(key=lambda l: (l.num_panels, l.num_distinct_types, l.key))

    cell.clear()
    for layout in layouts[:k]:
        cell[layout.key] = layout


def extract_top_n(
    dp: Dict[int, Dict[int, DPCell]],
    W: int,
    top_n: int = 10,
    delta: int = 5
) -> List[Layout]:
    """Extract top N layouts from DP table.

    Args:
        dp: DP table from solve()
        W: max width
        top_n: number of layouts to return
        delta: width tolerance from optimal

    Returns:
        List of top N layouts, sorted by (waste, num_panels, num_distinct_types, key)
    """
    # Only consider s=1 (mandatory used)
    mandatory_dp = dp[1]

    if not mandatory_dp:
        return []

    # Find U* = max feasible used_width
    u_star = max(mandatory_dp.keys())

    # Gather layouts from [U*-delta, U*]
    all_layouts: Dict[Tuple, Layout] = {}
    for u in range(max(0, u_star - delta), u_star + 1):
        if u in mandatory_dp:
            for key, layout in mandatory_dp[u].items():
                # Global dedup by key (keep the one with higher used_width)
                if key not in all_layouts or layout.used_width > all_layouts[key].used_width:
                    all_layouts[key] = layout

    # Sort by (waste ASC, num_panels ASC, num_distinct_types ASC, key ASC)
    layouts = list(all_layouts.values())
    layouts.sort(key=lambda l: (
        W - l.used_width,  # waste
        l.num_panels,
        l.num_distinct_types,
        l.key
    ))

    return layouts[:top_n]


def get_max_used_width(dp: Dict[int, Dict[int, DPCell]]) -> Optional[int]:
    """Get the maximum used width from the DP table where mandatory is used.

    Returns None if no feasible solution exists.
    """
    mandatory_dp = dp[1]
    if not mandatory_dp:
        return None
    return max(mandatory_dp.keys())
