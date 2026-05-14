# Task 011 — Topological sort with cycle detection

Difficulty: **hard**
Style: hand-authored

## Function to implement

```python
def topological_sort(graph: dict[str, list[str]]) -> list[str]:
    ...
```

## Specification

Given a directed graph as an adjacency list, return a topological
ordering of its nodes. If the graph contains a cycle, raise
`ValueError` with a message that identifies a cycle.

### Input

- `graph` is a dict mapping each node to a list of its **successors**
  (nodes it points to).
- All nodes must appear as keys, even if they have no outgoing edges
  (their value is `[]`). A node mentioned only as a successor but not
  as a key is an error — raise `ValueError`.
- Node identifiers are strings.

### Output

- A list of all nodes in dependency order: if `A → B`, then `A` appears
  before `B` in the output.
- The list contains every node in `graph` exactly once.
- For tied orderings (multiple valid topo sorts exist), break ties by
  **lexicographic order of node id** — the result must be deterministic.

### Examples

- `topological_sort({"a": ["b"], "b": ["c"], "c": []})` → `["a", "b", "c"]`
- `topological_sort({"a": [], "b": [], "c": []})` → `["a", "b", "c"]` (lex order on ties)
- `topological_sort({"a": ["c"], "b": ["c"], "c": []})` → `["a", "b", "c"]`

### Errors

- **Cycle**: raise `ValueError` with a message containing the word
  "cycle" and listing at least one node that is part of a cycle.
  Example: `ValueError("cycle detected involving: a, b, c")`.
- **Dangling successor**: raise `ValueError` if a successor is not
  itself a key in `graph`. Message should mention the missing node.
- **Empty graph**: returns `[]`.
- **Self-loop**: `{"a": ["a"]}` is a cycle. Raise `ValueError`.

## Out of scope

- Weighted edges
- Multigraphs (duplicate edges between two nodes)
- Disconnected components require no special handling — just include
  all nodes
