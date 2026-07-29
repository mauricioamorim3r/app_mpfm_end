from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from fastapi import Body, HTTPException

from app_config import DB_PATH
from services.db_scope import shared_db


def register_painel_operador_routes(app, ctx: dict) -> None:
    service = ctx["service"]
    db_conn = ctx["db_conn"]
    xml042_repo = ctx.get("xml042_repo")

    def _blocks_from_query(blocks: str) -> list[str]:
        return [item.strip() for item in re.split(r"[,;]", blocks or "") if item.strip()]

    @app.get("/api/painel-operador/mpfm-xml042")
    def api_painel_operador_mpfm_xml042(
        month: str = "",
        date_from: str = "",
        date_to: str = "",
        cod_cadastro_poco: str = "",
        bank: str = "",
    ):
        """Retorna dados MPFM importados (xml042) para o Painel Operador."""
        if xml042_repo is None:
            raise HTTPException(status_code=503, detail="Módulo xml042 não disponível.")
        try:
            rows = xml042_repo.list_imported_rows(month=month, cod_cadastro_poco=cod_cadastro_poco)
            files = xml042_repo.list_imported_files(month=month, cod_cadastro_poco=cod_cadastro_poco)
            # Filtros adicionais
            if date_from:
                rows = [r for r in rows if str(r.get("production_day", "")) >= date_from]
                files = [f for f in files if str(f.get("production_day", "")) >= date_from]
            if date_to:
                rows = [r for r in rows if str(r.get("production_day", "")) <= date_to]
                files = [f for f in files if str(f.get("production_day", "")) <= date_to]
            if bank:
                rows = [r for r in rows if str(r.get("bank", "")).upper() == bank.upper()]
                files = [f for f in files if str(f.get("bank", "")).upper() == bank.upper()]
            # Sumário por dia
            by_day: dict[str, dict] = {}
            for r in rows:
                day = str(r.get("production_day", ""))
                if day not in by_day:
                    by_day[day] = {"date": day, "oil_sm3_total": 0.0, "gas_1000sm3_total": 0.0, "water_sm3_total": 0.0, "banks": set()}
                by_day[day]["oil_sm3_total"] += float(r.get("oil_sm3") or 0)
                by_day[day]["gas_1000sm3_total"] += float(r.get("gas_1000sm3") or 0)
                by_day[day]["water_sm3_total"] += float(r.get("water_sm3") or 0)
                if r.get("bank"):
                    by_day[day]["banks"].add(r["bank"])
            daily = sorted(
                [{"date": d, **{k: v for k, v in info.items() if k != "banks"}, "banks": sorted(info["banks"])}
                 for d, info in by_day.items()],
                key=lambda x: x["date"],
            )
            return {
                "record_type": "mpfm-xml042",
                "summary": {
                    "rows": len(rows),
                    "files": len(files),
                    "days": len(daily),
                    "banks": sorted({str(r.get("bank", "")) for r in rows if r.get("bank")}),
                },
                "daily": daily,
                "rows": rows,
                "files": files,
            }
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.get("/api/painel-operador/status")
    def api_painel_operador_status():
        return service.status()

    @shared_db(DB_PATH)
    @app.get("/api/painel-operador/overview")
    def api_painel_operador_overview():
        try:
            return {
                "status": service.status(),
                "file_summary": service.file_index_summary(db_conn),
                "anp_summary": service.anp_export_summary(db_conn),
                "staging_summary": service.staging_summary(db_conn),
                "checklist_summary": service.daily_checklist_summary(db_conn),
            }
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.get("/api/painel-operador/contract")
    def api_painel_operador_contract():
        try:
            return service.contract()
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @shared_db(DB_PATH)

    @app.get("/api/painel-operador/data")
    def api_painel_operador_data(blocks: str = "", max_list_items: int = 200):
        try:
            return service.data(_blocks_from_query(blocks), max_list_items=max_list_items)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @shared_db(DB_PATH)

    @app.get("/api/painel-operador/ihm-reports")
    def api_painel_operador_ihm_reports(
        date_from: str = "",
        date_to: str = "",
        fluid: str = "",
        tag: str = "",
        limit: int = 500,
    ):
        try:
            return service.ihm_reports(
                date_from=date_from,
                date_to=date_to,
                fluid=fluid,
                tag=tag,
                limit=limit,
            )
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @shared_db(DB_PATH)

    @app.get("/api/painel-operador/gas-balance-ihm")
    def api_painel_operador_gas_balance_ihm(date_from: str = "", date_to: str = ""):
        try:
            return service.gas_balance_ihm(date_from=date_from, date_to=date_to)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.get("/api/painel-operador/database-summary")
    def api_painel_operador_database_summary():
        return service.database_summary()

    @app.get("/api/painel-operador/data-sources")
    def api_painel_operador_data_sources(validate: bool = False):
        try:
            return service.data_sources(validate=validate)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.post("/api/painel-operador/data-sources/validate")
    def api_painel_operador_validate_data_sources():
        try:
            return service.validate_data_sources()
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.post("/api/painel-operador/data-sources/{source_id}")
    def api_painel_operador_save_data_source(source_id: str, payload: dict = Body(...)):
        try:
            return service.save_data_source(source_id, payload)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.get("/api/painel-operador/staging-summary")
    def api_painel_operador_staging_summary():
        try:
            return service.staging_summary(db_conn)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.get("/api/painel-operador/calibration-control")
    def api_painel_operador_calibration_control(status: str = "", tag: str = ""):
        """Retorna status de calibração dos instrumentos primários."""
        try:
            data = service.data(["calibrationControl"], max_list_items=500)
            cc = data.get("calibrationControl") or {}
            rows = list(cc.get("rows") or [])
            if status:
                rows = [r for r in rows if status.lower() in str(r.get("status", "")).lower()]
            if tag:
                rows = [r for r in rows if tag.upper() in str(r.get("tag", "")).upper()]
            return {**cc, "rows": rows, "filtered": len(rows)}
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.get("/api/painel-operador/cartas-anp")
    def api_painel_operador_cartas_anp(category: str = "", status: str = ""):
        """Retorna eventos regulatórios das Cartas e Ofícios ANP."""
        try:
            data = service.data(["cartasAnp"], max_list_items=500)
            ca = data.get("cartasAnp") or {}
            events = list(ca.get("events") or [])
            if category:
                events = [e for e in events if e.get("category") == category]
            if status:
                events = [e for e in events if e.get("status") == status]
            return {**ca, "events": events}
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.get("/api/painel-operador/operating-ranges")
    def api_painel_operador_operating_ranges(tag: str = ""):
        """Retorna faixas operacionais de processo por ponto de medição."""
        try:
            data = service.data(["operatingRanges"], max_list_items=500)
            op = data.get("operatingRanges") or {}
            rows = list(op.get("rows") or [])
            if tag:
                rows = [r for r in rows if tag.upper() in str(r.get("tag", "")).upper()]
            return {**op, "rows": rows}
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.get("/api/painel-operador/open-nfsms")
    def api_painel_operador_open_nfsms():
        """Retorna NFSMs abertas conhecidas."""
        try:
            data = service.data(["failures"], max_list_items=200)
            failures = data.get("failures") or {}
            return {
                "known_open": failures.get("knownOpen") or [],
                "latest_open": failures.get("latestOpen") or [],
                "total_open": failures.get("open") or 0,
            }
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @shared_db(DB_PATH)

    @app.get("/api/painel-operador/file-index-summary")
    def api_painel_operador_file_index_summary():
        try:
            return service.file_index_summary(db_conn)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @shared_db(DB_PATH)

    @app.get("/api/painel-operador/anp-exports-summary")
    def api_painel_operador_anp_exports_summary():
        try:
            return service.anp_export_summary(db_conn)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @shared_db(DB_PATH)

    @app.get("/api/painel-operador/daily-checklist-summary")
    def api_painel_operador_daily_checklist_summary():
        try:
            return service.daily_checklist_summary(db_conn)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.get("/api/painel-operador/daily-checklist/inspect")
    def api_painel_operador_daily_checklist_inspect(path: str, include_rows: bool = False):
        try:
            return service.inspect_daily_checklist(path, include_rows=include_rows)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.post("/api/painel-operador/daily-checklist/import")
    def api_painel_operador_daily_checklist_import(payload: dict = Body(...)):
        try:
            return service.import_daily_checklist(db_conn, str((payload or {}).get("path") or ""))
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @shared_db(DB_PATH)

    @app.get("/api/painel-operador/daily-checklist")
    def api_painel_operador_daily_checklist(
        sheet_name: str = "",
        date_from: str = "",
        date_to: str = "",
        tag: str = "",
        q: str = "",
        limit: int = 120,
        offset: int = 0,
    ):
        try:
            return service.list_daily_checklist_rows(
                db_conn,
                sheet_name=sheet_name,
                date_from=date_from,
                date_to=date_to,
                tag=tag,
                q=q,
                limit=limit,
                offset=offset,
            )
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.get("/api/painel-operador/tank-balance")
    def api_painel_operador_tank_balance(
        date_from: str = "",
        date_to: str = "",
        q: str = "",
        status: str = "",
        limit: int = 120,
        offset: int = 0,
    ):
        try:
            return service.tank_balance(
                db_conn,
                date_from=date_from,
                date_to=date_to,
                q=q,
                status=status,
                limit=limit,
                offset=offset,
            )
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.get("/api/painel-operador/offspec-tank")
    def api_painel_operador_offspec_tank(
        date_from: str = "",
        date_to: str = "",
        q: str = "",
        status: str = "",
        limit: int = 120,
        offset: int = 0,
    ):
        try:
            return service.offspec_tank(
                db_conn,
                date_from=date_from,
                date_to=date_to,
                q=q,
                status=status,
                limit=limit,
                offset=offset,
            )
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.get("/api/painel-operador/quality-samples")
    def api_painel_operador_quality_samples(
        date_from: str = "",
        date_to: str = "",
        q: str = "",
        status: str = "",
        limit: int = 160,
        offset: int = 0,
    ):
        try:
            return service.quality_samples(
                db_conn,
                date_from=date_from,
                date_to=date_to,
                q=q,
                status=status,
                limit=limit,
                offset=offset,
            )
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.get("/api/painel-operador/mpfm-fiscal-oil")
    def api_painel_operador_mpfm_fiscal_oil(
        date_from: str = "",
        date_to: str = "",
        q: str = "",
        status: str = "",
        limit: int = 160,
        offset: int = 0,
    ):
        try:
            return service.mpfm_fiscal_oil(
                db_conn,
                date_from=date_from,
                date_to=date_to,
                q=q,
                status=status,
                limit=limit,
                offset=offset,
            )
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.get("/api/painel-operador/gas-balance")
    def api_painel_operador_gas_balance(
        date_from: str = "",
        date_to: str = "",
        q: str = "",
        status: str = "",
        limit: int = 160,
        offset: int = 0,
    ):
        try:
            return service.gas_balance(
                db_conn,
                date_from=date_from,
                date_to=date_to,
                q=q,
                status=status,
                limit=limit,
                offset=offset,
            )
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.post("/api/painel-operador/file-index/scan")
    def api_painel_operador_file_index_scan(hash_files: bool = True):
        try:
            return service.scan_file_index(db_conn, hash_files=hash_files)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.post("/api/painel-operador/anp-exports/import")
    def api_painel_operador_anp_exports_import():
        try:
            return service.import_anp_exports(db_conn)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @shared_db(DB_PATH)

    @app.get("/api/painel-operador/file-index")
    def api_painel_operador_file_index(
        q: str = "",
        date_from: str = "",
        date_to: str = "",
        category: str = "",
        document_kind: str = "",
        source_group: str = "",
        extension: str = "",
        tag: str = "",
        family: str = "",
        ignored: str = "",
        is_duplicate: str = "",
        parse_priority: str = "",
        limit: int = 100,
        offset: int = 0,
        include_payload: bool = False,
    ):
        filters = {
            "category": category,
            "document_kind": document_kind,
            "source_group": source_group,
            "extension": extension,
            "tag": tag,
            "family": family,
            "ignored": _normalize_optional_int(ignored),
            "is_duplicate": _normalize_optional_int(is_duplicate),
            "parse_priority": parse_priority,
        }
        try:
            return service.list_file_index(
                db_conn,
                q=q,
                date_from=date_from,
                date_to=date_to,
                filters=filters,
                limit=limit,
                offset=offset,
                include_payload=include_payload,
            )
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @shared_db(DB_PATH)

    @app.get("/api/painel-operador/anp-exports")
    def api_painel_operador_anp_exports(
        q: str = "",
        date_from: str = "",
        date_to: str = "",
        family: str = "",
        tag: str = "",
        record_kind: str = "",
        source_file: str = "",
        failure_type: str = "",
        notification_type: str = "",
        limit: int = 100,
        offset: int = 0,
        include_payload: bool = False,
    ):
        filters = {
            "family": family,
            "tag": tag,
            "record_kind": record_kind,
            "source_file": source_file,
            "failure_type": failure_type,
            "notification_type": notification_type,
        }
        try:
            return service.list_anp_exports(
                db_conn,
                q=q,
                date_from=date_from,
                date_to=date_to,
                filters=filters,
                limit=limit,
                offset=offset,
                include_payload=include_payload,
            )
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @shared_db(DB_PATH)

    @app.get("/api/painel-operador/xml-validation")
    def api_painel_operador_xml_validation(
        q: str = "",
        date_from: str = "",
        date_to: str = "",
        family: str = "",
        tag: str = "",
        kind: str = "",
        status: str = "",
        limit: int = 100,
        offset: int = 0,
    ):
        try:
            return service.xml_validation(
                db_conn,
                q=q,
                date_from=date_from,
                date_to=date_to,
                family=family,
                tag=tag,
                kind=kind,
                status=status,
                limit=limit,
                offset=offset,
            )
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @shared_db(DB_PATH)

    @app.get("/api/painel-operador/anp-comparison")
    def api_painel_operador_anp_comparison(
        family: str = "",
        tag: str = "",
        record_kind: str = "",
        status: str = "",
        date_from: str = "",
        date_to: str = "",
        limit: int = 100,
        offset: int = 0,
        tolerance: float = 0.001,
    ):
        try:
            return service.compare_anp_staging(
                db_conn,
                family=family,
                tag=tag,
                record_kind=record_kind,
                status=status,
                date_from=date_from,
                date_to=date_to,
                limit=limit,
                offset=offset,
                tolerance=tolerance,
            )
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.get("/api/painel-operador/measured-data")
    def api_painel_operador_measured_data(
        date_from: str = "",
        date_to: str = "",
        family: str = "",
        tag: str = "",
        source: str = "",
        limit: int = 120,
        offset: int = 0,
    ):
        try:
            return service.measured_data(
                db_conn,
                date_from=date_from,
                date_to=date_to,
                family=family,
                tag=tag,
                source=source,
                limit=limit,
                offset=offset,
            )
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @shared_db(DB_PATH)

    @app.get("/api/painel-operador/measurement-point-dossiers")
    def api_painel_operador_measurement_point_dossiers(
        date_from: str = "",
        date_to: str = "",
        family: str = "",
        tag: str = "",
        q: str = "",
        limit: int = 50,
    ):
        try:
            return service.measurement_point_dossiers(
                db_conn,
                date_from=date_from,
                date_to=date_to,
                family=family,
                tag=tag,
                q=q,
                limit=limit,
            )
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.get("/api/painel-operador/production-days")
    def api_painel_operador_production_days(
        date_from: str = "",
        date_to: str = "",
        family: str = "",
        tag: str = "",
        category: str = "",
        limit: int = 90,
    ):
        try:
            return service.production_days(
                db_conn,
                date_from=date_from,
                date_to=date_to,
                family=family,
                tag=tag,
                category=category,
                limit=limit,
            )
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @shared_db(DB_PATH)

    @app.get("/api/painel-operador/technical-monitor")
    def api_painel_operador_technical_monitor(
        date_from: str = "",
        date_to: str = "",
        family: str = "",
        tag: str = "",
        limit: int = 120,
    ):
        try:
            return service.technical_monitor(
                db_conn,
                date_from=date_from,
                date_to=date_to,
                family=family,
                tag=tag,
                limit=limit,
            )
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.post("/api/painel-operador/technical-monitor/process")
    def api_painel_operador_process_technical_monitor():
        try:
            return service.process_technical_monitor(db_conn)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.post("/api/painel-operador/measurement-limits")
    def api_painel_operador_save_measurement_limit(payload: dict = Body(...)):
        try:
            return service.save_measurement_limit(db_conn, payload)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.post("/api/painel-operador/sync")
    def api_painel_operador_sync():
        try:
            return service.sync_to_staging(db_conn)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.post("/api/painel-operador/calendar-pendencies/{pendency_id}/decision")
    def api_painel_operador_calendar_pendency_decision(pendency_id: str, payload: dict = Body(...)):
        try:
            return service.decide_calendar_pendency(db_conn, pendency_id, payload)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.post("/api/painel-operador/proposals/{proposal_id}/decision")
    def api_painel_operador_proposal_decision(proposal_id: str, payload: dict = Body(...)):
        try:
            return service.decide_proposal(db_conn, proposal_id, payload)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.get("/api/painel-operador/staging/{record_type}")
    def api_painel_operador_staging_records(
        record_type: str,
        q: str = "",
        date_from: str = "",
        date_to: str = "",
        family: str = "",
        tag: str = "",
        fluid: str = "",
        status: str = "",
        severity: str = "",
        kind: str = "",
        area: str = "",
        target_id: str = "",
        requirement_id: str = "",
        meter_type: str = "",
        active: str = "",
        file_exists: str = "",
        loaded: str = "",
        evidence_state: str = "",
        confidence: str = "",
        source_type: str = "",
        limit: int = 100,
        offset: int = 0,
        include_payload: bool = False,
    ):
        filters = {
            "family": family,
            "tag": tag,
            "fluid": fluid,
            "status": status,
            "severity": severity,
            "kind": kind,
            "area": area,
            "target_id": target_id,
            "requirement_id": requirement_id,
            "meter_type": meter_type,
            "active": active,
            "file_exists": _normalize_optional_int(file_exists),
            "loaded": _normalize_optional_int(loaded),
            "evidence_state": evidence_state,
            "confidence": confidence,
            "source_type": source_type,
        }
        try:
            return service.list_staging_records(
                db_conn,
                record_type,
                q=q,
                date_from=date_from,
                date_to=date_to,
                filters=filters,
                limit=limit,
                offset=offset,
                include_payload=include_payload,
            )
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.get("/api/painel-operador/nfsm-abertas-excel")
    def api_painel_operador_nfsm_abertas_excel():
        """Retorna NFSMs abertas lendo arquivos Excel (Falha de Medição + Parecer)."""
        try:
            import pandas as pd
            
            # Caminhos dos arquivos Excel
            base_path = Path(__file__).parent.parent / "Painel_Operador"
            falhas_path = base_path / "Falha de Medição.xlsx"
            parecer_path = base_path / "Parecer.xlsx"
            
            if not falhas_path.exists():
                raise HTTPException(status_code=404, detail=f"Arquivo não encontrado: {falhas_path}")
            if not parecer_path.exists():
                raise HTTPException(status_code=404, detail=f"Arquivo não encontrado: {parecer_path}")
            
            # Ler arquivos Excel
            df_falhas = pd.read_excel(falhas_path)
            df_parecer = pd.read_excel(parecer_path)
            
            # Normalizar nome da coluna (pode ser "Código da Falha" ou similar)
            falhas_col = next((col for col in df_falhas.columns if 'código' in col.lower() and 'falha' in col.lower()), None)
            parecer_col = next((col for col in df_parecer.columns if 'código' in col.lower() and 'falha' in col.lower()), None)
            
            if not falhas_col or not parecer_col:
                return {"error": "Coluna 'Código da Falha' não encontrada", "total_abertas": 0, "abertas": []}
            
            # Calcular NFSMs abertas (sem parecer)
            todas_falhas = set(df_falhas[falhas_col].dropna().astype(str))
            com_parecer = set(df_parecer[parecer_col].dropna().astype(str))
            codigos_abertos = todas_falhas - com_parecer
            
            # Enriquecer com detalhes das falhas
            abertas = []
            for codigo in sorted(codigos_abertos):
                falha_row = df_falhas[df_falhas[falhas_col] == codigo].iloc[0]
                
                # Calcular dias abertos
                data_ocorrencia = falha_row.get('Data & Hora da Ocorrência') or falha_row.get('Data de Ocorrência')
                dias_abertos = None
                if pd.notna(data_ocorrencia):
                    try:
                        if isinstance(data_ocorrencia, str):
                            data_dt = pd.to_datetime(data_ocorrencia)
                        else:
                            data_dt = data_ocorrencia
                        dias_abertos = (datetime.now() - data_dt).days
                    except:
                        pass
                
                abertas.append({
                    "codigo_falha": codigo,
                    "data_ocorrencia": str(data_ocorrencia) if pd.notna(data_ocorrencia) else None,
                    "tag": str(falha_row.get('Tag do Ponto') or falha_row.get('Tag') or ''),
                    "tipo_notificacao": str(falha_row.get('Tipo de Notificação') or ''),
                    "tipo_falha": str(falha_row.get('Tipo de Falha') or ''),
                    "dias_abertos": dias_abertos,
                    "responsavel": str(falha_row.get('Responsável pelo Relato') or ''),
                })
            
            return {
                "total_falhas": len(todas_falhas),
                "total_com_parecer": len(com_parecer),
                "total_abertas": len(codigos_abertos),
                "abertas": sorted(abertas, key=lambda x: x.get('dias_abertos') or 0, reverse=True),
                "atualizado_em": datetime.now().isoformat(),
            }
        except ImportError:
            raise HTTPException(status_code=503, detail="Biblioteca pandas não disponível")
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Erro ao processar NFSMs: {str(exc)}")

    @app.get("/api/painel-operador/dashboard-principal")
    def api_painel_operador_dashboard_principal(month: str = ""):
        """Retorna dados consolidados para o dashboard principal (mês vigente)."""
        try:
            from datetime import date
            
            # Se não especificado, usar mês atual
            if not month:
                hoje = date.today()
                month = hoje.strftime("%Y-%m")
            
            # Data from/to do mês
            ano, mes = month.split("-")
            date_from = f"{ano}-{mes}-01"
            
            # Último dia do mês
            if int(mes) == 12:
                date_to = f"{int(ano)+1}-01-01"
            else:
                date_to = f"{ano}-{str(int(mes)+1).zfill(2)}-01"
            
            # Buscar dados de diferentes APIs
            # 1. Comparação fiscal x MPFM (dados do checklist diário)
            comparacao_raw = service.mpfm_fiscal_oil(
                db_conn,
                date_from=date_from,
                date_to=date_to[:10],
                limit=500
            )
            
            # Normalizar formato para frontend
            comparacoes_mes = []
            for item in comparacao_raw.get("items", []):
                fiscal = float(item.get("fiscal_oil_m3") or 0)
                mpfm = float(item.get("total_mpfm_oil_m3") or 0)
                delta_pct = float(item.get("variance_percent") or 0)
                
                comparacoes_mes.append({
                    "data": item.get("production_date", ""),
                    "tag": "Total FPSO",  # Agregado de todos os pontos
                    "familia": "a001",  # Família óleo
                    "fiscal": round(fiscal, 2),
                    "mpfm": round(mpfm, 2),
                    "delta_pct": round(delta_pct, 2),
                    "delta_m3": round(mpfm - fiscal, 2),
                    "status": item.get("status", ""),
                    "comment": item.get("comment", ""),
                })
            
            # 2. Balanço de gás
            gas_balance_raw = service.gas_balance_ihm(date_from=date_from, date_to=date_to[:10])
            
            # Mapear campos para formato esperado pelo frontend
            gas_items = []
            for row in gas_balance_raw.get("rows", []):
                entrada = float(row.get("gas_injection_m3", 0) or 0)
                consumo = float(row.get("fuel_gas_m3", 0) or 0)
                flare = float(row.get("hp_flare_m3", 0) or 0) + float(row.get("lp_flare_m3", 0) or 0)
                saida = consumo + flare
                balanco = entrada - saida
                desvio_pct = (balanco / entrada * 100) if entrada != 0 else 0
                
                gas_items.append({
                    "data": row.get("production_date", ""),
                    "entrada": round(entrada, 2),
                    "saida": round(saida, 2),
                    "consumo": round(consumo, 2),
                    "flare": round(flare, 2),
                    "balanco": round(balanco, 2),
                    "desvio_pct": round(desvio_pct, 2),
                })
            
            gas_balance = {
                "total": len(gas_items),
                "items": gas_items,
                "summary": gas_balance_raw.get("summary", {}),
            }
            
            # 3. NFSMs abertas
            nfsm_data = api_painel_operador_nfsm_abertas_excel()
            
            # 4. Dados de staging para verificar completude
            staging_summary = service.staging_summary(db_conn)
            
            # 5. Verificar dados faltantes
            alertas = []
            hoje = date.today()
            
            # Verificar se há dados dos últimos 3 dias
            for i in range(1, 4):
                dia_check = date(hoje.year, hoje.month, hoje.day - i)
                dia_str = dia_check.isoformat()
                tem_dados = any(str(c.get("data", "")) == dia_str for c in comparacoes_mes)
                if not tem_dados:
                    alertas.append({
                        "tipo": "warn",
                        "titulo": "Dados faltantes",
                        "mensagem": f"Faltam dados de {dia_check.strftime('%d/%m/%Y')}",
                    })
            
            # Verificar se há comparação disponível
            if not comparacoes_mes:
                alertas.append({
                    "tipo": "error",
                    "titulo": "Comparação vazia",
                    "mensagem": f"Não há dados de comparação para {month}",
                })
            
            # Verificar balanço de gás
            if not gas_balance.get("items"):
                alertas.append({
                    "tipo": "warn",
                    "titulo": "Balanço de gás",
                    "mensagem": f"Balanço de gás não disponível para {month}",
                })
            
            return {
                "month": month,
                "date_from": date_from,
                "date_to": date_to[:10],
                "comparacoes": {
                    "total": len(comparacoes_mes),
                    "items": comparacoes_mes[:100],  # Limitar para performance
                },
                "gas_balance": gas_balance,
                "nfsm": nfsm_data,
                "alertas": alertas,
                "atualizado_em": datetime.now().isoformat(),
                "_debug_gas_mapping": True,  # Flag de debug
            }
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Erro ao gerar dashboard: {str(exc)}")

    def _normalize_optional_int(value: str):
        raw = str(value or "").strip()
        if raw == "":
            return ""
        return 1 if raw in {"1", "true", "True", "sim", "yes"} else 0
