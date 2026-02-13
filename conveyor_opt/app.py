"""Streamlit UI for Conveyor Glass Layout Optimizer."""

import sys
from pathlib import Path
from typing import Dict, List

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st

from conveyor_opt.models import GlassType, Layout
from conveyor_opt.case1 import run_case1
from conveyor_opt.case2 import run_case2


def format_layout_description(layout: Layout, type_map: Dict[int, GlassType]) -> str:
    """Format layout as human-readable string."""
    parts = []
    for (tid, orient), count in sorted(layout.counts.items()):
        t = type_map[tid]
        ori_str = "R" if orient else ""
        parts.append(f"{t.name}{ori_str}x{count}")
    return " + ".join(parts)


def get_type_color(type_id: int, total_types: int) -> str:
    """Generate distinct color for each type using HSL with spaced hues."""
    hue = (type_id * 360 // max(total_types, 1)) % 360
    return f"hsl({hue}, 70%, 45%)"


def render_layout_bar(layout: Layout, type_map: Dict[int, GlassType], W: int) -> str:
    """Render layout as horizontal bar diagram with colored panels."""
    waste = W - layout.used_width
    total_types = len(type_map)

    # Build list of panels with their widths and colors
    panels = []
    for (tid, orient), count in sorted(layout.counts.items()):
        t = type_map[tid]
        panel_width = t.h if orient else t.w
        color = get_type_color(tid, total_types)
        ori_label = " (R)" if orient else ""
        for _ in range(count):
            panels.append({
                'width': panel_width,
                'color': color,
                'label': f"{t.name}{ori_label}",
                'size': f"{panel_width}mm"
            })

    # Build HTML
    html_parts = [
        '<div style="display:flex; width:100%; height:60px; border:1px solid #ccc; '
        'border-radius:4px; overflow:hidden; background:#f8f8f8;">'
    ]

    for panel in panels:
        pct = (panel['width'] / W) * 100
        html_parts.append(
            f'<div style="width:{pct}%; background:{panel["color"]}; display:flex; '
            f'flex-direction:column; justify-content:center; align-items:center; '
            f'color:white; font-size:11px; text-shadow:0 0 2px rgba(0,0,0,0.5); '
            f'border-right:1px solid rgba(255,255,255,0.3); overflow:hidden;">'
            f'<span style="font-weight:bold;">{panel["label"]}</span>'
            f'<span>{panel["size"]}</span>'
            f'</div>'
        )

    # Add waste area if any
    if waste > 0:
        waste_pct = (waste / W) * 100
        html_parts.append(
            f'<div style="width:{waste_pct}%; background:#ddd; display:flex; '
            f'flex-direction:column; justify-content:center; align-items:center; '
            f'color:#666; font-size:11px;">'
            f'<span>waste</span>'
            f'<span>{waste}mm</span>'
            f'</div>'
        )

    html_parts.append('</div>')
    return ''.join(html_parts)


def results_to_summary_df(results: Dict[int, List[Layout]], types: List[GlassType], W: int):
    """Convert results to summary dataframe data."""
    type_map = {gt.type_id: gt for gt in types}
    rows = []
    for type_id in sorted(results.keys()):
        layouts = results[type_id]
        gt = type_map[type_id]
        if layouts:
            best = layouts[0]
            rows.append({
                'Type': gt.name,
                'Best Used Width': best.used_width,
                'Max Height': best.max_height,
                'Best Waste': W - best.used_width,
                'Panels': best.num_panels,
                'Layouts Found': len(layouts)
            })
        else:
            rows.append({
                'Type': gt.name,
                'Best Used Width': 0,
                'Max Height': 0,
                'Best Waste': W,
                'Panels': 0,
                'Layouts Found': 0
            })
    return rows


def main():
    st.set_page_config(page_title="Conveyor Glass Layout Optimizer", layout="wide")
    st.title("Conveyor Glass Layout Optimizer")

    # Initialize session state for glass types
    if 'glass_types' not in st.session_state:
        st.session_state['glass_types'] = []

    # Glass type input section
    st.subheader("Glass Types")

    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
    with col1:
        new_name = st.text_input("Name", key="new_name")
    with col2:
        new_width = st.number_input("Width (mm)", min_value=1, value=1000, key="new_width")
    with col3:
        new_height = st.number_input("Height (mm)", min_value=1, value=500, key="new_height")
    with col4:
        st.write("")  # Spacer
        st.write("")  # Spacer
        if st.button("Add"):
            if new_name:
                st.session_state['glass_types'].append({
                    'name': new_name,
                    'width': new_width,
                    'height': new_height
                })
                st.rerun()

    # Display current glass types
    if st.session_state['glass_types']:
        st.write("**Current Glass Types:**")
        for i, gt in enumerate(st.session_state['glass_types']):
            col1, col2 = st.columns([4, 1])
            with col1:
                st.write(f"{gt['name']}: {gt['width']} x {gt['height']} mm")
            with col2:
                if st.button("Remove", key=f"remove_{i}"):
                    st.session_state['glass_types'].pop(i)
                    st.rerun()
    else:
        st.info("Add at least one glass type to continue.")

    if st.session_state['glass_types']:
        # Convert to GlassType objects
        types = [
            GlassType(type_id=i, name=gt['name'], w=gt['width'], h=gt['height'])
            for i, gt in enumerate(st.session_state['glass_types'])
        ]

        st.divider()

        # Mode selection
        st.subheader("Configuration")
        mode = st.radio("Mode", ["Case 1 (Fixed W)", "Case 2 (Variable W)"], horizontal=True)

        # Parameters
        col1, col2, col3, col4 = st.columns(4)

        if mode == "Case 1 (Fixed W)":
            with col1:
                W = st.number_input("W (mm)", min_value=1, value=5500, key="W_input")
            with col2:
                H = st.number_input("H (mm)", min_value=0, value=0, key="H_input", help="Max height (0 = no limit)")
            with col3:
                top_n = st.number_input("Top N", min_value=1, value=10, key="top_n_input")
            with col4:
                delta = st.number_input("Delta (mm)", min_value=0, value=5, key="delta_input")
        else:
            with col1:
                W_min = st.number_input("W min (mm)", min_value=1, value=5200, key="W_min_input")
            with col2:
                W_max = st.number_input("W max (mm)", min_value=1, value=5500, key="W_max_input")
            with col3:
                H = st.number_input("H (mm)", min_value=0, value=0, key="H_input2", help="Max height (0 = no limit)")
            with col4:
                top_n = st.number_input("Top N", min_value=1, value=10, key="top_n_input2")
            delta = st.number_input("Delta (mm)", min_value=0, value=5, key="delta_input2")

        # Run button
        if st.button("Run Optimization", type="primary"):
            H_val = H if H > 0 else None  # 0 means no constraint
            with st.spinner("Running optimization..."):
                if mode == "Case 1 (Fixed W)":
                    results = run_case1(types, W=W, H=H_val, top_n=top_n, delta=delta)
                    selected_W = W
                else:
                    selected_W, results, score_by_W = run_case2(
                        types, W_min=W_min, W_max=W_max, H=H_val, top_n=top_n, delta=delta
                    )
                    st.success(f"Optimal W* selected: {selected_W} mm")

            # Store results in session state
            st.session_state['results'] = results
            st.session_state['W'] = selected_W
            st.session_state['result_types'] = types

        # Display results if available
        if 'results' in st.session_state:
            results = st.session_state['results']
            W = st.session_state['W']
            result_types = st.session_state['result_types']
            type_map = {gt.type_id: gt for gt in result_types}

            st.divider()
            st.subheader("Results")

            # Summary table
            st.write("**Summary**")
            summary_data = results_to_summary_df(results, result_types, W)
            st.dataframe(summary_data, use_container_width=True)

            # Details per type (expandable)
            st.write("**Details by Type**")
            for type_id in sorted(results.keys()):
                layouts = results[type_id]
                gt = type_map[type_id]
                with st.expander(f"{gt.name} ({len(layouts)} layouts)"):
                    for rank, layout in enumerate(layouts, 1):
                        waste = W - layout.used_width
                        st.markdown(
                            f"**Rank #{rank}** — Used: {layout.used_width}mm, "
                            f"Height: {layout.max_height}mm, "
                            f"Waste: {waste}mm, Panels: {layout.num_panels}"
                        )
                        st.markdown(
                            render_layout_bar(layout, type_map, W),
                            unsafe_allow_html=True
                        )
                        st.caption(format_layout_description(layout, type_map))
                        st.write("")  # Spacer between layouts


if __name__ == "__main__":
    main()
