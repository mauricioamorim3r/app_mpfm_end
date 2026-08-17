from services.importing.import_pipeline_service import prepare_ingestion_batches


def test_duplicate_pdf_hash_in_same_batch_skips_parse(tmp_path):
    first = tmp_path / "MPFM_DAILY_B03_20260723_A.pdf"
    second = tmp_path / "MPFM_DAILY_B03_20260723_B.pdf"
    first.write_bytes(b"same pdf bytes")
    second.write_bytes(b"same pdf bytes")

    parse_calls = []
    file_logs = []

    def parse_pdf(path, report_type):
        parse_calls.append(path)
        return {
            "date_from": "2026-07-23",
            "date_to": "2026-07-24",
            "tags": {"Riser_P5": {"instrument": "13FT0367"}},
        }

    result = prepare_ingestion_batches(
        [(str(first), first.name), (str(second), second.name)],
        run_id=1,
        source_type="test",
        parse_pdf_fn=parse_pdf,
        build_cadastro_index_fn=lambda: {"expected_tags": {"B03": {"RISERP5"}}},
        log_raw_file_fn=lambda *args, **kwargs: 1,
        log_file_fn=lambda *args, **kwargs: file_logs.append(args),
        find_existing_import_by_identity_fn=lambda identity_key: None,
        find_existing_import_by_hash_fn=lambda file_hash: None,
        log_parsing_event_fn=lambda *args, **kwargs: None,
        add_issue_fn=lambda *args, **kwargs: None,
    )

    assert len(parse_calls) == 1
    assert len(result["parsed_pdfs"]) == 1
    assert any("parse ignorado" in message for message in result["log"])
    assert any("parse ignorado" in log_args[-1] for log_args in file_logs)
