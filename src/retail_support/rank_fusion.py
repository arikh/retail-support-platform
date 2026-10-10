"""Merges two ranked lists of passages into one (reciprocal rank fusion).

Each list gives a passage points for its position: 1 / (RRF_K + position),
with position 1 for the first row. The points from the two lists are added.
Only the position counts, never the list's own number: a distance and a
word score cannot be compared, but "first" and "third" can.

No database and no model here: lists in, one list out.
"""

RRF_K = 60  # the usual constant; it keeps the gap between 1st and 2nd small


def fuse(dense: list[dict], keyword: list[dict], limit: int) -> list[dict]:
    """The `limit` passages with the most points, most points first.

    Each row has source, heading, content and score (the points)."""
    points: dict[tuple[str, str], float] = {}
    rows: dict[tuple[str, str], dict] = {}

    for ranked_list in (dense, keyword):
        for position, row in enumerate(ranked_list, start=1):
            key = (row["source"], row["heading"])  # what makes a passage itself
            points[key] = points.get(key, 0.0) + 1 / (RRF_K + position)
            if key not in rows:
                rows[key] = row

    # Most points first. Equal points: by source, then heading, so the order
    # is the same on every run.
    ordered = sorted(points, key=lambda key: (-points[key], key))

    fused = []
    for key in ordered[:limit]:
        source, heading = key
        fused.append(
            {
                "source": source,
                "heading": heading,
                "content": rows[key]["content"],
                "score": points[key],
            }
        )
    return fused