'use strict';

let _flowContext = null;
let _flowActiveStep = 'verif';
let _flowActiveHour = null;
let _flowEditingItemId = null;

function flowEscape(value) {
  return String(value ?? '').replace(/[&<>"']/g, ch => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  })[ch]);
}

function flowFmt(value, digits = 3) {
  if (value === null || value === undefined || value === '') return '-';
  const n = Number(value);
  if (!Number.isFinite(n)) return String(value);
  return new Intl.NumberFormat('pt-BR', {
    minimumFractionDigits: 0,
    maximumFractionDigits: digits,
  }).format(n);
}

function flowPct(value, digits = 2) {
  const n = Number(value);
  if (!Number.isFinite(n)) return '-';
  return `${flowFmt(n, digits)}%`;
}

function flowDate(value) {
  if (!value) return '-';
  const m = String(value).match(/^(\d{4})-(\d{2})-(\d{2})/);
  return m ? `${m[3]}/${m[2]}/${m[1]}` : String(value);
}

function flowKindFromStatus(status) {
  const value = String(status || '').toUpperCase();
  if (value.includes('OK') || value.includes('APROV') || value.includes('CONFORME')) return 'ok';
  if (value.includes('VERIFICAR') || value.includes('ATEN') || value.includes('ALERTA')) return 'warn';
  if (value.includes('REPROV') || value.includes('FALHA') || value.includes('BLOQUE')) return 'err';
  return 'info';
}

function flowStatusLabel(kind) {
  return {
    ok: 'Conforme',
    warn: 'Atenção',
    err: 'Investigar',
    info: 'Informativo',
  }[kind] || 'Informativo';
}

function flowBuildUrl() {
  const params = new URLSearchParams();
  const runId = document.getElementById('flowRunSelect')?.value || '';
  const bank = document.getElementById('flowBank')?.value.trim() || '';
  const tag = document.getElementById('flowTag')?.value.trim() || '';
  const day = document.getElementById('flowDay')?.value || '';
  if (runId) params.set('run_id', runId);
  if (!runId && bank) params.set('bank', bank);
  if (!runId && tag) params.set('tag', tag);
  if (!runId && day) params.set('day_ref', day);
  const suffix = params.toString();
  return `${API}/methodology-flow/context${suffix ? `?${suffix}` : ''}`;
}

async function loadMethodologyFlow(silent = false) {
  const root = document.getElementById('flowRoot');
  const status = document.getElementById('flowStatus');
  if (!root) return;
  flowWireEvents();
  if (!silent && status) {
    status.textContent = 'Carregando fluxo metodológico com dados reais...';
    root.innerHTML = '<div class="card flow-empty">Carregando run e evidências...</div>';
  }
  try {
    const payload = await j(flowBuildUrl());
    _flowContext = payload;
    flowRenderRunSelect(payload);
    if (payload?.ok) {
      const steps = payload.steps || [];
      if (!steps.some(step => step.id === _flowActiveStep)) _flowActiveStep = steps[0]?.id || 'verif';
      const validHours = flowValidHours(payload);
      if (_flowActiveHour === null || !validHours.includes(Number(_flowActiveHour))) {
        _flowActiveHour = validHours[0] ?? flowAllHours(payload)[0] ?? 0;
      }
    }
    flowRender(payload);
    if (status) {
      status.textContent = payload.ok
        ? `Run #${payload.run.id} carregado com dados reais. Clique nas etapas ou nas horas para investigar.`
        : (payload.message || 'Sem dados de reconciliação.');
    }
  } catch (err) {
    if (status) status.textContent = `Falha ao carregar fluxo: ${err.message || err}`;
    root.innerHTML = '<div class="card flow-empty">Não foi possível carregar o fluxo metodológico.</div>';
  }
}

function flowWireEvents() {
  if (flowWireEvents.done) return;
  flowWireEvents.done = true;
  document.getElementById('flowLoadBtn')?.addEventListener('click', () => loadMethodologyFlow());
  document.getElementById('flowRunSelect')?.addEventListener('change', () => {
    _flowActiveHour = null;
    _flowEditingItemId = null;
    loadMethodologyFlow();
  });
  document.getElementById('flowClearFilters')?.addEventListener('click', () => {
    ['flowBank', 'flowTag', 'flowDay'].forEach(id => {
      const el = document.getElementById(id);
      if (el) el.value = '';
    });
    const sel = document.getElementById('flowRunSelect');
    if (sel) sel.value = '';
    _flowActiveHour = null;
    _flowEditingItemId = null;
    loadMethodologyFlow();
  });
}

function flowRenderRunSelect(payload) {
  const sel = document.getElementById('flowRunSelect');
  if (!sel) return;
  const selectedId = payload?.run?.id ? String(payload.run.id) : '';
  const runs = payload?.runs || [];
  sel.innerHTML = '<option value="">Último run disponível</option>' + runs.map(run => {
    const label = `#${run.id} · ${run.day_ref || '-'} · ${run.bank || '-'} / ${run.tag || '-'} · ${run.status_final || '-'}`;
    const selected = String(run.id) === selectedId ? ' selected' : '';
    return `<option value="${flowEscape(run.id)}"${selected}>${flowEscape(label)}</option>`;
  }).join('');
  if (selectedId) sel.value = selectedId;
}

function flowRender(payload) {
  const root = document.getElementById('flowRoot');
  if (!root) return;
  if (!payload?.ok) {
    root.innerHTML = `<div class="card flow-empty">${flowEscape(payload?.message || 'Nenhum run encontrado.')}</div>`;
    return;
  }

  const run = payload.run || {};
  const resumo = payload.resumo || {};
  const pvt = payload.pvt || payload.pvt_snapshot || {};
  const steps = payload.steps || [];
  const step = steps.find(item => item.id === _flowActiveStep) || steps[0] || {};
  const hour = flowSelectedHour(payload);
  const status = run.status_final || resumo.status_final || resumo.status_linha || '-';
  const statusKind = flowKindFromStatus(status);

  root.innerHTML = `
    <section class="flow-hero card">
      <div class="flow-hero__main">
        <div class="flow-runline">
          <span>Run #${flowEscape(run.id || '-')}</span>
          <span>${flowEscape(run.bank || '-')} / ${flowEscape(run.tag || '-')}</span>
          <span>${flowDate(run.day_ref)}</span>
          <span>${flowEscape(run.campaign_phase || 'baseline')}</span>
        </div>
        <h3>Fluxo metodológico como trilha de decisão</h3>
        <p>Use esta tela para entender o motivo do status, onde estão as evidências, quais horas sustentam o cálculo e qual etapa precisa de ação técnica.</p>
      </div>
      <div class="flow-decision ${statusKind}">
        <span>Decisão</span>
        <strong>${flowEscape(status)}</strong>
        <em>${flowPct(resumo.cobertura_pct ?? run.cobertura_pct, 1)} cobertura</em>
      </div>
    </section>

    <div class="flow-kpis">
      ${flowKpi('HC MPFM', `${flowFmt(resumo.massa_hc_mpfm_t, 2)} t`, `Ref. ${flowFmt(resumo.massa_hc_ref_t, 2)} t`, flowDeviationKind(resumo.desvio_hc_pct, pvt.limite_hc_pct))}
      ${flowKpi('Desvio HC', flowPct(resumo.desvio_hc_pct, 3), `Limite ${flowPct(pvt.limite_hc_pct, 1)}`, flowDeviationKind(resumo.desvio_hc_pct, pvt.limite_hc_pct))}
      ${flowKpi('Total MPFM', `${flowFmt(resumo.massa_total_mpfm_t, 2)} t`, `Ref. ${flowFmt(resumo.massa_total_ref_t, 2)} t`, flowDeviationKind(resumo.desvio_total_pct, pvt.limite_total_pct))}
      ${flowKpi('Desvio Total', flowPct(resumo.desvio_total_pct, 3), `Limite ${flowPct(pvt.limite_total_pct, 1)}`, flowDeviationKind(resumo.desvio_total_pct, pvt.limite_total_pct))}
    </div>

    <div class="flow-decision-board">
      <section class="card flow-step-rail">
        <div class="flow-card-head">
          <h3>Etapas do método</h3>
          <p>Clique para ver evidências e métricas usadas no run.</p>
        </div>
        <div class="flow-steps">
          ${steps.map(flowStepButton).join('')}
        </div>
      </section>

      <section class="card flow-focus">
        ${flowStepDetail(step)}
      </section>

      <section class="card flow-hour-card">
        <div class="flow-card-head">
          <h3>Hora selecionada</h3>
          <p>Diagnóstico horário vindo do cálculo real.</p>
        </div>
        ${flowHourDetail(hour)}
        <div class="flow-hour-strip">
          ${flowAllHours(payload).map(h => flowHourButton(payload, h)).join('')}
        </div>
      </section>
    </div>

    <div class="flow-analysis-grid">
      ${flowRegistryPanel(payload, step, hour)}
      ${flowSourcePanel(payload)}
      ${flowFormulaPanel(pvt)}
    </div>
  `;
}

function flowDeviationKind(value, limit) {
  const n = Math.abs(Number(value));
  const lim = Math.abs(Number(limit));
  if (!Number.isFinite(n) || !Number.isFinite(lim)) return 'info';
  return n <= lim ? 'ok' : 'warn';
}

function flowKpi(label, value, sub, kind = 'info') {
  return `
    <div class="card flow-kpi ${kind}">
      <span>${flowEscape(label)}</span>
      <strong>${flowEscape(value)}</strong>
      <em>${flowEscape(sub || '')}</em>
    </div>
  `;
}

function flowStepButton(step) {
  const active = step.id === _flowActiveStep ? ' active' : '';
  const kind = step.kind || 'info';
  return `
    <button type="button" class="flow-step-btn ${kind}${active}" data-flow-step="${flowEscape(step.id)}">
      <b>${flowEscape(step.num || '')}</b>
      <span>${flowEscape(step.title || 'Etapa')}</span>
      <em>${flowStatusLabel(kind)}</em>
    </button>
  `;
}

function flowStepDetail(step) {
  const metrics = step.metrics || [];
  const evidence = step.evidence || [];
  return `
    <div class="flow-focus-head">
      <span class="flow-step-num ${step.kind || 'info'}">${flowEscape(step.num || '-')}</span>
      <div>
        <h3>${flowEscape(step.title || 'Etapa')}</h3>
        <p>${flowEscape(step.summary || 'Sem descrição para a etapa selecionada.')}</p>
      </div>
      <strong class="flow-state ${step.kind || 'info'}">${flowStatusLabel(step.kind)}</strong>
    </div>
    <div class="flow-metric-grid">
      ${metrics.map(metric => `
        <div class="flow-metric">
          <span>${flowEscape(metric.label)}</span>
          <strong>${flowEscape(metric.value)}</strong>
        </div>
      `).join('')}
    </div>
    <div class="flow-evidence">
      <div class="flow-section-label">Evidências e premissas</div>
      ${(evidence.length ? evidence : ['Sem evidência adicional gravada para esta etapa.']).map(item => `
        <div class="flow-evidence-row">${flowEscape(item)}</div>
      `).join('')}
    </div>
  `;
}

function flowMapCard(step) {
  const active = step.id === _flowActiveStep ? ' active' : '';
  return `
    <button type="button" class="flow-map-card ${step.kind || 'info'}${active}" data-flow-step="${flowEscape(step.id)}">
      <b>${flowEscape(step.num || '')}</b>
      <span>${flowEscape(step.title || 'Etapa')}</span>
      <em>${flowEscape((step.metrics || [])[0]?.value || flowStatusLabel(step.kind))}</em>
    </button>
  `;
}

function flowRegistryPanel(payload, step, hour) {
  const run = payload.run || {};
  const items = payload.flow_items || [];
  const selected = items.find(item => Number(item.id) === Number(_flowEditingItemId)) || null;
  const basePayload = selected?.payload || {};
  const itemKey = selected?.item_key || step.id || '';
  const itemType = selected?.item_type || 'nota';
  const status = selected?.status || 'aberto';
  const scope = selected?.scope || 'etapa';
  const hourValue = basePayload.hour ?? hour.hour ?? '';
  const stepValue = basePayload.step_id || step.id || '';
  return `
    <section class="card flow-registry-panel">
      <div class="flow-card-head flow-registry-head">
        <div>
          <h3>Registros da trilha metrológica</h3>
          <p>CRUD único para notas, evidências, pendências técnicas, decisões e revisões ligadas ao run.</p>
        </div>
        <button type="button" class="btn ghost" data-flow-item-new>Novo</button>
      </div>

      <form class="flow-registry-form" data-flow-item-form>
        <input type="hidden" name="id" value="${flowEscape(selected?.id || '')}">
        <input type="hidden" name="run_id" value="${flowEscape(run.id || '')}">
        <input type="hidden" name="item_key" value="${flowEscape(itemKey)}">
        <input type="hidden" name="payload_step_id" value="${flowEscape(stepValue)}">
        <input type="hidden" name="payload_hour" value="${flowEscape(hourValue)}">
        <div class="flow-registry-fields">
          <label>
            <span>Tipo</span>
            <select name="item_type">
              ${flowOption('nota', 'Nota técnica', itemType)}
              ${flowOption('evidencia', 'Evidência', itemType)}
              ${flowOption('pendencia', 'Pendência', itemType)}
              ${flowOption('decisao', 'Decisão', itemType)}
              ${flowOption('revisao', 'Revisão limite/CV', itemType)}
            </select>
          </label>
          <label>
            <span>Status</span>
            <select name="status">
              ${flowOption('aberto', 'Aberto', status)}
              ${flowOption('em_andamento', 'Em andamento', status)}
              ${flowOption('resolvido', 'Resolvido', status)}
              ${flowOption('cancelado', 'Cancelado', status)}
            </select>
          </label>
          <label>
            <span>Escopo</span>
            <select name="scope">
              ${flowOption('etapa', 'Etapa atual', scope)}
              ${flowOption('hora', 'Hora selecionada', scope)}
              ${flowOption('run', 'Run completo', scope)}
              ${flowOption('fonte', 'Fonte/evidência', scope)}
            </select>
          </label>
          <label>
            <span>Responsável</span>
            <input name="owner" value="${flowEscape(selected?.owner || '')}" placeholder="Operador, metrologia, automação">
          </label>
          <label>
            <span>Prazo</span>
            <input name="due_date" type="date" value="${flowEscape(selected?.due_date || '')}">
          </label>
        </div>
        <label class="flow-registry-title">
          <span>Título</span>
          <input name="title" value="${flowEscape(selected?.title || '')}" placeholder="Ex.: revisar CV do ${flowEscape(run.tag || 'TAG')} na hora ${String(hour.hour ?? 0).padStart(2, '0')}">
        </label>
        <label class="flow-registry-summary">
          <span>Descrição / evidência</span>
          <textarea name="summary" rows="3" placeholder="Registre a conclusão, evidência, ação requerida ou premissa de cálculo.">${flowEscape(selected?.summary || '')}</textarea>
        </label>
        <div class="flow-registry-actions">
          <span>${selected ? `Editando #${flowEscape(selected.id)}` : `Novo registro para etapa ${flowEscape(step.num || '-')}, hora ${String(hour.hour ?? 0).padStart(2, '0')}:00`}</span>
          <button type="submit" class="btn">Salvar registro</button>
          ${selected ? `<button type="button" class="btn danger" data-flow-item-delete="${flowEscape(selected.id)}">Excluir</button>` : ''}
        </div>
      </form>

      <div class="flow-registry-list">
        ${items.length ? items.slice(0, 12).map(flowRegistryRow).join('') : '<div class="flow-registry-empty">Nenhum registro manual para este run ainda.</div>'}
      </div>
    </section>
  `;
}

function flowOption(value, label, current) {
  return `<option value="${flowEscape(value)}"${String(value) === String(current) ? ' selected' : ''}>${flowEscape(label)}</option>`;
}

function flowItemTypeLabel(type) {
  return {
    nota: 'Nota',
    evidencia: 'Evidência',
    pendencia: 'Pendência',
    decisao: 'Decisão',
    revisao: 'Revisão',
  }[type] || type || 'Registro';
}

function flowRegistryRow(item) {
  const payload = item.payload || {};
  const selected = Number(item.id) === Number(_flowEditingItemId) ? ' active' : '';
  const meta = [
    item.scope || 'run',
    payload.step_id ? `etapa ${payload.step_id}` : '',
    payload.hour !== undefined && payload.hour !== '' ? `${String(payload.hour).padStart(2, '0')}:00` : '',
    item.due_date ? `prazo ${flowDate(item.due_date)}` : '',
  ].filter(Boolean).join(' · ');
  return `
    <button type="button" class="flow-registry-row${selected}" data-flow-item-edit="${flowEscape(item.id)}">
      <span class="flow-registry-pill ${flowKindFromStatus(item.status)}">${flowEscape(flowItemTypeLabel(item.item_type))}</span>
      <strong>${flowEscape(item.title || 'Registro sem título')}</strong>
      <em>${flowEscape(meta || item.status || 'aberto')}</em>
      <small>${flowEscape(item.summary || '')}</small>
    </button>
  `;
}

function flowReadRegistryForm(form) {
  const data = new FormData(form);
  const hourRaw = data.get('payload_hour');
  const hour = hourRaw === '' ? null : Number(hourRaw);
  const runRaw = data.get('run_id');
  return {
    run_id: runRaw ? Number(runRaw) : null,
    item_type: String(data.get('item_type') || 'nota'),
    status: String(data.get('status') || 'aberto'),
    scope: String(data.get('scope') || 'run'),
    item_key: String(data.get('item_key') || ''),
    owner: String(data.get('owner') || ''),
    due_date: String(data.get('due_date') || ''),
    title: String(data.get('title') || '').trim(),
    summary: String(data.get('summary') || '').trim(),
    payload: {
      step_id: String(data.get('payload_step_id') || ''),
      hour: Number.isFinite(hour) ? hour : null,
    },
  };
}

async function flowSaveRegistryItem(form) {
  const id = form.elements.id?.value || '';
  const body = flowReadRegistryForm(form);
  const url = id ? `${API}/methodology-flow/items/${encodeURIComponent(id)}` : `${API}/methodology-flow/items`;
  const method = id ? 'PUT' : 'POST';
  await j(url, { method, headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body) });
  _flowEditingItemId = null;
  await loadMethodologyFlow(true);
}

async function flowDeleteRegistryItem(id) {
  if (!id) return;
  await j(`${API}/methodology-flow/items/${encodeURIComponent(id)}`, { method: 'DELETE' });
  _flowEditingItemId = null;
  await loadMethodologyFlow(true);
}

function getMethodologyFlowActionContext() {
  const run = _flowContext?.run || {};
  const step = (_flowContext?.steps || []).find(item => item.id === _flowActiveStep) || {};
  return {
    run_id: run.id || null,
    bank: run.bank || '',
    tag: run.tag || '',
    day_ref: run.day_ref || '',
    active_step: _flowActiveStep || '',
    active_step_title: step.title || '',
    active_hour: _flowActiveHour,
  };
}

function flowAllHours(payload) {
  const hours = new Set();
  for (const rows of [payload.calc_horas || [], payload.mpfm_horas || [], payload.sep_horas || []]) {
    rows.forEach(row => {
      const h = Number(row.hora);
      if (Number.isFinite(h) && h >= 0 && h <= 23) hours.add(h);
    });
  }
  return [...hours].sort((a, b) => a - b);
}

function flowValidHours(payload) {
  const calc = payload.calc_horas || [];
  const valid = calc.filter(row => row.hora_valida).map(row => Number(row.hora)).filter(Number.isFinite);
  if (valid.length) return valid;
  return flowAllHours(payload);
}

function flowRowAt(rows, hour) {
  return (rows || []).find(row => Number(row.hora) === Number(hour)) || {};
}

function flowSelectedHour(payload) {
  const hour = Number(_flowActiveHour ?? flowValidHours(payload)[0] ?? 0);
  return {
    hour,
    calc: flowRowAt(payload.calc_horas, hour),
    mpfm: flowRowAt(payload.mpfm_horas, hour),
    sep: flowRowAt(payload.sep_horas, hour),
  };
}

function flowHourKind(payload, hour) {
  const calc = flowRowAt(payload.calc_horas, hour);
  const status = calc.status_linha || calc.flag_bsw || '';
  if (!calc || !Object.keys(calc).length) return 'missing';
  if (calc.hora_valida || flowKindFromStatus(status) === 'ok') return 'ok';
  return flowKindFromStatus(status) === 'err' ? 'err' : 'warn';
}

function flowHourButton(payload, hour) {
  const active = Number(hour) === Number(_flowActiveHour) ? ' active' : '';
  const kind = flowHourKind(payload, hour);
  return `<button type="button" class="flow-hour ${kind}${active}" data-flow-hour="${hour}">${String(hour).padStart(2, '0')}</button>`;
}

function flowHourDetail(hour) {
  const calc = hour.calc || {};
  const mpfm = hour.mpfm || {};
  const sep = hour.sep || {};
  return `
    <div class="flow-hour-main">
      <div>
        <span>Hora</span>
        <strong>${String(hour.hour).padStart(2, '0')}:00</strong>
      </div>
      <div>
        <span>Status linha</span>
        <strong>${flowEscape(calc.status_linha || (calc.hora_valida ? 'OK' : 'SEM DADOS'))}</strong>
      </div>
    </div>
    <div class="flow-hour-metrics">
      <div><span>HC MPFM</span><strong>${flowFmt(mpfm.hc_corr_t, 3)} t</strong></div>
      <div><span>HC REF</span><strong>${flowFmt(calc.massa_hc_ref_t, 3)} t</strong></div>
      <div><span>Desvio HC</span><strong>${flowPct(calc.desvio_hc_linha_pct, 3)}</strong></div>
      <div><span>BSW SEP</span><strong>${flowPct(sep.bsw_user_pct ?? calc.bsw_user_pct, 2)}</strong></div>
      <div><span>GSV SEP</span><strong>${flowFmt(sep.gsv_sep_sm3 ?? calc.gsv_sep_sm3, 3)} Sm³</strong></div>
      <div><span>P/T MPFM</span><strong>${flowFmt(mpfm.pressao_barg, 1)} barg / ${flowFmt(mpfm.temperatura_c, 1)} °C</strong></div>
    </div>
  `;
}

function flowSourcePanel(payload) {
  const sepSources = payload.sep_sources || [];
  const alarms = payload.alarms || [];
  const deadlines = payload.deadlines || [];
  return `
    <section class="card flow-source-panel">
      <div class="flow-card-head">
        <h3>Rastreabilidade operacional</h3>
        <p>Arquivos, alarmes e atividades relacionados ao run.</p>
      </div>
      <div class="flow-trace-columns">
        <div>
          <div class="flow-section-label">Separador</div>
          ${sepSources.length ? sepSources.slice(0, 5).map(src => `
            <div class="flow-trace-row">
              <strong>${flowEscape(src.fluid_kind || '-')} · ${flowEscape(src.meter_id || '-')}</strong>
              <span>${flowEscape(src.source_file || '-')}</span>
            </div>
          `).join('') : '<div class="flow-trace-empty">Nenhuma fonte SEP vinculada ao dia.</div>'}
        </div>
        <div>
          <div class="flow-section-label">Alarmes e prazos</div>
          ${alarms.length ? alarms.slice(0, 3).map(alarm => `
            <div class="flow-trace-row">
              <strong>${flowEscape(alarm.severity_code || alarm.status_code || 'alarme')}</strong>
              <span>${flowEscape(alarm.title || alarm.message || '-')}</span>
            </div>
          `).join('') : '<div class="flow-trace-empty">Sem alarme direto encontrado para o run.</div>'}
          ${deadlines.length ? `<div class="flow-deadline-note">${deadlines.length} prazo(s) metodológicos disponíveis.</div>` : ''}
        </div>
      </div>
    </section>
  `;
}

function flowFormulaPanel(pvt) {
  return `
    <section class="card flow-formula-panel">
      <div class="flow-card-head">
        <h3>Memorial aplicado</h3>
        <p>Fórmulas usadas no backend com PVT do run.</p>
      </div>
      <div class="flow-formula-list">
        <code>NSV_sep = GSV_sep × (1 - BSW / 100)</code>
        <code>V_STO = NSV_sep × FE (${flowFmt(pvt.fe, 6)})</code>
        <code>V_gas_total = V_gas_sep + V_STO × ΔRs (${flowFmt(pvt.rs, 4)})</code>
        <code>m_HC_REF = m_oil_REF + m_gas_REF</code>
        <code>δ_HC = 100 × (m_HC_MPFM - m_HC_REF) / m_HC_REF</code>
      </div>
      <p>O limite fixo é exibido como critério interno do run. A interpretação técnica continua dependente de incerteza, envelope, PVT e evidências.</p>
    </section>
  `;
}

document.addEventListener('click', (event) => {
  const newItem = event.target.closest?.('[data-flow-item-new]');
  if (newItem && document.getElementById('page-fluxo')?.contains(newItem)) {
    _flowEditingItemId = null;
    flowRender(_flowContext);
    return;
  }
  const editItem = event.target.closest?.('[data-flow-item-edit]');
  if (editItem && document.getElementById('page-fluxo')?.contains(editItem)) {
    _flowEditingItemId = Number(editItem.dataset.flowItemEdit);
    flowRender(_flowContext);
    return;
  }
  const deleteItem = event.target.closest?.('[data-flow-item-delete]');
  if (deleteItem && document.getElementById('page-fluxo')?.contains(deleteItem)) {
    flowDeleteRegistryItem(deleteItem.dataset.flowItemDelete);
    return;
  }
  const step = event.target.closest?.('[data-flow-step]');
  if (step && document.getElementById('page-fluxo')?.contains(step)) {
    _flowActiveStep = step.dataset.flowStep;
    _flowEditingItemId = null;
    flowRender(_flowContext);
    return;
  }
  const hour = event.target.closest?.('[data-flow-hour]');
  if (hour && document.getElementById('page-fluxo')?.contains(hour)) {
    _flowActiveHour = Number(hour.dataset.flowHour);
    _flowEditingItemId = null;
    flowRender(_flowContext);
  }
});

document.addEventListener('submit', (event) => {
  const form = event.target.closest?.('[data-flow-item-form]');
  if (form && document.getElementById('page-fluxo')?.contains(form)) {
    event.preventDefault();
    flowSaveRegistryItem(form).catch(err => {
      const status = document.getElementById('flowStatus');
      if (status) status.textContent = `Falha ao salvar registro da trilha: ${err.message || err}`;
    });
  }
});

window.loadMethodologyFlow = loadMethodologyFlow;
window.getMethodologyFlowActionContext = getMethodologyFlowActionContext;
