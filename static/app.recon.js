'use strict';

let _reconCurrentRunId = null;
let _pvtAll = [];
let _reconCurrentProposal = null;
let _reconLatestDataCheck = null;
let _reconCurrentMemorial = null;

function readReconIsoInput(id) {
  const el = document.getElementById(id);
  if (!el) return '';
  if (el.dataset?.isoValue) return el.dataset.isoValue;
  if (typeof parseBrDateToIso === 'function') {
    return parseBrDateToIso(el.value || '') || '';
  }
  return el.value || '';
}

function fmtFactor(value) {
  return value == null ? '—' : new Intl.NumberFormat('pt-BR', {maximumFractionDigits: 6}).format(value);
}

function formatReconCampaignStatus(status) {
  return ({
    ready_for_application: 'Pronto para aplicar',
    ready_manual: 'Pronto (manual)',
    within_limits_no_change: 'Dentro do limite',
    missing_current_k: 'Sem K atual',
    insufficient_window: 'Janela incompleta',
    missing_reference: 'Sem referência',
    manual_required: 'Falta K manual',
    accepted: 'Aceito',
    improved_not_accepted: 'Melhorou, mas fora do limite',
    monitoring_attention: 'Monitorar com atenção',
    stable_or_worse: 'Estável / pior',
    rejected: 'Rejeitado',
    pending: 'Pendente',
    baseline_review: 'Revisar base',
    ready_for_k: 'Pronto para K',
    monitoring: 'Monitorando',
  })[status] || (status || '—');
}

function showReconTab(tab) {
  ['pvt', 'run', 'history', 'memorial'].forEach(t => {
    const pane = document.getElementById(`recon-tab-${t}`);
    if (pane) pane.style.display = t === tab ? 'block' : 'none';
    const btn = document.getElementById(`rtab-${t}`);
    if (btn) {
      if (t === tab) {
        btn.style.background = 'var(--accent)';
        btn.style.color = 'white';
        btn.style.borderColor = 'var(--accent)';
      } else {
        btn.style.background = 'var(--panel2)';
        btn.style.color = 'var(--muted)';
        btn.style.borderColor = 'var(--line)';
      }
    }
  });
  if (tab === 'history') {
    loadReconHistory();
    loadReconCampaigns();
  }
  if (tab === 'memorial') loadReconMemorial();
  if (tab === 'run') renderReconPvtPreview();
}

async function loadRecon() {
  setLoading('page-recon', true);
  try {
    await loadPVTTable();
    await loadReconBankOptions();
    await loadReconHistory();
    await loadReconCampaigns();
    showReconTab('run');
    renderReconAnalyticalSummary({});
    renderReconCampaignSummary(null, null);
    renderReconMemorial(null);
    updateReconActionState(null);
    renderReconReadinessRunbook(null);
  } finally {
    setLoading('page-recon', false);
  }
}

// ── PVT Cadastro ─────────────────────────────────────────────────────────────
async function loadPVTTable() {
  const d = await j('/api/pvt-params');
  _pvtAll = d.params || [];
  const tbody = document.getElementById('pvtRows');
  if (!_pvtAll.length) {
    tbody.innerHTML = '<tr><td colspan="15" style="color:var(--muted);text-align:center">Nenhum parâmetro cadastrado. Clique em "+ Novo".</td></tr>';
    return;
  }
  const GOR_LABELS = {fixed: 'GOR Fixo', zero: 'GOR Zero', triphasic: 'Trifásico', unknown: 'Desconhecido'};
  tbody.innerHTML = _pvtAll.map(p => `
    <tr>
      <td>${p.id}</td>
      <td><strong>${p.bank}</strong></td>
      <td>${p.tag}</td>
      <td>${fmt(p.fe)}</td>
      <td>${fmt(p.rs)}</td>
      <td>${fmt(p.rho_oleo_std)}</td>
      <td>${fmt(p.rho_gas_std)}</td>
      <td>${fmt(p.rho_agua_std)}</td>
      <td><span class="badge ${p.gsv_confirmed ? 'ok' : 'warn'}">${p.gsv_confirmed ? 'Sim' : 'Não'}</span></td>
      <td><span class="badge ${p.gor_mode === 'unknown' ? 'warn' : 'ok'}">${GOR_LABELS[p.gor_mode] || p.gor_mode}</span></td>
      <td>${p.limite_hc_pct}%</td>
      <td>${p.limite_total_pct}%</td>
      <td style="font-size:11px">${p.valid_from || '—'} → ${p.valid_to || '—'}</td>
      <td style="font-size:11px;max-width:120px;overflow:hidden;text-overflow:ellipsis">${p.source || '—'}</td>
      <td style="display:flex;gap:4px">
        <button class="btn sm" onclick="openPVTModal(${p.id})">✏</button>
        <button class="btn sm secondary" onclick="deletePVT(${p.id})">🗑</button>
      </td>
    </tr>`).join('');
}

function openPVTModal(id) {
  const p = id ? _pvtAll.find(x => x.id === id) : null;
  const html = `
    <div class="modal show pvt-inline-modal" id="pvtModal" role="dialog" aria-modal="true" aria-labelledby="pvtModalTitle" data-remove-on-close="true">
        <div class="modalbox modal-w720">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
          <h3 class="section-title modal-h3" id="pvtModalTitle">${p ? 'Editar' : 'Novo'} Parâmetro PVT</h3>
          <button class="btn secondary sm" onclick="closePVTModal()">✕</button>
        </div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
          ${pvtField('bank', 'Banco', p?.bank || '', false, 'B03, B05, B08, B10...')}
          ${pvtField('tag', 'TAG do Medidor', p?.tag || '', false, '18FT0506...')}
          ${pvtField('fe', 'FE - Fator Encolhimento', p?.fe || '', true, 'ex: 0.8689')}
          ${pvtField('rs', 'RS - Razão Solubilidade (sm³/sm³)', p?.rs || '', true, 'ex: 64.25')}
          ${pvtField('rho_oleo_std', 'Densidade Óleo Std (kg/m³)', p?.rho_oleo_std || '', true, 'ex: 858.66')}
          ${pvtField('rho_gas_std', 'Densidade Gás Std (kg/m³)', p?.rho_gas_std || '', true, 'ex: 0.8604')}
          ${pvtField('rho_agua_std', 'Densidade Água Std (kg/m³)', p?.rho_agua_std || 998.2, true, 'ex: 998.2')}
          ${pvtField('temp_ref_c', 'Temperatura Ref (°c)', p?.temp_ref_c || 20, true, '')}
          ${pvtField('pres_ref_bar', 'Pressão Ref (bar a)', p?.pres_ref_bar || 1.01325, true, '')}
          ${pvtField('limite_hc_pct', 'Limite Desvio HC (%)', p?.limite_hc_pct || 5, true, '')}
          ${pvtField('limite_total_pct', 'Limite Desvio Total (%)', p?.limite_total_pct || 5, true, '')}
          ${pvtField('limite_agua_pct', 'Limite Alerta Água (%)', p?.limite_agua_pct || 20, true, '')}
        </div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:12px">
          <label style="display:flex;flex-direction:column;gap:4px;font-size:12px">
            GOR Mode
            <select id="pvtf-gor_mode" class="input">
              ${['unknown', 'fixed', 'zero', 'triphasic'].map(v =>
                `<option value="${v}" ${(p?.gor_mode || 'unknown') === v ? 'selected' : ''}>${
                  {unknown: 'Desconhecido', fixed: 'GOR Fixo', zero: 'GOR Zero', triphasic: 'Trifásico'}[v]}</option>`).join('')}
            </select>
          </label>
          <label style="display:flex;flex-direction:column;gap:4px;font-size:12px">
            GSV Óleo Confirmado como Gross Liquid Volume
            <select id="pvtf-gsv_confirmed" class="input">
              <option value="0" ${!p?.gsv_confirmed ? 'selected' : ''}>Não confirmado (bloqueia subtração)</option>
              <option value="1" ${p?.gsv_confirmed ? 'selected' : ''}>Confirmado</option>
            </select>
          </label>
          ${pvtField('valid_from', 'Vigência Início (YYYY-MM-DD)', p?.valid_from || '', false, '')}
          ${pvtField('valid_to', 'Vigência Fim (YYYY-MM-DD)', p?.valid_to || '', false, '')}
          ${pvtField('source', 'Fonte / Simulação', p?.source || '', false, 'ex: PVTSIM v22.3')}
          ${pvtField('author', 'Autor', p?.author || '', false, '')}
        </div>
        <div style="margin-top:12px">
          <label style="display:flex;flex-direction:column;gap:4px;font-size:12px">
            Notas
            <textarea id="pvtf-notes" class="input" rows="2">${escapeHtml(p?.notes || '')}</textarea>
          </label>
        </div>
        <div style="display:flex;gap:8px;justify-content:flex-end;margin-top:16px">
          <button class="btn secondary" onclick="closePVTModal()">Cancelar</button>
          <button class="btn" onclick="savePVT(${p?.id || 'null'})">💾 Salvar</button>
        </div>
      </div>
    </div>`;
  document.body.insertAdjacentHTML('beforeend', html);
  if (typeof bindAccessibleModals === 'function') bindAccessibleModals(document);
  if (typeof openAppModal === 'function') openAppModal('pvtModal');
}

function closePVTModal() {
  const modal = document.getElementById('pvtModal');
  if (!modal) return;
  if (typeof closeAppModal === 'function') closeAppModal(modal);
  modal.remove();
}

function pvtField(id, label, val, isNum, placeholder) {
  return `<label style="display:flex;flex-direction:column;gap:4px;font-size:12px">
    ${label}
    <input id="pvtf-${id}" class="input" type="${isNum ? 'number' : 'text'}"
      step="any" value="${escapeHtml(val)}" placeholder="${placeholder}">
  </label>`;
}

async function savePVT(id) {
  const get = k => {
    const el = document.getElementById(`pvtf-${k}`);
    return el ? el.value : null;
  };
  const body = {
    bank: get('bank'), tag: get('tag'),
    fe: parseFloat(get('fe')), rs: parseFloat(get('rs')),
    rho_oleo_std: parseFloat(get('rho_oleo_std')),
    rho_gas_std: parseFloat(get('rho_gas_std')),
    rho_agua_std: parseFloat(get('rho_agua_std')),
    temp_ref_c: parseFloat(get('temp_ref_c')),
    pres_ref_bar: parseFloat(get('pres_ref_bar')),
    gsv_confirmed: parseInt(get('gsv_confirmed')),
    gor_mode: get('gor_mode'),
    limite_hc_pct: parseFloat(get('limite_hc_pct')),
    limite_total_pct: parseFloat(get('limite_total_pct')),
    limite_agua_pct: parseFloat(get('limite_agua_pct')),
    valid_from: get('valid_from'), valid_to: get('valid_to'),
    source: get('source'), author: get('author'),
    notes: document.getElementById('pvtf-notes')?.value || '',
  };
  const url = id ? `/api/pvt-params/${id}` : '/api/pvt-params';
  const meth = id ? 'PUT' : 'POST';
  const previousBank = document.getElementById('recon-bank')?.value || '';
  await j(url, {method: meth, headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)});
  closePVTModal();
  await loadPVTTable();
  await loadReconBankOptions();
  const reconBank = document.getElementById('recon-bank');
  if (reconBank && body.bank) {
    reconBank.value = previousBank || body.bank;
    if (reconBank.value) await loadReconPVTOptions();
  }
  renderReconPvtPreview();
}

async function deletePVT(id) {
  if (!confirm(`Excluir parâmetro PVT id=${id}?`)) return;
  await j(`/api/pvt-params/${id}`, {method: 'DELETE'});
  await loadPVTTable();
  renderReconPvtPreview();
}

// ── Run page helpers ──────────────────────────────────────────────────────────
async function loadReconBankOptions() {
  const d = await j('/api/pvt-params');
  const banks = [...new Set((d.params || []).map(p => p.bank))].sort();
  const sel = document.getElementById('recon-bank');
  if (!sel) return;
  sel.innerHTML = '<option value="">Selecione banco...</option>' +
    banks.map(b => `<option value="${b}">${b}</option>`).join('');
}

async function loadReconPVTOptions() {
  const bank = document.getElementById('recon-bank')?.value;
  const tagSel = document.getElementById('recon-tag');
  const pvtSel = document.getElementById('recon-pvt-id');
  const previousTag = tagSel?.value || '';
  const previousPvt = pvtSel?.value || '';
  if (!bank) {
    if (tagSel) tagSel.innerHTML = '<option value="">Selecione banco primeiro</option>';
    if (pvtSel) pvtSel.innerHTML = '<option value="">Selecione banco primeiro</option>';
    _reconLatestDataCheck = null;
    renderReconPvtPreview();
    renderReconDataCheck(null);
    return;
  }
  const [pvtData, mpfmTagData] = await Promise.all([
    j(`/api/pvt-params?bank=${bank}`),
    j(`/api/recon/mpfm-tags?bank=${encodeURIComponent(bank)}`),
  ]);
  const pvts = pvtData.params || [];
  const mpfmTags = mpfmTagData.tags || [];
  const pvtTags = pvts.map(p => p.tag).filter(Boolean);
  const tags = [...new Set([...mpfmTags, ...pvtTags])];
  tagSel.innerHTML = tags.length
    ? tags.map(t => `<option value="${t}">${t}</option>`).join('')
    : '<option value="">Sem TAG MPFM/PVT para este banco</option>';
  if (tagSel && tags.length) {
    tagSel.value = tags.includes(previousTag) ? previousTag : tags[0];
  }
  pvtSel.innerHTML = pvts.length
    ? pvts.map(p => `<option value="${p.id}">[${p.id}] ${p.tag} | FE=${p.fe} RS=${p.rs} | ${p.gor_mode} | ${p.valid_from || 'sem vigência'}</option>`).join('')
    : '<option value="">Cadastre PVT para este banco</option>';
  if (pvtSel && previousPvt && pvts.some(p => String(p.id) === String(previousPvt))) {
    pvtSel.value = previousPvt;
  }
  const month = document.getElementById('globalMonth')?.value || '';
  const dateInput = document.getElementById('recon-date');
  if (dateInput && !dateInput.value && month) dateInput.value = `${month}-01`;
  if (typeof refreshDateInputDisplay === 'function') refreshDateInputDisplay(document);
  renderReconPvtPreview();
  checkReconDataAvailability();
}

function renderReconPvtPreview() {
  const host = document.getElementById('recon-pvt-preview');
  if (!host) return;
  const pvtId = Number(document.getElementById('recon-pvt-id')?.value || 0);
  const p = (_pvtAll || []).find(x => x.id === pvtId);
  if (!p) {
    host.innerHTML = `<div class="recon-preview-card"><div class="k">PVT ativo</div><div class="v">Selecione um parâmetro</div><div class="m">O preview mostra FE, RS, densidades, limites e vigência da base usada no cálculo.</div></div>`;
    updateReconActionState(_reconLatestDataCheck);
    renderReconReadinessRunbook(_reconLatestDataCheck);
    return;
  }
  host.innerHTML = `
    <div class="recon-preview-card"><div class="k">Banco / TAG</div><div class="v">${p.bank} · ${p.tag}</div><div class="m">Parâmetro PVT usado na reconciliação.</div></div>
    <div class="recon-preview-card"><div class="k">Base PVT</div><div class="v">FE ${fmt(p.fe)} · RS ${fmt(p.rs)}</div><div class="m">ρ óleo ${fmt(p.rho_oleo_std)} · ρ gás ${fmt(p.rho_gas_std)} · ρ água ${fmt(p.rho_agua_std)}</div></div>
    <div class="recon-preview-card"><div class="k">Critérios QA</div><div class="v">HC ${fmt(p.limite_hc_pct)}% · Total ${fmt(p.limite_total_pct)}%</div><div class="m">GSV ${p.gsv_confirmed ? 'confirmado' : 'não confirmado'} · ${p.gor_mode || 'sem modo'}</div></div>
    <div class="recon-preview-card"><div class="k">Vigência / Fonte</div><div class="v">${p.valid_from || 'sem início'} → ${p.valid_to || 'aberto'}</div><div class="m" title="${p.source || ''}">${p.source || 'sem fonte declarada'}</div></div>
  `;
  updateReconActionState(_reconLatestDataCheck);
  renderReconReadinessRunbook(_reconLatestDataCheck);
}

// ── Verificação de disponibilidade de dados ────────────────────────────────
async function checkReconDataAvailability() {
  const bank = document.getElementById('recon-bank')?.value;
  const tag = document.getElementById('recon-tag')?.value;
  const day_ref = readReconIsoInput('recon-date');
  const pvtId = document.getElementById('recon-pvt-id')?.value;
  if (!bank || !tag || !day_ref) {
    _reconLatestDataCheck = null;
    renderReconDataCheck(null);
    return;
  }
  try {
    const pvtQuery = pvtId ? `&pvt_id=${encodeURIComponent(pvtId)}` : '';
    const d = await j(`/api/recon/data-check?bank=${encodeURIComponent(bank)}&tag=${encodeURIComponent(tag)}&day_ref=${encodeURIComponent(day_ref)}${pvtQuery}`);
    _reconLatestDataCheck = d;
    renderReconDataCheck(d);
  } catch (e) {
    _reconLatestDataCheck = null;
    renderReconDataCheck(null);
  }
}

function updateReconActionState(data) {
  const btn = document.getElementById('btnCalcRecon');
  const bank = document.getElementById('recon-bank')?.value;
  const tag = document.getElementById('recon-tag')?.value;
  const date = readReconIsoInput('recon-date');
  const pvtId = document.getElementById('recon-pvt-id')?.value;
  const hasBasics = Boolean(bank && tag && date && pvtId);
  const hasData = Boolean(data && data.mpfm_count > 0 && data.sep_count > 0);
  if (btn) {
    btn.disabled = !(hasBasics && hasData);
    btn.title = hasBasics && !hasData
      ? 'A campanha precisa ter dados MPFM e separador importados para esta data.'
      : '';
  }
  const proposed = _reconCurrentProposal?.proposed_k_factor_selected;
  const useKBtn = document.getElementById('btnUseProposedK');
  if (useKBtn) {
    useKBtn.disabled = !(proposed != null && Number.isFinite(Number(proposed)));
    useKBtn.title = useKBtn.disabled
      ? 'Calcule uma campanha base com proposta de K antes de preencher o K aplicado.'
      : 'Copiar o K proposto para o campo de K aplicado.';
  }
  const campaign = readReconCampaignInputs();
  const monitorBtn = document.getElementById('btnReconMonitor');
  if (monitorBtn) {
    const canMonitor = Boolean(
      campaign.campaign_id &&
      campaign.monitor_day_ref &&
      campaign.applied_k_factor != null &&
      bank &&
      tag &&
      pvtId
    );
    monitorBtn.disabled = !canMonitor;
    monitorBtn.title = canMonitor
      ? ''
      : 'Informe campanha, K aplicado e data de monitoramento para registrar o pós-24h.';
  }
}

function refreshReconReadiness() {
  updateReconActionState(_reconLatestDataCheck);
  renderReconReadinessRunbook(_reconLatestDataCheck);
}

function renderReconReadinessRunbook(data) {
  const host = document.getElementById('recon-readiness-runbook');
  if (!host) return;
  const bank = document.getElementById('recon-bank')?.value || '';
  const tag = document.getElementById('recon-tag')?.value || '';
  const date = readReconIsoInput('recon-date');
  const pvtId = document.getElementById('recon-pvt-id')?.value || '';
  const campaign = readReconCampaignInputs();
  const hasIdentity = Boolean(bank && tag && date);
  const selectedPvtCount = Number(data?.selected_pvt_count || 0);
  const hasPvt = Boolean(pvtId && (!data || selectedPvtCount > 0));
  const mpfm = Number(data?.mpfm_count || 0);
  const sep = Number(data?.sep_count || 0);
  const hasEvidence = Boolean(data && mpfm > 0 && sep > 0);
  const completeEvidence = Boolean(hasEvidence && mpfm >= 20 && sep >= 20);
  const baseReady = Boolean(hasIdentity && hasPvt && hasEvidence);
  const campaignReady = Boolean(_reconCurrentRunId || campaign.campaign_id);
  const monitorReady = Boolean(
    campaign.campaign_id &&
    campaign.applied_k_factor != null &&
    campaign.monitor_day_ref
  );
  const status = baseReady
    ? (completeEvidence ? 'Pronto para calcular' : 'Parcial com dados suficientes')
    : 'Bloqueado';
  const statusClass = baseReady ? (completeEvidence ? 'is-ready' : 'is-partial') : 'is-blocked';
  const detail = (() => {
    if (!hasIdentity) return 'Selecione banco, TAG e data para abrir a verificação da janela.';
    if (!data) return 'Aguardando checagem de MPFM, separador e PVT para esta janela.';
    if (!hasEvidence) return 'MPFM e separador precisam estar presentes antes do cálculo base.';
    if (!hasPvt) return 'Selecione um PVT vigente para amarrar FE, RS, densidades e limites.';
    if (!completeEvidence) return 'Há dados suficientes para calcular, mas a cobertura 24h está parcial.';
    return 'MPFM, separador e PVT estão confirmados para a campanha base.';
  })();
  const steps = [
    ['Identificar', hasIdentity, hasIdentity ? `${bank} · ${tag} · ${date}` : 'Banco, TAG e data'],
    ['Evidências', hasEvidence, data ? `MPFM ${mpfm}/24h · SEP ${sep}/24h` : 'Aguardando checagem'],
    ['PVT', hasPvt, pvtId ? `PVT ${pvtId}` : 'Selecione parâmetro'],
    ['Base 24h', campaignReady, campaignReady ? `Run ${_reconCurrentRunId || campaign.campaign_id}` : 'Calcular campanha base'],
    ['K / pós-24h', monitorReady, monitorReady ? 'Pronto para monitorar' : 'Aplicar K antes do pós'],
  ];
  host.innerHTML = `
    <div class="recon-readiness-runbook__banner ${statusClass}">
      <div>
        <span class="recon-readiness-runbook__eyebrow">Prontidão da campanha</span>
        <strong>${status}</strong>
        <small>${detail}</small>
      </div>
      <span class="recon-readiness-runbook__next">${baseReady ? 'Próxima ação: calcular base' : 'Próxima ação: completar pré-requisitos'}</span>
    </div>
    <div class="recon-readiness-runbook__steps">
      ${steps.map(([label, done, note], idx) => `
        <div class="recon-readiness-runbook__step ${done ? 'is-ready' : idx === steps.findIndex(item => !item[1]) ? 'is-active' : ''}">
          <span>${done ? '✓' : idx + 1}</span>
          <strong>${label}</strong>
          <small>${escapeHtml(note)}</small>
        </div>`).join('')}
    </div>`;
}

function renderReconDataCheck(data) {
  const host = document.getElementById('recon-data-check');
  if (!host) return;
  updateReconActionState(data);
  if (!data) {
    host.innerHTML = '<div class="recon-data-panel recon-data-panel--idle"><strong>Dados da janela</strong><span>Selecione banco, TAG e data para verificar MPFM e separador.</span></div>';
    renderReconReadinessRunbook(data);
    return;
  }
  const statusClass = count => count === 0 ? 'is-missing' : count < 20 ? 'is-partial' : 'is-ready';
  const readiness = data.mpfm_count > 0 && data.sep_count > 0
    ? (data.mpfm_count >= 20 && data.sep_count >= 20 ? 'Pronto para calcular' : 'Dados parciais disponíveis')
    : 'Aguardando dados importados';
  const alignmentHint = data.sep_alignment_exists ? '' : ' · sem alinhamento formal do separador';
  const selectedPvtCount = Number(data.selected_pvt_count || 0);
  host.innerHTML = `
    <div class="recon-data-panel">
      <div class="recon-data-panel__head"><strong>Dados encontrados na base</strong><span>${readiness}${alignmentHint}</span></div>
      <div class="recon-data-panel__items">
        <div class="recon-data-item ${statusClass(data.mpfm_count)}"><span>MPFM</span><strong>${data.mpfm_count}/24h</strong></div>
        <div class="recon-data-item ${statusClass(data.sep_count)}"><span>Separador</span><strong>${data.sep_count}/24h</strong></div>
        <div class="recon-data-item ${selectedPvtCount ? 'is-ready' : 'is-missing'}"><span>PVT selecionado</span><strong>${selectedPvtCount}</strong></div>
      </div>
    </div>`;
  renderReconReadinessRunbook(data);
}

function readReconAnalyticalInputs() {
  const num = id => {
    const raw = document.getElementById(id)?.value;
    if (raw === '' || raw == null) return null;
    const value = parseFloat(raw);
    return Number.isFinite(value) ? value : null;
  };
  const txt = id => document.getElementById(id)?.value?.trim() || '';
  return {
    flow_mode: document.getElementById('recon-flow-mode')?.value || 'topside_sep',
    activity_kind: document.getElementById('recon-activity-kind')?.value || 'calibracao_periodica',
    test_start_at: txt('recon-start-at'),
    duration_hours: num('recon-duration-hours'),
    reference_system: txt('recon-reference-system'),
    mpfm_pressure_barg: num('recon-mpfm-pressure'),
    mpfm_temperature_c: num('recon-mpfm-temperature'),
    sep_pressure_barg: num('recon-sep-pressure'),
    sep_temperature_c: num('recon-sep-temperature'),
    bsw_pct: num('recon-bsw-pct'),
    density_coriolis_kg_m3: num('recon-density-coriolis'),
    density_lab_kg_m3: num('recon-density-lab'),
    density_other_kg_m3: num('recon-density-other'),
    density_source: txt('recon-density-source'),
    analysis_reference: txt('recon-analysis-reference'),
    analysis_notes: txt('recon-analysis-notes'),
  };
}

function readReconCampaignInputs() {
  const num = id => {
    const raw = document.getElementById(id)?.value;
    if (raw === '' || raw == null) return null;
    const value = parseFloat(raw);
    return Number.isFinite(value) ? value : null;
  };
  const txt = id => document.getElementById(id)?.value?.trim() || '';
  const campaignRaw = txt('recon-campaign-id');
  const campaignId = campaignRaw && /^\d+$/.test(campaignRaw) ? Number(campaignRaw) : null;
  return {
    campaign_id: campaignId,
    current_k_factor: num('recon-current-k-factor'),
    proposal_mode: document.getElementById('recon-proposal-mode')?.value || 'hc',
    proposed_k_factor_manual: num('recon-proposed-k-manual'),
    monitor_day_ref: readReconIsoInput('recon-monitor-date'),
    applied_k_factor: num('recon-applied-k-factor'),
    applied_at: txt('recon-applied-at'),
  };
}

function setReconInputValue(id, value) {
  const el = document.getElementById(id);
  if (!el) return;
  const nextValue = value == null ? '' : String(value);
  el.value = nextValue;
  if (el.dataset?.brDate === '1') {
    el.dataset.isoValue = nextValue;
    if (typeof refreshDateInputDisplay === 'function') refreshDateInputDisplay(document);
  }
  refreshReconReadiness();
}

function renderReconAnalyticalSummary(snapshot) {
  const host = document.getElementById('recon-analytical-summary');
  if (!host) return;
  const data = snapshot || {};
  const rows = [
    ['Arranjo', data.flow_mode === 'topside_sep' ? 'TOPSIDE vs SEPARADOR' : (data.flow_mode || '—')],
    ['Atividade', data.activity_kind || '—'],
    ['Início', data.test_start_at || '—'],
    ['Duração', data.duration_hours != null ? `${fmt(data.duration_hours)} h` : '—'],
    ['Referência', data.reference_system || '—'],
    ['P/T MPFM', (data.mpfm_pressure_barg != null || data.mpfm_temperature_c != null) ? `${fmt(data.mpfm_pressure_barg)} barg / ${fmt(data.mpfm_temperature_c)} °C` : '—'],
    ['P/T SEP', (data.sep_pressure_barg != null || data.sep_temperature_c != null) ? `${fmt(data.sep_pressure_barg)} barg / ${fmt(data.sep_temperature_c)} °C` : '—'],
    ['FE / RS', (data.fe != null || data.rs != null) ? `${fmt(data.fe)} / ${fmt(data.rs)}` : '—'],
    ['BSW', data.bsw_pct != null ? `${fmt(data.bsw_pct)}%` : '—'],
    ['ρ coriolis', data.density_coriolis_kg_m3 != null ? `${fmt(data.density_coriolis_kg_m3)} kg/m³` : '—'],
    ['ρ laboratório', data.density_lab_kg_m3 != null ? `${fmt(data.density_lab_kg_m3)} kg/m³` : '—'],
    ['Outra ρ', data.density_other_kg_m3 != null ? `${fmt(data.density_other_kg_m3)} kg/m³` : '—'],
    ['Fonte', data.density_source || '—'],
    ['Ref. analítica', data.analysis_reference || '—'],
  ];
  host.innerHTML = `
    <div class="recon-analytical-card recon-analytical-card--summary">
      <div class="recon-analytical-title">Snapshot analítico da campanha</div>
      <div class="recon-analytical-copy">Esses dados ficam associados ao run para leitura posterior e rastreabilidade.</div>
      <div class="recon-analytical-summary-grid">
        ${rows.map(([label, value]) => `<div class="recon-analytical-kv"><span>${label}</span><strong>${value}</strong></div>`).join('')}
      </div>
      ${data.analysis_notes ? `<div class="recon-analytical-notes"><span>Notas</span><strong>${data.analysis_notes}</strong></div>` : ''}
    </div>
  `;
}

function renderReconCampaignSummary(campaign, proposal) {
  const host = document.getElementById('recon-campaign-summary');
  if (!host) return;
  if (!campaign && !proposal) {
    _reconCurrentProposal = null;
    host.innerHTML = '';
    return;
  }
  const c = campaign || {};
  const p = proposal || {};
  _reconCurrentProposal = proposal || {
    proposed_k_factor_selected: c.proposed_k_factor_selected,
    proposal_status: c.proposal_status,
    proposal_rule: c.proposal_rule,
    proposal_mode: c.proposal_mode,
  };
  const selected = p.proposed_k_factor_selected != null ? p.proposed_k_factor_selected : c.proposed_k_factor_selected;
  const proposalStatus = p.proposal_status || c.proposal_status || '';
  const monitoringStatus = c.monitoring_status || c.status || '';
  const basisName = p.basis_name || (c.proposal_mode === 'total' ? 'Total 24h' : 'HC 24h');
  const basisDesvio = p.basis_desvio_pct != null ? `${fmt(p.basis_desvio_pct)}%` : '—';
  const basisLimit = p.basis_limit_pct != null ? `${fmt(p.basis_limit_pct)}%` : '—';
  const proposalRule = p.acceptance_rule || 'K_novo = K_atual x (massa_ref_24h / massa_mpfm_24h) na base selecionada.';
  const proposalRecommendation = p.recommendation || 'Revisar a campanha e decidir aplicação/monitoramento.';
  const monitoringRule = c.monitoring_status
    ? 'Aceitar apenas quando HC e Total do monitoramento 24h ficarem dentro dos limites configurados no PVT.'
    : 'Após aplicar o K, monitorar nova janela de 24h no mesmo arranjo MPFM x Separador.';
  host.innerHTML = `
    <div class="recon-analytical-card recon-analytical-card--summary">
      <div class="recon-analytical-title">Campanha 24h e fator K operacional</div>
      <div class="recon-analytical-copy">A regra do sistema usa razão de massas em janela de 24h para organizar base, aplicação do K e monitoramento posterior.</div>
      <div class="recon-analytical-summary-grid">
        <div class="recon-analytical-kv"><span>Campanha</span><strong>${c.id || '—'}</strong></div>
        <div class="recon-analytical-kv"><span>K atual</span><strong>${p.current_k_factor != null ? fmtFactor(p.current_k_factor) : (c.current_k_factor != null ? fmtFactor(c.current_k_factor) : '—')}</strong></div>
        <div class="recon-analytical-kv"><span>K proposto HC</span><strong>${p.proposed_k_factor_hc != null ? fmtFactor(p.proposed_k_factor_hc) : (c.proposed_k_factor_hc != null ? fmtFactor(c.proposed_k_factor_hc) : '—')}</strong></div>
        <div class="recon-analytical-kv"><span>K proposto Total</span><strong>${p.proposed_k_factor_total != null ? fmtFactor(p.proposed_k_factor_total) : (c.proposed_k_factor_total != null ? fmtFactor(c.proposed_k_factor_total) : '—')}</strong></div>
        <div class="recon-analytical-kv"><span>Base escolhida</span><strong>${p.proposal_mode || c.proposal_mode || 'hc'}</strong></div>
        <div class="recon-analytical-kv"><span>Grandeza base</span><strong>${basisName}</strong></div>
        <div class="recon-analytical-kv"><span>Δ base</span><strong>${basisDesvio}</strong></div>
        <div class="recon-analytical-kv"><span>Limite da base</span><strong>${basisLimit}</strong></div>
        <div class="recon-analytical-kv"><span>Regra</span><strong>${p.proposal_rule || c.proposal_rule || 'mass_ratio_24h'}</strong></div>
        <div class="recon-analytical-kv"><span>Status da proposta</span><strong>${formatReconCampaignStatus(proposalStatus)}</strong></div>
        <div class="recon-analytical-kv"><span>K selecionado</span><strong>${selected != null ? fmtFactor(selected) : '—'}</strong></div>
        <div class="recon-analytical-kv"><span>K aplicado</span><strong>${c.applied_k_factor != null ? fmtFactor(c.applied_k_factor) : '—'}</strong></div>
        <div class="recon-analytical-kv"><span>Δ HC base</span><strong>${c.baseline_desvio_hc_pct != null ? fmt(c.baseline_desvio_hc_pct) + '%' : '—'}</strong></div>
        <div class="recon-analytical-kv"><span>Δ Total base</span><strong>${c.baseline_desvio_total_pct != null ? fmt(c.baseline_desvio_total_pct) + '%' : '—'}</strong></div>
        <div class="recon-analytical-kv"><span>Δ HC pós</span><strong>${c.post_desvio_hc_pct != null ? fmt(c.post_desvio_hc_pct) + '%' : '—'}</strong></div>
        <div class="recon-analytical-kv"><span>Δ Total pós</span><strong>${c.post_desvio_total_pct != null ? fmt(c.post_desvio_total_pct) + '%' : '—'}</strong></div>
        <div class="recon-analytical-kv"><span>Ganho HC</span><strong>${c.improvement_hc_pp != null ? fmt(c.improvement_hc_pp) + ' pp' : '—'}</strong></div>
        <div class="recon-analytical-kv"><span>Ganho Total</span><strong>${c.improvement_total_pp != null ? fmt(c.improvement_total_pp) + ' pp' : '—'}</strong></div>
        <div class="recon-analytical-kv"><span>Status monitoramento</span><strong>${formatReconCampaignStatus(monitoringStatus)}</strong></div>
      </div>
      <div class="recon-analytical-notes"><span>Regra de proposta</span><strong>${proposalRule}</strong></div>
      <div class="recon-analytical-notes"><span>Conduta</span><strong>${proposalRecommendation}</strong></div>
      <div class="recon-analytical-notes"><span>Regra de aceitação</span><strong>${monitoringRule}</strong></div>
    </div>
  `;
  refreshReconReadiness();
}

function reconMemorialStatusClass(status) {
  return ({
    ok: 'ok',
    warn: 'warn',
    missing: 'warn',
    critical: 'err',
    OK: 'ok',
    ATENÇÃO: 'warn',
    VERIFICAR: 'err',
    INDISPONÍVEL: 'warn',
    accepted: 'ok',
    rejected: 'err',
  })[status] || 'warn';
}

function reconMemorialStatusLabel(status) {
  return ({
    ok: 'Conforme',
    warn: 'Atenção',
    missing: 'Pendente',
    critical: 'Bloqueio',
    accepted: 'Aceito',
    rejected: 'Rejeitado',
  })[status] || (status || 'Pendente');
}

function openReconCurrentExcel() {
  if (!_reconCurrentRunId) {
    alert('Abra um run ou calcule uma campanha antes de exportar.');
    return;
  }
  window.open(`/api/recon/export-excel/${_reconCurrentRunId}`);
}

async function loadReconMemorial(runId = _reconCurrentRunId, options = {}) {
  const status = document.getElementById('recon-memorial-status');
  if (!runId) {
    renderReconMemorial(null);
    return;
  }
  if (status) status.textContent = `Carregando memorial do run #${runId}...`;
  try {
    const data = await j(`/api/recon/runs/${runId}/memorial`);
    _reconCurrentRunId = runId;
    renderReconMemorial(data);
    if (options.switchTab) showReconTab('memorial');
  } catch (e) {
    _reconCurrentMemorial = null;
    if (status) status.textContent = `Falha ao carregar memorial: ${e.message}`;
  }
}

function renderReconMemorial(data) {
  const wrap = document.getElementById('recon-memorial-wrap');
  const status = document.getElementById('recon-memorial-status');
  if (!wrap) return;
  if (!data || !data.ok) {
    _reconCurrentMemorial = null;
    wrap.innerHTML = `
      <div class="card ops-card recon-memorial-empty">
        <strong>Nenhum run selecionado</strong>
        <span>Use o histórico, abra uma campanha ou calcule uma nova reconciliação para montar o memorial com dados reais.</span>
      </div>`;
    if (status) status.textContent = 'Aguardando run de reconciliação.';
    return;
  }
  _reconCurrentMemorial = data;
  const run = data.run || {};
  const summary = data.summary || {};
  const pvt = data.pvt || {};
  const analytical = data.analytical || {};
  const evidence = data.evidence || {};
  const sepSources = evidence.sep_sources || [];
  const mpfmSources = evidence.mpfm_sources || [];
  if (status) {
    status.textContent = `Run #${run.id} · ${run.bank || '—'} / ${run.tag || '—'} · ${fmtDate(run.day_ref)} · status ${run.status_final || '—'}`;
  }
  wrap.innerHTML = `
    <div class="recon-memorial-grid">
      <div class="card ops-card recon-memorial-card recon-memorial-card--wide">
        <div class="recon-memorial-head">
          <div>
            <h3 class="section-title modal-h3">Run #${escapeHtml(run.id)} · ${escapeHtml(run.bank || '—')} / ${escapeHtml(run.tag || '—')}</h3>
            <div class="text-muted-12 mt4">${escapeHtml(fmtDate(run.day_ref))} · campanha ${escapeHtml(run.campaign_id || '—')} · fase ${escapeHtml(run.campaign_phase || 'baseline')}</div>
          </div>
          <span class="badge ${reconMemorialStatusClass(run.status_final)}">${escapeHtml(run.status_final || '—')}</span>
        </div>
        <div class="recon-memorial-kpis">
          ${reconMemorialKpi('HC MPFM', summary.massa_hc_mpfm_t, 't', `Ref. ${fmt(summary.massa_hc_ref_t)} t`)}
          ${reconMemorialKpi('Desvio HC', summary.desvio_hc_pct, '%', `Limite ${fmt(pvt.limite_hc_pct)}%`, reconMemorialStatusClass(summary.status_hc))}
          ${reconMemorialKpi('Total MPFM', summary.massa_total_mpfm_t, 't', `Ref. ${fmt(summary.massa_total_ref_t)} t`)}
          ${reconMemorialKpi('Cobertura', summary.cobertura_pct, '%', `${summary.horas_validas ?? '—'}/${summary.horas_janela ?? 24}h`)}
        </div>
      </div>

      <div class="card ops-card recon-memorial-card">
        <h3 class="section-title modal-h3">Base PVT aplicada</h3>
        <div class="recon-memorial-kv-list">
          ${reconMemorialKv('FE / SF', pvt.fe)}
          ${reconMemorialKv('RS / DeltaRs', pvt.rs)}
          ${reconMemorialKv('rho óleo std', pvt.rho_oleo_std, 'kg/m3')}
          ${reconMemorialKv('rho gás std', pvt.rho_gas_std, 'kg/m3')}
          ${reconMemorialKv('rho água std', pvt.rho_agua_std, 'kg/m3')}
          ${reconMemorialKv('GSV confirmado', pvt.gsv_confirmed ? 'Sim' : 'Não')}
          ${reconMemorialKv('GOR mode', pvt.gor_mode || '—')}
          ${reconMemorialKv('Fonte', pvt.source || 'Snapshot do run')}
        </div>
      </div>

      <div class="card ops-card recon-memorial-card">
        <h3 class="section-title modal-h3">Snapshot analítico</h3>
        <div class="recon-memorial-kv-list">
          ${reconMemorialKv('Atividade', analytical.activity_kind || '—')}
          ${reconMemorialKv('Referência', analytical.reference_system || '—')}
          ${reconMemorialKv('BSW', analytical.bsw_pct, '%')}
          ${reconMemorialKv('rho coriolis', analytical.density_coriolis_kg_m3, 'kg/m3')}
          ${reconMemorialKv('rho laboratório', analytical.density_lab_kg_m3, 'kg/m3')}
          ${reconMemorialKv('Fonte densidade', analytical.density_source || '—')}
          ${reconMemorialKv('Ref. analítica', analytical.analysis_reference || '—')}
        </div>
      </div>
    </div>

    <div class="card ops-card recon-memorial-card mt12">
      <div class="recon-memorial-section-head">
        <h3 class="section-title modal-h3">Cadeia de cálculo aplicada</h3>
        <span class="text-muted-12">Amostra horária + totalização real do run.</span>
      </div>
      <div class="tablewrap">
        <table class="table compact recon-memorial-table">
          <thead><tr><th>Etapa</th><th>Fórmula</th><th>Valor</th><th>Observação técnica</th></tr></thead>
          <tbody>
            ${(data.formula_rows || []).map(row => `
              <tr>
                <td><strong>${escapeHtml(row.name)}</strong></td>
                <td><code>${escapeHtml(row.formula)}</code></td>
                <td>${fmt(row.value)} ${escapeHtml(row.unit || '')}</td>
                <td>${escapeHtml(row.note || '')}</td>
              </tr>`).join('')}
          </tbody>
        </table>
      </div>
    </div>

    <div class="recon-memorial-grid mt12">
      <div class="card ops-card recon-memorial-card">
        <h3 class="section-title modal-h3">Checklist técnico</h3>
        <div class="recon-memorial-checklist">
          ${(data.checklist || []).map(item => `
            <div class="recon-memorial-check recon-memorial-check--${reconMemorialStatusClass(item.status)}">
              <div><strong>${escapeHtml(item.label)}</strong><span>${escapeHtml(item.detail)}</span></div>
              <span class="badge ${reconMemorialStatusClass(item.status)}">${escapeHtml(reconMemorialStatusLabel(item.status))}</span>
              ${item.evidence ? `<small>${escapeHtml(item.evidence)}</small>` : ''}
            </div>`).join('')}
        </div>
      </div>

      <div class="card ops-card recon-memorial-card">
        <h3 class="section-title modal-h3">Decisão por grandeza</h3>
        <div class="recon-memorial-decision-list">
          ${(data.decisions || []).map(row => `
            <div class="recon-memorial-decision">
              <div>
                <strong>${escapeHtml(row.label)}</strong>
                <span>Ref. ${fmt(row.ref)} · MPFM ${fmt(row.mpfm)}</span>
              </div>
              <div>
                <strong>${fmt(row.deviation_pct)}%</strong>
                <span>limite ${fmt(row.limit_pct)}%</span>
              </div>
              <span class="badge ${reconMemorialStatusClass(row.status)}">${escapeHtml(row.status || '—')}</span>
            </div>`).join('')}
        </div>
        <div class="recon-memorial-flags">
          ${(data.qa_flags || []).length
            ? (data.qa_flags || []).map(flag => `<span>${escapeHtml(flag)}</span>`).join('')
            : '<span>Sem flags QA consolidadas no run.</span>'}
        </div>
      </div>
    </div>

    <div class="card ops-card recon-memorial-card mt12">
      <div class="recon-memorial-section-head">
        <h3 class="section-title modal-h3">Evidências usadas</h3>
        <span class="text-muted-12">${mpfmSources.length} fonte(s) MPFM · ${sepSources.length} arquivo(s) SEP</span>
      </div>
      <div class="recon-memorial-evidence-grid">
        <div>
          <strong>MPFM</strong>
          ${mpfmSources.length ? mpfmSources.map(src => `<span>${escapeHtml(src)}</span>`).join('') : '<span>Fonte diária não informada.</span>'}
        </div>
        <div>
          <strong>Separador</strong>
          ${sepSources.length ? sepSources.slice(0, 8).map(src => `<span>${escapeHtml(src.fluid_kind || '')} · ${escapeHtml(src.meter_id || '')} · ${escapeHtml(src.source_file || '')}</span>`).join('') : '<span>Sem fonte de separador associada.</span>'}
        </div>
      </div>
    </div>

    <div class="card ops-card recon-memorial-card mt12">
      <h3 class="section-title modal-h3">Recomendações técnicas</h3>
      <div class="recon-memorial-recommendations">
        ${(data.recommendations || []).map(item => `<div>${escapeHtml(item)}</div>`).join('')}
      </div>
    </div>
  `;
}

function reconMemorialKpi(label, value, unit, meta, statusClass = '') {
  return `<div class="recon-memorial-kpi ${statusClass ? `recon-memorial-kpi--${statusClass}` : ''}">
    <span>${escapeHtml(label)}</span>
    <strong>${fmt(value)}${unit ? ` ${escapeHtml(unit)}` : ''}</strong>
    <small>${escapeHtml(meta || '')}</small>
  </div>`;
}

function reconMemorialKv(label, value, unit = '') {
  const numeric = typeof value === 'number' || (typeof value === 'string' && value.trim() !== '' && Number.isFinite(Number(value)));
  const shown = value == null || value === '' ? '—' : (numeric ? fmt(Number(value)) : String(value));
  return `<div class="recon-memorial-kv"><span>${escapeHtml(label)}</span><strong>${escapeHtml(shown)}${unit && shown !== '—' ? ` ${escapeHtml(unit)}` : ''}</strong></div>`;
}

function showReconCampaignOnlySummary() {
  document.getElementById('recon-resumo-linha').innerHTML =
    '<tbody><tr><td colspan="5" style="color:var(--muted);text-align:center">Abra um run da campanha ou execute uma nova janela para ver a compara\u00e7\u00e3o 24h detalhada.</td></tr></tbody>';
  document.getElementById('recon-resumo-st').innerHTML =
    '<tbody><tr><td colspan="5" style="color:var(--muted);text-align:center">O contexto operacional da campanha permanece vis\u00edvel abaixo enquanto o detalhamento por hora n\u00e3o for carregado.</td></tr></tbody>';
  document.getElementById('recon-qa-flags').innerHTML = '';
  document.getElementById('recon-status-badge').innerHTML =
    '<span style="font-size:14px;font-weight:700;color:var(--accent)">Campanha aberta para revis\u00e3o</span>';
  document.getElementById('recon-cobertura-badge').innerHTML =
    '<span style="color:var(--muted);font-size:12px">Use "Ver" no hist\u00f3rico para carregar a compara\u00e7\u00e3o calculada desse run.</span>';
  document.getElementById('recon-resumo-card').style.display = 'block';
  document.getElementById('recon-calc-card').style.display = 'none';
}

function setReconCampaignContext(campaign) {
  if (!campaign) return;
  setReconInputValue('recon-campaign-id', campaign.id);
  setReconInputValue('recon-current-k-factor', campaign.current_k_factor);
  setReconInputValue('recon-proposal-mode', campaign.proposal_mode || 'hc');
  setReconInputValue('recon-proposed-k-manual', campaign.proposed_k_factor_manual);
  setReconInputValue('recon-monitor-date', campaign.post_day_ref || '');
  setReconInputValue('recon-applied-k-factor', campaign.applied_k_factor);
  setReconInputValue('recon-applied-at', campaign.applied_at || '');
  refreshReconReadiness();
}

// ── Janela de teste — toggle de visibilidade ──────────────────────────────────
function toggleTestWindowInputs() {
  const mode = document.querySelector('input[name="recon-window-mode"]:checked')?.value;
  const row = document.getElementById('recon-test-window-row');
  if (row) row.classList.toggle('is-hidden', mode !== 'test_window');
  refreshReconReadiness();
}

// ── Cálculo ───────────────────────────────────────────────────────────────────
async function runRecon() {
  const bank = document.getElementById('recon-bank')?.value;
  const tag = document.getElementById('recon-tag')?.value;
  const date = readReconIsoInput('recon-date');
  const pvtId = document.getElementById('recon-pvt-id')?.value;
  const author = document.getElementById('recon-author')?.value;
  const notes = document.getElementById('recon-notes')?.value;
  const analytical = readReconAnalyticalInputs();
  const campaignInputs = readReconCampaignInputs();

  if (!bank || !tag || !date || !pvtId) {
    alert('Preencha banco, TAG, data e parâmetros PVT.');
    return;
  }
  if (!_reconLatestDataCheck || _reconLatestDataCheck.mpfm_count === 0 || _reconLatestDataCheck.sep_count === 0) {
    alert('A campanha TOPSIDE vs SEPARADOR precisa de dados MPFM e separador importados para a data selecionada.');
    return;
  }

  // Lê janela de teste (opcional)
  let test_window = null;
  const windowMode = document.querySelector('input[name="recon-window-mode"]:checked')?.value;
  if (windowMode === 'test_window') {
    const hIni = parseInt(document.getElementById('recon-hora-inicio')?.value ?? '', 10);
    const hFim = parseInt(document.getElementById('recon-hora-fim')?.value ?? '', 10);
    if (isNaN(hIni) || isNaN(hFim) || hIni < 0 || hIni > 23 || hFim < 0 || hFim > 23) {
      alert('Informe hora início e hora fim da janela de teste (0–23).');
      return;
    }
    // fim < ini é tratado como janela que atravessa meia-noite pelo backend
    test_window = { hora_inicio: hIni, hora_fim: hFim };
  }

  const btn = document.getElementById('btnCalcRecon');
  btn.disabled = true;
  btn.textContent = '⌛ Calculando...';

  try {
    const body = {
      bank,
      tag,
      day_ref: date,
      pvt_params_id: parseInt(pvtId, 10),
      author,
      notes,
      analytical,
      current_k_factor: campaignInputs.current_k_factor,
      proposal_mode: campaignInputs.proposal_mode,
      proposed_k_factor_manual: campaignInputs.proposed_k_factor_manual,
      campaign_phase: 'baseline',
    };
    if (test_window) body.test_window = test_window;

    const res = await j('/api/recon/calcular', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(body)
    });
    _reconCurrentRunId = res.run_id;
    renderReconResumo(res.resumo, res.meta);
    renderReconCalcTable(res.calc_horas);
    renderReconAnalyticalSummary(res.meta?.analytical_snapshot || {});
    renderReconCampaignSummary(res.meta?.campaign || null, res.meta?.k_proposal || null);
    setReconCampaignContext(res.meta?.campaign || null);
    document.getElementById('recon-resumo-card').style.display = 'block';
    document.getElementById('recon-calc-card').style.display = 'block';
    document.getElementById('btnReconExcel').onclick = () =>
      window.open(`/api/recon/export-excel/${res.run_id}`);
    await loadReconMemorial(res.run_id);
    await loadReconHistory();
    await loadReconCampaigns();
  } catch (e) {
    alert('Erro: ' + e.message);
  } finally {
    btn.disabled = false;
    btn.textContent = '⚙ Calcular campanha base';
    updateReconActionState(_reconLatestDataCheck);
  }
}

async function runReconMonitoring() {
  const bank = document.getElementById('recon-bank')?.value;
  const tag = document.getElementById('recon-tag')?.value;
  const pvtId = document.getElementById('recon-pvt-id')?.value;
  const author = document.getElementById('recon-author')?.value;
  const notes = document.getElementById('recon-notes')?.value;
  const analytical = readReconAnalyticalInputs();
  const campaignInputs = readReconCampaignInputs();

  if (!campaignInputs.campaign_id) {
    alert('Calcule primeiro a campanha base para gerar o ID da campanha.');
    return;
  }
  if (!campaignInputs.monitor_day_ref) {
    alert('Informe a data do monitoramento pós-aplicação.');
    return;
  }
  if (!bank || !tag || !pvtId) {
    alert('Banco, TAG e parâmetros PVT precisam permanecer preenchidos.');
    return;
  }

  const btn = document.getElementById('btnReconMonitor');
  btn.disabled = true;
  btn.textContent = '⌛ Registrando...';

  try {
    const res = await j('/api/recon/calcular', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        bank,
        tag,
        day_ref: campaignInputs.monitor_day_ref,
        pvt_params_id: parseInt(pvtId, 10),
        author,
        notes,
        analytical,
        campaign_id: campaignInputs.campaign_id,
        campaign_phase: 'post',
        current_k_factor: campaignInputs.current_k_factor,
        proposal_mode: campaignInputs.proposal_mode,
        proposed_k_factor_manual: campaignInputs.proposed_k_factor_manual,
        applied_k_factor: campaignInputs.applied_k_factor,
        applied_at: campaignInputs.applied_at,
      })
    });
    _reconCurrentRunId = res.run_id;
    renderReconResumo(res.resumo, res.meta);
    renderReconCalcTable(res.calc_horas);
    renderReconAnalyticalSummary(res.meta?.analytical_snapshot || {});
    renderReconCampaignSummary(res.meta?.campaign || null, res.meta?.k_proposal || null);
    setReconCampaignContext(res.meta?.campaign || null);
    document.getElementById('recon-resumo-card').style.display = 'block';
    document.getElementById('recon-calc-card').style.display = 'block';
    document.getElementById('btnReconExcel').onclick = () =>
      window.open(`/api/recon/export-excel/${res.run_id}`);
    await loadReconMemorial(res.run_id);
    await loadReconHistory();
    await loadReconCampaigns();
  } catch (e) {
    alert('Erro: ' + e.message);
  } finally {
    btn.disabled = false;
    btn.textContent = '📈 Registrar monitoramento 24h';
  }
}

function useReconProposedK() {
  const value = _reconCurrentProposal?.proposed_k_factor_selected;
  if (value != null && Number.isFinite(value)) {
    setReconInputValue('recon-applied-k-factor', value);
    refreshReconReadiness();
    return;
  }
  alert('Nenhum K selecionado disponível para aplicar.');
}

function statusFill(s) {
  return s === 'OK' ? 'color:var(--green)' :
    s === 'ATENÇÃO' ? 'color:var(--amber)' :
      s === 'VERIFICAR' ? 'color:var(--red)' : 'color:var(--muted)';
}

function renderReconResumo(r, meta) {
  const linha = [
    ['Massa HC (t)', r.massa_hc_ref_t, r.massa_hc_mpfm_t, r.desvio_hc_pct, r.status_hc],
    ['Massa Total (t)', r.massa_total_ref_t, r.massa_total_mpfm_t, r.desvio_total_pct, r.status_total],
    ['Massa Água (t)', r.massa_agua_ref_t, r.massa_agua_mpfm_t, r.desvio_agua_pct, r.status_agua],
  ];
  document.getElementById('recon-resumo-linha').innerHTML =
    `<thead><tr><th>Indicador</th><th>SEP Ref</th><th>MPFM</th><th>Δ%</th><th>Status</th></tr></thead>` +
    '<tbody>' + linha.map(([label, ref, mpfm, dev, st]) =>
      `<tr><td>${label}</td><td>${fmt(ref)}</td><td>${fmt(mpfm)}</td>
       <td style="${statusFill(st)}">${fmt(dev)}%</td>
       <td style="${statusFill(st)};font-weight:600">${st || '—'}</td></tr>`
    ).join('') + '</tbody>';

  const st_rows = [
    ['Óleo ST (m³)', r.oleo_std_ref_sm3, r.oleo_st_mpfm_m3, r.desvio_oleo_st_pct, r.status_oleo_st],
    ['Gás ST (sm³)', r.gas_total_ref_sm3, r.gas_st_mpfm_ksm3, r.desvio_gas_st_pct, r.status_gas_st],
    ['Água ST (m³)', r.agua_ref_sm3, r.agua_st_mpfm_m3, r.desvio_agua_st_pct, r.status_agua_st],
  ];
  document.getElementById('recon-resumo-st').innerHTML =
    `<thead><tr><th>Indicador</th><th>Ref Reconc.</th><th>MPFM ST</th><th>Δ%</th><th>Status</th></tr></thead>` +
    '<tbody>' + st_rows.map(([label, ref, mpfm, dev, st]) =>
      `<tr><td>${label}</td><td>${fmt(ref)}</td><td>${fmt(mpfm)}</td>
       <td style="${statusFill(st)}">${dev != null ? fmt(dev) + '%' : 'Bloqueado'}</td>
       <td style="${statusFill(st)};font-weight:600">${st || '—'}</td></tr>`
    ).join('') + '</tbody>';

  const sf = r.status_final || 'INDISPONÍVEL';
  document.getElementById('recon-status-badge').innerHTML =
    `<span style="font-size:14px;font-weight:700;${statusFill(sf)}">
       Status Final: ${sf}
     </span>`;
  document.getElementById('recon-cobertura-badge').innerHTML = (() => {
    const janela = r.horas_janela ?? 24;
    const isTestWindow = janela < 24;
    const label = isTestWindow
      ? `<span style="background:var(--amber);color:var(--bg);font-size:10px;font-weight:700;padding:1px 5px;border-radius:4px;margin-right:4px">JANELA TESTE</span>${r.horas_validas}/${janela}h`
      : `${r.horas_validas}/24h`;
    const pct = `(${r.cobertura_pct}%)`;
    const warn = r.consolidado_completo ? '' : ' ⚠ incompleto';
    return `<span style="color:var(--muted);font-size:12px">${label} ${pct}${warn}</span>`;
  })();

  const flags = (typeof r.qa_flags_consolidados === 'string'
    ? r.qa_flags_consolidados.split('|')
    : r.qa_flags_consolidados || []).filter(Boolean);
  document.getElementById('recon-qa-flags').innerHTML = flags.length
    ? `<div style="font-size:11px;color:var(--amber)">⚠ QA: ${flags.join(' · ')}</div>`
    : '';
}

function renderReconCalcTable(rows) {
  const ST = {OK: 'var(--green)', ATENÇÃO: 'var(--amber)', VERIFICAR: 'var(--red)'};
  document.getElementById('recon-calc-rows').innerHTML = rows.map(r => {
    const col = ST[r.status_final] || 'var(--muted)';
    const pct = v => v != null ? `<span style="color:${Math.abs(v) < 5 ? 'var(--green)' : Math.abs(v) < 10 ? 'var(--amber)' : 'var(--red)'}">${v.toFixed(3)}%</span>` : '—';
    return `<tr style="box-shadow:inset 0 0 0 1px ${col}">
      <td><strong>${r.hora}</strong></td>
      <td>${fmt(r.gsv_sep_sm3)}</td>
      <td>${fmt(r.agua_sep_sm3)}</td>
      <td>${fmt(r.gas_livre_sep_sm3)}</td>
      <td>${fmt(r.oleo_base_ref_sm3)}</td>
      <td>${fmt(r.oleo_std_reconc_sm3)}</td>
      <td>${fmt(r.gas_dissolvido_sm3)}</td>
      <td>${fmt(r.gas_total_reconc_sm3)}</td>
      <td>${fmt(r.massa_oleo_ref_t)}</td>
      <td>${fmt(r.massa_gas_ref_t)}</td>
      <td>${fmt(r.massa_agua_ref_t)}</td>
      <td><strong>${fmt(r.massa_hc_ref_t)}</strong></td>
      <td><strong>${fmt(r.massa_total_ref_t)}</strong></td>
      <td>${pct(r.desvio_hc_linha_pct)}</td>
      <td>${pct(r.desvio_total_linha_pct)}</td>
      <td>${pct(r.desvio_agua_linha_pct)}</td>
      <td style="font-size:11px;color:var(--muted)">${r.agua_fonte || ''}</td>
      <td style="font-size:10px;color:var(--amber)">${(r.qa_flags || '').replace(/\|/g, ' · ')}</td>
      <td>${r.status_linha ? `<span class="badge ${r.status_linha === 'OK' ? 'ok' : r.status_linha === 'ATENÇÃO' ? 'warn' : 'err'}">${r.status_linha}</span>` : '—'}</td>
      <td>${r.status_final ? `<span class="badge ${r.status_final === 'OK' ? 'ok' : r.status_final === 'ATENÇÃO' ? 'warn' : 'err'}">${r.status_final}</span>` : '—'}</td>
    </tr>`;
  }).join('');
}

// ── Histórico ────────────────────────────────────────────────────────────────
async function loadReconHistory() {
  const d = await j('/api/recon/runs');
  const rows = d.runs || [];
  document.getElementById('recon-history-rows').innerHTML = !rows.length
    ? '<tr><td colspan="12" style="color:var(--muted);text-align:center">Nenhuma reconciliação executada ainda.</td></tr>'
    : rows.map(r => `<tr>
        <td>${r.id}</td>
        <td>${r.campaign_id || '—'}</td>
        <td>${r.campaign_phase || 'baseline'}</td>
        <td style="font-size:11px">${r.run_at}</td>
        <td><strong>${r.bank}</strong></td>
        <td>${r.tag}</td>
        <td>${fmtDate(r.day_ref)}</td>
        <td>${r.horas_validas}/24 (${r.cobertura_pct}%)</td>
        <td>${r.status_linha ? `<span class="badge ${r.status_linha === 'OK' ? 'ok' : r.status_linha === 'ATENÇÃO' ? 'warn' : 'err'}">${r.status_linha}</span>` : '—'}</td>
        <td>${r.status_final ? `<span class="badge ${r.status_final === 'OK' ? 'ok' : r.status_final === 'ATENÇÃO' ? 'warn' : 'err'}">${r.status_final}</span>` : '—'}</td>
        <td>${r.author || '—'}</td>
        <td style="display:flex;gap:4px">
          <button class="btn sm" onclick="loadReconRunDetail(${r.id})">Ver</button>
          <button class="btn sm secondary" onclick="loadReconMemorial(${r.id}, {switchTab:true})">Memorial</button>
          <button class="btn sm secondary" onclick="window.open('/api/recon/export-excel/${r.id}')">↓ Excel</button>
        </td>
      </tr>`).join('');
}

async function loadReconCampaigns() {
  const d = await j('/api/recon/campaigns');
  const rows = d.campaigns || [];
  const host = document.getElementById('recon-campaign-rows');
  if (!host) return;
  host.innerHTML = !rows.length
    ? '<tr><td colspan="10" style="color:var(--muted);text-align:center">Nenhuma campanha 24h cadastrada ainda.</td></tr>'
    : rows.map(r => `<tr>
        <td>${r.id}</td>
        <td><strong>${r.bank}</strong></td>
        <td>${r.tag}</td>
        <td>${fmtDate(r.baseline_day_ref)}</td>
        <td>${r.post_day_ref ? fmtDate(r.post_day_ref) : '—'}</td>
        <td>${r.current_k_factor != null ? fmtFactor(r.current_k_factor) : '—'}</td>
        <td>${r.proposed_k_factor_selected != null ? fmtFactor(r.proposed_k_factor_selected) : '—'}</td>
        <td>${r.applied_k_factor != null ? fmtFactor(r.applied_k_factor) : '—'}</td>
        <td><span class="badge ${r.monitoring_status === 'accepted' ? 'ok' : r.monitoring_status === 'rejected' ? 'err' : 'warn'}">${formatReconCampaignStatus(r.monitoring_status || r.status)}</span></td>
        <td><button class="btn sm" onclick="loadReconCampaign(${r.id})">Abrir</button></td>
      </tr>`).join('');
}

async function loadReconCampaign(campaignId) {
  const c = await j(`/api/recon/campaigns/${campaignId}`);
  showReconTab('run');
  setReconInputValue('recon-bank', c.bank || '');
  await loadReconPVTOptions();
  setReconInputValue('recon-tag', c.tag || '');
  setReconInputValue('recon-date', c.baseline_day_ref || '');
  setReconInputValue('recon-pvt-id', c.pvt_params_id || '');
  setReconCampaignContext(c);
  renderReconAnalyticalSummary(c.analytical_snapshot || {});
  renderReconCampaignSummary(c, null);
  renderReconPvtPreview();
  showReconCampaignOnlySummary();
  if (c.baseline_run_id) await loadReconMemorial(c.baseline_run_id);
}

async function loadReconRunDetail(runId) {
  const d = await j(`/api/recon/runs/${runId}`);
  showReconTab('run');
  setReconInputValue('recon-bank', d.bank || '');
  await loadReconPVTOptions();
  setReconInputValue('recon-tag', d.tag || '');
  setReconInputValue('recon-date', d.day_ref || '');
  setReconInputValue('recon-pvt-id', d.pvt_params_id || '');
  _reconCurrentRunId = runId;
  if (d.calc_hourly_json && d.resumo_json) {
    renderReconResumo(d.resumo_json, {});
    renderReconCalcTable(d.calc_hourly_json);
    renderReconAnalyticalSummary(d.analytical_snapshot || {});
    if (d.campaign_id) {
      try {
        const campaign = await j(`/api/recon/campaigns/${d.campaign_id}`);
        setReconCampaignContext(campaign);
        renderReconCampaignSummary(campaign, null);
      } catch (_) {
        renderReconCampaignSummary(null, null);
      }
    } else {
      renderReconCampaignSummary(null, null);
    }
    renderReconPvtPreview();
    document.getElementById('recon-resumo-card').style.display = 'block';
    document.getElementById('recon-calc-card').style.display = 'block';
    document.getElementById('btnReconExcel').onclick = () =>
      window.open(`/api/recon/export-excel/${runId}`);
    await loadReconMemorial(runId);
  }
}
