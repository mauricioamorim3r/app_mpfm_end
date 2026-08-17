from __future__ import annotations

from datetime import datetime


DIMENSION_COLUMNS = {
    "bank": "bank",
    "metric": "metric_name",
    "tag": "tag",
}


def refresh_measurement_dimensions(conn, *, run_id: int | None = None) -> dict[str, int]:
    """Incrementally materialize dropdown dimensions from active measurements."""
    now = datetime.now().isoformat(timespec="seconds")
    source = "measurements_active"
    counts: dict[str, int] = {}
    for kind, column in DIMENSION_COLUMNS.items():
        where = [f"COALESCE({column}, '')<>''"]
        params: list[object] = [kind, now]
        if run_id is not None:
            where.append("run_id=?")
            params.append(int(run_id))
        before = conn.total_changes
        conn.execute(
            f"""
            INSERT OR IGNORE INTO measurement_dimensions(
                dimension_kind, dimension_value, updated_at
            )
            SELECT ?, {column}, ?
            FROM {source}
            WHERE {' AND '.join(where)}
            GROUP BY {column}
            """,
            params,
        )
        counts[kind] = conn.total_changes - before
    conn.commit()
    return counts


def ensure_measurement_dimensions(conn) -> dict[str, int]:
    """Backfill once for an existing database; later imports are incremental."""
    row = conn.execute("SELECT COUNT(*) FROM measurement_dimensions").fetchone()
    if row and int(row[0] or 0) > 0:
        return {kind: 0 for kind in DIMENSION_COLUMNS}
    return refresh_measurement_dimensions(conn)


def load_measurement_dimensions(conn) -> dict[str, list[str]]:
    result = {"banks": [], "metrics": [], "tags": []}
    output_keys = {"bank": "banks", "metric": "metrics", "tag": "tags"}
    for row in conn.execute(
        """
        SELECT dimension_kind, dimension_value
        FROM measurement_dimensions
        ORDER BY dimension_kind, dimension_value
        """
    ).fetchall():
        kind, value = row[0], row[1]
        key = output_keys.get(kind)
        if key and value:
            result[key].append(value)
    return result
