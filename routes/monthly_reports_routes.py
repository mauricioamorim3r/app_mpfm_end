from __future__ import annotations

from urllib.parse import urlencode

from fastapi import HTTPException
from fastapi.responses import HTMLResponse, JSONResponse

from services.monthly_reports import (
    DEFAULT_MONTHLY_REPORT_GROUPS,
    build_monthly_report_payload,
    render_monthly_report_html,
)


def register_monthly_reports_routes(app, ctx: dict) -> None:
    db_conn = ctx["db_conn"]
    normalize_tag_name = ctx["normalize_tag_name"]
    month_pt = ctx["month_pt"]

    def _build_payload(
        month: str,
        mode: str,
        group_key: str,
        date_from: str,
        date_to: str,
        custom_title: str,
        subsea_bank: str,
        subsea_tag: str,
        topside_bank: str,
        topside_tag: str,
    ) -> dict:
        try:
            return build_monthly_report_payload(
                db_conn,
                month=month,
                mode=mode,
                group_key=group_key,
                custom={
                    "date_from": date_from,
                    "date_to": date_to,
                    "title": custom_title,
                    "subsea_bank": subsea_bank,
                    "subsea_tag": subsea_tag,
                    "topside_bank": topside_bank,
                    "topside_tag": topside_tag,
                },
                normalize_tag_name=normalize_tag_name,
                month_pt=month_pt,
            )
        except ValueError as exc:
            raise HTTPException(400, str(exc))

    @app.get("/api/monthly-reports/context")
    def api_monthly_reports_context():
        return {
            "groups": DEFAULT_MONTHLY_REPORT_GROUPS,
            "modes": [
                {"value": "default", "label": "Padrão mensal"},
                {"value": "custom", "label": "Customizado"},
            ],
        }

    @app.get("/api/monthly-reports/preview")
    def api_monthly_reports_preview(
        month: str = "",
        mode: str = "default",
        group_key: str = "",
        date_from: str = "",
        date_to: str = "",
        custom_title: str = "",
        subsea_bank: str = "",
        subsea_tag: str = "",
        topside_bank: str = "",
        topside_tag: str = "",
    ):
        payload = _build_payload(month, mode, group_key, date_from, date_to, custom_title, subsea_bank, subsea_tag, topside_bank, topside_tag)
        qs = urlencode(
            {
                "month": month,
                "mode": mode,
                "group_key": group_key,
                "date_from": date_from,
                "date_to": date_to,
                "custom_title": custom_title,
                "subsea_bank": subsea_bank,
                "subsea_tag": subsea_tag,
                "topside_bank": topside_bank,
                "topside_tag": topside_tag,
            }
        )
        return JSONResponse(
            {
                "summary": payload.get("summary") or {},
                "meta": payload.get("meta") or {},
                "groups": [
                    {
                        "key": item.get("key"),
                        "title": item.get("title"),
                        "stats": item.get("stats") or {},
                    }
                    for item in payload.get("groups") or []
                ],
                "html_url": f"/api/monthly-reports/html?{qs}",
                "print_url": f"/api/monthly-reports/html?{qs}&print=1",
            }
        )

    @app.get("/api/monthly-reports/html")
    def api_monthly_reports_html(
        month: str = "",
        mode: str = "default",
        group_key: str = "",
        date_from: str = "",
        date_to: str = "",
        custom_title: str = "",
        subsea_bank: str = "",
        subsea_tag: str = "",
        topside_bank: str = "",
        topside_tag: str = "",
        print: int = 0,
    ):
        payload = _build_payload(month, mode, group_key, date_from, date_to, custom_title, subsea_bank, subsea_tag, topside_bank, topside_tag)
        html = render_monthly_report_html(payload)
        if print:
            html = html.replace("params.get('print') === '1'", "true")
        return HTMLResponse(html)
