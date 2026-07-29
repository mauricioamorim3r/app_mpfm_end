"""
services/db_scope.py
─────────────────────────────────────────────────────────────────────────────
Utilitário para compartilhar uma conexão SQLite dentro de uma requisição.

Uso:
    from services.db_scope import shared_db

    @shared_db
    def meu_endpoint(...):
        # Todas as chamadas a db_conn() dentro desta função reutilizam
        # a mesma conexão SQLite.
        ...
"""

from __future__ import annotations

import contextvars
import functools
import inspect
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Callable

_db_conn_fn: contextvars.ContextVar[Callable | None] = contextvars.ContextVar(
    "_scoped_db_conn_fn", default=None
)


def set_scoped_db_conn(fn: Callable) -> None:
    _db_conn_fn.set(fn)


def get_scoped_db_conn() -> Callable | None:
    return _db_conn_fn.get()


def _default_db_conn(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path), timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 30000")
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
    except Exception:
        pass
    return conn


def shared_db(db_path: Path, db_conn_factory: Callable | None = None):
    """Decorador de endpoint que abre uma conexão SQLite compartilhada."""
    factory = db_conn_factory or (lambda: _default_db_conn(db_path))

    def decorator(endpoint: Callable):
        if inspect.iscoroutinefunction(endpoint):
            @functools.wraps(endpoint)
            async def async_wrapper(*args, **kwargs):
                conn = factory()
                token = _db_conn_fn.set(lambda: conn)
                try:
                    return await endpoint(*args, **kwargs)
                finally:
                    _db_conn_fn.reset(token)
                    try:
                        conn.close()
                    except Exception:
                        pass
            return async_wrapper
        else:
            @functools.wraps(endpoint)
            def sync_wrapper(*args, **kwargs):
                conn = factory()
                token = _db_conn_fn.set(lambda: conn)
                try:
                    return endpoint(*args, **kwargs)
                finally:
                    _db_conn_fn.reset(token)
                    try:
                        conn.close()
                    except Exception:
                        pass
            return sync_wrapper
    return decorator


@contextmanager
def shared_db_context(db_path: Path, db_conn_factory: Callable | None = None):
    """Context manager alternativo ao decorador."""
    factory = db_conn_factory or (lambda: _default_db_conn(db_path))
    conn = factory()
    token = _db_conn_fn.set(lambda: conn)
    try:
        yield conn
    finally:
        _db_conn_fn.reset(token)
        try:
            conn.close()
        except Exception:
            pass
