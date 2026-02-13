"""Data structures for the glass layout optimizer."""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple


@dataclass(frozen=True)
class GlassType:
    """A glass panel type with dimensions."""
    type_id: int
    name: str
    w: int  # width in mm
    h: int  # height in mm


@dataclass(frozen=True)
class Variant:
    """A variant of a glass type (original or rotated orientation)."""
    variant_id: int
    type_id: int
    orient: int  # 0 = original, 1 = rotated
    width: int   # width along conveyor direction
    height: int  # height perpendicular to conveyor


@dataclass
class Layout:
    """A layout configuration."""
    key: Tuple[Tuple[int, int, int], ...]  # canonical key: tuple of (type_id, orient, count)
    used_width: int
    max_height: int  # max height of all panels (perpendicular to conveyor)
    num_panels: int
    num_distinct_types: int
    counts: Dict[Tuple[int, int], int] = field(default_factory=dict)  # (type_id, orient) -> count


def generate_variants(types: List[GlassType]) -> List[Variant]:
    """Generate all variants for the given glass types.

    For each type:
    - Always create orient=0 variant (width = w, height = h)
    - Create orient=1 variant (width = h, height = w) only if w != h
    """
    variants = []
    vid = 0
    for gt in types:
        # Original orientation
        variants.append(Variant(
            variant_id=vid,
            type_id=gt.type_id,
            orient=0,
            width=gt.w,
            height=gt.h
        ))
        vid += 1

        # Rotated orientation (only if not square)
        if gt.w != gt.h:
            variants.append(Variant(
                variant_id=vid,
                type_id=gt.type_id,
                orient=1,
                width=gt.h,
                height=gt.w
            ))
            vid += 1

    return variants


def make_canonical_key(counts: Dict[Tuple[int, int], int]) -> Tuple[Tuple[int, int, int], ...]:
    """Create a canonical key from counts dict.

    Args:
        counts: dict mapping (type_id, orient) -> count

    Returns:
        Sorted tuple of (type_id, orient, count) for non-zero counts
    """
    items = [(tid, ori, cnt) for (tid, ori), cnt in counts.items() if cnt > 0]
    return tuple(sorted(items))


def add_variant_to_layout(layout: Layout, variant: Variant) -> Layout:
    """Create a new layout by adding one variant to the existing layout.

    Returns a new Layout object (immutable operation).
    """
    new_counts = dict(layout.counts)
    key = (variant.type_id, variant.orient)
    old_count = new_counts.get(key, 0)
    new_counts[key] = old_count + 1

    # Count distinct types (by type_id only, not orientation)
    distinct_types = len(set(tid for tid, _ in new_counts.keys()))

    return Layout(
        key=make_canonical_key(new_counts),
        used_width=layout.used_width + variant.width,
        max_height=max(layout.max_height, variant.height),
        num_panels=layout.num_panels + 1,
        num_distinct_types=distinct_types,
        counts=new_counts
    )


def empty_layout() -> Layout:
    """Create an empty layout."""
    return Layout(
        key=(),
        used_width=0,
        max_height=0,
        num_panels=0,
        num_distinct_types=0,
        counts={}
    )
