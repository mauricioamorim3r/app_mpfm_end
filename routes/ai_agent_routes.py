"""
routes/ai_agent_routes.py
─────────────────────────────────────────────────────────────────────────────
Agentes de IA especializados para o MPFM App.

- POST /api/ai/agent/alarms   → Análise inteligente de alarmes FCS320
- POST /api/ai/agent/fechamento → Qualidade do fechamento diário
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timedelta
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from routes.ai_routes import _create_ai_conversation, _log_ai_message, _token_count
from services.ai_assistant import RESPONSE_FORMAT_INSTRUCTIONS, SYSTEM_MPFM, ask_ai

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ai/agent", tags=["ai-agent"])


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _ai_db_conn():
    import app_config
    conn = sqlite3.connect(str(app_config.DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _normalize_date(value: str | None, default_offset_days: int = 0) -> str:
    if value and len(value) >= 10:
        return value[:10]
    d = datetime.now() + timedelta(days=default_offset_days)
    return d.date().isoformat()


async def _call_ai_agent(
    *,
    system: str,
    user: str,
    provider: str,
    model: Optional[str],
    max_tokens: int = 8192,
    temperature: float = 0.2,
    conversation_title: str,
    source_page: str = "assistente",
    request_type: str = "agent",
) -> dict[str, Any]:
    """Chama o modelo de IA e registra a mensagem no histórico."""
    conversation_id = _create_ai_conversation(conversation_title, source_page)

    try:
        resp = await ask_ai(
            user=user,
            system=system,
            provider=provider,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        logger.exception("ai_agent error")
        raise HTTPException(status_code=500, detail=f"Erro ao chamar o modelo: {exc}")

    _log_ai_message(
        conversation_id=conversation_id,
        role="user",
        content=f"[{request_type}]\n\n{user[:2000]}",
        metadata={"request_type": request_type},
    )
    assistant_message_id = _log_ai_message(
        conversation_id=conversation_id,
        role="assistant",
        content=resp.content,
        provider=resp.provider,
        model=resp.model,
        input_tokens=_token_count(resp.input_tokens),
        output_tokens=_token_count(resp.output_tokens),
        metadata={"request_type": request_type},
    )

    return {
        "content": resp.content,
        "provider": resp.provider,
        "model": resp.model,
        "input_tokens": _token_count(resp.input_tokens),
        "output_tokens": _token_count(resp.output_tokens),
        "conversation_id": conversation_id,
        "message_id": assistant_message_id,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Agente de Alarmes FCS320
# ─────────────────────────────────────────────────────────────────────────────

class AlarmAgentRequest(BaseModel):
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    bank: Optional[str] = None
    status: Optional[str] = Field(None, description="Filtrar por status_code")
    severity: Optional[str] = Field(None, description="Filtrar por severity_code")
    priority: Optional[str] = Field(None, description="Filtrar por priority_code")
    limit: int = Field(150, ge=1, le=500)
    provider: Optional[str] = Field("kimi", description="Provider de IA")
    model: Optional[str] = Field(None, description="Modelo específico")


@router.post("/alarms", summary="Análise inteligente de alarmes FCS320")
async def ai_agent_alarms(req: AlarmAgentRequest):
    """
    Analisa alarmes FCS320 do período/banco informado e retorna:
    - Resumo executivo
    - Agrupamento por recorrência
    - Alarmes críticos prioritários
    - Sugestões de ação
    """
    date_from = _normalize_date(req.date_from, -7)
    date_to = _normalize_date(req.date_to, 0)

    conn = _ai_db_conn()
    try:
        sql = """
            SELECT id, record_type, production_date, event_at, measurement_point, tag,
                   instrument, title, message, category_code, family_code, severity_code,
                   priority_code, status_code, occurrence_count, distinct_alarm_count,
                   impact, immediate_action, bank
            FROM alarm_records
            WHERE active = 1
              AND source_kind = 'pdf'
              AND production_date BETWEEN ? AND ?
        """
        params = [date_from, date_to]
        if req.bank:
            sql += " AND bank = ?"
            params.append(req.bank.upper())
        if req.status:
            sql += " AND status_code = ?"
            params.append(req.status)
        if req.severity:
            sql += " AND severity_code = ?"
            params.append(req.severity)
        if req.priority:
            sql += " AND priority_code = ?"
            params.append(req.priority)
        sql += " ORDER BY production_date DESC, event_at DESC, severity_code, priority_code LIMIT ?"
        params.append(req.limit)

        rows = conn.execute(sql, params).fetchall()

        summary = conn.execute(
            """
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN status_code NOT IN ('closed','cancelled') THEN 1 ELSE 0 END) AS open_n,
                SUM(CASE WHEN severity_code = 'critical' THEN 1 ELSE 0 END) AS critical_n,
                SUM(CASE WHEN severity_code = 'warning' THEN 1 ELSE 0 END) AS warning_n,
                SUM(CASE WHEN record_type = 'incident' THEN 1 ELSE 0 END) AS incidents
            FROM alarm_records
            WHERE active = 1 AND source_kind = 'pdf'
              AND production_date BETWEEN ? AND ?
            """,
            (date_from, date_to),
        ).fetchone()

        recurrent = conn.execute(
            """
            SELECT COALESCE(measurement_point, tag, '') AS point, title, record_type,
                   COUNT(*) AS n,
                   SUM(CASE WHEN status_code NOT IN ('closed','cancelled') THEN 1 ELSE 0 END) AS open_n
            FROM alarm_records
            WHERE active = 1 AND source_kind = 'pdf'
              AND production_date BETWEEN ? AND ?
            GROUP BY COALESCE(measurement_point, tag, ''), title, record_type
            HAVING COUNT(*) > 1
            ORDER BY n DESC
            LIMIT 15
            """,
            (date_from, date_to),
        ).fetchall()
    finally:
        conn.close()

    if not rows:
        return {
            "content": f"Não há alarmes FCS320 no período **{date_from}** a **{date_to}**.",
            "provider": req.provider or "kimi",
            "model": req.model or "moonshot-v1-8k",
            "input_tokens": 0,
            "output_tokens": 0,
            "conversation_id": None,
            "message_id": None,
            "meta": {"date_from": date_from, "date_to": date_to, "count": 0},
        }

    alarm_lines = []
    for r in rows:
        alarm_lines.append(
            f"#{r['id']} {r['production_date']} {r['event_at'] or ''} | "
            f"{r['bank'] or 'n/d'} {r['measurement_point'] or r['tag'] or ''} | "
            f"{r['record_type']} | {r['title']} | "
            f"sev={r['severity_code']} prior={r['priority_code']} status={r['status_code']} | "
            f"ocorrencias={r['occurrence_count'] or 1}"
        )

    recurrent_lines = [
        f"{r['point'] or 'n/d'} | {r['record_type']} | {r['title']}: "
        f"{r['n']} ocorrências, {r['open_n']} abertas"
        for r in recurrent
    ]

    user_prompt = f"""Analise os alarmes FCS320 do período {date_from} a {date_to}.

=== Sumário do período ===
Total: {summary['total'] or 0} | Abertos: {summary['open_n'] or 0} | Críticos: {summary['critical_n'] or 0} | Warnings: {summary['warning_n'] or 0} | Incidentes: {summary['incidents'] or 0}

=== Alarmes mais recorrentes ===
{chr(10).join(recurrent_lines) if recurrent_lines else 'Nenhum padrão recorrente identificado.'}

=== Lista detalhada dos alarmes ===
{chr(10).join(alarm_lines)}

Forneça:
1. Resumo executivo (2-3 parágrafos)
2. Top 5 alarmes que merecem atenção imediata, com justificativa
3. Padrões / recorrências operacionalmente relevantes
4. Sugestões de ação práticas e rastreáveis
5. Riscos se não forem tratados
"""

    system = (
        SYSTEM_MPFM
        + "\n\n"
        + RESPONSE_FORMAT_INSTRUCTIONS
        + "\n\n"
        + "Você está analisando alarmes do sistema FCS320 de medidores multifásicos offshore. "
        "Seja direto, técnico e operacional. Agrupe por ponto de medição e tipo de problema quando possível. "
        "Sugira ações concretas e indique quais alarmes devem virar pendências rastreáveis."
    )

    result = await _call_ai_agent(
        system=system,
        user=user_prompt,
        provider=req.provider or "kimi",
        model=req.model,
        conversation_title=f"Análise alarmes {date_from} a {date_to}",
        source_page="alertas",
        request_type="agent_alarms",
    )
    result["meta"] = {"date_from": date_from, "date_to": date_to, "count": len(rows)}
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Agente de Qualidade do Fechamento Diário
# ─────────────────────────────────────────────────────────────────────────────

class ClosingAgentRequest(BaseModel):
    date: Optional[str] = Field(None, description="Dia de referência (YYYY-MM-DD); padrão = ontem")
    provider: Optional[str] = Field("kimi", description="Provider de IA")
    model: Optional[str] = Field(None, description="Modelo específico")


@router.post("/fechamento", summary="Qualidade do fechamento diário")
async def ai_agent_fechamento(req: ClosingAgentRequest):
    """
    Analisa a qualidade do fechamento diário (MPFM, SEP, XML042, alarmes, cards)
    e retorna status, lacunas, desvios e ações recomendadas.
    """
    day = _normalize_date(req.date, -1)
    month = day[:7]

    conn = _ai_db_conn()
    try:
        # MPFM diário
        mpfm_rows = conn.execute(
            """
            SELECT bank, tag, instrument, metric_name, metric_value
            FROM measurements_curated
            WHERE day_ref = ? AND row_kind = 'daily' AND is_official = 1
            ORDER BY bank, tag, metric_name
            """,
            (day,),
        ).fetchall()

        # SEP do dia
        sep_rows = conn.execute(
            """
            SELECT sa.bank, sa.mpfm_tag, sa.sep_tag, sa.sep_meter_id,
                   m.metric_name, m.metric_value
            FROM sep_alignments sa
            LEFT JOIN measurements_curated m
              ON m.day_ref = sa.production_date
             AND m.tag = sa.sep_tag
             AND m.row_kind = 'daily'
             AND m.is_official = 1
            WHERE sa.production_date = ? AND sa.is_active = 1
            ORDER BY sa.bank, sa.sep_tag
            """,
            (day,),
        ).fetchall()

        # XML042 do dia
        xml_rows = conn.execute(
            """
            SELECT production_day, cod_cadastro_poco, well_operator_name, subsea_tag,
                   bank, oil_sm3, gas_1000sm3, water_sm3, ind_valido
            FROM xml042_imported_rows
            WHERE production_day = ?
            ORDER BY bank, cod_cadastro_poco
            """,
            (day,),
        ).fetchall()

        # Alarmes do dia
        alarm_rows = conn.execute(
            """
            SELECT id, production_date, event_at, bank, measurement_point, tag,
                   title, severity_code, priority_code, status_code
            FROM alarm_records
            WHERE active = 1 AND source_kind = 'pdf'
              AND production_date = ?
              AND status_code NOT IN ('closed','cancelled')
            ORDER BY severity_code, priority_code
            LIMIT 30
            """,
            (day,),
        ).fetchall()

        # Cards do dia
        card_rows = conn.execute(
            """
            SELECT production_date, bank, card_type, tag, instrument, title,
                   flow_velocity_ms, dp_value, sep_test_aligned
            FROM daily_cards
            WHERE production_date = ? AND is_active = 1
            ORDER BY bank, card_type, tag
            LIMIT 50
            """,
            (day,),
        ).fetchall()

        # Issues de validação do dia
        issue_rows = conn.execute(
            """
            SELECT issue_type, severity, ref_key, details
            FROM validation_issues
            WHERE day_ref = ?
            ORDER BY severity
            LIMIT 20
            """,
            (day,),
        ).fetchall()

        # Cobertura horária
        hour_rows = conn.execute(
            """
            SELECT hour_ref, COUNT(DISTINCT bank) AS banks, COUNT(*) AS points
            FROM measurements_curated
            WHERE day_ref = ? AND row_kind = 'hourly'
            GROUP BY hour_ref
            ORDER BY hour_ref
            """,
            (day,),
        ).fetchall()
    finally:
        conn.close()

    # Monta contexto textual
    sections = []
    sections.append(f"=== Data de referência: {day} (mês {month}) ===")

    sections.append("\n=== MPFM Diário ===")
    if mpfm_rows:
        mpfm_lines = []
        for r in mpfm_rows:
            mpfm_lines.append(
                f"{r['bank']} {r['tag']} {r['instrument']}: {r['metric_name']} = {r['metric_value']}"
            )
        sections.extend(mpfm_lines[:60])
    else:
        sections.append("Sem dados MPFM diários para este dia.")

    sections.append("\n=== Separador ===")
    if sep_rows:
        sep_lines = []
        for r in sep_rows:
            sep_lines.append(
                f"{r['bank']} {r['mpfm_tag']} x {r['sep_tag']} ({r['sep_meter_id']}): "
                f"{r['metric_name']} = {r['metric_value']}"
            )
        sections.extend(sep_lines[:40])
    else:
        sections.append("Sem alinhamentos SEP para este dia.")

    sections.append("\n=== XML 042 ===")
    if xml_rows:
        for r in xml_rows:
            sections.append(
                f"{r['bank']} {r['subsea_tag']} ({r['cod_cadastro_poco']}): "
                f"óleo={r['oil_sm3']} Sm³  gás={r['gas_1000sm3']} 1000Sm³  água={r['water_sm3']} Sm³  válido={r['ind_valido']}"
            )
    else:
        sections.append("Sem XML 042 importado para este dia.")

    sections.append("\n=== Alarmes em aberto ===")
    if alarm_rows:
        for r in alarm_rows:
            sections.append(
                f"#{r['id']} {r['bank']} {r['measurement_point'] or r['tag']}: {r['title']} "
                f"[sev={r['severity_code']}/prior={r['priority_code']}/status={r['status_code']}]"
            )
    else:
        sections.append("Sem alarmes FCS320 em aberto para este dia.")

    sections.append("\n=== Cards diários ===")
    if card_rows:
        for r in card_rows:
            extra = []
            if r['flow_velocity_ms']:
                extra.append(f"v={r['flow_velocity_ms']}")
            if r['dp_value']:
                extra.append(f"dp={r['dp_value']}")
            if r['sep_test_aligned']:
                extra.append(f"sep={r['sep_test_aligned']}")
            suffix = f" ({', '.join(extra)})" if extra else ""
            sections.append(
                f"{r['bank']} {r['card_type']} {r['tag']}: {r['title']}{suffix}"
            )
    else:
        sections.append("Sem cards diários para este dia.")

    sections.append("\n=== Issues de validação ===")
    if issue_rows:
        for r in issue_rows:
            sections.append(f"{r['severity']} | {r['issue_type']} | {r['ref_key']}: {r['details']}")
    else:
        sections.append("Sem issues de validação para este dia.")

    sections.append("\n=== Cobertura horária ===")
    if hour_rows:
        for r in hour_rows:
            sections.append(f"Hora {r['hour_ref']:02d}: {r['banks']} bancos, {r['points']} pontos")
    else:
        sections.append("Sem dados horários para este dia.")

    user_prompt = (
        f"Analise a qualidade do fechamento diário de {day} com base nos dados abaixo.\n\n"
        + "\n".join(sections)
        + "\n\nForneça:\n"
        "1. Status geral do fechamento (pronto / com ressalvas / bloqueado)\n"
        "2. Principais lacunas ou inconsistências entre MPFM, SEP e XML042\n"
        "3. Desvios ou outliers que merecem investigação\n"
        "4. Alarmes e cards que impactam o fechamento\n"
        "5. Ações recomendadas em ordem de prioridade\n"
        "6. Checklist mínimo para liberar o fechamento D-1"
    )

    system = (
        SYSTEM_MPFM
        + "\n\n"
        + RESPONSE_FORMAT_INSTRUCTIONS
        + "\n\n"
        + "Você é um revisor técnico de fechamento diário de medição multifásica offshore. "
        "Avalie a consistência entre MPFM, separador e XML042. Seja prático e indique ações rastreáveis. "
        "Não invente dados; use apenas o contexto fornecido."
    )

    result = await _call_ai_agent(
        system=system,
        user=user_prompt,
        provider=req.provider or "kimi",
        model=req.model,
        conversation_title=f"Fechamento {day}",
        source_page="painel-operador",
        request_type="agent_fechamento",
    )
    result["meta"] = {"date": day, "month": month}
    return result
