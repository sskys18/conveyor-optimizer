Below is a complete, end-to-end project guide that includes everything needed to build the system exactly as specified:
	•	All data structures
	•	DP solver with mandatory state
	•	Top-N extraction with \Delta = 5 mm
	•	Case 1 (fixed W) + Case 2 (choose W) pipelines
	•	Deterministic formatting and export
	•	Excel-ready output design
	•	JSON output design per mandatory type
	•	CLI wrapper + configuration file format

This is written as a technical design document you can implement directly.

⸻

1) Project Scope and Deliverables

1.1 What the system must do

Inputs
	•	Conveyor width:
	•	Case 1: fixed W=5500
	•	Case 2: integer W \in [5200, 5500]
	•	Glass types list:
Each type t has dimensions (w_t, h_t), and may be rotated (swap width/height).

Outputs

For every mandatory type m\in T:
	•	Best achievable used width U^*(m,W)
	•	Best waste width W - U^*(m,W)
	•	Best waste ratio (W-U^*)/W
	•	Top N = 10 unique layouts within \Delta = 5 mm of optimal waste
(optimal + near-optimal alternatives)

Additionally for Case 2:
	•	Evaluate all W \in [5200,5500] and pick W^* minimizing average waste ratio across mandatory types.
	•	Then report Top-N layouts for each mandatory type under the selected W^*.

Determinism

Runs must be deterministic:
	•	same inputs → same ordering and same selected layouts
	•	deterministic tie-breaking rules

⸻

2) Mathematical Model (Reference)

For a fixed width W and mandatory type m:

Decision variables
x_{t,o} \in \mathbb{Z}_{\ge0} \quad t\in T,\; o\in\{0,1\}
where o denotes orientation.

Widths
	•	a_{t,0} = w_t
	•	a_{t,1} = h_t
(If w_t=h_t, use only one orientation)

Capacity
\sum_{t,o} a_{t,o}x_{t,o} \le W

Mandatory
x_{m,0} + x_{m,1} \ge 1

Objective
Maximize used width:
\max \sum_{t,o} a_{t,o}x_{t,o}

⸻

3) Defaults (Hard Requirements)

These must be enforced as the system’s standard behavior:

3.1 Top N
	•	Top N = 10

3.2 Near-optimal tolerance

Return layouts whose waste is within \Delta = 5 mm of optimal waste.

Let:
	•	U^* = best used width (optimal)
	•	U = used width of a candidate layout

Then accept:
U \ge U^* - 5

3.3 Ranking / tie-break order

Sort candidate layouts by:
	1.	Waste width W-U (ascending)
	2.	Number of panels (ascending)
	3.	Number of distinct types used (ascending)
	4.	Canonical key (lexicographic)

This ensures stable, operationally reasonable results.

⸻

4) Data Structures (Core)

4.1 Type record

Represents one glass type:

Fields
	•	type_id: int (0..|T|-1)
	•	name: str
	•	w: int
	•	h: int

Notes
	•	Keep type_id stable and deterministic (e.g., sort by name, or preserve input order).

⸻

4.2 Orientation variant (“item”)

Represents a selectable panel in a specific orientation:

Fields
	•	variant_id: int
	•	type_id: int
	•	orient: int  (0 = original width w, 1 = rotated width h)
	•	width: int (mm)

Variant generation rule
For each type:
	•	Always include width = w
	•	Include width = h only if h \ne w

⸻

4.3 Layout representation

A layout is a multiset of variant counts, represented in canonical sparse form.

Canonical Key (Uniqueness identity)

A layout key is a sorted tuple of nonzero counts:

key = ((type_id, orient, count), (type_id, orient, count), ...)

	•	Sorted by (type_id, orient)
	•	Only include items with count > 0

Two layouts are duplicates iff their keys are identical.

Layout metadata

Store minimal metadata for ranking and reporting:

Fields
	•	key: tuple
	•	used_width: int
	•	num_panels: int
	•	num_distinct_types: int

How to compute
	•	used_width: DP index or computed incrementally
	•	num_panels: sum of all counts
	•	num_distinct_types: count of unique type_id appearing in key

“Add one variant” operation

Given a layout key and a variant (type_id, orient):
	•	increase its count by 1
	•	update key deterministically

Implementation detail:
	•	you can convert key → dict, increment, convert back
	•	for speed, implement incremental tuple update (optional)

⸻

4.4 DP cell container (Top-K unique layouts per state and used width)

For each DP cell:
	•	store a set of unique layouts by key
	•	trim to keep only top DP_K candidates according to cell ranking

Recommended representation:

Cell
	•	dict[key -> Layout]

For trimming:
	•	sort layouts by (num_panels, num_distinct_types, key)
	•	keep first DP_K

Recommended constants
	•	TopN = 10
	•	Delta = 5
	•	DP_K = 20 (internal buffer)

⸻

5) DP Solver with Mandatory State (Exact Design)

5.1 DP state definition

Two layers:
	•	s = 0 → mandatory type not used yet
	•	s = 1 → mandatory type already used at least once

DP storage:

DP[s][u] = Cell (Top-K unique layouts achieving used width u)

Where:
	•	u ranges from 0..W

⸻

5.2 Initialization
	•	DP[0][0] contains one empty layout:
	•	key = ()
	•	used_width = 0
	•	num_panels = 0
	•	num_distinct_types = 0
	•	all other cells empty

⸻

5.3 Transition rule (unbounded knapsack)

For each used width u from 0..W:
For each state s in {0,1}:
For each variant v:
	•	a = v.width
	•	if u + a <= W:
	•	For each layout L in DP[s][u]:
	•	create L' = L + v
	•	new width = u + a
	•	new state:
	•	if v.type_id == mandatory_type_id: s' = 1
	•	else s' = s
	•	insert L' into DP[s'][u+a] with dedup + trimming

⸻

5.4 Insertion and dedup logic

Insertion to a target cell does:
	1.	Compute canonical key for L'
	2.	If key already exists:
	•	keep the better one per cell rank:
(\#panels, \#distinctTypes, key)
(In practice identical key implies identical layout; replacement is rarely needed.)
	3.	Insert into dict
	4.	If dict size exceeds a small threshold (e.g., 2 * DP_K), trim:
	•	convert dict values to list
	•	sort by cell rank
	•	keep first DP_K
	•	rebuild dict

This keeps memory stable.

⸻

6) Top-N Extraction with \Delta = 5

After DP finishes for mandatory type m:

6.1 Feasibility detection

Look at DP[1][u] for all u.

If all empty:
	•	scenario is infeasible
	•	return empty Top-N list and a status flag

⸻

6.2 Compute optimal used width

U^* = \max\{u \mid DP[1][u] \neq \emptyset\}

Waste:
	•	best waste = W - U*
	•	best waste ratio = (W-U*)/W

⸻

6.3 Gather candidates within tolerance

Accept widths:
u \in [\max(0,U^*-5),\; U^*]

Collect all layouts from DP[1][u] across these widths.

⸻

6.4 Global dedup and final ranking

Even though DP cells are unique, still do a final dedup step:
	•	global_dict[key] = best_layout

Final ranking key:

(waste = W-used_width, num_panels, num_distinct_types, key)

Take the first TopN=10.

⸻

7) Case 1 Pipeline (Fixed W=5500)

7.1 Flow

Given W=5500:

For each mandatory type m\in T:
	1.	run DP solver for (W, mandatory=m)
	2.	extract Top-N with \Delta=5
	3.	store result object per mandatory type

7.2 Outputs per type

Per mandatory type m, store:
	•	mandatory_type
	•	W
	•	best_used_width
	•	best_waste_width
	•	best_waste_ratio
	•	top_layouts[] (ranked list of up to 10)

⸻

8) Case 2 Pipeline (Choose best W in [5200,5500])

8.1 Score definition (default)

Average best waste ratio across all mandatory types:

S_{\text{avg}}(W)=\frac{1}{|T|}\sum_{m\in T} \frac{W-U^*(m,W)}{W}

8.2 Infeasible scenario handling

If mandatory scenario m is infeasible at width W:
	•	assign ratio = 1.0 (worst penalty)
This discourages choosing W values that break some mandatory types.

8.3 Width selection flow

For each W\in[5200..5500]:
	1.	For every mandatory type m:
	•	run DP solver for (W, mandatory=m) but you only need U*
	2.	compute S_avg(W)
	3.	store score

Choose:
	•	smallest S_avg(W)
	•	tie-break by smallest W

Let that be W^*.

8.4 Final results at selected W*

Once W^* is selected:
	•	run full DP again for each mandatory type to collect Top-10 layouts with \Delta=5
	•	export results

⸻

9) Deterministic Formatting and Export

You require deterministic output in:
	•	JSON (per mandatory type)
	•	Excel-ready tables (CSV/XLSX)

Determinism requirements:
	•	deterministic type ordering (e.g., by name)
	•	deterministic variant generation (always orient 0 first)
	•	deterministic canonical key
	•	deterministic sorting with lexicographic key as last tie-breaker

⸻

10) Export Specifications

10.1 JSON output format (per mandatory type)

Recommended JSON structure:

{
  "mandatory_type": "A",
  "W": 5500,
  "status": "feasible",
  "best_used_width": 5498,
  "best_waste_width": 2,
  "best_waste_ratio": 0.0003636,
  "delta_mm": 5,
  "topN": 10,
  "layouts": [
    {
      "rank": 1,
      "used_width": 5498,
      "waste_width": 2,
      "waste_ratio": 0.0003636,
      "num_panels": 8,
      "num_distinct_types": 3,
      "composition": [
        {"type": "A", "orient": "w", "width_mm": 581, "count": 2},
        {"type": "C", "orient": "h(rot)", "width_mm": 1488, "count": 1}
      ],
      "canonical_key": "((0,0,2),(2,1,1))"
    }
  ]
}

Notes:
	•	canonical_key string is optional but helpful for debugging and audit.
	•	composition list should be sorted by type, then orient for determinism.

⸻

10.2 Excel-ready outputs

You will typically produce two Excel sheets (or two CSV files):

Sheet 1: Summary (one row per mandatory type)

Columns:

Column	Meaning
Case	fixed / variable
Selected_W	W used
MandatoryType	type name
Feasible	TRUE/FALSE
BestUsedWidth	U^*
BestWasteWidth	W-U^*
BestWasteRatio	(W-U^*)/W
NumLayoutsReturned	<= TopN

Sheet 2: Layout Details (one row per returned layout)

Columns:

Column	Meaning
Case	fixed / variable
W	width used
MandatoryType	scenario type
Rank	1..TopN
UsedWidth	used
WasteWidth	W-used
WasteRatio	ratio
NumPanels	total panels
NumDistinctTypes	distinct types
CompositionString	human readable
CanonicalKey	stable identity string

CompositionString format example:

A(w=581)x2 | B(h=1623)x1 | C(w=621)x3

This is human-friendly and Excel-friendly.

⸻

11) CLI Wrapper Design

You want a CLI that can run:
	•	Case 1
	•	Case 2
	•	exports to JSON and Excel-ready outputs

11.1 Proposed CLI commands

Command: case1

conveyor_opt case1 --input glass.csv --W 5500 --topN 10 --delta 5 \
  --json_out out/case1_json --excel_out out/case1.xlsx

Command: case2

conveyor_opt case2 --input glass.csv --W_min 5200 --W_max 5500 \
  --topN 10 --delta 5 --aggregator avg \
  --json_out out/case2_json --excel_out out/case2.xlsx \
  --score_out out/score_by_W.csv

Optional flags
	•	--dpK 20
	•	--tie_break panels,types,key (if you later want customization)
	•	--infeasible_penalty 1.0
	•	--threads N (optional parallelism for Case 2)

⸻

12) Config File Format

Provide a config YAML to run without long CLI arguments.

12.1 Example config.yml

input:
  file: "glass.csv"
  format: "csv"  # csv or json

solver:
  topN: 10
  delta_mm: 5
  dpK: 20
  infeasible_penalty_ratio: 1.0

case1:
  enabled: true
  W: 5500

case2:
  enabled: true
  W_min: 5200
  W_max: 5500
  aggregator: "avg"   # avg or max or weighted

output:
  json_dir: "out/json"
  excel_file: "out/results.xlsx"
  score_csv: "out/score_by_W.csv"


⸻

13) Input File Spec

13.1 CSV input format

Recommended columns:

name	width_mm	height_mm
A	581	1674
B	588	1623
C	621	1488

Rules:
	•	name must be unique
	•	widths/heights must be positive integers

⸻

14) Quality Assurance Plan

14.1 Unit test targets

Canonical key uniqueness
	•	same multiset in different order → same key
	•	different orientation counts → different key

Feasibility detection
	•	mandatory type width > W in both orientations → infeasible

DP correctness on small samples

For small W (e.g. 30) and few types:
	•	brute force enumeration can verify DP results match true optimum

Near-optimal extraction correctness
	•	ensure returned used widths satisfy:
U \ge U^*-5

Deterministic order
	•	repeated runs produce identical layout ordering

⸻

15) Performance Notes

Expected drivers:
	•	W ≤ 5500
	•	number of variants ≈ 2|T|
	•	DP_K small (20)

Case 2 repeats the process up to 301 widths.
If mandatory types are many, runtime may grow.

Practical scaling approaches (optional):
	•	parallelize over mandatory types and/or W values
	•	cache intermediate results if needed

⸻

16) Implementation Checklist (Engineering To-Do)

16.1 Core implementation
	•	Parse input file (CSV/JSON)
	•	Build stable type_id mapping
	•	Generate orientation variants (remove duplicates when w==h)
	•	Implement canonical key logic
	•	Implement “add variant” operation
	•	Implement DP cell insert/dedup/trim
	•	Implement DP solver with mandatory state
	•	Implement Top-N extraction with \Delta=5
	•	Implement Case 1 pipeline
	•	Implement Case 2 pipeline (score evaluation + select W*)
	•	Implement deterministic formatting

16.2 Exporters
	•	JSON export per mandatory type (directory or single file)
	•	Excel export (summary + layout detail sheets)
(or generate CSVs if Excel library is undesired)
	•	Score-by-W export (CSV)

16.3 CLI + config
	•	CLI entry points: case1, case2
	•	YAML config loader
	•	Merge CLI overrides with config defaults

⸻

17) Recommended Output Example (Human Readable)

For a mandatory type A at W=5500:

Best: used=5499, waste=1, ratio=0.0001818
Top layouts (Δ=5mm, TopN=10):
	1.	Waste 1mm: A(w=581)x1 | B(w=588)x2 | C(h=1488)x2
	2.	Waste 1mm: A(h=1674)x1 | C(w=621)x1 | …
	3.	Waste 2mm: A(w=581)x2 | …
…

⸻

18) If You Want the Code Next

This guide fully specifies behavior. If you now say “write the code”, I will deliver:
	•	A complete Python project structure:
	•	solver.py (DP + extraction)
	•	case1.py, case2.py
	•	io.py (CSV/JSON load, JSON/Excel export)
	•	cli.py (argparse / typer)
	•	config.py (YAML)
	•	Deterministic outputs
	•	Example input templates
	•	Example run commands

No further clarification is required to implement correctly.
