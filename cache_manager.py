"""
Sistema de Cache Simples para MPFM Manager
Reduz queries repetidas em até 90%
"""
import time
from functools import wraps
from typing import Any, Optional, Dict, Callable
import hashlib
import json


class SimpleCache:
    """Cache em memória com TTL (Time To Live)"""

    def __init__(self):
        self._cache: Dict[str, tuple[Any, float]] = {}
        self._stats = {'hits': 0, 'misses': 0}

    def get(self, key: str, ttl: int = 3600) -> Optional[Any]:
        """
        Busca valor no cache

        Args:
            key: Chave única
            ttl: Time-to-live em segundos (padrão: 1 hora)

        Returns:
            Valor cacheado ou None se expirado/não existe
        """
        if key in self._cache:
            value, timestamp = self._cache[key]
            if time.time() - timestamp < ttl:
                self._stats['hits'] += 1
                return value
            else:
                # Expirou, remove
                del self._cache[key]

        self._stats['misses'] += 1
        return None

    def set(self, key: str, value: Any) -> None:
        """Salva valor no cache"""
        self._cache[key] = (value, time.time())

    def invalidate(self, pattern: Optional[str] = None) -> int:
        """
        Invalida cache

        Args:
            pattern: Se fornecido, remove apenas keys que contêm o padrão

        Returns:
            Número de entradas removidas
        """
        if pattern is None:
            count = len(self._cache)
            self._cache.clear()
            return count

        keys_to_remove = [k for k in self._cache if pattern in k]
        for k in keys_to_remove:
            del self._cache[k]
        return len(keys_to_remove)

    def get_stats(self) -> dict:
        """Retorna estatísticas de uso"""
        total = self._stats['hits'] + self._stats['misses']
        hit_rate = (self._stats['hits'] / total * 100) if total > 0 else 0
        return {
            'hits': self._stats['hits'],
            'misses': self._stats['misses'],
            'hit_rate': f'{hit_rate:.1f}%',
            'cached_items': len(self._cache)
        }


# Instância global
_cache = SimpleCache()


def cached(ttl: int = 3600, key_prefix: str = ''):
    """
    Decorator para cachear resultados de funções

    Args:
        ttl: Time-to-live em segundos
        key_prefix: Prefixo para a chave de cache

    Exemplo:
        @cached(ttl=1800, key_prefix='metadata')
        def get_dropdown_options():
            return expensive_query()
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Gera chave única baseada em função + argumentos
            key_data = {
                'func': func.__name__,
                'prefix': key_prefix,
                'args': str(args),
                'kwargs': str(sorted(kwargs.items()))
            }
            digest = hashlib.md5(json.dumps(key_data, sort_keys=True).encode()).hexdigest()
            # Keep the namespace visible so selective invalidation works.
            # Previously the prefix was inside the MD5 payload, making calls
            # such as invalidate_cache("mpfm_metadata") unable to match it.
            key = f"{key_prefix}:{digest}" if key_prefix else digest

            # Tenta buscar no cache
            cached_value = _cache.get(key, ttl)
            if cached_value is not None:
                return cached_value

            # Cache miss - executa função
            result = func(*args, **kwargs)
            _cache.set(key, result)
            return result

        return wrapper
    return decorator


def invalidate_cache(pattern: Optional[str] = None) -> int:
    """
    Invalida cache globalmente ou por padrão

    Exemplo:
        invalidate_cache('metadata')  # Remove tudo que tem 'metadata' na key
        invalidate_cache()             # Remove tudo
    """
    return _cache.invalidate(pattern)


def get_cache_stats() -> dict:
    """Retorna estatísticas de cache"""
    return _cache.get_stats()


# ═══════════════════════════════════════════════════════════════════
# EXEMPLOS DE USO
# ═══════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    # Exemplo 1: Cachear metadados de dropdown
    @cached(ttl=1800, key_prefix='dropdown')
    def get_banks_list():
        import sqlite3
        conn = sqlite3.connect('data/mpfm_local.db')
        banks = [r[0] for r in conn.execute(
            "SELECT DISTINCT bank FROM measurements_curated ORDER BY bank"
        ).fetchall()]
        conn.close()
        return banks

    # Primeira chamada - cache miss
    print('[*] Primeira chamada...')
    start = time.time()
    banks = get_banks_list()
    print(f'    Tempo: {time.time()-start:.3f}s, Resultado: {len(banks)} bancos')

    # Segunda chamada - cache hit
    print('[*] Segunda chamada...')
    start = time.time()
    banks = get_banks_list()
    print(f'    Tempo: {time.time()-start:.3f}s, Resultado: {len(banks)} bancos')

    # Estatísticas
    print(f'\n[*] Cache stats: {get_cache_stats()}')

    # Exemplo 2: Invalidar cache após importação
    print('\n[*] Invalidando cache de dropdowns...')
    invalidated = invalidate_cache('dropdown')
    print(f'    Removidas {invalidated} entradas')
