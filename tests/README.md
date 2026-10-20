# Own tests and reproducible evidence

Use Python 3.12+ from the repository root. There are no third-party dependencies.

```sh
python tests/make_cases.py
python tests/record_checks.py
python -m unittest discover -s tests -p "test_*.py" -v
python tests/run_scale.py
python tests/benchmark.py --repeats 5
```

On Windows use `py -3` instead of `python` if necessary. The supplied launcher
also supports `python tools/run.py --input tests/my_cases.jsonl`. The full
commands, algorithms, correctness arguments and benchmark are in `ANALYSIS.md`.

## Inputs, expectations and actual results

- `cases.json`: 36 own small fixtures, each with an English justification and
  independently computed expected values. `make_cases.py` creates this file.
- `my_cases.jsonl`: the same inputs in the supplied adapter's request format.
- `expected.jsonl`: one semantic expectation per input. For non-unique answers
  it intentionally omits arbitrary witnesses, such as forest edge IDs, label
  numbering, topological order or parent choices. It is not a literal-output
  golden file. Compare actual outputs using the semantic checker.
- `evidence/actual.jsonl`: real stdout from `tools/run.py --input`, checked
  semantically by `record_checks.py` against independent oracles.
- `evidence/commands.json`, `setup.txt`, `public_checks.txt`, `own_tests.txt`,
  `checker_tools.txt`: executed commands and their actual saved check logs.
- `evidence/route_examples.json`: actual helper calls, returned vertex routes,
  original edge IDs and checked weights, including source and unreachable calls.
- `evidence/alternative_witnesses.json`: explicitly accepted alternative forests,
  SCC labels, topological orders and parent IDs, with explicitly rejected
  invalid witnesses; also helper calls using distinct parallel-edge IDs.

## Independent verification

`oracles.py` uses component relabelling, exhaustive edge subsets, transitive
closure, Kahn's algorithm and synchronous Bellman-Ford for tiny reference
values. It does not call submitted algorithms to obtain those expectations.
`test_algorithms.py` compares semantic results on 200 random cases per family
with seeds 3101 through 3105. Both MST methods are tested per forest case:
1200 task results in total. It also tests all fixed cases, required helper
calls, alternative/invalid witnesses, input immutability, and 108 mixed requests
in one real adapter process (forward/reverse/forward fixture batches).

The scalable `certify_forest` verifier independently checks distinct IDs,
acyclicity, edge weights, complete spanning, component count and optimality.
Binary lifting finds maximum weights on tree paths; an input edge lighter than
that maximum invalidates optimality. Tests show this certificate rejects a
feasible but nonoptimal tree as well as repeated IDs. Benchmark outputs are not
accepted merely because Kruskal and Prim agree.

## Full limits

`generators.py:scale_cases` reproducibly generates 15 maximum-vertex inputs,
including maximum operation/edge counts. Independent expectations are derived
from the constructions (chains, rings, pairs, stars and two separate trees).
`run_scale.py` invokes the real JSON Lines program, checks semantic answers and
MSF certificates, and applies a 20-second process timeout to every case.

`evidence/scale.json` records counts, pass results, real process/JSON-I/O times
and input/output SHA-256 values. All actual output arrays are retained in
`evidence/scale_outputs.jsonl.gz`, one JSON object with `name` and `output` per
line. Read without extracting to disk:

```python
import gzip, json
with gzip.open('tests/evidence/scale_outputs.jsonl.gz', 'rt', encoding='utf-8') as f:
    for line in f:
        result = json.loads(line)
        print(result['name'], result['output'].keys())
```

The compressed evidence is not imported by the submitted program. The helper's
100000-vertex route is also checked on both positive and negative deep chains.

## Benchmark

`generators.py:random_connected` generates identical graph objects for both
methods at (n,m)=(1000,2500),(10000,25000),(100000,250000), seeds 4300,13300,103300.
`benchmark.py` validates each forest independently, warms each method up,
records five real timings per method and size, and computes medians.
`evidence/benchmark.json` stores raw measurements, environment, timer and input
fingerprints; `environment.json` contains the measured CPU and RAM details.
See `ANALYSIS.md` for timing boundaries, interpretation and limitations.
