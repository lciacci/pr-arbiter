"""Reference solution for task_011: Kahn's algorithm with lex-ordered tie-breaking."""
import heapq


def topological_sort(graph: dict[str, list[str]]) -> list[str]:
    if not graph:
        return []
    # Validate that all successors are keys
    nodes = set(graph.keys())
    for src, dsts in graph.items():
        for dst in dsts:
            if dst not in nodes:
                raise ValueError(f"dangling successor: {dst!r} is not a key in the graph")
    # Compute in-degrees
    indegree: dict[str, int] = {n: 0 for n in nodes}
    for src, dsts in graph.items():
        for dst in dsts:
            indegree[dst] += 1
    # Lex-ordered min-heap of roots
    heap: list[str] = [n for n, d in indegree.items() if d == 0]
    heapq.heapify(heap)
    result: list[str] = []
    while heap:
        n = heapq.heappop(heap)
        result.append(n)
        for m in graph[n]:
            indegree[m] -= 1
            if indegree[m] == 0:
                heapq.heappush(heap, m)
    if len(result) != len(nodes):
        # Cycle — surface nodes with remaining indegree > 0
        remaining = sorted(n for n in nodes if indegree[n] > 0)
        raise ValueError(f"cycle detected involving: {', '.join(remaining)}")
    return result
