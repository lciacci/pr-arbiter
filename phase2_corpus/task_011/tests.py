"""Tests for topological_sort."""
import pytest
from solution import topological_sort


def test_simple_chain():
    assert topological_sort({"a": ["b"], "b": ["c"], "c": []}) == ["a", "b", "c"]


def test_empty_graph():
    assert topological_sort({}) == []


def test_no_edges_lexicographic():
    assert topological_sort({"c": [], "a": [], "b": []}) == ["a", "b", "c"]


def test_diamond():
    # a → b, a → c, b → d, c → d
    result = topological_sort({"a": ["b", "c"], "b": ["d"], "c": ["d"], "d": []})
    # a first, d last; b and c in either order — lex order says b first
    assert result == ["a", "b", "c", "d"]


def test_multiple_roots_lex_order():
    # a → c, b → c — both a and b can go first; lex says a
    assert topological_sort({"a": ["c"], "b": ["c"], "c": []}) == ["a", "b", "c"]


def test_simple_cycle_detected():
    with pytest.raises(ValueError, match="cycle"):
        topological_sort({"a": ["b"], "b": ["a"]})


def test_self_loop_is_cycle():
    with pytest.raises(ValueError, match="cycle"):
        topological_sort({"a": ["a"]})


def test_three_node_cycle():
    with pytest.raises(ValueError, match="cycle"):
        topological_sort({"a": ["b"], "b": ["c"], "c": ["a"]})


def test_cycle_message_mentions_a_cycle_node():
    try:
        topological_sort({"a": ["b"], "b": ["c"], "c": ["a"]})
        pytest.fail("expected ValueError")
    except ValueError as e:
        msg = str(e)
        # Must name at least one of the cycle members
        assert any(n in msg for n in ["a", "b", "c"])


def test_dangling_successor_raises():
    with pytest.raises(ValueError, match="ghost|missing|not.*key|dangl"):
        topological_sort({"a": ["ghost"]})


def test_all_nodes_in_output():
    g = {"a": ["b"], "b": [], "c": [], "d": ["a"]}
    result = topological_sort(g)
    assert set(result) == {"a", "b", "c", "d"}
    assert len(result) == 4


def test_disconnected_components():
    # Two independent chains: a → b, x → y
    g = {"a": ["b"], "b": [], "x": ["y"], "y": []}
    result = topological_sort(g)
    # a must precede b, x must precede y
    assert result.index("a") < result.index("b")
    assert result.index("x") < result.index("y")
    assert set(result) == {"a", "b", "x", "y"}


def test_deterministic_with_many_roots():
    g = {"z": [], "y": [], "x": [], "a": []}
    assert topological_sort(g) == ["a", "x", "y", "z"]


def test_complex_dag():
    # Build deps:
    g = {
        "frontend": ["api", "auth"],
        "api": ["db", "cache"],
        "auth": ["db"],
        "db": [],
        "cache": [],
    }
    result = topological_sort(g)
    # All deps must come before dependents
    for src, dsts in g.items():
        for dst in dsts:
            assert result.index(src) < result.index(dst)
