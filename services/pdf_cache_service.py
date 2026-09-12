"""
Sistema de cache para parse de PDFs MPFM.

Reduz tempo de processamento de ~18 minutos para segundos quando
PDFs já foram processados anteriormente.

Armazena:
- Hash SHA256 do arquivo
- Dados extraídos (texto + metadados)
- Timestamp do processamento

Uso:
    from services.pdf_cache_service import PDFCache

    cache = PDFCache()
    data = cache.get_or_parse(pdf_path, parse_function)
"""
import hashlib
import json
import logging
import os
import tempfile
import time
from pathlib import Path
from typing import Callable, Any

logger = logging.getLogger(__name__)


class PDFCache:
    """Cache persistente para dados extraídos de PDFs."""

    def __init__(self, cache_dir: str | Path = "data/pdf_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Estatísticas
        self.stats = {
            "hits": 0,
            "misses": 0,
            "errors": 0,
        }

    def _file_hash(self, path: Path) -> str:
        """Calcula SHA256 do arquivo."""
        sha256 = hashlib.sha256()
        with open(path, "rb") as f:
            # Lê em chunks para não sobrecarregar memória
            for chunk in iter(lambda: f.read(65536), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def _cache_path(self, pdf_path: Path, file_hash: str) -> Path:
        """Retorna caminho do arquivo de cache."""
        # O hash evita colisões entre PDFs homônimos de bancos/pastas diferentes.
        return self.cache_dir / f"{file_hash}.cache.json"

    def get(
        self,
        pdf_path: Path,
        *,
        cache_version: str = "1",
        file_hash: str | None = None,
    ) -> dict | None:
        """
        Tenta recuperar dados do cache.

        Retorna None se:
        - Cache não existe
        - PDF foi modificado (hash diferente)
        - Cache corrompido
        """
        current_hash = file_hash or self._file_hash(pdf_path)
        cache_path = self._cache_path(pdf_path, current_hash)

        if not cache_path.exists():
            return None

        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                cached = json.load(f)

            if cached.get("file_hash") != current_hash:
                return None
            if cached.get("cache_version") != cache_version:
                return None

            self.stats["hits"] += 1
            return cached.get("data")

        except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
            self.stats["errors"] += 1
            logger.warning("Falha ao ler cache do PDF %s: %s", pdf_path, exc)
            return None

    def put(
        self,
        pdf_path: Path,
        data: Any,
        *,
        cache_version: str = "1",
        file_hash: str | None = None,
    ) -> None:
        """
        Armazena dados no cache.

        Args:
            pdf_path: Caminho do PDF
            data: Dados extraídos (deve ser serializável para JSON)
        """
        temp_path: Path | None = None
        try:
            current_hash = file_hash or self._file_hash(pdf_path)
            cache_path = self._cache_path(pdf_path, current_hash)

            cached = {
                "file_path": str(pdf_path),
                "file_hash": current_hash,
                "cache_version": cache_version,
                "cached_at": time.time(),
                "data": data,
            }

            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                suffix=".tmp",
                dir=self.cache_dir,
                delete=False,
            ) as cache_file:
                temp_path = Path(cache_file.name)
                json.dump(cached, cache_file, ensure_ascii=False, separators=(",", ":"))
                cache_file.flush()
                os.fsync(cache_file.fileno())
            temp_path.replace(cache_path)
        except (OSError, TypeError, ValueError) as exc:
            self.stats["errors"] += 1
            logger.warning("Falha ao gravar cache do PDF %s: %s", pdf_path, exc)
        finally:
            if temp_path and temp_path.exists():
                try:
                    temp_path.unlink()
                except OSError as exc:
                    logger.warning("Falha ao remover cache temporário %s: %s", temp_path, exc)

    def get_or_parse(
        self,
        pdf_path: Path,
        parse_func: Callable[[Path], Any],
        *,
        cache_version: str = "1",
    ) -> Any:
        """
        Tenta cache primeiro, senão faz parse e armazena.

        Args:
            pdf_path: Caminho do PDF
            parse_func: Função que faz parse do PDF

        Returns:
            Dados extraídos (do cache ou parseados)
        """
        # Tenta cache
        pdf_path = Path(pdf_path)
        file_hash = self._file_hash(pdf_path)
        cached_data = self.get(
            pdf_path,
            cache_version=cache_version,
            file_hash=file_hash,
        )
        if cached_data is not None:
            return cached_data

        # Cache miss - faz parse
        self.stats["misses"] += 1

        try:
            data = parse_func(pdf_path)
            self.put(
                pdf_path,
                data,
                cache_version=cache_version,
                file_hash=file_hash,
            )
            return data
        except Exception:
            self.stats["errors"] += 1
            raise

    def clear(self) -> int:
        """Remove todos os arquivos de cache. Retorna quantidade removida."""
        removed = 0
        for cache_file in self.cache_dir.glob("*.cache.json"):
            try:
                cache_file.unlink()
                removed += 1
            except OSError as exc:
                self.stats["errors"] += 1
                logger.warning("Falha ao remover cache %s: %s", cache_file, exc)
        return removed

    def get_stats(self) -> dict:
        """Retorna estatísticas de uso do cache."""
        total = self.stats["hits"] + self.stats["misses"]
        hit_rate = (self.stats["hits"] / total * 100) if total > 0 else 0

        return {
            **self.stats,
            "total_requests": total,
            "hit_rate_pct": round(hit_rate, 1),
        }


# Singleton global - pode ser importado diretamente
_global_cache = None


def get_pdf_cache() -> PDFCache:
    """Retorna instância singleton do cache."""
    global _global_cache
    if _global_cache is None:
        _global_cache = PDFCache()
    return _global_cache
