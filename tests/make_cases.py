"""Own fixtures with independent reasoning; materialize as JSON/JSON Lines."""
import json
from pathlib import Path

from oracles import reference


def cases():
    result = []

    def add(name, request, reason):
        result.append({'name': name, 'input': request,
                       'expected': reference(request), 'justification': reason})

    add('transport ping', {'task': 'ping'}, 'The supplied transport contract returns ready.')
    for task in ('dsu', 'kruskal', 'prim', 'scc', 'topo'):
        key = 'operations' if task == 'dsu' else 'edges'
        add(task + ' empty', {'task': task, 'n': 0, key: []},
            'No vertices, edges or operations; all arrays are empty, forest cost and component count are zero.')
    add('DSU balanced and redundant merges', {'task': 'dsu', 'n': 8, 'operations': [
        [0, 1], [2, 3], [0, 2], [4, 5], [6, 7], [4, 6], [0, 4], [7, 1], [3, 3]]},
        'Component sizes progress 2,2,4,4,4,4,8,8,8; counts 7,6,5,4,3,2,1,1,1. Relabelling is an independent oracle.')
    add('DSU singleton self unions', {'task': 'dsu', 'n': 1, 'operations': [[0, 0], [0, 0]]},
        'Both states are [1,1]; a self union changes nothing.')
    add('DSU no operations', {'task': 'dsu', 'n': 4, 'operations': []},
        'Only post-operation states are output, so the answer is empty.')
    forests = [
        ('isolates', 5, [], 'Five isolated vertices; zero selected edges and zero cost.'),
        ('ties and parallel', 4, [[0, 1, 2], [0, 1, 2], [1, 2, 2], [0, 2, 2], [2, 2, -99]],
         'The triangle needs two edges of weight 2; vertex 3 is isolated; cost 4, components 2. Negative loop is unusable.'),
        ('disconnected negative', 7, [[0, 1, -4], [0, 1, 8], [1, 2, 3], [0, 2, 1], [3, 4, -9], [5, 5, -100]],
         'On {0,1,2} choose -4 and 1, on {3,4} choose -9; 5 and 6 are isolates. Cost -12, components 4.'),
        ('positive 64 bit', 5, [[0, 1, 1000000000], [1, 2, 1000000000], [2, 3, 1000000000], [3, 4, 1000000000]],
         'This tree is the only spanning tree; cost 4000000000 exceeds signed 32 bits.'),
        ('negative 64 bit', 5, [[0, 1, -1000000000], [1, 2, -1000000000], [2, 3, -1000000000], [3, 4, -1000000000]],
         'The unique tree has cost -4000000000, below signed 32 bits.'),
        ('loops only', 2, [[0, 0, -8], [1, 1, 7]], 'Both vertices remain isolated; no loop can enter a forest.'),
    ]
    for task in ('kruskal', 'prim'):
        for name, n, edges, reason in forests:
            add(task + ' ' + name, {'task': task, 'n': n, 'edges': edges},
                reason + ' The oracle also exhaustively enumerates every feasible subset.')
    add('SCC duplicate condensation and isolates', {'task': 'scc', 'n': 7, 'edges': [
        [0, 1], [1, 0], [1, 2], [0, 2], [0, 2], [2, 3], [3, 2], [3, 4], [4, 4], [5, 5]]},
        'Mutual reachability gives {0,1},{2,3},{4},{5},{6}; only the first-to-second and second-to-third cross pairs exist.')
    add('SCC one giant component', {'task': 'scc', 'n': 4, 'edges': [[0, 1], [1, 2], [2, 3], [3, 0]]},
        'Every vertex reaches every other around the directed ring; condensation is empty.')
    add('SCC all isolates', {'task': 'scc', 'n': 5, 'edges': []},
        'Reflexive reachability only; all five SCCs are distinct.')
    add('topo finished vertex is safe', {'task': 'topo', 'n': 5, 'edges': [[0, 1], [0, 2], [2, 1], [2, 1]]},
        'Precedence 0 before 2 before 1; 3 and 4 unconstrained. DFS edge 2->1 reaches an already finished vertex.')
    add('topo disconnected cycle', {'task': 'topo', 'n': 5, 'edges': [[0, 1], [2, 3], [3, 2]]},
        'The separate cycle 2->3->2 forbids any whole-graph topological order.')
    add('topo self loop', {'task': 'topo', 'n': 1, 'edges': [[0, 0]]},
        'A self loop is a directed cycle.')
    add('topo isolates', {'task': 'topo', 'n': 5, 'edges': []},
        'Any permutation of all five vertices is valid.')
    add('DAG route example', {'task': 'dag', 'n': 5, 'source': 0, 'edges': [[0, 1, 3], [0, 2, 8], [1, 2, -7], [2, 3, 4]]},
        'Shortest distances are [0,3,-4,0,null]; route to 3 uses IDs [0,2,3], with sum 3-7+4=0.')
    add('DAG tied parallel routes', {'task': 'dag', 'n': 5, 'source': 0, 'edges': [[0, 1, 2], [0, 1, 2], [0, 2, 1], [2, 1, 1], [1, 3, -3], [2, 3, -2]]},
        'Distances [0,2,1,-1,null]; IDs 0 or 1 or path [2,3] reach 1 optimally; 3 has two equal shortest routes.')
    add('DAG nonzero source and unreachable', {'task': 'dag', 'n': 5, 'source': 3, 'edges': [[0, 1, -8], [3, 2, -1], [2, 4, 0]]},
        'Distances [null,null,-1,0,-1]; never relax the unreachable negative edge 0->1.')
    add('DAG cycle outside reachability', {'task': 'dag', 'n': 5, 'source': 0, 'edges': [[0, 1, 2], [3, 4, -1], [4, 3, 1]]},
        'The unreachable cycle 3->4->3 still requires false and empty result arrays.')
    add('DAG unreachable self loop', {'task': 'dag', 'n': 2, 'source': 0, 'edges': [[1, 1, -1]]},
        'Even an unreachable self loop invalidates the whole graph.')
    add('DAG singleton', {'task': 'dag', 'n': 1, 'source': 0, 'edges': []},
        'The only distance is zero; source parent is -1 and route is [0].')
    for weight in (-1000000000, 1000000000):
        add('DAG 64 bit ' + str(weight), {'task': 'dag', 'n': 5, 'source': 0,
            'edges': [[u, u + 1, weight] for u in range(4)]},
            'The unique path to vertex v has v edges and weight v*w; the last distance is +/-4000000000.')
    return result


if __name__ == '__main__':
    folder = Path(__file__).resolve().parent
    fixtures = cases()
    (folder / 'cases.json').write_text(json.dumps(fixtures, indent=2) + '\n', encoding='utf-8')
    (folder / 'my_cases.jsonl').write_text(''.join(json.dumps(case['input']) + '\n' for case in fixtures), encoding='utf-8')
    (folder / 'expected.jsonl').write_text(''.join(json.dumps(case['expected']) + '\n' for case in fixtures), encoding='utf-8')
    print(f'Wrote {len(fixtures)} independently justified cases.')
