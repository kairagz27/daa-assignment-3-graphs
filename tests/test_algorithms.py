"""Semantic tests, independent random oracles and route reconstruction tests."""
import copy
import json
from pathlib import Path
import random
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src' / 'Python'))
sys.path.insert(0, str(ROOT / 'tools'))
import algorithms
from main import handle
from public_validate import check
from make_cases import cases
from oracles import certify_forest, reference


class GraphTests(unittest.TestCase):
    def assert_valid(self, request, answer=None):
        if answer is None:
            before = copy.deepcopy(request)
            answer = handle(request)
            self.assertEqual(request, before, 'input must not be mutated')
        self.assertTrue(check(request, answer, reference(request)), (request, answer))
        return answer

    def test_own_fixed_cases(self):
        for case in cases():
            with self.subTest(case=case['name']):
                self.assert_valid(case['input'])

    def test_repeated_mixed_requests_in_one_real_process(self):
        requests = [case['input'] for case in cases()]
        batch = requests + list(reversed(requests)) + requests
        process = subprocess.run(
            [sys.executable, str(ROOT / 'src' / 'Python' / 'main.py')],
            input=''.join(json.dumps(request) + '\n' for request in batch),
            text=True, encoding='utf-8', capture_output=True, timeout=20, check=True,
        )
        self.assertEqual(process.stderr, '')
        lines = process.stdout.splitlines()
        self.assertEqual(len(lines), len(batch))
        for request, line in zip(batch, lines):
            self.assert_valid(request, json.loads(line))

    def test_random_dsu_relabelling(self):
        rng = random.Random(3101)
        for _ in range(200):
            n = rng.randrange(9)
            operations = [[rng.randrange(n), rng.randrange(n)] for _ in range(30)] if n else []
            self.assert_valid({'task': 'dsu', 'n': n, 'operations': operations})

    def test_random_forests_exhaustive_subsets(self):
        rng = random.Random(3102)
        for _ in range(200):
            n = rng.randrange(7)
            edges = [[rng.randrange(n), rng.randrange(n), rng.randrange(-4, 5)] for _ in range(rng.randrange(11))] if n else []
            request = {'task': 'kruskal', 'n': n, 'edges': edges}
            kruskal = self.assert_valid(request)
            request = dict(request, task='prim')
            prim = self.assert_valid(request)
            self.assertEqual((kruskal['cost'], kruskal['components']), (prim['cost'], prim['components']))
            certify_forest(request, kruskal)
            certify_forest(request, prim)

    def test_random_scc_transitive_closure(self):
        rng = random.Random(3103)
        for _ in range(200):
            n = rng.randrange(9)
            edges = [[rng.randrange(n), rng.randrange(n)] for _ in range(20)] if n else []
            self.assert_valid({'task': 'scc', 'n': n, 'edges': edges})

    def test_random_topo_kahn(self):
        rng = random.Random(3104)
        for iteration in range(200):
            n = rng.randrange(9)
            edges = [[rng.randrange(n), rng.randrange(n)] for _ in range(15)] if n else []
            if iteration % 2:
                permutation = rng.sample(range(n), n)
                edges = [[permutation[u], permutation[v]] for u, v in edges if u < v]
            self.assert_valid({'task': 'topo', 'n': n, 'edges': edges})

    def test_random_dag_bellman_ford(self):
        rng = random.Random(3105)
        for iteration in range(200):
            n = rng.randrange(1, 9)
            edges = [[rng.randrange(n), rng.randrange(n), rng.randrange(-10, 11)] for _ in range(18)]
            if iteration % 2:
                permutation = rng.sample(range(n), n)
                edges = [[permutation[u], permutation[v], w] for u, v, w in edges if u < v]
            request = {'task': 'dag', 'n': n, 'edges': edges, 'source': rng.randrange(n)}
            answer = self.assert_valid(request)
            if answer['acyclic']:
                for target in range(n):
                    self.verify_route(request, answer, target)

    def verify_route(self, request, answer, target):
        source, edges = request['source'], request['edges']
        route = algorithms.reconstruct_route(source, target, edges, answer['parent_edge'])
        if answer['distance'][target] is None:
            self.assertEqual(route, [])
            return {'target': target, 'route': route, 'edge_ids': [], 'cost': None}
        self.assertEqual((route[0], route[-1]), (source, target))
        self.assertEqual(len(route), len(set(route)))
        ids = [answer['parent_edge'][v] for v in route[1:]]
        for u, v, edge_id in zip(route, route[1:], ids):
            self.assertEqual(edges[edge_id][:2], [u, v])
        cost = sum(edges[i][2] for i in ids)
        self.assertEqual(cost, answer['distance'][target])
        return {'target': target, 'route': route, 'edge_ids': ids, 'cost': cost}

    def test_route_helper_required_calls(self):
        records = []
        for case in cases():
            if case['name'] in ('DAG route example', 'DAG tied parallel routes'):
                request = case['input']
                answer = handle(request)
                calls = [self.verify_route(request, answer, target) for target in (3, 0, 4, 1)]
                records.append({'case': case['name'], 'input': request, 'result': answer, 'calls': calls})
        path = ROOT / 'tests' / 'evidence' / 'route_examples.json'
        path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps(records, indent=2) + '\n', encoding='utf-8')

    def test_semantic_check_accepts_alternatives_rejects_bad_witnesses(self):
        trials = [
            ({'task': 'kruskal', 'n': 3, 'edges': [[0, 1, 1], [1, 2, 1], [0, 2, 1]]},
             [{'cost': 2, 'components': 1, 'edge_ids': [0, 1]}, {'cost': 2, 'components': 1, 'edge_ids': [2, 1]}],
             [{'cost': 2, 'components': 1, 'edge_ids': [0, 0]}, {'cost': 2, 'components': 1, 'edge_ids': [0, 1, 2]}]),
            ({'task': 'prim', 'n': 3, 'edges': [[0, 1, 1], [1, 2, 1], [0, 2, 1]]},
             [{'cost': 2, 'components': 1, 'edge_ids': [0, 1]}, {'cost': 2, 'components': 1, 'edge_ids': [2, 1]}],
             [{'cost': 2, 'components': 1, 'edge_ids': [2, 2]}]),
            ({'task': 'scc', 'n': 3, 'edges': [[0, 1], [1, 0], [1, 2], [0, 2]]},
             [{'component': [0, 0, 1], 'condensation': [[0, 1]]}, {'component': [9, 9, 4], 'condensation': [[9, 4]]}],
             [{'component': [0, 0, 1], 'condensation': [[0, 1], [0, 1]]},
              {'component': [0, 0, 0], 'condensation': []}, {'component': [0, 0, 1], 'condensation': [[1, 0]]}]),
            ({'task': 'topo', 'n': 3, 'edges': [[0, 2], [1, 2]]},
             [{'acyclic': True, 'order': [0, 1, 2]}, {'acyclic': True, 'order': [1, 0, 2]}],
             [{'acyclic': True, 'order': [2, 0, 1]}, {'acyclic': True, 'order': [0, 0, 2]}]),
            ({'task': 'dag', 'n': 3, 'source': 0, 'edges': [[0, 1, 2], [0, 1, 2], [1, 2, -3]]},
             [{'acyclic': True, 'distance': [0, 2, -1], 'parent_edge': [-1, 0, 2]},
              {'acyclic': True, 'distance': [0, 2, -1], 'parent_edge': [-1, 1, 2]}],
             [{'acyclic': True, 'distance': [0, 2, -1], 'parent_edge': [-1, 2, 0]},
              {'acyclic': True, 'distance': [0, 2, -1], 'parent_edge': [-1, 0, 1]}]),
        ]
        records = []
        for request, good, bad in trials:
            expected = reference(request)
            for answer in good:
                self.assertTrue(check(request, answer, expected), answer)
                if request['task'] == 'dag':
                    self.verify_route(request, answer, 2)
            for answer in bad:
                self.assertFalse(check(request, answer, expected), answer)
            record = {'input': request, 'accepted': good, 'rejected': bad}
            if request['task'] == 'dag':
                record['route_calls'] = [self.verify_route(request, answer, 2) for answer in good]
            records.append(record)
        path = ROOT / 'tests' / 'evidence' / 'alternative_witnesses.json'
        path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps(records, indent=2) + '\n', encoding='utf-8')

    def test_independent_forest_certificate_rejects_nonoptimal_tree(self):
        request = {'task': 'kruskal', 'n': 3, 'edges': [[0, 1, -5], [1, 2, -4], [0, 2, 8]]}
        certify_forest(request, {'cost': -9, 'components': 1, 'edge_ids': [0, 1]})
        with self.assertRaises(AssertionError):
            certify_forest(request, {'cost': 3, 'components': 1, 'edge_ids': [0, 2]})
        with self.assertRaises(AssertionError):
            certify_forest(request, {'cost': -10, 'components': 1, 'edge_ids': [0, 0]})


if __name__ == '__main__':
    unittest.main(verbosity=2)
