from __future__ import annotations

from collections.abc import Iterable, Iterator
from typing import Any


def iter_pivoted_measurements(
    rows: Iterable,
    selected_metrics: list[str],
) -> Iterator[list[Any]]:
    """Pivot an already ordered measurement cursor using constant row memory."""
    current_key = None
    metric_values: dict[str, Any] = {}

    def output_row(key, values):
        day, hour, bank, loop, tipo, tag = key
        base = [
            day,
            "" if hour is None else f"{int(hour):02d}:00",
            bank,
            loop,
            tipo,
            tag,
        ]
        return base + [values.get(metric) for metric in selected_metrics]

    for row in rows:
        key = (row[0], row[1], row[2], row[3], row[4], row[5])
        if current_key is not None and key != current_key:
            yield output_row(current_key, metric_values)
            metric_values = {}
        current_key = key
        metric_values[row[6]] = row[7]

    if current_key is not None:
        yield output_row(current_key, metric_values)
