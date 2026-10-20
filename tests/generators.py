"""Reproducible graph generator shared by benchmark and scale checks."""
import random


def random_connected(n, m, seed):
    rng = random.Random(seed)
    edges = [[v, rng.randrange(v), rng.randint(-10**9, 10**9)] for v in range(1, n)]
    while len(edges) < m:
        edges.append([rng.randrange(n), rng.randrange(n), rng.randint(-10**9, 10**9)])
    rng.shuffle(edges)
    return edges


def scale_cases():
    n, m = 100000, 250000
    operations = [[v - 1, v] for v in range(1, n)]
    operations.extend([[i % n, (i % n if i % 2 else 0)] for i in range(m - len(operations))])
    states = [[n - i - 1, i + 2] for i in range(n - 1)] + [[1, n] for _ in range(m - n + 1)]
    yield 'dsu_full_operations', {'task': 'dsu', 'n': n, 'operations': operations}, {'states': states}
    del operations, states

    rng = random.Random(3201)
    edges = [[v, v + 1, -10**9] for v in range(49999)]
    edges += [[v, v + 1, -10**9] for v in range(50000, n - 2)]
    while len(edges) < m:
        low, high = (0, 50000) if len(edges) % 2 else (50000, n - 1)
        edges.append([rng.randrange(low, high), rng.randrange(low, high), rng.randint(0, 10**9)])
    rng.shuffle(edges)
    for task in ('kruskal', 'prim'):
        yield task + '_full_disconnected', {'task': task, 'n': n, 'edges': edges}, {'cost': -99997 * 10**9, 'components': 3}
        yield task + '_full_isolates', {'task': task, 'n': n, 'edges': []}, {'cost': 0, 'components': n}
    del edges

    chain = [[v, v + 1] for v in range(n - 1)]
    forward = chain + [[i % (n - 1), i % (n - 1) + 1] for i in range(m - n + 1)]
    yield 'scc_full_deep_chain', {'task': 'scc', 'n': n, 'edges': forward}, {'component': list(range(n))}
    yield 'topo_full_deep_chain', {'task': 'topo', 'n': n, 'edges': forward}, {'acyclic': True}
    del chain, forward

    edges = [[v, (v + 1) % n] for v in range(n)]
    edges += [[rng.randrange(n), rng.randrange(n)] for _ in range(m - n)]
    yield 'scc_full_giant_ring', {'task': 'scc', 'n': n, 'edges': edges}, {'component': [0] * n}
    del edges

    edges = [[v, v ^ 1] for v in range(n)] + [[v, v + 2] for v in range(0, n - 2, 2)]
    edges += [edges[i % len(edges)] for i in range(m - len(edges))]
    yield 'scc_full_many_components', {'task': 'scc', 'n': n, 'edges': edges}, {'component': [v // 2 for v in range(n)]}
    del edges

    edges = [[0, v] for v in range(1, n)]
    edges += [[0, i % (n - 1) + 1] for i in range(m - len(edges))]
    yield 'topo_full_high_degree', {'task': 'topo', 'n': n, 'edges': edges}, {'acyclic': True}
    edges[-2:] = [[n - 2, n - 1], [n - 1, n - 2]]
    yield 'topo_full_late_cycle', {'task': 'topo', 'n': n, 'edges': edges}, {'acyclic': False}
    del edges

    for weight in (-10**9, 10**9):
        edges = [[v, v + 1, weight] for v in range(n - 1)]
        edges += [[i % (n - 1), i % (n - 1) + 1, weight] for i in range(m - len(edges))]
        yield 'dag_full_chain_' + str(weight), {'task': 'dag', 'n': n, 'source': 0, 'edges': edges}, {
            'acyclic': True, 'distance': [v * weight for v in range(n)]}
        del edges

    edges = [[v, v + 1, 1] for v in range(n - 1) if v != n // 2 - 1]
    edges.append([n - 1, n // 2, 0])
    edges += [[0, 1, 1] for _ in range(m - len(edges))]
    yield 'dag_full_unreachable_cycle', {'task': 'dag', 'n': n, 'source': 0, 'edges': edges}, {'acyclic': False}
    yield 'dag_full_isolates', {'task': 'dag', 'n': n, 'source': n - 1, 'edges': []}, {
        'acyclic': True, 'distance': [None] * (n - 1) + [0]}
