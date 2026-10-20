"""Independent small-input oracles and a scalable MSF optimality certificate."""

from collections import deque
from itertools import combinations


def connected_labels(n, edges):
    adjacency = [[] for _ in range(n)]
    for edge in edges:
        u, v = edge[:2]
        adjacency[u].append(v)
        adjacency[v].append(u)
    labels = [-1] * n
    count = 0
    for start in range(n):
        if labels[start] != -1:
            continue
        labels[start] = count
        queue = deque([start])
        while queue:
            for v in adjacency[queue.popleft()]:
                if labels[v] == -1:
                    labels[v] = count
                    queue.append(v)
        count += 1
    return labels, count


def kahn_order(n, edges):
    adjacency = [[] for _ in range(n)]
    indegree = [0] * n
    for edge in edges:
        u, v = edge[:2]
        adjacency[u].append(v)
        indegree[v] += 1
    queue = deque(v for v in range(n) if indegree[v] == 0)
    order = []
    while queue:
        u = queue.popleft()
        order.append(u)
        for v in adjacency[u]:
            indegree[v] -= 1
            if indegree[v] == 0:
                queue.append(v)
    return order if len(order) == n else None


def reference(request):
    """Use relabelling, exhaustive subsets, closure, Kahn or Bellman-Ford.

    These are deliberately different from the submitted algorithms. Only use
    this oracle on tiny inputs; full-limit MSF checks use certify_forest().
    """
    task = request['task']
    if task == 'ping':
        return {'status': 'ready'}
    n = request['n']
    if task == 'dsu':
        labels = list(range(n))
        states = []
        for u, v in request['operations']:
            old, new = labels[v], labels[u]
            labels = [new if label == old else label for label in labels]
            states.append([len(set(labels)), max((labels.count(x) for x in set(labels)), default=0)])
        return {'states': states}
    edges = request['edges']
    if task in ('kruskal', 'prim'):
        _, count = connected_labels(n, edges)
        best = None
        for ids in combinations(range(len(edges)), n - count):
            chosen = [edges[i] for i in ids]
            if connected_labels(n, chosen)[1] == count:
                cost = sum(edge[2] for edge in chosen)
                if best is None or cost < best:
                    best = cost
        assert best is not None
        return {'cost': best, 'components': count}
    if task == 'scc':
        reach = [[u == v for v in range(n)] for u in range(n)]
        for u, v in edges:
            reach[u][v] = True
        for k in range(n):
            for u in range(n):
                for v in range(n):
                    reach[u][v] |= reach[u][k] and reach[k][v]
        labels = [min(v for v in range(n) if reach[u][v] and reach[v][u]) for u in range(n)]
        return {'component': labels}
    order = kahn_order(n, edges)
    if task == 'topo':
        return {'acyclic': order is not None}
    if task == 'dag':
        if order is None:
            return {'acyclic': False}
        distance = [None] * n
        distance[request['source']] = 0
        # Synchronous Bellman-Ford: iteration k covers paths of <= k edges.
        for _ in range(n - 1):
            previous = distance
            distance = previous.copy()
            for u, v, weight in edges:
                if previous[u] is not None:
                    candidate = previous[u] + weight
                    if distance[v] is None or candidate < distance[v]:
                        distance[v] = candidate
            if distance == previous:
                break
        return {'acyclic': True, 'distance': distance}
    raise ValueError(task)


def certify_forest(request, answer):
    """Check feasibility and optimality without running Kruskal or Prim.

    A spanning forest is optimal iff each non-loop input edge has weight at
    least the maximum weight on its tree path. Otherwise exchanging the
    heavier tree edge improves the forest. Binary lifting checks every edge
    in O(log n) time after O(n log n) preprocessing. Negative weights are safe.
    """
    n, edges = request['n'], request['edges']
    ids = answer['edge_ids']
    assert len(ids) == len(set(ids)), 'repeated edge ID'
    assert all(type(i) is int and 0 <= i < len(edges) for i in ids)
    assert sum(edges[i][2] for i in ids) == answer['cost'], 'incorrect sum'
    adjacency = [[] for _ in range(n)]
    for i in ids:
        u, v, weight = edges[i]
        assert u != v, 'selected self-loop'
        adjacency[u].append((v, weight, i))
        adjacency[v].append((u, weight, i))
    depth = [-1] * n
    labels = [-1] * n
    parent = list(range(n))
    negative_infinity = float('-inf')
    maximum = [negative_infinity] * n
    count = 0
    for root in range(n):
        if depth[root] != -1:
            continue
        depth[root] = 0
        labels[root] = count
        stack = [(root, -1)]
        while stack:
            u, incoming_id = stack.pop()
            for v, weight, edge_id in adjacency[u]:
                if edge_id == incoming_id:
                    continue
                assert depth[v] == -1, 'selected cycle'
                depth[v] = depth[u] + 1
                labels[v] = count
                parent[v] = u
                maximum[v] = weight
                stack.append((v, edge_id))
        count += 1
    assert answer['components'] == count and len(ids) == n - count
    assert all(labels[u] == labels[v] for u, v, _ in edges), 'not spanning'
    ancestors, maxima = [parent], [maximum]
    for _ in range(1, max(1, n.bit_length())):
        old, weights = ancestors[-1], maxima[-1]
        ancestors.append([old[old[v]] for v in range(n)])
        maxima.append([max(weights[v], weights[old[v]]) for v in range(n)])

    def path_max(u, v):
        result = negative_infinity
        if depth[u] < depth[v]:
            u, v = v, u
        difference = depth[u] - depth[v]
        for k in range(len(ancestors)):
            if difference & (1 << k):
                result = max(result, maxima[k][u])
                u = ancestors[k][u]
        if u == v:
            return result
        for k in range(len(ancestors) - 1, -1, -1):
            if ancestors[k][u] != ancestors[k][v]:
                result = max(result, maxima[k][u], maxima[k][v])
                u, v = ancestors[k][u], ancestors[k][v]
        return max(result, maxima[0][u], maxima[0][v])

    for u, v, weight in edges:
        assert u == v or weight >= path_max(u, v), 'nonoptimal forest'
    return True
