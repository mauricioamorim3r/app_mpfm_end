from __future__ import annotations

from copy import deepcopy
from datetime import datetime

from services.ops.monitoring_service import list_monitoring_rows


def _field(
    key: str,
    label: str,
    *,
    section: str,
    field_type: str = "text",
    options: list[str] | list[dict] | None = None,
    rows: int = 3,
    width: str = "half",
    placeholder: str = "",
) -> dict:
    return {
        "key": key,
        "label": label,
        "section": section,
        "type": field_type,
        "options": options or [],
        "rows": rows,
        "width": width,
        "placeholder": placeholder,
    }


ROTINA_ACTIVITY_DEF = [
    {"id": "A01", "title": "Confirmar fechamento do relatório diário", "criterion": "Relatório disponível, período correto e sem ausência injustificada de medidores ou bancos."},
    {"id": "A02", "title": "Verificar integridade de comunicação e atualização dos dados", "criterion": "Dados atualizados, sem falha persistente de comunicação e relógio coerente com o sistema."},
    {"id": "A03", "title": "Analisar alarmes, warnings e eventos", "criterion": "Toda ocorrência relevante analisada, classificada e registrada."},
    {"id": "A04", "title": "Verificar status operacional do medidor e do cálculo", "criterion": "Modo coerente com a operação, sem fallback injustificado."},
    {"id": "A05", "title": "Verificar variáveis principais de processo e diagnóstico", "criterion": "Variáveis presentes, coerentes e sem congelamento indevido."},
    {"id": "A06", "title": "Verificar coerência de PVT e conversão para condição padrão", "criterion": "Sem indício de erro sistemático de conversão ou incoerência forte."},
    {"id": "A07", "title": "Monitorar desvio de desempenho topside vs subsea", "criterion": "Desvio dentro da faixa ou com tendência e ação registradas."},
    {"id": "A08", "title": "Verificar integridade de transmissor e redundância A/B", "criterion": "Sem troca não rastreada e sem suspeita ignorada."},
    {"id": "A09", "title": "Gerar logs para análise aprofundada, quando necessário", "criterion": "Log gerado, salvo e vinculado ao problema, quando aplicável."},
    {"id": "A10", "title": "Registrar ação, responsável e prazo", "criterion": "Toda ocorrência relevante com tratativa rastreável."},
]

ROTINA_VARIABLE_DEF = [
    ["V01", "Pressão", "bar", "Valor coerente com a condição operacional e sem congelamento."],
    ["V02", "Temperatura", "°C", "Valor coerente com a condição operacional e sem congelamento."],
    ["V03", "dP de Venturi", "bar", "Sinal disponível e fisicamente plausível."],
    ["V04", "Gamma count", "counts/s", "Tendência coerente e sem comportamento anormal."],
    ["V05", "DensityOil", "kg/m³", "Valor disponível e consistente com histórico/processo."],
    ["V06", "DensityGas", "kg/m³", "Valor disponível e consistente com histórico/processo."],
    ["V07", "DensityWater", "kg/m³", "Confirmar se medido ou manual quando aplicável."],
    ["V08", "WLR", "%", "Valor coerente com histórico e condição do poço."],
    ["V09", "GVF", "%", "Valor coerente com histórico e condição do poço."],
    ["V10", "Vazão óleo padrão", "Sm³/d", "Valor coerente com produção esperada."],
    ["V11", "Vazão gás padrão", "Sm³/d", "Valor coerente com produção esperada."],
    ["V12", "Vazão água padrão", "Sm³/d", "Valor coerente com produção esperada."],
]


def _rotina_fields() -> list[dict]:
    return [
        _field("record_code", "Código do registro", section="identificacao"),
        _field("base_date", "Data-base D-1", section="identificacao", field_type="date"),
        _field("analysis_datetime", "Data/hora da análise", section="identificacao", field_type="datetime-local"),
        _field("period_ref", "Período de referência", section="identificacao"),
        _field("measurement_point", "Ponto de medição", section="identificacao", field_type="measurement-point", width="half"),
        _field("bank", "Banco", section="identificacao"),
        _field("tag", "TAG", section="identificacao"),
        _field("instrument", "Instrumento", section="identificacao"),
        _field("loop", "Loop", section="identificacao"),
        _field("meter_type", "Tipo", section="identificacao"),
        _field("unit_project", "Unidade / Projeto", section="identificacao"),
        _field("offshore_analyst", "Técnico / analista offshore", section="identificacao"),
        _field("offshore_role", "Função offshore", section="identificacao"),
        _field("consulted_operator", "Operação consultada", section="identificacao"),
        _field("onshore_reviewer", "Responsável medição onshore", section="identificacao"),
        _field("offshore_conclusion", "Conclusão offshore", section="encerramento", field_type="select", options=["", "Sem anomalia relevante", "Com ressalvas", "Com anomalia relevante", "Necessita suporte especializado"]),
        _field("onshore_status", "Status de revisão onshore", section="encerramento", field_type="select", options=["", "Pendente revisão", "Em validação", "Fechado D-1", "Fechado com ressalvas", "Bloqueado"]),
        _field("overview_note", "Observação geral do dia", section="encerramento", field_type="textarea", rows=4, width="full"),
        _field("escalation_dest", "Escalonamento principal", section="encerramento", field_type="select", options=["", "Nenhum / não necessário", "Automação / TI industrial", "Instrumentação", "Operação / Produção", "Fornecedor / suporte especializado", "Medição onshore"]),
        _field("attachments_ref", "Pasta / protocolo / referência de anexos", section="encerramento"),
        _field("next_day_focus", "Ponto de atenção para o dia seguinte", section="encerramento"),
        _field("suggested_status", "Status sugerido pelo formulário", section="encerramento"),
        _field("onshore_review_date", "Data da revisão onshore", section="encerramento", field_type="date"),
        _field("final_decision", "Decisão final do dia", section="encerramento", field_type="select", options=["", "Fechar D-1 normalmente", "Fechar D-1 com ressalvas", "Manter acompanhamento", "Bloquear fechamento até análise complementar"]),
        _field("offshore_note", "Comentário do técnico offshore", section="encerramento", field_type="textarea", rows=3, width="full"),
        _field("onshore_note", "Comentário do responsável onshore", section="encerramento", field_type="textarea", rows=3, width="full"),
    ]


LOGBOOK_DOC_TYPES = [
    "", "Certificado de calibração", "Boletim de cromatografia", "Estudo PVT",
    "Relatório de inspeção", "Relatório técnico", "Plano de ação", "Procedimento", "Outro",
]
LOGBOOK_DISCIPLINES = ["", "Medição", "Metrologia", "Reservatórios", "Processo", "Instrumentação", "Qualidade", "Outro"]
LOGBOOK_SOURCES = ["", "E-mail", "SharePoint", "Pasta de rede", "Sistema interno", "Fornecedor / laboratório", "Outro"]
LOGBOOK_LINKED_KIND = ["", "Registro mestre", "Evidência associada", "Substitui documento anterior", "Complementa análise", "Anexo de suporte"]
LOGBOOK_FORM_TYPES = ["", "Análise PVT", "Boletim de cromatografia", "Certificado de calibração", "Análise crítica", "Logbook", "Outro HTML"]
LOGBOOK_CHANNELS = ["", "E-mail", "Portal", "Pasta compartilhada", "Laboratório / fornecedor", "Entrega interna", "Outro"]
LOGBOOK_PERIODICITY = ["", "Pontual", "Mensal", "Trimestral", "Semestral", "Anual", "Sob demanda"]
LOGBOOK_STATUS = ["", "Recebido", "Em análise", "Pendente", "Concluído", "Substituído", "Obsoleto"]
LOGBOOK_CRITICALITY = ["", "Alta", "Média", "Baixa"]
LOGBOOK_PRIORITY = ["", "Urgente", "Alta", "Normal", "Baixa"]
LOGBOOK_ACTIONS = ["", "Recebido e registrado", "Encaminhado para análise", "Em revisão técnica", "Solicitada complementação", "Aprovado / aceito", "Reprovado / devolvido", "Substituído", "Arquivado"]
LOGBOOK_FINAL_STATE = ["", "Aceito", "Aceito com ressalvas", "Pendente de complemento", "Rejeitado", "Substituído", "Obsoleto"]


def _logbook_fields() -> list[dict]:
    return [
        _field("record_code", "Código do registro", section="identificacao"),
        _field("reference_date", "Data de referência", section="identificacao", field_type="date"),
        _field("measurement_point", "Ponto relacionado", section="identificacao", field_type="measurement-point"),
        _field("bank", "Banco", section="identificacao"),
        _field("tag", "TAG", section="identificacao"),
        _field("instrument", "Instrumento", section="identificacao"),
        _field("doc_type", "Tipo de documento", section="identificacao", field_type="select", options=LOGBOOK_DOC_TYPES),
        _field("doc_subtype", "Subtipo", section="identificacao"),
        _field("doc_number", "Número do documento", section="identificacao"),
        _field("doc_title", "Título do documento", section="identificacao", width="full"),
        _field("issuer", "Emissor", section="identificacao"),
        _field("asset", "Ativo / sistema", section="identificacao"),
        _field("discipline", "Disciplina", section="identificacao", field_type="select", options=LOGBOOK_DISCIPLINES),
        _field("file_name", "Nome do arquivo", section="rastreabilidade"),
        _field("file_path", "Caminho / pasta", section="rastreabilidade", width="full"),
        _field("source_system", "Sistema de origem", section="rastreabilidade", field_type="select", options=LOGBOOK_SOURCES),
        _field("revision", "Revisão", section="rastreabilidade"),
        _field("linked_doc", "Documento vinculado", section="rastreabilidade"),
        _field("linked_kind", "Tipo de vínculo", section="rastreabilidade", field_type="select", options=LOGBOOK_LINKED_KIND),
        _field("related_reference", "Referência correlata", section="rastreabilidade"),
        _field("link_note", "Observação do vínculo", section="rastreabilidade", field_type="textarea", width="full"),
        _field("related_form_type", "Tipo de formulário associado", section="rastreabilidade", field_type="select", options=LOGBOOK_FORM_TYPES),
        _field("related_form_path", "Caminho do HTML relacionado", section="rastreabilidade", width="full"),
        _field("related_record_code", "Código do registro relacionado", section="rastreabilidade"),
        _field("related_record_note", "Nota do relacionamento", section="rastreabilidade", field_type="textarea", width="full"),
        _field("received_date", "Data de recebimento", section="tratativa", field_type="date"),
        _field("received_by", "Recebido por", section="tratativa"),
        _field("channel", "Canal", section="tratativa", field_type="select", options=LOGBOOK_CHANNELS),
        _field("review_required", "Requer revisão?", section="tratativa", field_type="select", options=["", "Sim", "Não"]),
        _field("due_date", "Prazo", section="tratativa", field_type="date"),
        _field("periodicity", "Periodicidade", section="tratativa", field_type="select", options=LOGBOOK_PERIODICITY),
        _field("expiry_date", "Validade / vencimento", section="tratativa", field_type="date"),
        _field("owner_area", "Área responsável", section="tratativa"),
        _field("current_owner", "Responsável atual", section="tratativa"),
        _field("status", "Status", section="tratativa", field_type="select", options=LOGBOOK_STATUS),
        _field("criticality", "Criticidade", section="tratativa", field_type="select", options=LOGBOOK_CRITICALITY),
        _field("priority", "Prioridade", section="tratativa", field_type="select", options=LOGBOOK_PRIORITY),
        _field("action_taken", "Ação tomada", section="tratativa", field_type="select", options=LOGBOOK_ACTIONS),
        _field("next_step", "Próximo passo", section="tratativa"),
        _field("last_action_date", "Data da última ação", section="tratativa", field_type="date"),
        _field("next_review_date", "Próxima revisão", section="tratativa", field_type="date"),
        _field("evidence_summary", "Resumo da evidência", section="encerramento", field_type="textarea", rows=4, width="full"),
        _field("technical_note", "Nota técnica", section="encerramento", field_type="textarea", rows=4, width="full"),
        _field("decision_basis", "Base da decisão", section="encerramento", field_type="textarea", rows=4, width="full"),
        _field("evidence_ref", "Referência de evidência", section="encerramento"),
        _field("history_log", "Histórico / trilha", section="encerramento", field_type="textarea", rows=5, width="full"),
        _field("final_state", "Estado final", section="encerramento", field_type="select", options=LOGBOOK_FINAL_STATE),
        _field("close_date", "Data de fechamento", section="encerramento", field_type="date"),
        _field("closed_by", "Fechado por", section="encerramento"),
        _field("archive_location", "Local de arquivamento", section="encerramento", width="full"),
        _field("final_note", "Observação final", section="encerramento", field_type="textarea", rows=4, width="full"),
    ]


PVT_STATUS = ["", "EM_ANALISE", "PENDENTE_INFO", "REVISADA", "CONCLUIDA"]
PVT_CONTEXTO = ["", "Desenvolvimento de reservatório", "Atualização de modelo composicional", "Otimização de produção", "Medição / alocação", "Investigação de amostra"]
PVT_FLUIDO = ["", "OLEO_PRETO", "OLEO_VOLATIL", "GAS_CONDENSADO", "GAS"]
PVT_FAMILIA = ["", "Black-oil", "Composicional", "Híbrido / comparativo"]
PVT_ESCOPO = ["", "PVT laboratorial completo", "Validação de amostra / recombinação", "Atualização de correlações", "Suporte a medição / alocação", "Revisão crítica de relatório recebido"]
PVT_BASE_AMOSTRA = ["", "Fundo (single phase)", "Superfície / separador", "Recombinada", "Mista / múltiplas correntes"]
PVT_ORIGEM_AMOSTRA = ["", "Bottomhole / downhole", "Separador de teste", "Separador de produção", "Cilindro de gás", "Frasco de condensado / óleo", "Recombinada em laboratório"]
PVT_BOOL3 = ["", "Sim", "Não", "Parcial", "Não informado", "Não evidenciado", "Não avaliado", "Não se aplica"]
PVT_COHERENCE = ["", "Coerente", "Inconsistente", "Não avaliado", "Não se aplica"]
PVT_APPROVAL = ["", "Aprovado", "Aprovado com ressalvas", "Pendente", "Não aprovado"]
PVT_POST_UPDATE = ["", "Executada", "Pendente", "Não se aplica"]


def _pvt_fields() -> list[dict]:
    return [
        _field("record_code", "Código do registro", section="identificacao"),
        _field("reference_date", "Data de referência", section="identificacao", field_type="date"),
        _field("analysis_date", "Data da análise", section="identificacao", field_type="date"),
        _field("measurement_point", "Ponto de medição", section="identificacao", field_type="measurement-point"),
        _field("bank", "Banco", section="identificacao"),
        _field("tag", "TAG", section="identificacao"),
        _field("instrument", "Instrumento", section="identificacao"),
        _field("status", "Status", section="identificacao", field_type="select", options=PVT_STATUS),
        _field("analise_num", "Número da análise", section="identificacao"),
        _field("relatorio_num", "Número do relatório", section="identificacao"),
        _field("cliente", "Cliente", section="identificacao"),
        _field("laboratorio", "Laboratório", section="identificacao"),
        _field("analista", "Analista", section="identificacao"),
        _field("analista_funcao", "Função do analista", section="identificacao"),
        _field("aprovador", "Aprovador", section="identificacao"),
        _field("storage_location", "Local de armazenamento", section="identificacao", width="full"),
        _field("ativo", "Ativo", section="contexto"),
        _field("campo", "Campo", section="contexto"),
        _field("reservatorio", "Reservatório", section="contexto"),
        _field("poco", "Poço", section="contexto"),
        _field("bacia", "Bacia", section="contexto"),
        _field("objetivo", "Objetivo", section="contexto"),
        _field("objetivo_detalhe", "Objetivo detalhado", section="contexto", field_type="textarea", rows=4, width="full"),
        _field("contexto", "Contexto", section="contexto", field_type="select", options=PVT_CONTEXTO),
        _field("escopo", "Escopo", section="contexto", field_type="select", options=PVT_ESCOPO),
        _field("familia_estudo", "Família do estudo", section="contexto", field_type="select", options=PVT_FAMILIA),
        _field("fluido", "Fluido", section="contexto", field_type="select", options=PVT_FLUIDO),
        _field("ponto_fase", "Ponto / fase", section="contexto"),
        _field("review_interval", "Intervalo de revisão", section="contexto"),
        _field("trigger_update", "Motivo do update", section="contexto", field_type="select", options=["", "Alteração significativa do fluido", "Periodicidade de reavaliação", "Indicador de desempenho MPFM", "Nova campanha de amostragem", "Outro"]),
        _field("api_base", "API base", section="amostra"),
        _field("data_relatorio", "Data do relatório", section="amostra", field_type="date"),
        _field("data_amostra", "Data da amostra", section="amostra", field_type="date"),
        _field("temp_amostra", "Temperatura da amostra", section="amostra"),
        _field("pres_amostra", "Pressão da amostra", section="amostra"),
        _field("base_amostra", "Base da amostra", section="amostra", field_type="select", options=PVT_BASE_AMOSTRA),
        _field("origem_amostra", "Origem da amostra", section="amostra", field_type="select", options=PVT_ORIGEM_AMOSTRA),
        _field("fase_coleta", "Fase da coleta", section="amostra"),
        _field("recipiente", "Recipiente", section="amostra"),
        _field("single_phase", "Single phase", section="amostra", field_type="select", options=PVT_BOOL3),
        _field("agua_livre", "Água livre", section="amostra", field_type="select", options=["", "Não", "Sim", "Não informado"]),
        _field("contaminacao", "Contaminação", section="amostra", field_type="select", options=["", "Sem indícios", "Leve", "Moderada", "Crítica", "Não informado"]),
        _field("contaminacao_origem", "Origem da contaminação", section="amostra"),
        _field("contaminacao_pct", "% contaminação", section="amostra"),
        _field("representativa", "Amostra representativa", section="amostra", field_type="select", options=["", "Sim", "Não", "Parcial"]),
        _field("criterio_repr", "Critério de representatividade", section="amostra", field_type="textarea", rows=3, width="full"),
        _field("drawdown", "Drawdown", section="amostra", field_type="select", options=["", "Não", "Sim", "Não evidenciado"]),
        _field("bifasico", "Bifásico", section="amostra", field_type="select", options=["", "Não", "Sim", "Não evidenciado"]),
        _field("cleanup", "Cleanup", section="amostra", field_type="select", options=["", "Sim", "Não", "Não informado"]),
        _field("obs_amostra", "Observações da amostra", section="amostra", field_type="textarea", rows=4, width="full"),
        _field("recombinada", "Recombinada", section="base_recomb", field_type="select", options=["", "Sim", "Não", "Não se aplica"]),
        _field("base_recomb", "Base de recombinação", section="base_recomb"),
        _field("sep_stages", "Estágios de separação", section="base_recomb"),
        _field("sep_p", "Pressões do separador", section="base_recomb"),
        _field("sep_t", "Temperaturas do separador", section="base_recomb"),
        _field("gor_campo", "GOR de campo", section="base_recomb"),
        _field("cgr_campo", "CGR de campo", section="base_recomb"),
        _field("gas_gravity_base", "Gravidade do gás base", section="base_recomb"),
        _field("rho_base", "Densidade base", section="base_recomb"),
        _field("mass_balance_ok", "Balanço de massa ok", section="consistencia", field_type="select", options=["", "Sim", "Não", "Parcial"]),
        _field("mass_balance_dev", "Desvio do balanço de massa", section="consistencia"),
        _field("diff_separator", "Consistência com separadores", section="consistencia", field_type="select", options=PVT_COHERENCE),
        _field("cme_cvd", "Coerência CME/CVD", section="consistencia", field_type="select", options=PVT_COHERENCE),
        _field("visc_trend", "Tendência viscosidade", section="consistencia", field_type="select", options=["", "Coerente", "Inconsistente", "Não avaliado"]),
        _field("dens_trend", "Tendência densidade", section="consistencia", field_type="select", options=["", "Coerente", "Inconsistente", "Não avaliado"]),
        _field("comp_trend", "Tendência composição", section="consistencia", field_type="select", options=["", "Coerente", "Inconsistente", "Não avaliada"]),
        _field("sat_consistency", "Consistência de saturação", section="consistencia", field_type="select", options=["", "Sim", "Não", "Parcial"]),
        _field("eos_model", "Modelo EoS", section="consistencia", field_type="select", options=["", "SRK", "Peng-Robinson", "Outro", "Não informado"]),
        _field("eos_params", "Parâmetros EoS", section="consistencia", field_type="textarea", rows=3, width="full"),
        _field("eos_dev", "Desvio EoS", section="consistencia"),
        _field("eos_criteria", "Critérios EoS", section="consistencia", field_type="textarea", rows=3, width="full"),
        _field("gradiente_gor", "Gradiente GOR", section="consistencia", field_type="select", options=PVT_COHERENCE),
        _field("gradiente_sat", "Gradiente saturação", section="consistencia", field_type="select", options=PVT_COHERENCE),
        _field("compartimentacao", "Compartimentação", section="consistencia", field_type="select", options=["", "Sem indício relevante", "Com indício de compartimentalização", "Não avaliado"]),
        _field("multi_eos", "Múltiplos EoS / fluidos", section="consistencia", field_type="select", options=["", "Não", "Sim, múltiplos fluidos", "Sim, múltiplos EoS", "Não avaliado"]),
        _field("units_consistency", "Consistência de unidades", section="consistencia", field_type="select", options=["", "Sim", "Não", "Parcial"]),
        _field("welltest_consistency", "Consistência com well test", section="consistencia", field_type="select", options=["", "Sim", "Não", "Não avaliado"]),
        _field("measured_simulated", "Medido x simulado", section="consistencia", field_type="select", options=["", "Apresentado e coerente", "Apresentado com ressalvas", "Não apresentado"]),
        _field("tests_summary", "Resumo dos testes", section="propriedades", field_type="textarea", rows=4, width="full"),
        _field("tests_gap", "Lacunas dos testes", section="propriedades", field_type="textarea", rows=3, width="full"),
        _field("prod_history", "Histórico de produção", section="propriedades", field_type="textarea", rows=3, width="full"),
        _field("rate_info", "Informações de vazão", section="propriedades", field_type="textarea", rows=3, width="full"),
        _field("faixa_aplicacao", "Faixa de aplicação", section="propriedades"),
        _field("new_version", "Nova versão", section="propriedades"),
        _field("prev_version", "Versão anterior", section="propriedades"),
        _field("model_version", "Versão do modelo", section="propriedades"),
        _field("c10_version", "Versão C10+", section="propriedades"),
        _field("blackoil_note", "Nota black-oil", section="propriedades", field_type="textarea", rows=3, width="full"),
        _field("gas_note", "Nota de gás", section="propriedades", field_type="textarea", rows=3, width="full"),
        _field("systems_note", "Nota de sistemas", section="propriedades", field_type="textarea", rows=3, width="full"),
        _field("obs_fluido", "Observações do fluido", section="propriedades", field_type="textarea", rows=3, width="full"),
        _field("observacoes", "Observações gerais", section="conclusao", field_type="textarea", rows=4, width="full"),
        _field("limitacoes", "Limitações", section="conclusao", field_type="textarea", rows=4, width="full"),
        _field("nc_criticas", "Não conformidades críticas", section="conclusao", field_type="textarea", rows=3, width="full"),
        _field("conclusao", "Conclusão técnica", section="conclusao", field_type="textarea", rows=5, width="full"),
        _field("verdict", "Veredito", section="conclusao"),
        _field("acao_recomendada", "Ação recomendada", section="conclusao"),
        _field("specialist_approval", "Aprovação especialista", section="conclusao", field_type="select", options=PVT_APPROVAL),
        _field("post_update", "Pós-update", section="conclusao", field_type="select", options=PVT_POST_UPDATE),
        _field("exp_comment", "Comentário de exportação", section="conclusao", field_type="textarea", rows=3, width="full"),
        _field("bo_pb", "Bo em Pb", section="correlacoes"),
        _field("bo_res", "Bo no reservatório", section="correlacoes"),
        _field("rs_pb", "Rs em Pb", section="correlacoes"),
        _field("rv", "Rv", section="correlacoes"),
        _field("bg", "Bg", section="correlacoes"),
        _field("co", "Co", section="correlacoes"),
        _field("pb", "Pb", section="correlacoes"),
        _field("dew", "Dew point", section="correlacoes"),
        _field("ug_res", "µg reservatório", section="correlacoes"),
        _field("uo_res", "µo reservatório", section="correlacoes"),
        _field("z_res", "Z reservatório", section="correlacoes"),
        _field("gas_gravity", "Gravidade do gás", section="correlacoes"),
        _field("rho_sto", "Rho STO", section="correlacoes"),
        _field("c7mw", "C7+ MW", section="correlacoes"),
        _field("cgr", "CGR", section="correlacoes"),
        _field("sat_dev", "Desvio de saturação", section="correlacoes"),
        _field("pres_res", "Pressão reservatório", section="correlacoes"),
        _field("temp_res", "Temperatura reservatório", section="correlacoes"),
    ]


SCHEMAS = {
    "rotina": {
        "title": "Rotina Diária MPFM Offshore",
        "code_prefix": "ROT",
        "sections": [
            {"id": "identificacao", "label": "Identificação do Dia"},
            {"id": "encerramento", "label": "Encerramento do D-1"},
        ],
        "fields": _rotina_fields(),
        "repeatable_sections": [
            {
                "id": "activities",
                "label": "Atividades padrão do procedimento",
                "columns": [
                    {"key": "id", "label": "ID", "type": "text", "readonly": True},
                    {"key": "title", "label": "Atividade", "type": "text", "readonly": True},
                    {"key": "criterion", "label": "Critério", "type": "text", "readonly": True},
                    {"key": "applicable", "label": "Aplicável", "type": "select", "options": ["", "Sim", "Não"]},
                    {"key": "status", "label": "Status", "type": "select", "options": ["", "Conforme", "Pendente", "Não conforme", "Não aplicável"]},
                    {"key": "time", "label": "Hora", "type": "time"},
                    {"key": "target", "label": "Alvo", "type": "text"},
                    {"key": "evidence", "label": "Evidência", "type": "text"},
                    {"key": "result", "label": "Resultado", "type": "textarea"},
                    {"key": "action", "label": "Ação", "type": "textarea"},
                ],
            },
            {
                "id": "meters",
                "label": "Condição operacional por medidor",
                "add_label": "+ Medidor",
                "columns": [
                    {"key": "tag", "label": "Tag", "type": "text"},
                    {"key": "area", "label": "Área", "type": "text"},
                    {"key": "online", "label": "Online", "type": "select", "options": ["", "Sim", "Não", "NA"]},
                    {"key": "communication", "label": "Comunicação", "type": "select", "options": ["", "Sim", "Não", "NA"]},
                    {"key": "alarms", "label": "Alarmes", "type": "select", "options": ["", "Sim", "Não", "NA"]},
                    {"key": "warnings", "label": "Warnings", "type": "select", "options": ["", "Sim", "Não", "NA"]},
                    {"key": "events", "label": "Eventos", "type": "select", "options": ["", "Sim", "Não", "NA"]},
                    {"key": "clock", "label": "Relógio", "type": "select", "options": ["", "Sim", "Não", "NA"]},
                    {"key": "trend", "label": "Tendência", "type": "select", "options": ["", "Sim", "Não", "NA"]},
                    {"key": "dataset", "label": "Dataset", "type": "select", "options": ["", "Correto", "Incorreto", "Indisponível"]},
                    {"key": "flow_status", "label": "Status de fluxo", "type": "select", "options": ["", "OK", "Atenção", "Falha", "Fallback/manual"]},
                    {"key": "mode", "label": "Modo", "type": "text"},
                    {"key": "ab", "label": "A/B", "type": "text"},
                    {"key": "live_pvt", "label": "PVT live", "type": "select", "options": ["", "Sim", "Não", "NA"]},
                    {"key": "pvt_warning", "label": "Aviso PVT", "type": "select", "options": ["", "Sim", "Não", "NA"]},
                    {"key": "conclusion", "label": "Conclusão", "type": "text"},
                ],
            },
            {
                "id": "variables",
                "label": "Verificação detalhada quando necessária",
                "add_label": "+ Variável",
                "columns": [
                    {"key": "var_id", "label": "Código", "type": "variable-preset", "options": [{"value": item[0], "label": f"{item[0]} · {item[1]}"} for item in ROTINA_VARIABLE_DEF]},
                    {"key": "name", "label": "Variável", "type": "text"},
                    {"key": "unit", "label": "Unidade", "type": "text"},
                    {"key": "criterion", "label": "Critério", "type": "text"},
                    {"key": "tag", "label": "Tag", "type": "text"},
                    {"key": "value", "label": "Valor", "type": "text"},
                    {"key": "status", "label": "Status", "type": "select", "options": ["", "Conforme", "Atenção", "Não conforme", "Pendente"]},
                    {"key": "evidence", "label": "Evidência", "type": "text"},
                    {"key": "notes", "label": "Observações", "type": "textarea"},
                ],
            },
            {
                "id": "deviations",
                "label": "Controle de desvio",
                "add_label": "+ Desvio",
                "columns": [
                    {"key": "line", "label": "Linha", "type": "text"},
                    {"key": "base", "label": "Base", "type": "text"},
                    {"key": "hc_ref", "label": "HC ref", "type": "number"},
                    {"key": "hc_cmp", "label": "HC comp", "type": "number"},
                    {"key": "hc_dev", "label": "Desvio HC", "type": "number", "readonly": True},
                    {"key": "hc_lim", "label": "Limite HC", "type": "number"},
                    {"key": "tot_ref", "label": "Total ref", "type": "number"},
                    {"key": "tot_cmp", "label": "Total comp", "type": "number"},
                    {"key": "tot_dev", "label": "Desvio Total", "type": "number", "readonly": True},
                    {"key": "tot_lim", "label": "Limite Total", "type": "number"},
                    {"key": "days", "label": "Dias", "type": "number"},
                    {"key": "status", "label": "Status", "type": "text", "readonly": True},
                    {"key": "evidence", "label": "Evidência", "type": "text"},
                    {"key": "comment", "label": "Comentário", "type": "textarea"},
                ],
            },
            {
                "id": "occurrences",
                "label": "Registro detalhado de ocorrências",
                "add_label": "+ Ocorrência",
                "columns": [
                    {"key": "occ_id", "label": "ID", "type": "text"},
                    {"key": "dt", "label": "Data/hora", "type": "datetime-local"},
                    {"key": "tag", "label": "Tag", "type": "text"},
                    {"key": "category", "label": "Categoria", "type": "select", "options": ["", "Comunicação", "Alarmes / warnings", "Eventos / mudança indevida", "Transmissor / A/B", "PVT / condição padrão", "Desvio topside vs subsea", "Variável crítica", "Outro"]},
                    {"key": "severity", "label": "Severidade", "type": "select", "options": ["", "Baixa", "Média", "Alta", "Crítica"]},
                    {"key": "description", "label": "Descrição", "type": "textarea"},
                    {"key": "evidence", "label": "Evidência", "type": "text"},
                    {"key": "impact", "label": "Impacto", "type": "textarea"},
                    {"key": "cause", "label": "Causa presumida", "type": "textarea"},
                    {"key": "immediate", "label": "Ação imediata", "type": "textarea"},
                    {"key": "corrective", "label": "Ação corretiva", "type": "textarea"},
                    {"key": "owner", "label": "Responsável", "type": "text"},
                    {"key": "due", "label": "Prazo", "type": "date"},
                    {"key": "status", "label": "Status", "type": "select", "options": ["", "Aberta", "Em andamento", "Concluída", "Monitoramento"]},
                    {"key": "ref", "label": "Referência", "type": "text"},
                ],
            },
            {
                "id": "actions",
                "label": "Tratativas abertas ou em andamento",
                "add_label": "+ Tratativa",
                "columns": [
                    {"key": "action_id", "label": "ID", "type": "text"},
                    {"key": "origin", "label": "Origem", "type": "text"},
                    {"key": "related", "label": "Relacionamento", "type": "text"},
                    {"key": "description", "label": "Descrição", "type": "textarea"},
                    {"key": "owner", "label": "Responsável", "type": "text"},
                    {"key": "due", "label": "Prazo", "type": "date"},
                    {"key": "priority", "label": "Prioridade", "type": "select", "options": ["", "Baixa", "Média", "Alta", "Crítica"]},
                    {"key": "status", "label": "Status", "type": "select", "options": ["", "Aberta", "Em andamento", "Concluída", "Cancelada"]},
                    {"key": "done", "label": "Concluída em", "type": "date"},
                    {"key": "effectiveness", "label": "Efetividade", "type": "text"},
                    {"key": "verification", "label": "Verificação", "type": "date"},
                    {"key": "notes", "label": "Observações", "type": "textarea"},
                ],
            },
        ],
    },
    "logbook": {
        "title": "Logbook de Documentos",
        "code_prefix": "LOG",
        "sections": [
            {"id": "identificacao", "label": "01 Identificação do Registro"},
            {"id": "rastreabilidade", "label": "02 Documento e Rastreabilidade"},
            {"id": "tratativa", "label": "03 Tratativa e Acompanhamento"},
            {"id": "encerramento", "label": "04 Encerramento"},
        ],
        "fields": _logbook_fields(),
        "repeatable_sections": [],
    },
    "pvt": {
        "title": "Análise PVT",
        "code_prefix": "PVT",
        "sections": [
            {"id": "identificacao", "label": "01 Documento e Rastreabilidade do Relatório PVT"},
            {"id": "contexto", "label": "02 Contexto da Análise"},
            {"id": "amostra", "label": "03 Amostra e Qualidade"},
            {"id": "base_recomb", "label": "04 Base de Recombinação"},
            {"id": "consistencia", "label": "05 Consistência Técnica"},
            {"id": "propriedades", "label": "06 Propriedades e Ensaios"},
            {"id": "correlacoes", "label": "07 Parâmetros e Correlações"},
            {"id": "conclusao", "label": "08 Conclusão e Decisão"},
        ],
        "fields": _pvt_fields(),
        "repeatable_sections": [],
    },
}


def get_record_definition(record_type: str) -> dict:
    record_type = str(record_type or "").strip().lower()
    if record_type not in SCHEMAS:
        raise ValueError(f"Tipo de registro inválido: {record_type}")
    return deepcopy(SCHEMAS[record_type])


def _normalize_point(value: str, normalize_tag_name_fn) -> str:
    return normalize_tag_name_fn(value or "")


def list_measurement_points(load_cadastro_fn) -> list[dict]:
    cadastro = load_cadastro_fn() or {}
    points = []
    seen = set()
    for section_name, meter_type in (("banks_subsea", "Subsea"), ("banks_topside", "Topside")):
        for entry in cadastro.get(section_name, []):
            if not entry.get("ativo", True):
                continue
            bank = str(entry.get("bank_code") or "").strip().upper()
            point = str(entry.get("sistema") or "").strip()
            instrument = str(entry.get("tag_associado") or "").strip()
            if not bank or not point:
                continue
            point_id = f"{bank}|{point}|{instrument}"
            if point_id in seen:
                continue
            seen.add(point_id)
            points.append(
                {
                    "id": point_id,
                    "bank": bank,
                    "measurement_point": point,
                    "tag": point,
                    "instrument": instrument,
                    "loop": str(entry.get("loop") or "").strip(),
                    "meter_type": meter_type,
                    "technology": str(entry.get("tecnologia") or "").strip(),
                    "stream": str(entry.get("stream") or "").strip(),
                    "well_name": str(entry.get("nome_anp") or "").strip(),
                    "equinor_well": str(entry.get("poco_equinor") or "").strip(),
                    "riser_pair": str(entry.get("chega_riser") or "").strip(),
                    "label": " · ".join([part for part in [bank, point, instrument, meter_type] if part]),
                }
            )
    points.sort(key=lambda item: (item["bank"], item["measurement_point"], item["instrument"]))
    return points


def build_schema_payload(record_type: str, *, load_cadastro_fn, visibility: dict | None = None) -> dict:
    definition = get_record_definition(record_type)
    visible_keys = list((visibility or {}).get("visible_keys") or [])
    if not visible_keys:
        visible_keys = [field["key"] for field in definition.get("fields", [])]
        visible_keys.extend(section["id"] for section in definition.get("repeatable_sections", []))
    return {
        "definition": definition,
        "measurement_points": list_measurement_points(load_cadastro_fn),
        "visibility": {"visible_keys": visible_keys},
        "visibility_items": [
            {"key": field["key"], "label": field["label"], "kind": "field"}
            for field in definition.get("fields", [])
        ] + [
            {"key": section["id"], "label": section["label"], "kind": "repeatable"}
            for section in definition.get("repeatable_sections", [])
        ],
    }


def generate_record_code(record_type: str, base_date: str = "") -> str:
    definition = get_record_definition(record_type)
    dt = datetime.now()
    suffix = base_date.replace("-", "") if base_date else dt.strftime("%Y%m%d")
    return f"{definition['code_prefix']}-{suffix}-{dt.strftime('%H%M%S')}"


def _point_by_id(load_cadastro_fn, point_id: str) -> dict | None:
    for point in list_measurement_points(load_cadastro_fn):
        if point["id"] == point_id:
            return point
    return None


def _daily_metrics_for_point(db_conn_fn, bank: str, point_tag: str, day_ref: str, normalize_tag_name_fn) -> dict:
    result = {"metrics": {}, "hours_available": 0, "issues": []}
    if not (bank and point_tag and day_ref):
        return result
    conn = db_conn_fn()
    cur = conn.cursor()
    rows = cur.execute(
        """
        SELECT row_kind, hour_ref, metric_name, metric_value, tag
        FROM measurements_active
        WHERE day_ref=? AND bank=? AND row_kind IN ('daily','hourly')
        """,
        (day_ref, bank),
    ).fetchall()
    issues = cur.execute(
        """
        SELECT issue_type, severity, details
        FROM validation_issues
        WHERE day_ref=? AND ref_key LIKE ?
        ORDER BY created_at DESC
        """,
        (day_ref, f"{bank}%"),
    ).fetchall()
    conn.close()
    norm_tag = normalize_tag_name_fn(point_tag)
    hours = set()
    metrics = {}
    for row in rows:
        if normalize_tag_name_fn(row["tag"] or "") != norm_tag:
            continue
        if row["row_kind"] == "daily":
            metrics[row["metric_name"]] = row["metric_value"]
        elif row["hour_ref"] is not None:
            hours.add(int(row["hour_ref"]))
    result["metrics"] = metrics
    result["hours_available"] = len(hours)
    result["issues"] = [dict(row) for row in issues]
    return result


def _monitoring_deviation_rows(db_conn_fn, point: dict, base_date: str, load_cadastro_fn, normalize_tag_name_fn) -> list[dict]:
    if not (point and base_date):
        return []
    payload = list_monitoring_rows(
        db_conn_fn,
        month=str(base_date)[:7],
        bank=point.get("bank", ""),
        tag=point.get("measurement_point", ""),
        meter_type=point.get("meter_type", ""),
        load_cadastro_fn=load_cadastro_fn,
        normalize_tag_name=normalize_tag_name_fn,
    )
    target_norm = normalize_tag_name_fn(point.get("measurement_point", ""))
    rows = []
    for row in payload.get("rows") or []:
        if row.get("production_date") != base_date:
            continue
        if str(row.get("bank") or "").upper() != point.get("bank", "").upper():
            continue
        if normalize_tag_name_fn(row.get("tag") or "") != target_norm:
            continue
        rows.append(
            {
                "line": row.get("pair_label") or f"{row.get('tag', '')} × {row.get('pair_tag', '')}",
                "base": row.get("meter_type") or "",
                "hc_ref": row.get("hc_reference"),
                "hc_cmp": row.get("hc_compare"),
                "hc_dev": row.get("hc_deviation_pct"),
                "hc_lim": payload.get("limits", {}).get("hc_pct", 10.0),
                "tot_ref": row.get("total_reference"),
                "tot_cmp": row.get("total_compare"),
                "tot_dev": row.get("total_deviation_pct"),
                "tot_lim": payload.get("limits", {}).get("total_pct", 7.0),
                "days": row.get("days_outside_limits") or 0,
                "status": row.get("status_label") or "",
                "evidence": row.get("pair_bank") or "",
                "comment": row.get("observations") or "",
            }
        )
    return rows


def _default_routine_activities() -> list[dict]:
    rows = []
    for item in ROTINA_ACTIVITY_DEF:
        rows.append(
            {
                "id": item["id"],
                "title": item["title"],
                "criterion": item["criterion"],
                "applicable": "Sim",
                "status": "",
                "time": "",
                "target": "",
                "evidence": "",
                "result": "",
                "action": "",
            }
        )
    return rows


def _compute_rotina_status(payload: dict) -> str:
    deviations = payload.get("deviations") or []
    occurrences = payload.get("occurrences") or []
    statuses = {str(item.get("status") or "").strip().lower() for item in deviations + occurrences}
    if any("protocolo" in status and "sgm-fm" in status for status in statuses):
        return "Bloqueado"
    if "crítica" in statuses or "critica" in statuses:
        return "Bloqueado"
    if {"não conforme", "nao conforme", "alta", "crítica", "critica"} & statuses:
        return "Com ressalvas"
    if any("dias consecutivos fora do limite" in status for status in statuses):
        return "Em acompanhamento"
    if any(status in {"aberta", "em andamento", "monitoramento", "atenção", "atencao"} for status in statuses):
        return "Em acompanhamento"
    return "Sem anomalia relevante"


def build_prefill_payload(
    record_type: str,
    *,
    db_conn_fn,
    load_cadastro_fn,
    normalize_tag_name_fn,
    point_id: str = "",
    base_date: str = "",
    reference_date: str = "",
) -> dict:
    record_type = str(record_type or "").strip().lower()
    point = _point_by_id(load_cadastro_fn, point_id) if point_id else None
    today = datetime.now().strftime("%Y-%m-%d")
    base_date = base_date or reference_date or today
    shared = {
        "record_code": generate_record_code(record_type, base_date),
        "measurement_point": point["measurement_point"] if point else "",
        "bank": point["bank"] if point else "",
        "tag": point["measurement_point"] if point else "",
        "instrument": point["instrument"] if point else "",
        "loop": point["loop"] if point else "",
        "meter_type": point["meter_type"] if point else "",
    }

    if record_type == "rotina":
        daily = _daily_metrics_for_point(db_conn_fn, shared["bank"], shared["tag"], base_date, normalize_tag_name_fn)
        metrics = daily["metrics"]
        deviations = _monitoring_deviation_rows(db_conn_fn, point, base_date, load_cadastro_fn, normalize_tag_name_fn) if point else []
        note_parts = []
        if metrics:
            note_parts.append(f"HC: {metrics.get('MPFM corr HC (t)', '—')} t | Total: {metrics.get('MPFM corr Total (t)', '—')} t | Horas: {daily['hours_available']}/24.")
        if daily["issues"]:
            note_parts.append(f"Issues do dia: {len(daily['issues'])}.")
        payload = {
            **shared,
            "base_date": base_date,
            "analysis_datetime": datetime.now().strftime("%Y-%m-%dT%H:%M"),
            "period_ref": f"D-1 · {base_date}",
            "unit_project": "Bacalhau FPSO",
            "offshore_analyst": "",
            "offshore_role": "",
            "consulted_operator": "",
            "onshore_reviewer": "",
            "offshore_conclusion": "",
            "onshore_status": "Pendente revisão",
            "overview_note": " ".join(note_parts).strip(),
            "escalation_dest": "",
            "attachments_ref": "",
            "next_day_focus": "",
            "suggested_status": "Com ressalvas" if deviations or daily["issues"] else "Sem anomalia relevante",
            "onshore_review_date": "",
            "final_decision": "",
            "offshore_note": "",
            "onshore_note": "",
            "activities": _default_routine_activities(),
            "meters": [
                {
                    "tag": shared["tag"],
                    "area": shared["meter_type"],
                    "online": "",
                    "communication": "",
                    "alarms": "",
                    "warnings": "",
                    "events": "",
                    "clock": "",
                    "trend": "",
                    "dataset": "Correto" if metrics else "",
                    "flow_status": "",
                    "mode": "",
                    "ab": "",
                    "live_pvt": "",
                    "pvt_warning": "",
                    "conclusion": "",
                }
            ] if point else [],
            "variables": [],
            "deviations": deviations,
            "occurrences": [],
            "actions": [],
        }
        payload["suggested_status"] = _compute_rotina_status(payload)
        return payload

    if record_type == "logbook":
        return {
            **shared,
            "reference_date": reference_date or base_date,
            "doc_type": "",
            "doc_subtype": "",
            "doc_number": "",
            "doc_title": f"Registro relacionado a {shared['measurement_point']}" if point else "",
            "issuer": "",
            "asset": point.get("stream", "") if point else "",
            "discipline": "Medição",
            "file_name": "",
            "file_path": "",
            "source_system": "",
            "revision": "",
            "linked_doc": "",
            "linked_kind": "",
            "related_reference": f"{shared['bank']} / {shared['tag']}" if point else "",
            "link_note": "",
            "related_form_type": "",
            "related_form_path": "",
            "related_record_code": "",
            "related_record_note": "",
            "received_date": reference_date or base_date,
            "received_by": "",
            "channel": "",
            "review_required": "Sim",
            "due_date": "",
            "periodicity": "Sob demanda",
            "expiry_date": "",
            "owner_area": "Medição",
            "current_owner": "",
            "status": "Recebido",
            "criticality": "",
            "priority": "Normal",
            "action_taken": "Recebido e registrado",
            "next_step": "",
            "last_action_date": "",
            "next_review_date": "",
            "evidence_summary": "",
            "technical_note": "",
            "decision_basis": "",
            "evidence_ref": "",
            "history_log": "",
            "final_state": "",
            "close_date": "",
            "closed_by": "",
            "archive_location": "",
            "final_note": "",
        }

    conn = db_conn_fn()
    cur = conn.cursor()
    pvt_row = None
    if shared["bank"] and shared["tag"]:
        rows = cur.execute(
            """
            SELECT *
            FROM pvt_params
            WHERE bank=? AND tag=?
            ORDER BY COALESCE(valid_from,'') DESC, id DESC
            LIMIT 1
            """,
            (shared["bank"], shared["tag"]),
        ).fetchall()
        pvt_row = dict(rows[0]) if rows else None
    conn.close()
    return {
        **shared,
        "reference_date": reference_date or base_date,
        "analysis_date": today,
        "status": "EM_ANALISE",
        "analise_num": "",
        "relatorio_num": "",
        "cliente": "Equinor",
        "laboratorio": "",
        "analista": "",
        "analista_funcao": "",
        "aprovador": "",
        "storage_location": "",
        "ativo": point.get("stream", "") if point else "",
        "campo": "Bacalhau",
        "reservatorio": "",
        "poco": point.get("well_name", "") or point.get("equinor_well", "") if point else "",
        "bacia": "",
        "objetivo": "Validação técnica do estudo PVT",
        "objetivo_detalhe": "",
        "contexto": "Medição / alocação" if point else "",
        "escopo": "Revisão crítica de relatório recebido",
        "familia_estudo": "",
        "fluido": "",
        "ponto_fase": shared["measurement_point"],
        "review_interval": "",
        "trigger_update": "",
        "api_base": "",
        "data_relatorio": "",
        "data_amostra": "",
        "temp_amostra": "",
        "pres_amostra": "",
        "base_amostra": "",
        "origem_amostra": "",
        "fase_coleta": "",
        "recipiente": "",
        "single_phase": "",
        "agua_livre": "",
        "contaminacao": "",
        "contaminacao_origem": "",
        "contaminacao_pct": "",
        "representativa": "",
        "criterio_repr": "",
        "drawdown": "",
        "bifasico": "",
        "cleanup": "",
        "obs_amostra": "",
        "recombinada": "",
        "base_recomb": "",
        "sep_stages": "",
        "sep_p": "",
        "sep_t": "",
        "gor_campo": pvt_row.get("rs") if pvt_row else "",
        "cgr_campo": "",
        "gas_gravity_base": pvt_row.get("rho_gas_std") if pvt_row else "",
        "rho_base": pvt_row.get("rho_oleo_std") if pvt_row else "",
        "mass_balance_ok": "",
        "mass_balance_dev": "",
        "diff_separator": "",
        "cme_cvd": "",
        "visc_trend": "",
        "dens_trend": "",
        "comp_trend": "",
        "sat_consistency": "",
        "eos_model": "",
        "eos_params": "",
        "eos_dev": "",
        "eos_criteria": "",
        "gradiente_gor": "",
        "gradiente_sat": "",
        "compartimentacao": "",
        "multi_eos": "",
        "units_consistency": "",
        "welltest_consistency": "",
        "measured_simulated": "",
        "tests_summary": "",
        "tests_gap": "",
        "prod_history": "",
        "rate_info": "",
        "faixa_aplicacao": "",
        "new_version": "",
        "prev_version": "",
        "model_version": "",
        "c10_version": "",
        "blackoil_note": "",
        "gas_note": "",
        "systems_note": "",
        "obs_fluido": "",
        "observacoes": pvt_row.get("notes") if pvt_row else "",
        "limitacoes": "",
        "nc_criticas": "",
        "conclusao": "",
        "verdict": "",
        "acao_recomendada": "",
        "specialist_approval": "",
        "post_update": "",
        "exp_comment": "",
        "bo_pb": "",
        "bo_res": "",
        "rs_pb": pvt_row.get("rs") if pvt_row else "",
        "rv": "",
        "bg": "",
        "co": "",
        "pb": "",
        "dew": "",
        "ug_res": "",
        "uo_res": "",
        "z_res": "",
        "gas_gravity": "",
        "rho_sto": "",
        "c7mw": "",
        "cgr": "",
        "sat_dev": "",
        "pres_res": "",
        "temp_res": "",
    }


def build_record_summary(record_type: str, payload: dict) -> dict:
    payload = payload or {}
    if record_type == "rotina":
        status = payload.get("suggested_status") or _compute_rotina_status(payload)
        title = payload.get("measurement_point") or payload.get("tag") or "Rotina diária"
        return {
            "title": f"{title} · {payload.get('base_date') or ''}".strip(" ·"),
            "status": status,
            "date": payload.get("base_date") or "",
            "context": "Rotina Diária",
        }
    if record_type == "logbook":
        title = payload.get("doc_title") or payload.get("doc_type") or "Logbook"
        return {
            "title": title,
            "status": payload.get("status") or "",
            "date": payload.get("reference_date") or payload.get("received_date") or "",
            "context": payload.get("measurement_point") or payload.get("asset") or "",
        }
    title = payload.get("objetivo") or payload.get("poco") or payload.get("measurement_point") or "Análise PVT"
    return {
        "title": title,
        "status": payload.get("status") or "",
        "date": payload.get("analysis_date") or payload.get("reference_date") or "",
        "context": payload.get("measurement_point") or payload.get("tag") or "",
    }
