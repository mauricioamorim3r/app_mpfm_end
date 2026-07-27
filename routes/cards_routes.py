from __future__ import annotations

from fastapi import HTTPException, Request

from routes.date_utils import normalize_date_input, normalize_date_range
from repositories.cards import CardsRepository
from services.cards import build_daily_cards
from services.deadline_excel_import import DEFAULT_RANP44_DEADLINES_PATH, import_ranp44_deadlines


def register_cards_routes(app, ctx: dict) -> None:
    upsert_card_override = ctx["upsert_card_override"]
    recompute_card_resolution = ctx["recompute_card_resolution"]
    deadline_payload = ctx["deadline_payload"]
    cards_repo = CardsRepository(ctx["db_conn"])

    @app.get("/api/cards/daily")
    def api_cards_daily(date_from: str = "", date_to: str = "", bank: str = "", date: str = ""):
        date = normalize_date_input(date)
        date_from, date_to = normalize_date_range(date_from, date_to)
        if date and not date_from and not date_to:
            date_from = date_to = date
        if not date_to:
            date_to = cards_repo.get_latest_daily_day()
        if not date_from:
            date_from = date_to
        return {"cards": build_daily_cards(cards_repo, date_from, date_to, bank)}

    @app.post("/api/cards/upsert")
    async def api_cards_upsert(request: Request):
        body = await request.json()
        card_id = upsert_card_override(body)
        return {"ok": True, "id": card_id}

    @app.post("/api/cards/manual")
    async def api_cards_manual(request: Request):
        body = await request.json()
        body["card_type"] = "Manual"
        card_id = upsert_card_override(body)
        return {"ok": True, "id": card_id}

    @app.get("/api/duplicates/cards")
    def api_card_duplicates(date_from: str = "", date_to: str = "", bank: str = ""):
        date_from, date_to = normalize_date_range(date_from, date_to)
        if not date_to:
            date_to = cards_repo.get_latest_card_day()
        if not date_from:
            date_from = date_to
        return {"rows": cards_repo.list_card_duplicates(date_from, date_to, bank)}

    @app.post("/api/duplicates/cards/resolve")
    async def api_card_duplicates_resolve(request: Request):
        body = await request.json()
        production_date = body.get("production_date", "")
        bank = str(body.get("bank", "")).upper()
        card_type = body.get("card_type", "")
        tag = body.get("tag", "") or ""
        instrument = body.get("instrument", "") or ""
        action = body.get("action", "use")
        official_id = body.get("official_id")
        delete_ids = body.get("delete_ids") or []
        ids = cards_repo.get_card_duplicate_ids(production_date, bank, card_type, tag, instrument)
        if not ids:
            raise HTTPException(404, "Conflito de card não encontrado")
        if action == "delete" and delete_ids:
            cards_repo.resolve_card_duplicates(ids, action, official_id, delete_ids)
            chosen = recompute_card_resolution(production_date, bank, card_type, tag, instrument)
        elif action == "pending":
            cards_repo.resolve_card_duplicates(ids, action, official_id, delete_ids)
            chosen = None
        else:
            if not official_id:
                raise HTTPException(400, "official_id é obrigatório")
            chosen = cards_repo.resolve_card_duplicates(ids, action, official_id, delete_ids)
        return {"ok": True, "chosen": chosen}

    @app.delete("/api/cards/{card_id}")
    def api_cards_delete(card_id: int):
        row = cards_repo.get_card_by_id(card_id)
        if not row:
            raise HTTPException(404, "Card não encontrado")
        cards_repo.soft_delete_card(card_id)
        try:
            recompute_card_resolution(row["production_date"], row["bank"], row["card_type"], row["tag"] or "", row["instrument"] or "")
        except Exception:
            pass
        return {"ok": True, "id": card_id}

    @app.get("/api/deadlines")
    def api_deadlines(active_only: str = "1"):
        active_only_flag = str(active_only).strip().lower() not in {"0", "false", "off", "no"}
        rows = cards_repo.list_deadlines(1 if active_only_flag else 0)
        return {"items": [deadline_payload(r) for r in rows]}

    @app.post("/api/deadlines")
    async def api_deadlines_upsert(request: Request):
        body = await request.json()
        new_id = cards_repo.upsert_deadline(body)
        return {"ok": True, "id": new_id}

    @app.post("/api/deadlines/import-excel")
    async def api_deadlines_import_excel(request: Request):
        body = await request.json()
        path = body.get("path") or DEFAULT_RANP44_DEADLINES_PATH
        dry_run = bool(body.get("dry_run", False))
        try:
            result = import_ranp44_deadlines(ctx["db_conn"], path, dry_run=dry_run)
        except FileNotFoundError as exc:
            raise HTTPException(404, str(exc)) from exc
        except Exception as exc:
            raise HTTPException(400, f"Falha ao importar planilha de prazos: {exc}") from exc
        return {"ok": True, **result}

    @app.delete("/api/deadlines/{item_id}")
    def api_deadlines_delete(item_id: int):
        cards_repo.delete_deadline(item_id)
        return {"ok": True}
