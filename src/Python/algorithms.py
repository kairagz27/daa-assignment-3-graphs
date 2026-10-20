"""Graph algorithms for the supplied JSON Lines adapter (Python 3.12+)."""

from heapq import heappop, heappush


class DisjointSet:
    """Disjoint sets with iterative path compression and union by size."""

    def __init__(self, n: int) -> None:
        self.parent = list(range(n))
        self.size = [1] * n
        self.components = n
        self.largest = int(n > 0)

    def find(self, vertex: int) -> int:
        root = vertex
        while self.parent[root] != root:
            root = self.parent[root]
        while vertex != root:
            previous = self.parent[vertex]
            self.parent[vertex] = root
            vertex = previous
        return root

    def union(self, u: int, v: int) -> bool:
        """Merge distinct sets; return whether the partition changed."""
        a, b = self.find(u), self.find(v)
        if a == b:
            return False
        if self.size[a] < self.size[b]:
            a, b = b, a
        self.parent[b] = a
        self.size[a] += self.size[b]
        self.components -= 1
        self.largest = max(self.largest, self.size[a])
        return True


def dsu(request: dict) -> dict:
    """Return [component count, largest size] after each union."""
    sets = DisjointSet(request["n"])
    states = []
    for u, v in request["operations"]:
        sets.union(u, v)
        states.append([sets.components, sets.largest])
    return {"states": states}


def kruskal(request: dict) -> dict:
    """Minimum spanning forest by sorted edges and DSU."""
    sets = DisjointSet(request["n"])
    edges = request["edges"]
    selected = []
    cost = 0
    # Sort IDs, retaining the original edge array and its numbering.
    for edge_id in sorted(range(len(edges)), key=lambda i: edges[i][2]):
        u, v, weight = edges[edge_id]
        if sets.union(u, v):
            selected.append(edge_id)
            cost += weight
    return {"cost": cost, "edge_ids": selected, "components": sets.components}


def prim(request: dict) -> dict:
    """Minimum spanning forest by adjacency lists and a lazy min-heap."""
    n = request["n"]
    adjacency = [[] for _ in range(n)]
    for edge_id, (u, v, weight) in enumerate(request["edges"]):
        if u != v:
            adjacency[u].append((weight, edge_id, v))
            adjacency[v].append((weight, edge_id, u))

    visited = bytearray(n)
    selected = []
    cost = 0
    components = 0
    for start in range(n):
        if visited[start]:
            continue
        components += 1
        visited[start] = 1
        heap = []
        for entry in adjacency[start]:
            heappush(heap, entry)
        while heap:
            weight, edge_id, vertex = heappop(heap)
            if visited[vertex]:
                continue
            visited[vertex] = 1
            selected.append(edge_id)
            cost += weight
            for entry in adjacency[vertex]:
                if not visited[entry[2]]:
                    heappush(heap, entry)
    return {"cost": cost, "edge_ids": selected, "components": components}


def _finish_order(adjacency: list[list[int]], detect_cycle: bool) -> list[int] | None:
    """Three-state iterative DFS; None signals a cycle when detection is on.

    Each frame stores its vertex and the index of the next unexamined edge.
    Retaining that index avoids rescanning a high-degree vertex on return.
    """
    state = bytearray(len(adjacency))  # 0: unvisited, 1: active, 2: finished
    finished = []
    for start in range(len(adjacency)):
        if state[start]:
            continue
        state[start] = 1
        stack = [(start, 0)]
        while stack:
            vertex, next_edge = stack[-1]
            if next_edge == len(adjacency[vertex]):
                stack.pop()
                state[vertex] = 2
                finished.append(vertex)
                continue
            neighbour = adjacency[vertex][next_edge]
            stack[-1] = (vertex, next_edge + 1)
            if state[neighbour] == 0:
                state[neighbour] = 1
                stack.append((neighbour, 0))
            elif detect_cycle and state[neighbour] == 1:
                return None
    return finished


def scc(request: dict) -> dict:
    """Kosaraju: DFS finish order, then DFS of the transposed graph."""
    n = request["n"]
    edges = request["edges"]
    adjacency = [[] for _ in range(n)]
    transpose = [[] for _ in range(n)]
    for u, v in edges:
        adjacency[u].append(v)
        transpose[v].append(u)
    finished = _finish_order(adjacency, detect_cycle=False)

    component = [-1] * n
    label = 0
    for start in reversed(finished):
        if component[start] != -1:
            continue
        component[start] = label
        stack = [start]
        while stack:
            vertex = stack.pop()
            for neighbour in transpose[vertex]:
                if component[neighbour] == -1:
                    component[neighbour] = label  # Mark on push, once per vertex.
                    stack.append(neighbour)
        label += 1

    pairs = set()
    condensation = []
    for u, v in edges:
        pair = (component[u], component[v])
        if pair[0] != pair[1] and pair not in pairs:
            pairs.add(pair)
            condensation.append(list(pair))
    return {"component": component, "condensation": condensation}


def topo(request: dict) -> dict:
    """Check every component using DFS; reverse finish order for a DAG."""
    adjacency = [[] for _ in range(request["n"])]
    for u, v in request["edges"]:
        adjacency[u].append(v)
    finished = _finish_order(adjacency, detect_cycle=True)
    if finished is None:
        return {"acyclic": False, "order": []}
    finished.reverse()
    return {"acyclic": True, "order": finished}


def dag(request: dict) -> dict:
    """Whole-graph DFS cycle check followed by topological relaxation."""
    n = request["n"]
    source = request["source"]
    edges = request["edges"]
    adjacency = [[] for _ in range(n)]
    outgoing_ids = [[] for _ in range(n)]
    for edge_id, (u, v, _) in enumerate(edges):
        adjacency[u].append(v)
        outgoing_ids[u].append(edge_id)
    finished = _finish_order(adjacency, detect_cycle=True)
    if finished is None:
        return {"acyclic": False, "distance": [], "parent_edge": []}

    distance = [None] * n
    parent_edge = [-1] * n
    distance[source] = 0
    for u in reversed(finished):
        if distance[u] is None:
            continue
        for edge_id in outgoing_ids[u]:
            _, v, weight = edges[edge_id]
            candidate = distance[u] + weight
            if distance[v] is None or candidate < distance[v]:
                distance[v] = candidate
                parent_edge[v] = edge_id
    return {"acyclic": True, "distance": distance, "parent_edge": parent_edge}


def reconstruct_route(
    source: int, target: int, edges: list[list[int]], parent_edge: list[int]
) -> list[int]:
    """Reconstruct a valid DAG result's vertex route in O(L) time/space.

    Requires the parent_edge array from an acyclic dag() result for source.
    An unreachable target returns []; the source returns [source].
    """
    if target == source:
        return [source]
    if parent_edge[target] == -1:
        return []
    route = [target]
    while target != source:
        edge_id = parent_edge[target]
        target = edges[edge_id][0]
        route.append(target)
    route.reverse()
    return route
