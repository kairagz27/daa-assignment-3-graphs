"""Compare both MSF implementations on the identical seeded graph objects."""
import argparse
import gc
import hashlib
import json
import os
from pathlib import Path
import platform
import statistics
import sys
from time import get_clock_info, perf_counter_ns

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src' / 'Python'))
import algorithms
from generators import random_connected
from oracles import certify_forest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repeats', type=int, default=5)
    args = parser.parse_args()
    if args.repeats < 3:
        parser.error('at least three timings per method are required')
    rows = []
    for n, m in ((1000, 2500), (10000, 25000), (100000, 250000)):
        seed = 3300 + n
        edges = random_connected(n, m, seed)
        fingerprint = hashlib.sha256(json.dumps(edges, separators=(',', ':')).encode()).hexdigest()
        request = {'n': n, 'edges': edges}
        # Validate both forests independently before any timing.
        expected_cost = None
        for method in (algorithms.kruskal, algorithms.prim):
            answer = method(request)
            certify_forest(request, answer)
            if expected_cost is None:
                expected_cost = answer['cost']
            assert answer['cost'] == expected_cost and answer['components'] == 1
        # One additional, untimed warm-up per method on this same graph.
        for method in (algorithms.kruskal, algorithms.prim):
            answer = method(request)
            certify_forest(request, answer)
        del answer
        timings = {'kruskal': [], 'prim': []}
        for repetition in range(args.repeats):
            names = ('kruskal', 'prim') if repetition % 2 == 0 else ('prim', 'kruskal')
            for name in names:
                method = getattr(algorithms, name)
                gc.collect()  # Outside timing; GC remains enabled during calls.
                started = perf_counter_ns()
                answer = method(request)
                elapsed_ns = perf_counter_ns() - started
                timings[name].append(elapsed_ns / 1e6)
                assert answer['cost'] == expected_cost and answer['components'] == 1
                certify_forest(request, answer)  # Outside timing, for every run.
                del answer
        assert hashlib.sha256(json.dumps(edges, separators=(',', ':')).encode()).hexdigest() == fingerprint
        row = {'n': n, 'm': m, 'seed': seed, 'graph_sha256': fingerprint, 'verified_cost': expected_cost,
               'components': 1, 'milliseconds': timings,
               'median_ms': {name: statistics.median(values) for name, values in timings.items()}}
        rows.append(row)
        print(json.dumps(row), flush=True)
    clock = get_clock_info('perf_counter')
    result = {'runtime': sys.version, 'platform': platform.platform(), 'processor': platform.processor(),
              'logical_cpu_count': os.cpu_count(), 'timer': 'time.perf_counter_ns',
              'timer_implementation': clock.implementation, 'timer_resolution_seconds': clock.resolution,
              'gc_enabled': gc.isenabled(), 'repeats': args.repeats,
              'warmup': 'One extra untimed call per method per size, after independent pre-validation calls.',
              'timing_boundary': 'Algorithm function call: includes internal adjacency/DSU/sort/heap construction and result allocation; excludes input graph generation, JSON parsing/serialization, imports, process startup, validation and output; no compilation.',
              'rows': rows}
    evidence = ROOT / 'tests' / 'evidence'
    evidence.mkdir(exist_ok=True)
    (evidence / 'benchmark.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
