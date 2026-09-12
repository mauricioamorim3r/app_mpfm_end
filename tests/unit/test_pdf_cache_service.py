from pathlib import Path

from services.pdf_cache_service import PDFCache


def test_cache_is_content_addressed_and_versioned(tmp_path: Path):
    cache = PDFCache(tmp_path / "cache")
    first = tmp_path / "first" / "report.pdf"
    second = tmp_path / "second" / "report.pdf"
    first.parent.mkdir()
    second.parent.mkdir()
    first.write_bytes(b"first")
    second.write_bytes(b"second")
    calls = []

    def parse(path: Path):
        calls.append(path.read_bytes())
        return {"value": path.read_text()}

    assert cache.get_or_parse(first, parse, cache_version="parser-1") == {"value": "first"}
    assert cache.get_or_parse(second, parse, cache_version="parser-1") == {"value": "second"}
    assert cache.get_or_parse(first, parse, cache_version="parser-1") == {"value": "first"}
    assert len(calls) == 2

    assert cache.get_or_parse(first, parse, cache_version="parser-2") == {"value": "first"}
    assert len(calls) == 3
