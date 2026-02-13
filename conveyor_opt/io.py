"""I/O functions for loading input and exporting results."""

import csv
import json
import os
from typing import Dict, List

from .models import GlassType, Layout


def load_csv(path: str) -> List[GlassType]:
    """Load glass types from a CSV file.

    Expected columns: name, width_mm, height_mm

    Args:
        path: path to CSV file

    Returns:
        List of GlassType objects
    """
    types = []
    with open(path, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            gt = GlassType(
                type_id=i,
                name=row['name'].strip(),
                w=int(row['width_mm']),
                h=int(row['height_mm'])
            )
            types.append(gt)
    return types


def export_json(
    results: Dict[int, List[Layout]],
    types: List[GlassType],
    W: int,
    output_dir: str
) -> None:
    """Export results to JSON files, one per mandatory type.

    Args:
        results: dict mapping mandatory_type_id -> list of layouts
        types: list of glass types (for name lookup)
        W: conveyor width used
        output_dir: directory to write JSON files
    """
    os.makedirs(output_dir, exist_ok=True)
    type_map = {gt.type_id: gt for gt in types}

    for type_id, layouts in results.items():
        gt = type_map[type_id]
        data = {
            "mandatory_type": {
                "id": type_id,
                "name": gt.name,
                "width": gt.w,
                "height": gt.h
            },
            "conveyor_width": W,
            "layouts": []
        }

        for rank, layout in enumerate(layouts, 1):
            layout_data = {
                "rank": rank,
                "used_width": layout.used_width,
                "waste": W - layout.used_width,
                "num_panels": layout.num_panels,
                "num_distinct_types": layout.num_distinct_types,
                "panels": []
            }
            for (tid, orient), count in sorted(layout.counts.items()):
                t = type_map[tid]
                layout_data["panels"].append({
                    "type_id": tid,
                    "name": t.name,
                    "orientation": "rotated" if orient else "original",
                    "width_used": t.h if orient else t.w,
                    "count": count
                })
            data["layouts"].append(layout_data)

        output_path = os.path.join(output_dir, f"mandatory_{gt.name}.json")
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)


def export_summary_csv(
    results: Dict[int, List[Layout]],
    types: List[GlassType],
    W: int,
    output_path: str
) -> None:
    """Export summary CSV with one row per mandatory type.

    Args:
        results: dict mapping mandatory_type_id -> list of layouts
        types: list of glass types
        W: conveyor width
        output_path: path to output CSV
    """
    type_map = {gt.type_id: gt for gt in types}

    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            'mandatory_type_id', 'mandatory_type_name',
            'best_used_width', 'best_waste', 'best_num_panels',
            'num_layouts_found'
        ])

        for type_id in sorted(results.keys()):
            layouts = results[type_id]
            gt = type_map[type_id]

            if layouts:
                best = layouts[0]
                writer.writerow([
                    type_id, gt.name,
                    best.used_width, W - best.used_width, best.num_panels,
                    len(layouts)
                ])
            else:
                writer.writerow([type_id, gt.name, 0, W, 0, 0])


def export_details_csv(
    results: Dict[int, List[Layout]],
    types: List[GlassType],
    W: int,
    output_path: str
) -> None:
    """Export detailed CSV with one row per layout.

    Args:
        results: dict mapping mandatory_type_id -> list of layouts
        types: list of glass types
        W: conveyor width
        output_path: path to output CSV
    """
    type_map = {gt.type_id: gt for gt in types}

    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            'mandatory_type_id', 'mandatory_type_name', 'rank',
            'used_width', 'waste', 'num_panels', 'num_distinct_types',
            'layout_description'
        ])

        for type_id in sorted(results.keys()):
            layouts = results[type_id]
            gt = type_map[type_id]

            for rank, layout in enumerate(layouts, 1):
                # Build human-readable layout description
                parts = []
                for (tid, orient), count in sorted(layout.counts.items()):
                    t = type_map[tid]
                    ori_str = "R" if orient else ""
                    parts.append(f"{t.name}{ori_str}x{count}")
                desc = " + ".join(parts)

                writer.writerow([
                    type_id, gt.name, rank,
                    layout.used_width, W - layout.used_width,
                    layout.num_panels, layout.num_distinct_types,
                    desc
                ])


def export_score_by_W_csv(
    score_by_W: Dict[int, float],
    output_path: str
) -> None:
    """Export W -> waste ratio scores to CSV.

    Args:
        score_by_W: dict mapping W -> average waste ratio
        output_path: path to output CSV
    """
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['W', 'avg_waste_ratio'])
        for W in sorted(score_by_W.keys()):
            writer.writerow([W, f"{score_by_W[W]:.6f}"])
