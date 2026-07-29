'use strict';

function monitoringEscape(value) {
  return String(value ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
}

function monitoringMonth() {
  return document.getElementById('globalMonth')?.value || '';
}

function monitoringFormatMilSm3(value) {
  return value == null ? '—' : fmt((Number(value) || 0) / 1000);
}

function monitoringFormatPct(value) {
  if (value == null || Number.isNaN(Number(value))) return '—';
  return `${fmt(Number(value))}%`;
}

function monitoringLimitClass(row) {
  if (row.limit_status === 'Fora do limite') return 'row-err';
  if (row.limit_status === 'Sem par no dia') return 'row-warn';
  return '';
}

function monitoringDeviationCell(value, limit) {
  if (value == null || Number.isNaN(Number(value))) return '<span class="badge warn">Sem par</span>';
  const css = Math.abs(Number(value)) > limit ? 'err' : 'ok';
  return `<span class="badge ${css}">${monitoringFormatPct(value)}</span>`;
}

function monitoringSourceBadge(mode) {
  if (mode === 'Medição + anotação') return '<span class="badge info">Medição + anotação</span>';
  if (mode === 'Anotação manual') return '<span class="badge warn">Manual</span>';
  return '<span class="badge ok">Medição</span>';
}

function monitoringFillFilter(id, items) {
  const select = document.getElementById(id);
  if (!select) return;
  const current = select.value;
  select.innerHTML = '<option value="">Todos</option>' + (items || []).map(item => `<option value="${monitoringEscape(item)}">${monitoringEscape(item)}</option>`).join('');
  if (current && (items || []).includes(current)) select.value = current;
}

function monitoringRenderSummary(summary = {}) {
  const host = document.getElementById('monitoringSummary');
  if (!host) return;
  const cards = [
    ['Linhas', summary.rows || 0, 'linhas diárias no recorte', 'monitoring-summary-card'],
    ['Com par válido', summary.paired || 0, 'topside/subsea encontrados no mesmo dia', 'monitoring-summary-card'],
    ['Fora HC', summary.outside_hc || 0, 'abs(desvio HC) > 10%', 'monitoring-summary-card monitoring-summary-card--crit'],
    ['Fora Total', summary.outside_total || 0, 'abs(desvio total) > 7%', 'monitoring-summary-card monitoring-summary-card--warn'],
    ['8+ consecutivos', summary.warning_pairs || 0, 'pares com sequência >= 8 dias fora do limite', 'monitoring-summary-card monitoring-summary-card--warn'],
    ['Protocolo SGM-FM', summary.protocol_pairs || 0, 'pares que atingiram o gatilho do 10º dia consecutivo', 'monitoring-summary-card monitoring-summary-card--crit'],
    ['Com evento', summary.with_event || 0, 'linhas com evento registrado', 'monitoring-summary-card'],
    ['Sem par no dia', summary.without_counterpart || 0, 'há pareamento cadastral, mas falta a outra ponta', 'monitoring-summary-card monitoring-summary-card--muted'],
  ];
  host.innerHTML = cards.map(([label, value, meta, cls]) => `
    <div class="${cls}">
      <div class="monitoring-summary-card__label">${label}</div>
      <div class="monitoring-summary-card__value">${value}</div>
      <div class="monitoring-summary-card__meta">${meta}</div>
    </div>
  `).join('');
}

function monitoringNormalizeTag(value) {
  return String(value || '')
    .trim()
    .toUpperCase()
    .replace(/[^A-Z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '');
}

function monitoringPairBadgeClass(value, limit) {
  if (value == null || Number.isNaN(Number(value))) return 'warn';
  return Math.abs(Number(value)) > limit ? 'err' : 'ok';
}

function monitoringFocusPairDefinitions() {
  return [
    {
      key: 'PE4_RISERP5',
      title: 'PE-04 × Riser P5',
      subseaTag: 'PE_4',
      topsideTag: 'RISER_P5',
      subseaLabel: 'Medidor Subsea · PE-4',
      topsideLabel: 'Medidor Topside · Riser P5',
    },
    {
      key: 'PE2_RISERP2',
      title: 'PE-02 × Riser P2',
      subseaTag: 'PE_2',
      topsideTag: 'RISER_P2',
      subseaLabel: 'Medidor Subsea · PE-2',
      topsideLabel: 'Medidor Topside · Riser P2',
    },
    {
      key: 'PW104_RISERP4',
      title: 'PW-104DA × Riser P4',
      subseaTag: 'PW_104DA',
      topsideTag: 'RISER_P4',
      subseaLabel: 'Medidor Subsea · PW-104DA',
      topsideLabel: 'Medidor Topside · Riser P4',
    },
  ];
}

function monitoringFocusRowsForTag(rows, meterType, normalizedTag) {
  return (rows || [])
    .filter(row => row.meter_type === meterType && monitoringNormalizeTag(row.tag) === normalizedTag)
    .sort((a, b) => String(a.production_date).localeCompare(String(b.production_date)));
}

function monitoringFocusLatestDeviation(subseaRows, topsideRows) {
  const combined = [...(subseaRows || []), ...(topsideRows || [])]
    .filter(row => row.hc_deviation_pct != null || row.total_deviation_pct != null)
    .sort((a, b) => String(b.production_date).localeCompare(String(a.production_date)));
  return combined[0] || null;
}

function monitoringPairSummaryMap(monthlyPairs = []) {
  const map = new Map();
  (monthlyPairs || []).forEach((pair) => {
    if (pair?.key) map.set(pair.key, pair);
  });
  return map;
}

function monitoringFocusTable(rows, label) {
  const instrument = rows[0]?.instrument ? ` · ${monitoringEscape(rows[0].instrument)}` : '';
  if (!rows.length) {
    return `
      <div class="monitoring-focus-panel">
        <div class="monitoring-focus-panel__title">${label}</div>
        <div class="soft-empty monitoring-focus-empty">Sem linhas no recorte atual.</div>
      </div>
    `;
  }
  return `
    <div class="monitoring-focus-panel">
      <div class="monitoring-focus-panel__title">${label}${instrument}</div>
      <div class="monitoring-focus-tablewrap" role="region" aria-label="${label}">
        <table class="table monitoring-focus-table">
          <thead>
            <tr>
              <th>Data</th>
              <th>Óleo (m³)</th>
              <th>Gás (mil sm³)</th>
              <th>Água (m³)</th>
              <th>Óleo (t)</th>
              <th>Gás (t)</th>
              <th>Água (t)</th>
              <th>Pressão (barg)</th>
              <th>Temperatura (°C)</th>
            </tr>
          </thead>
          <tbody>
            ${rows.map(row => `
              <tr>
                <td class="mono">${fmtDate(row.production_date)}</td>
                <td class="num">${fmt(row.oil_sm3)}</td>
                <td class="num">${monitoringFormatMilSm3(row.gas_sm3)}</td>
                <td class="num">${fmt(row.water_sm3)}</td>
                <td class="num">${fmt(row.oil_t)}</td>
                <td class="num">${fmt(row.gas_t)}</td>
                <td class="num">${fmt(row.water_t)}</td>
                <td class="num">${fmt(row.pressure_barg)}</td>
                <td class="num monitoring-focus-temp">${fmt(row.temperature_c)}</td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    </div>
  `;
}

function renderMonitoringFocusPairs(rows = [], limits = { hc_pct: 10, total_pct: 7 }, monthlyPairs = []) {
  const host = document.getElementById('monitoringFocusPairs');
  if (!host) return;
  const definitions = monitoringFocusPairDefinitions();
  const monthlyPairMap = monitoringPairSummaryMap(monthlyPairs);
  host.innerHTML = definitions.map(def => {
    const subseaRows = monitoringFocusRowsForTag(rows, 'Subsea', def.subseaTag);
    const topsideRows = monitoringFocusRowsForTag(rows, 'Topside', def.topsideTag);
    const latest = monitoringFocusLatestDeviation(subseaRows, topsideRows);
    const monthSummary = monthlyPairMap.get(`${def.subseaTag}|${def.topsideTag}`) || null;
    const hcClass = monitoringPairBadgeClass(latest?.hc_deviation_pct, limits.hc_pct || 10);
    const totalClass = monitoringPairBadgeClass(latest?.total_deviation_pct, limits.total_pct || 7);
    const monthHcClass = monitoringPairBadgeClass(monthSummary?.monthly_hc_deviation_pct, limits.hc_pct || 10);
    const monthTotalClass = monitoringPairBadgeClass(monthSummary?.monthly_total_deviation_pct, limits.total_pct || 7);
    const pairedDays = monthSummary?.days_paired ?? Math.max(subseaRows.length, topsideRows.length);
    const latestDate = latest?.production_date ? fmtDate(latest.production_date) : monthSummary?.latest_date ? fmtDate(monthSummary.latest_date) : 'Sem par no recorte';
    const streakNote = monthSummary?.current_consecutive_outside_days ? ` · ${monthSummary.current_consecutive_outside_days} dia(s) consecutivos fora do limite` : '';
    const protocolBadge = monthSummary?.protocol_required || monthSummary?.protocol_triggered_in_month
      ? '<span class="badge err">Protocolo SGM-FM</span>'
      : monthSummary?.warning_threshold_reached
        ? `<span class="badge warn">Máx ${monthSummary.max_consecutive_outside_days} dia(s) consecutivos</span>`
        : '';
    return `
      <div class="monitoring-focus-card">
        <div class="monitoring-focus-card__head">
          <div>
            <div class="monitoring-focus-card__title">${def.title}</div>
            <div class="monitoring-focus-card__meta">${pairedDays} dia(s) com par no mês · última referência ${latestDate}${streakNote}</div>
            <div class="monitoring-focus-card__meta">Referência da razão: <strong>Topside</strong>. Cálculo mostrado = ((Subsea / Topside) - 1) × 100.</div>
          </div>
          <div class="monitoring-focus-card__stats" aria-label="Desvios do par ${def.title}">
            <span class="badge ${hcClass}">Último dia HC ${monitoringFormatPct(latest?.hc_deviation_pct)}</span>
            <span class="badge ${totalClass}">Último dia Total ${monitoringFormatPct(latest?.total_deviation_pct)}</span>
            <span class="badge ${monthHcClass}">Acum. mês HC ${monitoringFormatPct(monthSummary?.monthly_hc_deviation_pct)}</span>
            <span class="badge ${monthTotalClass}">Acum. mês Total ${monitoringFormatPct(monthSummary?.monthly_total_deviation_pct)}</span>
            <span class="badge info">Limites ±${limits.hc_pct || 10}% / ±${limits.total_pct || 7}%</span>
            ${protocolBadge}
          </div>
        </div>
        <div class="monitoring-focus-card__body">
          ${monitoringFocusTable(subseaRows, def.subseaLabel)}
          ${monitoringFocusTable(topsideRows, def.topsideLabel)}
        </div>
      </div>
    `;
  }).join('');
}

function monitoringResetForm(prefill = {}) {
  const month = monitoringMonth();
  const today = prefill.production_date || (month ? `${month}-01` : '');
  document.getElementById('btnSaveMonitoring').dataset.itemId = prefill.id || '';
  document.getElementById('monFormDate').value = today;
  document.getElementById('monFormBank').value = prefill.bank || document.getElementById('monBank')?.value || '';
  document.getElementById('monFormTag').value = prefill.tag || document.getElementById('monTag')?.value || '';
  document.getElementById('monFormMeterType').value = prefill.meter_type || document.getElementById('monMeterType')?.value || 'Subsea';
  document.getElementById('monFormInstrument').value = prefill.instrument || '';
  document.getElementById('monFormLoop').value = prefill.loop || '';
  document.getElementById('monFormEventOccurred').value = prefill.event_occurred || '';
  document.getElementById('monFormEventType').value = prefill.event_type || '';
  document.getElementById('monFormEventStatus').value = prefill.event_status || '';
  document.getElementById('monFormRedundancy').value = prefill.sensor_redundancy_ptdp || '';
  document.getElementById('monFormIntegrity').value = prefill.integrity_communication || '';
  document.getElementById('monFormNewPvt').value = prefill.new_pvt_result || '';
  document.getElementById('monFormNewKFactor').value = prefill.new_k_factor_implemented || '';
  document.getElementById('monFormOperationMode').value = prefill.operation_mode || '';
  document.getElementById('monFormAlignedSep').value = prefill.aligned_separator_test || '';
  document.getElementById('monFormObservations').value = prefill.observations || '';
  document.getElementById('monitoringFormStatus').textContent = prefill.id ? `Editando linha ${prefill.bank} · ${prefill.tag} · ${prefill.meter_type}.` : 'Nenhuma alteração pendente.';
  if (typeof refreshDateInputDisplay === 'function') refreshDateInputDisplay(document);
}

function monitoringBuildPayload() {
  return {
    id: document.getElementById('btnSaveMonitoring').dataset.itemId || undefined,
    production_date: document.getElementById('monFormDate').value,
    bank: document.getElementById('monFormBank').value.trim().toUpperCase(),
    tag: document.getElementById('monFormTag').value.trim(),
    meter_type: document.getElementById('monFormMeterType').value,
    instrument: document.getElementById('monFormInstrument').value.trim(),
    loop: document.getElementById('monFormLoop').value.trim(),
    event_occurred: document.getElementById('monFormEventOccurred').value,
    event_type: document.getElementById('monFormEventType').value.trim(),
    event_status: document.getElementById('monFormEventStatus').value.trim(),
    sensor_redundancy_ptdp: document.getElementById('monFormRedundancy').value.trim(),
    integrity_communication: document.getElementById('monFormIntegrity').value.trim(),
    new_pvt_result: document.getElementById('monFormNewPvt').value,
    new_k_factor_implemented: document.getElementById('monFormNewKFactor').value,
    operation_mode: document.getElementById('monFormOperationMode').value.trim(),
    aligned_separator_test: document.getElementById('monFormAlignedSep').value,
    observations: document.getElementById('monFormObservations').value.trim(),
  };
}

function monitoringRowActionButtons(row) {
  const deleteDisabled = row.id ? '' : 'disabled';
  const rowIndex = state.monitoringRows.findIndex(candidate =>
    candidate.production_date === row.production_date &&
    candidate.bank === row.bank &&
    candidate.tag === row.tag &&
    candidate.meter_type === row.meter_type
  );
  return `
    <button class="btn secondary sm" onclick="editMonitoringRowByIndex(${Number.isFinite(rowIndex) ? rowIndex : -1})">Editar</button>
    <button class="btn danger sm" ${deleteDisabled} onclick="deleteMonitoringRow(${Number.isFinite(row.id) ? row.id : 0})">Excluir</button>
  `;
}

function renderMonitoringTable(rows = [], limits = { hc_pct: 10, total_pct: 7 }) {
  const head = document.getElementById('monitoringHead');
  const body = document.getElementById('monitoringRows');
  if (!head || !body) return;
  head.innerHTML = `<tr>
    <th>Data</th><th>Banco</th><th>TAG</th><th>Tipo</th><th>Instrumento</th><th>Loop</th><th>Horas</th>
    <th>Óleo [sm³]</th><th>Gás [mil sm³]</th><th>Água [sm³]</th>
    <th>Óleo [t]</th><th>Gás [t]</th><th>Água [t]</th><th>HC [t]</th><th>Total [t]</th>
    <th>Pressão [barg]</th><th>Temperatura [°C]</th>
    <th>Par de comparação</th><th>Desvio % HC</th><th>Desvio % Total</th><th>Status limites</th><th>Dias consec. fora</th><th>Tratamento</th>
    <th>Evento?</th><th>Tipo do evento</th><th>Status do evento</th><th>Sensores P/T/ΔP</th><th>Integridade/Com.</th>
    <th>Novo PVT?</th><th>Novo K-Factor?</th><th>Modo operação</th><th>Alinhado p/ SEP teste?</th><th>Observações</th><th>Origem</th><th>Ações</th>
  </tr>`;
  body.innerHTML = rows.map(row => `
    <tr class="${monitoringLimitClass(row)}">
      <td class="mono">${fmtDate(row.production_date)}</td>
      <td>${tagChip(row.bank)}</td>
      <td class="mono">${monitoringEscape(row.tag || '')}</td>
      <td>${monitoringEscape(row.meter_type || '')}</td>
      <td class="mono">${monitoringEscape(row.instrument || '—')}</td>
      <td>${monitoringEscape(row.loop || '—')}</td>
      <td class="mono">${row.hours_available ?? 0}</td>
      <td class="num">${fmt(row.oil_sm3)}</td>
      <td class="num">${monitoringFormatMilSm3(row.gas_sm3)}</td>
      <td class="num">${fmt(row.water_sm3)}</td>
      <td class="num">${fmt(row.oil_t)}</td>
      <td class="num">${fmt(row.gas_t)}</td>
      <td class="num">${fmt(row.water_t)}</td>
      <td class="num" style="color:var(--accent);font-weight:700">${fmt(row.hc_t)}</td>
      <td class="num">${fmt(row.total_t)}</td>
      <td class="num">${fmt(row.pressure_barg)}</td>
      <td class="num">${fmt(row.temperature_c)}</td>
      <td>${monitoringEscape(row.pair_label || '—')}</td>
      <td>${monitoringDeviationCell(row.hc_deviation_pct, limits.hc_pct || 10)}</td>
      <td>${monitoringDeviationCell(row.total_deviation_pct, limits.total_pct || 7)}</td>
      <td>${row.limit_status ? `${badge(row.limit_status === 'Fora do limite' ? 'error' : row.limit_status === 'Dentro do limite' ? 'ok' : 'attention')} ${row.status_label && row.status_label !== row.limit_status ? `<span class="muted" style="display:block;font-size:11px;margin-top:4px">${monitoringEscape(row.status_label)}</span>` : ''}` : '—'}</td>
      <td>${row.days_outside_limits ? `<span class="badge ${row.protocol_required ? 'err' : row.attention_threshold_reached ? 'warn' : 'info'}">${row.days_outside_limits}</span>` : '—'}</td>
      <td>${row.protocol_required ? '<span class="badge err">Iniciar protocolo SGM-FM</span>' : row.attention_threshold_reached ? '<span class="badge warn">Atenção 8+ dias</span>' : '—'}</td>
      <td>${monitoringEscape(row.event_occurred || '—')}</td>
      <td>${monitoringEscape(row.event_type || '—')}</td>
      <td>${monitoringEscape(row.event_status || '—')}</td>
      <td>${monitoringEscape(row.sensor_redundancy_ptdp || '—')}</td>
      <td>${monitoringEscape(row.integrity_communication || '—')}</td>
      <td>${monitoringEscape(row.new_pvt_result || '—')}</td>
      <td>${monitoringEscape(row.new_k_factor_implemented || '—')}</td>
      <td>${monitoringEscape(row.operation_mode || '—')}</td>
      <td>${monitoringEscape(row.aligned_separator_test || '—')}</td>
      <td class="monitoring-observations" title="${monitoringEscape(row.observations || '')}">${monitoringEscape(row.observations || '—')}</td>
      <td>${monitoringSourceBadge(row.source_mode)}</td>
      <td>${monitoringRowActionButtons(row)}</td>
    </tr>
  `).join('') || '<tr><td colspan="35" class="muted">Sem linhas no recorte selecionado.</td></tr>';
}

async function loadMonitoring(silent = false) {
  if (!silent) setLoading('page-monitoramento', true);
  try {
  const qs = new URLSearchParams({
    month: monitoringMonth(),
    bank: document.getElementById('monBank')?.value || '',
    tag: document.getElementById('monTag')?.value || '',
    meter_type: document.getElementById('monMeterType')?.value || '',
    event_status: document.getElementById('monEventStatus')?.value || '',
    only_outside_limits: document.getElementById('monOnlyOutsideLimits')?.checked ? '1' : '0',
  });
  const data = await j(`${API}/ops/mpfm-monitoring?${qs}`).catch(() => ({ rows: [], summary: {}, limits: { hc_pct: 10, total_pct: 7 } }));
  state.monitoringRows = data.rows || [];
  state.monitoringMonthlyPairs = data.monthly_pairs || [];
  monitoringFillFilter('monBank', data.banks || []);
  monitoringFillFilter('monTag', data.tags || []);
  monitoringFillFilter('monEventStatus', data.event_statuses || []);
  renderMonitoringFocusPairs(state.monitoringRows, data.limits || { hc_pct: 10, total_pct: 7 }, state.monitoringMonthlyPairs);
  renderMonitoringTable(state.monitoringRows, data.limits || { hc_pct: 10, total_pct: 7 });
  monitoringRenderSummary(data.summary || {});
  if (!document.getElementById('btnSaveMonitoring').dataset.itemId) {
    monitoringResetForm();
  }
  } finally {
    if (!silent) setLoading('page-monitoramento', false);
  }
}

window.editMonitoringRowByIndex = (rowIndex) => {
  const row = state.monitoringRows?.[Number(rowIndex)];
  if (!row) {
    document.getElementById('monitoringFormStatus').textContent = 'Linha não encontrada para edição.';
    return;
  }
  monitoringResetForm(row);
};

window.deleteMonitoringRow = async (id) => {
  if (!id) {
    document.getElementById('monitoringFormStatus').textContent = 'Esta linha não tem anotação salva para excluir.';
    return;
  }
  if (!confirm('Excluir esta anotação operacional?')) return;
  try {
    const res = await fetch(`${API}/ops/mpfm-monitoring/${id}`, { method: 'DELETE' });
    if (!res.ok) {
      const payload = await res.json().catch(() => ({}));
      throw new Error(payload.detail || payload.error || `Falha HTTP ${res.status}`);
    }
    monitoringResetForm();
    await loadMonitoring();
    document.getElementById('monitoringFormStatus').textContent = 'Anotação excluída.';
  } catch(err) {
    document.getElementById('monitoringFormStatus').textContent = `Erro ao excluir: ${err.message}`;
  }
};

document.getElementById('btnLoadMonitoring')?.addEventListener('click', loadMonitoring);
document.getElementById('btnMonitoringNew')?.addEventListener('click', () => monitoringResetForm());
document.getElementById('btnResetMonitoring')?.addEventListener('click', () => monitoringResetForm());
document.getElementById('btnSaveMonitoring')?.addEventListener('click', async () => {
  const status = document.getElementById('monitoringFormStatus');
  const payload = monitoringBuildPayload();
  if (!payload.production_date || !payload.bank || !payload.tag || !payload.meter_type) {
    status.textContent = 'Data, banco, TAG e tipo são obrigatórios.';
    return;
  }
  await j(`${API}/ops/mpfm-monitoring`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  status.textContent = 'Registro salvo.';
  await loadMonitoring();
});
document.getElementById('btnDeleteMonitoring')?.addEventListener('click', async () => {
  const id = Number(document.getElementById('btnSaveMonitoring').dataset.itemId || 0);
  await window.deleteMonitoringRow(id);
});
