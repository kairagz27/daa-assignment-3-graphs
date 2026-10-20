# Analysis: Graph Algorithms for a Campus Festival

## Implementation and reproduction

The selected language in `submission.json` is **Python**. The submission uses
Python 3.12-compatible syntax and only the standard library. The supplied
`src/Python/main.py` JSON Lines adapter is unchanged. All six implementations
and the route helper are in `src/Python/algorithms.py`. No graph library is used.
The other language directories are unchanged template alternatives and are not
selected or required for this submission.

Run all commands below from the repository root with Python 3.12 or newer:

```sh
# No build or package installation is required; syntax compilation is optional.
python -m py_compile src/Python/algorithms.py src/Python/main.py
python tools/run.py --setup
python tools/run.py --check
python tools/run.py --input tests/my_cases.jsonl
python -m unittest discover -s tests -p "test_*.py" -v
python tests/run_scale.py
python tests/benchmark.py --repeats 5
```

On Windows, `py -3` can replace `python`. To regenerate small fixtures and save
actual check logs:

```sh
python tests/make_cases.py
python tests/record_checks.py
```

`record_checks.py` checks the saved actual outputs semantically against
independent expectations. `--input` alone prints outputs without checking them.
The unmodified public checking tools are also tested by that script. GitHub
Actions runs the supplied Public checks, the own unit suite and the full-limit
suite using Python 3.12. Local measurements below used CPython 3.14.0; the
workflow result is the separate evidence for Python 3.12.

## Contracts, integer safety and state reset

A request has an independent graph. DSU objects, adjacency lists, visitation
arrays, heaps, finish orders, distances, parent IDs and result lists are created
inside each call. There is no mutable algorithm state at module scope, and no
input list is sorted or edited in place. The adapter reads one line, dispatches
it, and prints exactly one JSON object. The original `ping` response remains
`{"status":"ready"}`. Imports and algorithm calls print nothing.

Vertices are 0 through n-1; an edge ID is its original position in `edges`.
Kruskal sorts IDs rather than modifying the input; Prim stores IDs in heap
entries; DAG relaxation stores incoming edge IDs rather than predecessor
vertices. Python integer arithmetic handles the maximum forest/path magnitude
99999 * 10^9 = 99999000000000, well within signed 64 bits and beyond signed
32 bits. SCC labels and all other integer results also fit signed 64 bits.
`None` is serialized as JSON `null`; a finite distance of -1 is never confused
with unreachable. Valid-input assumptions are exactly those in the assignment.

All DFS work uses explicit stacks. `_finish_order` stores `(vertex, next_edge)`
for each suspended frame; after a child finishes it resumes at the next edge,
without rescanning earlier neighbours. Each adjacency entry is examined once.
At most n vertices are active. Neither DFS nor DSU `find` uses recursion or
changes Python's recursion limit. The SCC second pass marks a vertex before
pushing it, so duplicates cannot cause multiple pending copies of that vertex.

## 1. Disjoint-set union

**Steps.** Start with singleton roots and sizes of 1. `find` first walks to a
root and then traverses the same parent chain, setting each parent to that
root. `union` finds both roots, does nothing if they agree, and otherwise
attaches the smaller component to the larger. Decrease the component count,
add the two sizes, update the largest size, and append the post-operation state.

**Invariant and correctness.** Parent pointers form rooted trees. Each tree
contains exactly one current connectivity component, and the size at its root
is its vertex count. Initially the invariant holds for singletons. Compression
changes only the route to an existing root, preserving the partition. A union
of different roots combines exactly the components joined by the new
undirected connection, updates their correct combined size, and reduces the
count by one. Induction over operations proves each reported count and largest
size. A redundant connection or self-union changes neither value. Nonroot size
entries are not read as component sizes.

**Boundaries.** With n=0 there are no operations and the internal largest size
is 0. With n>0 the initial largest size is 1, but no initial state is emitted.
An empty operation list always produces `states=[]`.

**Complexity.** Initialization O(n); q unions O(q alpha(n)) amortized with path
compression and union by size. Total O(n + q alpha(n)) time and O(n+q) memory,
including q returned states; internal DSU memory is O(n).

## 2. Kruskal minimum spanning forest

**Steps.** Sort original IDs by weight. Start an empty forest and singleton
DSU. For each ID, select its edge exactly when `union(u,v)` merges different
roots. Add its weight to `cost`. Return the selected IDs and final DSU count.

**Invariant and correctness.** Selected edges form a forest and can be extended
to a minimum spanning forest. Initially this is immediate. An edge whose ends
already belong to one tree would create a cycle and is skipped. For an accepted
edge, consider the cut given by one current DSU component. Every lighter edge
has already been processed; a lighter edge crossing the current cut could not
have been rejected, because DSU components only merge. The selected edge is
therefore a lightest crossing edge. By the cut exchange argument, it can replace
an edge crossing the same cut in an optimal extension without increasing cost.
The invariant follows. At the end every original edge has endpoints connected
in the forest, so it spans each input component and is optimal there. The final
DSU count is exactly the input component count, and the forest has n-c edges.

**Boundaries.** Loops never merge roots. Parallel edges keep distinct original
IDs. Ties may select any optimum; negative weights require no special case.
Isolates remain DSU components. n=0 returns zero cost, zero components and no
edges. Costs use Python integers.

**Complexity.** O(n + m log(m+1)) time, including initialization, sorting and
amortized DSU operations; O(n+m) memory, including sorted IDs and output.

## 3. Prim minimum spanning forest

**Steps.** Build both directions of each non-loop edge in adjacency lists.
For each unvisited start vertex, increment the component count, visit it, and
push its incident edges into a min-heap. Pop the cheapest entry; ignore it if
its destination was already visited. Otherwise select the edge, visit the new
vertex and push its edges to unvisited neighbours. Restart when the heap empties.

**Invariant and correctness.** Within one restart, visited vertices form a tree
inside the start's connected component, and the heap contains every edge
crossing from this visited set to its unvisited remainder, possibly with stale
entries to visited vertices. Discarding stale entries cannot remove a crossing
edge. The cheapest remaining valid entry is a lightest cut edge and can be
added to an optimal tree by the cut property. It reaches a new vertex, so no
cycle forms. If the heap is empty there is no edge to an unvisited vertex in
that input component; its tree is complete. The outer loop starts exactly once
per component, including isolates. Summing its minimum component trees gives
a minimum spanning forest with n-c selected edges.

**Boundaries.** Loops are excluded before heap insertion. Parallel and tied
edges retain separate IDs; stale entries are skipped. Negative weights are
ordered correctly by the heap. Disconnected and empty graphs work through the
outer loop, which yields components=0 for n=0.

**Complexity.** This is lazy-heap Prim: each undirected non-loop edge is pushed
at most once, when its first endpoint becomes visited. O(m) entries are pushed
and popped, each O(log(m+1)); adjacency construction and the outer loop take
O(n+m). Total O(n + m log(m+1)) time and O(n+m) memory including the heap,
adjacency, visitation and selected IDs. This implementation does not claim the
indexed-heap O((n+m) log(n+1)) bound.

## 4. Kosaraju strongly connected components

**Steps.** Build the original directed graph and its transpose. Run DFS over
all vertices in the original graph, recording finish order. Process vertices
in decreasing finish order; from each still unlabelled vertex run DFS in the
transpose and assign a new label to every reached vertex. Scan original edges
and add each cross-label ordered pair once using a set.

**Invariant and correctness.** The first pass records true DFS finish times,
including in graphs with cycles. For distinct SCCs C and D with an edge C->D,
the maximum finish time in C exceeds that in D: if C is explored first it
finishes after reaching D; if D is explored first it cannot reach C and finishes
before C's later exploration. Thus a remaining SCC with largest finish time has
no incoming edge from another unassigned SCC in the original graph. In the
transpose it cannot reach another unassigned SCC. All its own vertices remain
mutually reachable after transposition, so the second-pass traversal labels
exactly that SCC. Induction labels every SCC exactly once. The final scan emits
exactly the image of original cross-component edges; the set removes duplicate
pairs and internal edges are excluded.

**Boundaries.** Duplicate edges and self-loops do not change reachability.
Isolates receive their own labels. Empty input yields two empty arrays. Labels
are consecutive nonnegative integers here, though the checker does not require
this numbering. Condensation output follows first occurrence in the input and
is not sorted, preserving the expected linear bound.

**Complexity.** Two DFS passes and the final scan visit O(n+m) data. Hash-based
pair deduplication gives expected O(n+m) time, with O(n+m) memory for graphs,
stacks, labels, finish order, the set and returned condensation. Hash operations
are expected O(1), rather than a worst-case deterministic guarantee.

## 5. DFS topological ordering

**Steps.** Run `_finish_order` over the complete graph with three states:
unvisited (0), active (1), and finished (2). An edge to an active vertex returns
failure immediately. Otherwise reverse the final finish list.

**Invariant and correctness.** Active vertices are exactly the current DFS
ancestor path. An edge u->v to an active vertex closes a directed path from v
to u, so it proves a cycle; a self-loop is included. Conversely, if a directed
cycle exists, its vertices cannot all finish without some DFS exploration
encountering an active vertex on that cycle. An edge to a finished vertex is
safe and is not treated as a cycle. If no cycle is found, for every edge u->v,
either v is first explored from u and finishes before u, or it was already
finished. Both cases put u before v in reversed finish order. Every vertex is
started once and appended once, so the output is a permutation satisfying all
precedence constraints. The outer loop includes every disconnected component.

**Boundaries.** Any cycle returns exactly `acyclic=false, order=[]`, even if a
previous component had already finished. Duplicate edges are harmless. n=0
returns true and an empty order; isolates appear once in any valid order.

**Complexity.** O(n+m) time and O(n+m) memory, including adjacency and the output.
The progress index in each suspended DFS frame prevents quadratic rescanning.

## 6. DAG shortest paths and route reconstruction

**Steps.** Build directed adjacency for a whole-graph three-state DFS cycle
check, together with outgoing original edge IDs. Reject the entire request if
any cycle is present. Otherwise initialize all distances to `None` and parents
to -1, except the source distance 0. In reverse finish order, skip unreachable
vertices and relax their outgoing edges. A strictly smaller candidate replaces
the distance and parent ID; an equal candidate keeps the previous witness.

**Invariant and correctness.** Before processing vertex u in topological order,
every predecessor has already been processed, so every possible last edge of a
source-to-u path has been considered. By induction, u's distance is the minimum
such path cost, or is `None` exactly when no such path exists. Relaxing from u
therefore correctly considers all shortest-path candidates ending with u->v.
Negative weights are valid because a DAG has no cycle and topological order,
rather than weight order, determines finalization. Vertices with no source path
are never used for arithmetic. Each assigned parent ends at the right vertex
and satisfies distance[u]+w=distance[v]. Parent traversal strictly decreases
topological position, so it cannot cycle and must end at the source. The source
cannot acquire a reachable incoming parent in a DAG, so its parent remains -1.
Checking all components before relaxation detects even unreachable cycles.

**Route helper.** `reconstruct_route(source, target, edges, parent_edge)` takes
the parent array from a successful acyclic `dag` result for that source. It
returns `[source]` for the source and `[]` for an unreachable target; these are
helper results, not new JSON tasks. For a reachable target it repeatedly follows
`edges[parent_edge[target]][0]`, collects vertices backwards and reverses once.
By the parent invariant each step is a valid incoming edge on a shortest route,
and reversal yields the correct source-to-target direction. The precondition is
a valid acyclic result; arbitrary corrupted parent arrays are not supported.

**Boundaries.** A cycle anywhere returns false and two empty arrays. Empty
edges, n=1, a nonzero source, unreachable vertices, finite -1 distances, parallel
edges and tied optimal routes are covered. `parent_edge` stores the chosen
edge's input ID even when several incoming edges share endpoints or cost.

**Complexity.** O(n+m) time and memory for adjacency, DFS, relaxation and returned
arrays. For a reachable route of L vertices the helper takes O(L) time and
O(L) space including its result. Source/unreachable calls take O(1).

## Actual route-helper calls

The following are actual calls executed and checked in
`tests/test_algorithms.py`; complete inputs and outputs are saved in
`tests/evidence/route_examples.json`.

For `E=[[0,1,3],[0,2,8],[1,2,-7],[2,3,4]]`, source 0, n=5:

```python
result = dag({"n": 5, "source": 0, "edges": E})
# distance = [0, 3, -4, 0, None]
# parent_edge = [-1, 0, 2, 3, -1]
P = result["parent_edge"]
reconstruct_route(0, 3, E, P)  # [0, 1, 2, 3]
reconstruct_route(0, 0, E, P)  # [0]
reconstruct_route(0, 4, E, P)  # []
```

The route to 3 uses IDs [0,2,3]: 0->1 (3), 1->2 (-7), 2->3 (4),
sum 0, equal to distance[3]. The source uses no edges and has cost 0.
Unreachable vertex 4 has no selected edges and distance `None`.

For `T=[[0,1,2],[0,1,2],[0,2,1],[2,1,1],[1,3,-3],[2,3,-2]]`:

```python
result = dag({"n": 5, "source": 0, "edges": T})
# distance = [0, 2, 1, -1, None]
# parent_edge = [-1, 0, 2, 5, -1]
reconstruct_route(0, 1, T, result["parent_edge"])  # [0, 1], ID [0], cost 2
reconstruct_route(0, 3, T, result["parent_edge"])  # [0, 2, 3], IDs [2,5], cost -1
reconstruct_route(0, 0, T, result["parent_edge"])  # [0], IDs [], cost 0
reconstruct_route(0, 4, T, result["parent_edge"])  # [], unreachable
```

IDs 0 and 1 are tied parallel edges. Both direct routes to vertex 1 cost 2,
as does 0->2->1 using IDs [2,3]. To vertex 3, IDs [0,4] and [2,5] both
cost -1. The tests validate directions using the exact parent IDs and sum their
weights, rather than guessing which parallel edge a vertex sequence uses.
A separate alternative witness test uses
`A=[[0,1,2],[0,1,2],[1,2,-3]]` with parent arrays [-1,0,2] and [-1,1,2].
Both helper calls `reconstruct_route(0,2,A,P)` return [0,1,2], with respective
IDs [0,2] and [1,2], both costing -1. These calls are retained in
`tests/evidence/alternative_witnesses.json`.

## Testing and independent expectations

The evidence is produced by real commands, not illustrative output:

| Check | Executed result | Evidence |
|---|---|---|
| Supplied setup | PASS, ready response | `tests/evidence/setup.txt` |
| Public cases | All 36 PASS | `tests/evidence/public_checks.txt` |
| Public persistent process | Two full batches, 72 requests PASS | Same log |
| Own fixed cases | 36 semantically correct outputs | `tests/cases.json`, `my_cases.jsonl`, `expected.jsonl`, `evidence/actual.jsonl` |
| Own unit suite | 10 test methods PASS | `tests/evidence/own_tests.txt` |
| Random tiny cases | 1200 task results PASS | Seeds and assertions in `tests/test_algorithms.py` |
| Own persistent process | 108 mixed requests in forward/reverse/forward order PASS | Unit suite |
| Full-limit suite | 15 cases PASS, n=100000, up to m/q=250000 | `tests/evidence/scale.json` |
| Route helper | Reachable, source, unreachable, tied/parallel; deep route L=100000 PASS | Route evidence and scale log |

The expected values do not come from the submitted algorithms. The fixed cases
include an English justification in `tests/cases.json`. `tests/oracles.py`
uses direct component relabelling for DSU, exhaustive feasible edge subsets for
tiny MSF instances, transitive closure for SCC, Kahn's indegree procedure for
cycle/order feasibility and synchronous Bellman-Ford for shortest distances.
Each random test uses a local deterministic RNG: 3101 DSU, 3102 forests,
3103 SCC, 3104 topo, 3105 DAG. There are 200 instances per family; each forest
instance is evaluated with both methods, giving 1200 method results. Directed
tests include both arbitrary cyclic graphs and DAGs with permuted vertex IDs.

Witnesses are checked semantically using the supplied `public_validate.check`
with independently obtained expected values. Forest witnesses must have valid,
distinct IDs, no cycle, the correct sum and component count, and span every
input component at the optimum cost. SCC labels are compared by equivalence
classes, and the condensation must contain exactly the distinct cross pairs.
Topological answers must be full permutations with all edges forward. DAG
parents must have the right endpoints, tight shortest-path weights, and chains
ending at the source. Alternative forests, labels, orders and tied/parallel
parent arrays are explicitly accepted. Duplicate forest IDs, a cyclic edge
set, merged distinct SCCs, duplicate/reversed condensation, precedence
violations, repeated vertices in orders and wrong parent edge directions are
explicitly rejected. See `evidence/alternative_witnesses.json`. A separate test
proves the independent forest certificate rejects a feasible nonoptimal tree.

`tests/generators.py` specifies the full-limit inputs reproducibly. They include
250000 unions, disconnected negative-weight forests with two large trees and
an isolate, 100000 isolates, deep SCC/topo chains, one giant SCC, 50000 SCCs,
a high-degree DFS root, late cycles, positive/negative DAG paths reaching
+/-99999000000000 and a cycle in the unreachable half of a graph. The connected
random full-limit graph is additionally verified during the benchmark.
`tests/run_scale.py` uses the real adapter and a 20-second timeout for every
case. Actual full outputs are preserved losslessly in
`tests/evidence/scale_outputs.jsonl.gz`; input/output SHA-256 values and timings
are in `scale.json`. Compressed output is evidence, not a runtime dependency.

## Kruskal-Prim benchmark

### Method and environment

Measurements were actually taken on 2026-10-20. Environment:

- AMD Ryzen 7 7735HS with Radeon Graphics, 8 physical cores, 16 logical processors.
- 16 GB installed RAM; Windows reports 16369225728 usable bytes (15.25 GiB).
- Windows x86-64, CPython 3.14.0, ordinary single-threaded Python calls.
- Timer: `time.perf_counter_ns()` (Windows QueryPerformanceCounter); nanoseconds
  converted to milliseconds. Full runtime/platform/timer metadata is in
  `tests/evidence/benchmark.json`; hardware is in `environment.json`.

Reproduction command: `python tests/benchmark.py --repeats 5`.
For n=1000,10000,100000 use m=2500,25000,250000 and seed=3300+n.
`random_connected` first connects each vertex v>0 to a uniformly sampled earlier
vertex, with an integer weight sampled uniformly from [-10^9,10^9]. It then adds
random endpoint pairs with the same weight distribution until there are m
edges and shuffles the edge list. Parallel edges and self-loops are possible.
The graph is connected by construction; the stored graph hash identifies the
exact input order. Both methods receive the same in-memory edge list, unchanged.

Before timing, both returned forests are checked independently by
`certify_forest`. It builds the selected forest, checks distinct IDs,
acyclicity, correct sum and spanning, then uses binary lifting to find the
maximum edge on every input edge's tree path. A forest is optimal exactly when
every non-loop input edge has weight at least that path maximum: otherwise an
exchange improves it; conversely this condition certifies the spanning trees'
minimum weight by the cycle/exchange property. This is independent of either
measured implementation. Costs and witnesses are validated before measuring;
every warm-up and timed result is validated outside its timed interval too.

After initial validation calls, there is one additional untimed warm-up per
method per size. Each method has five measured runs. Order alternates:
Kruskal then Prim in even-numbered repetitions, reversed in odd ones. Garbage
collection is requested before each timer starts and remains enabled during
the call. The interval includes the full algorithm function call, internal
DSU/adjacency/sort/heap construction and result allocation. Input graph
generation, JSON parsing/serialization, process startup, imports, validation,
output printing and result disposal after the call are excluded for both
methods. There is no compilation in the interval. This is a function benchmark,
not a measurement of end-to-end JSON Lines throughput.

### Measured results

All times below are milliseconds. Each median is the middle of the five raw
values, calculated without rounding the raw measurements first.

| n | m | Seed | Kruskal: five runs (ms) | Median (ms) | Prim: five runs (ms) | Median (ms) |
|---:|---:|---:|---|---:|---|---:|
| 1000 | 2500 | 4300 | 6.2550, 4.4077, 2.9665, 2.9790, 3.3794 | 3.3794 | 11.5672, 7.0941, 6.9013, 5.0033, 4.1866 | 6.9013 |
| 10000 | 25000 | 13300 | 35.3740, 36.4712, 32.4733, 30.0874, 29.7427 | 32.4733 | 67.2779, 62.9633, 64.3655, 67.0153, 63.3572 | 64.3655 |
| 100000 | 250000 | 103300 | 501.5255, 490.2850, 526.6824, 522.4590, 517.6753 | 517.6753 | 1306.9557, 1271.0618, 1273.9131, 1261.8185, 1340.8454 | 1273.9131 |

Every benchmark graph has components=1 and n-1 selected edges. Independently
certified costs are -512023677965, -5310914843101 and -53339690907812 for the
three increasing sizes. All graph SHA-256 values, raw timings and exact medians
are saved in `tests/evidence/benchmark.json`.

### Observations and limitations

Kruskal was faster in this measured family at every size. Prim/Kruskal median
ratios were 2.04, 1.98 and 2.46. Kruskal performs one optimized Python
sort plus DSU operations; this Prim implementation builds tuple adjacency lists
and performs many heap pushes/pops, including stale entries. Those operations
and allocations plausibly explain the larger constant cost here. This is an
implementation-level interpretation, not a universal ranking of MST methods.

Both implementations have O(n + m log(m+1)) time and O(n+m) memory, as established
above independently of measurements. With m about 2.5n, growth should roughly
follow n log n, but constants, cache effects, allocation and scheduling influence
the observed ratios. Timing data alone does not prove an asymptotic bound.

The generator covers one connected sparse family and one seed per size. The
initial random recursive tree affects its structure; these are not uniformly
sampled connected graphs. Five repetitions on one laptop cannot establish
performance for dense graphs, all weight distributions or other runtimes.
Small-graph variation includes clock/scheduling and CPU-frequency effects;
we retain every value and report medians without discarding outliers. Internal
adjacency construction is included for Prim, which is part of its real request
cost. This comparison does not isolate prebuilt-data-structure kernels or claim
that one method is always faster. The scale suite separately covers disconnected
graphs, isolates and adversarial deep traversals.

## Sources and AI assistance

The assignment's supplied README, PDF, JSON adapter, public cases and checking
tools are the specification and test infrastructure. Source:
https://github.com/RZhaniya/daa-assignment-3-graphs . The template's adapter and
public checking tools were retained; no prewritten graph algorithm library was
used. The Python standard library provides lists, sorting, sets, `heapq`, JSON,
random generation, timers and unit testing.

**AI disclosure:** OpenAI Codex assisted with implementing all six algorithms
and the route helper, designing independent tests and the forest certificate,
running checks and benchmarks, and writing this analysis. The correctness
arguments and measurements were checked by the automated commands and
independent oracles described above. These are automated verification results;
this report does not claim that the student independently authored or manually
verified the AI-generated work. The submitting student should review and
understand it and apply the course syllabus's academic-integrity rules.
Only executed tests and actual measurements are reported. The separate Moodle
quiz and final grade are not part of these program checks.
