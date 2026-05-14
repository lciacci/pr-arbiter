"""Reference solution for task_008."""


def merge_intervals(intervals: list[tuple[int, int]]) -> list[tuple[int, int]]:
    for s, e in intervals:
        if s > e:
            raise ValueError(f"invalid interval: ({s}, {e})")
    if not intervals:
        return []
    sorted_ivs = sorted(intervals, key=lambda iv: iv[0])
    out: list[tuple[int, int]] = [sorted_ivs[0]]
    for start, end in sorted_ivs[1:]:
        last_start, last_end = out[-1]
        if start <= last_end:  # overlap (touching counts)
            out[-1] = (last_start, max(last_end, end))
        else:
            out.append((start, end))
    return out
