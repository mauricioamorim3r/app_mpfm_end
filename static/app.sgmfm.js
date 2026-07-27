'use strict';

function sgmfmEsc(value) {
  return String(value ?? '').replace(/[&<>"']/g, (char) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
}

function sgmfmOptionMarkup(options, current) {
  return (options || []).map((option) => {
    const item = typeof option === 'string' ? {value: option, label: option || '—'} : option;
    const selected = String(item.value ?? '') === String(current ?? '') ? ' selected' : '';
    return `<option value="${sgmfmEsc(item.value ?? '')}"${selected}>${sgmfmEsc(item.label ?? item.value ?? '')}</option>`;
  }).join('');
}

function sgmfmCurrent() {
  state.sgmfm = state.sgmfm || {recordType:'rotina', schema:{}, currentId:null, currentPayload:null, currentRecord:null, visibility:{}, summary:null};
  return state.sgmfm;
}

function sgmfmSchemaFor(type) {
  return sgmfmCurrent().schema?.[type] || null;
}

function sgmfmStatusOptions(type) {
  if (type === 'rotina') return ['', 'Sem anomalia relevante', 'Com ressalvas', 'Em acompanhamento', 'Bloqueado'];
  if (type === 'logbook') return ['', 'Recebido', 'Em análise', 'Pendente', 'Concluído', 'Substituído', 'Obsoleto'];
  return ['', 'EM_ANALISE', 'PENDENTE_INFO', 'REVISADA', 'CONCLUIDA'];
}

function downloadSGMFMTemplate() {
  const type = sgmfmCurrent().recordType || 'rotina';
  const a = document.createElement('a');
  a.href = `${API}/sgmfm/template/${encodeURIComponent(type)}`;
  a.download = '';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
}

async function loadSGMFM() {
  setLoading('page-sgmfm', true);
  try {
    const s = sgmfmCurrent();
    await Promise.all([loadSGMFMSummary(), ensureSGMFMSchema(s.recordType)]);
    renderSGMFMFilters();
    await loadSGMFMRecords();
    if (!s.currentPayload) {
      await newSGMFMRecord();
    } else {
      renderSGMFMForm();
    }
  } finally {
    setLoading('page-sgmfm', false);
  }
}

async function loadSGMFMSummary() {
  const data = await j(`${API}/sgmfm/summary`).catch(() => ({summary:{}}));
  const summary = data.summary || {};
  sgmfmCurrent().summary = summary;
  const bind = (key, totalId, metaId) => {
    const row = summary[key] || {};
    const totalEl = document.getElementById(totalId);
    const metaEl = document.getElementById(metaId);
    if (totalEl) totalEl.textContent = fmt(row.total ?? 0);
    if (metaEl) metaEl.textContent = row.latest ? `último: ${fmtDate(row.latest)}` : 'sem registros';
  };
  bind('rotina', 'sgmSummaryRotina', 'sgmSummaryRotinaMeta');
  bind('logbook', 'sgmSummaryLogbook', 'sgmSummaryLogbookMeta');
  bind('pvt', 'sgmSummaryPvt', 'sgmSummaryPvtMeta');
}

async function ensureSGMFMSchema(type) {
  const s = sgmfmCurrent();
  s.schema = s.schema || {};
  if (s.schema[type]) return s.schema[type];
  const data = await j(`${API}/sgmfm/schema?record_type=${encodeURIComponent(type)}`);
  s.schema[type] = data;
  s.visibility[type] = data.visibility || {visible_keys:[]};
  return data;
}

function renderSGMFMFilters() {
  const s = sgmfmCurrent();
  const type = s.recordType;
  document.getElementById('sgmTabRotina')?.classList.toggle('active', type === 'rotina');
  document.getElementById('sgmTabLogbook')?.classList.toggle('active', type === 'logbook');
  document.getElementById('sgmTabPvt')?.classList.toggle('active', type === 'pvt');
  const statusEl = document.getElementById('sgmStatus');
  if (statusEl) {
    statusEl.innerHTML = sgmfmOptionMarkup(sgmfmStatusOptions(type), statusEl.value || '');
  }
  const bankEl = document.getElementById('sgmBank');
  const schema = sgmfmSchemaFor(type);
  const banks = Array.from(new Set((schema?.measurement_points || []).map((item) => item.bank).filter(Boolean))).sort();
  if (bankEl) {
    const current = bankEl.value || '';
    bankEl.innerHTML = `<option value="">Todos</option>${banks.map((bank) => `<option value="${sgmfmEsc(bank)}"${bank === current ? ' selected' : ''}>${sgmfmEsc(bank)}</option>`).join('')}`;
  }
  ['sgmDateFrom','sgmDateTo','sgmStatus','sgmBank','sgmQuery'].forEach((id) => {
    const el = document.getElementById(id);
    if (el && !el.dataset.bound) {
      el.dataset.bound = '1';
      const evt = id === 'sgmQuery' ? 'input' : 'change';
      el.addEventListener(evt, () => loadSGMFMRecords());
    }
  });
  enhanceBrazilianDateInputs(document.getElementById('page-sgmfm') || document);
}

async function loadSGMFMRecords() {
  const s = sgmfmCurrent();
  const type = s.recordType;
  const qs = new URLSearchParams({
    date_from: parseBrDateToIso(document.getElementById('sgmDateFrom')?.dataset.isoValue || document.getElementById('sgmDateFrom')?.value || ''),
    date_to: parseBrDateToIso(document.getElementById('sgmDateTo')?.dataset.isoValue || document.getElementById('sgmDateTo')?.value || ''),
    status: document.getElementById('sgmStatus')?.value || '',
    bank: document.getElementById('sgmBank')?.value || '',
    q: document.getElementById('sgmQuery')?.value || '',
  });
  const data = await j(`${API}/sgmfm/${type}?${qs}`).catch(() => ({items:[]}));
  s.records = s.records || {};
  s.records[type] = data.items || [];
  renderSGMFMRecordList();
}

function renderSGMFMRecordList() {
  const s = sgmfmCurrent();
  const rows = s.records?.[s.recordType] || [];
  const list = document.getElementById('sgmRecordList');
  const title = document.getElementById('sgmListTitle');
  const meta = document.getElementById('sgmListMeta');
  if (title) title.textContent = `Registros de ${s.recordType === 'rotina' ? 'Rotina' : s.recordType === 'logbook' ? 'Logbook' : 'PVT'}`;
  if (meta) meta.textContent = `${rows.length} item(ns)`;
  if (!list) return;
  if (!rows.length) {
    list.innerHTML = `<div class="empty-state">Nenhum registro encontrado para os filtros atuais.</div>`;
    return;
  }
  list.innerHTML = rows.map((row) => `
    <button type="button" class="sgmfm-recorditem${Number(s.currentId) === Number(row.id) ? ' active' : ''}" onclick="openSGMFMRecord(${row.id})">
      <strong>${sgmfmEsc(row.record_code || row.title || 'Registro')}</strong>
      <span>${sgmfmEsc(row.title || 'Sem título')}</span>
      <small>${sgmfmEsc([fmtDate(row.base_date || row.reference_date || row.analysis_date), row.bank, row.tag].filter(Boolean).join(' · '))}</small>
      <em>${sgmfmEsc(row.status || 'sem status')}</em>
    </button>
  `).join('');
}

function sgmfmVisibleKeys() {
  const s = sgmfmCurrent();
  return new Set((s.visibility?.[s.recordType]?.visible_keys || []).map(String));
}

function sgmfmShouldShow(key) {
  const visible = sgmfmVisibleKeys();
  return visible.size === 0 || visible.has(String(key));
}

function sgmfmFieldMarkup(field, payload, schema) {
  if (!sgmfmShouldShow(field.key)) return '';
  const value = payload?.[field.key] ?? '';
  const widthCls = field.width === 'full' ? ' full' : field.width === 'half' ? '' : ` ${field.width || ''}`;
  let control = '';
  if (field.type === 'textarea') {
    control = `<textarea id="sgmField_${sgmfmEsc(field.key)}" data-sgm-key="${sgmfmEsc(field.key)}" rows="${field.rows || 3}" placeholder="${sgmfmEsc(field.placeholder || '')}">${sgmfmEsc(value)}</textarea>`;
  } else if (field.type === 'select' || field.type === 'variable-preset') {
    control = `<select id="sgmField_${sgmfmEsc(field.key)}" data-sgm-key="${sgmfmEsc(field.key)}" data-sgm-type="${sgmfmEsc(field.type)}">${sgmfmOptionMarkup(field.options || [''], value)}</select>`;
  } else if (field.type === 'measurement-point') {
    const options = [{value:'', label:'Selecione...'}].concat((schema.measurement_points || []).map((point) => ({value: point.id, label: point.label})));
    const current = (schema.measurement_points || []).find((point) => point.measurement_point === value || point.id === value)?.id || '';
    control = `<select id="sgmField_${sgmfmEsc(field.key)}" data-sgm-key="${sgmfmEsc(field.key)}" data-sgm-type="measurement-point">${sgmfmOptionMarkup(options, current)}</select>`;
  } else {
    const inputType = field.type || 'text';
    const readonly = field.readonly ? ' readonly' : '';
    control = `<input id="sgmField_${sgmfmEsc(field.key)}" data-sgm-key="${sgmfmEsc(field.key)}" type="${sgmfmEsc(inputType)}" value="${sgmfmEsc(value)}" placeholder="${sgmfmEsc(field.placeholder || '')}"${readonly}>`;
  }
  return `<div class="field sgmfm-field${widthCls}"><label for="sgmField_${sgmfmEsc(field.key)}">${sgmfmEsc(field.label)}</label>${control}</div>`;
}

function sgmfmRepeatableMarkup(section, payload) {
  if (!sgmfmShouldShow(section.id)) return '';
  const rows = payload?.[section.id] || [];
  const header = section.columns.map((col) => `<th>${sgmfmEsc(col.label)}</th>`).join('') + '<th></th>';
  const body = rows.map((row, rowIndex) => sgmfmRepeatableRowMarkup(section, row, rowIndex)).join('');
  return `
    <div class="sgmfm-repeatable" data-repeatable-id="${sgmfmEsc(section.id)}">
      <div class="sgmfm-repeatable__head">
        <h3>${sgmfmEsc(section.label)}</h3>
        <button class="btn secondary sm" type="button" onclick="addSGMFMRepeatableRow('${sgmfmEsc(section.id)}')">${sgmfmEsc(section.add_label || '+ Adicionar')}</button>
      </div>
      <div class="tablewrap">
        <table class="sgmfm-table">
          <thead><tr>${header}</tr></thead>
          <tbody id="sgmRepeat_${sgmfmEsc(section.id)}">${body || `<tr><td colspan="${section.columns.length + 1}" class="muted">Sem linhas cadastradas.</td></tr>`}</tbody>
        </table>
      </div>
    </div>
  `;
}

function sgmfmRepeatableRowMarkup(section, row, rowIndex) {
  const cells = section.columns.map((col) => {
    const value = row?.[col.key] ?? '';
    let control = '';
    if (col.type === 'textarea') {
      control = `<textarea data-repeatable="${sgmfmEsc(section.id)}" data-row="${rowIndex}" data-key="${sgmfmEsc(col.key)}" rows="2"${col.readonly ? ' readonly' : ''}>${sgmfmEsc(value)}</textarea>`;
    } else if (col.type === 'select' || col.type === 'variable-preset') {
      control = `<select data-repeatable="${sgmfmEsc(section.id)}" data-row="${rowIndex}" data-key="${sgmfmEsc(col.key)}" data-col-type="${sgmfmEsc(col.type)}"${col.readonly ? ' disabled' : ''}>${sgmfmOptionMarkup(col.options || [''], value)}</select>`;
    } else {
      control = `<input data-repeatable="${sgmfmEsc(section.id)}" data-row="${rowIndex}" data-key="${sgmfmEsc(col.key)}" type="${sgmfmEsc(col.type || 'text')}" value="${sgmfmEsc(value)}"${col.readonly ? ' readonly' : ''}>`;
    }
    return `<td>${control}</td>`;
  }).join('');
  return `<tr>${cells}<td><button class="btn secondary sm" type="button" onclick="removeSGMFMRepeatableRow('${sgmfmEsc(section.id)}', ${rowIndex})">✕</button></td></tr>`;
}

function renderSGMFMForm() {
  const s = sgmfmCurrent();
  const schema = sgmfmSchemaFor(s.recordType);
  const payload = s.currentPayload || {};
  const mount = document.getElementById('sgmFormMount');
  if (!mount || !schema?.definition) return;
  const grouped = {};
  (schema.definition.fields || []).forEach((field) => {
    (grouped[field.section] = grouped[field.section] || []).push(field);
  });
  mount.innerHTML = `
    <div class="sgmfm-form">
      ${(schema.definition.sections || []).map((section) => `
        <section class="card sgmfm-section">
          <h3>${sgmfmEsc(section.label)}</h3>
          <div class="sgmfm-grid">
            ${(grouped[section.id] || []).map((field) => sgmfmFieldMarkup(field, payload, schema)).join('')}
          </div>
        </section>
      `).join('')}
      ${(schema.definition.repeatable_sections || []).map((section) => sgmfmRepeatableMarkup(section, payload)).join('')}
    </div>
  `;
  const title = document.getElementById('sgmFormTitle');
  const meta = document.getElementById('sgmFormMeta');
  if (title) title.textContent = payload.record_code || 'Novo registro';
  if (meta) meta.textContent = payload.measurement_point ? `${payload.measurement_point} · ${payload.bank || 'sem banco'}` : 'Registro sem ponto definido';
  enhanceBrazilianDateInputs(mount);
  bindSGMFMFormEnhancements();
}

function bindSGMFMFormEnhancements() {
  const schema = sgmfmSchemaFor(sgmfmCurrent().recordType);
  const pointSelect = document.getElementById('sgmField_measurement_point');
  if (pointSelect && !pointSelect.dataset.bound) {
    pointSelect.dataset.bound = '1';
    pointSelect.addEventListener('change', () => {
      const point = (schema?.measurement_points || []).find((item) => item.id === pointSelect.value);
      if (!point) return;
      ['bank','tag','instrument','loop','meter_type'].forEach((key) => {
        const input = document.getElementById(`sgmField_${key}`);
        if (input) input.value = point[key === 'tag' ? 'measurement_point' : key] || '';
      });
    });
  }
  document.querySelectorAll('select[data-col-type="variable-preset"]').forEach((select) => {
    if (select.dataset.bound) return;
    select.dataset.bound = '1';
    select.addEventListener('change', () => {
      const rowIndex = select.dataset.row;
      const sectionId = select.dataset.repeatable;
      const chosen = select.value;
      const preset = [
        ['V01', 'Pressão', 'bar', 'Valor coerente com a condição operacional e sem congelamento.'],
        ['V02', 'Temperatura', '°C', 'Valor coerente com a condição operacional e sem congelamento.'],
        ['V03', 'dP de Venturi', 'bar', 'Sinal disponível e fisicamente plausível.'],
        ['V04', 'Gamma count', 'counts/s', 'Tendência coerente e sem comportamento anormal.'],
        ['V05', 'DensityOil', 'kg/m³', 'Valor disponível e consistente com histórico/processo.'],
        ['V06', 'DensityGas', 'kg/m³', 'Valor disponível e consistente com histórico/processo.'],
        ['V07', 'DensityWater', 'kg/m³', 'Confirmar se medido ou manual quando aplicável.'],
        ['V08', 'WLR', '%', 'Valor coerente com histórico e condição do poço.'],
        ['V09', 'GVF', '%', 'Valor coerente com histórico e condição do poço.'],
        ['V10', 'Vazão óleo padrão', 'sm³/d', 'Valor coerente com produção esperada.'],
        ['V11', 'Vazão gás padrão', 'sm³/d', 'Valor coerente com produção esperada.'],
        ['V12', 'Vazão água padrão', 'sm³/d', 'Valor coerente com produção esperada.'],
      ].find((item) => item[0] === chosen);
      if (!preset) return;
      [['name', preset[1]], ['unit', preset[2]], ['criterion', preset[3]]].forEach(([key, value]) => {
        const target = document.querySelector(`[data-repeatable="${sectionId}"][data-row="${rowIndex}"][data-key="${key}"]`);
        if (target) target.value = value;
      });
    });
  });
}

function collectSGMFMFormPayload() {
  const s = sgmfmCurrent();
  const schema = sgmfmSchemaFor(s.recordType);
  const payload = {};
  (schema?.definition?.fields || []).forEach((field) => {
    const el = document.getElementById(`sgmField_${field.key}`);
    if (!el) return;
    if (field.type === 'measurement-point') {
      const point = (schema.measurement_points || []).find((item) => item.id === el.value);
      payload[field.key] = point ? point.measurement_point : '';
      return;
    }
    const raw = el.dataset?.isoValue || el.value || '';
    payload[field.key] = raw;
  });
  (schema.definition.repeatable_sections || []).forEach((section) => {
    const rows = {};
    document.querySelectorAll(`[data-repeatable="${section.id}"]`).forEach((el) => {
      const row = Number(el.dataset.row);
      const key = el.dataset.key;
      rows[row] = rows[row] || {};
      rows[row][key] = el.dataset?.isoValue || el.value || '';
    });
    payload[section.id] = Object.keys(rows).sort((a, b) => Number(a) - Number(b)).map((key) => rows[key]);
  });
  payload.record_code = payload.record_code || s.currentPayload?.record_code || '';
  return payload;
}

async function newSGMFMRecord() {
  const s = sgmfmCurrent();
  await ensureSGMFMSchema(s.recordType);
  const data = await j(`${API}/sgmfm/${s.recordType}/prefill`).catch(() => ({payload:{record_code:''}}));
  s.currentId = null;
  s.currentRecord = null;
  s.currentPayload = data.payload || {};
  renderSGMFMForm();
  setSGMFMStatus('Novo registro iniciado.');
}

async function openSGMFMRecord(recordId) {
  const s = sgmfmCurrent();
  const data = await j(`${API}/sgmfm/${s.recordType}/${recordId}`);
  s.currentId = recordId;
  s.currentRecord = data.record;
  s.currentPayload = data.record?.payload || {};
  renderSGMFMRecordList();
  renderSGMFMForm();
  setSGMFMStatus(`Registro ${data.record?.record_code || recordId} carregado.`);
}

async function saveSGMFMRecord() {
  const s = sgmfmCurrent();
  const payload = collectSGMFMFormPayload();
  const body = {id: s.currentId, record_code: payload.record_code || s.currentRecord?.record_code || '', payload};
  const res = await j(`${API}/sgmfm/${s.recordType}`, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body)});
  s.currentId = res.id;
  await openSGMFMRecord(res.id);
  await loadSGMFMSummary();
  await loadSGMFMRecords();
  setSGMFMStatus('Registro salvo com sucesso.');
}

async function prefillSGMFMRecord() {
  const s = sgmfmCurrent();
  const payload = collectSGMFMFormPayload();
  const schema = sgmfmSchemaFor(s.recordType);
  const selectedPointId = document.getElementById('sgmField_measurement_point')?.value || '';
  const point = (schema.measurement_points || []).find((item) => item.id === selectedPointId || item.measurement_point === payload.measurement_point);
  const dateBase = payload.base_date || payload.reference_date || payload.analysis_date || '';
  const data = await j(`${API}/sgmfm/${s.recordType}/prefill?point_id=${encodeURIComponent(point?.id || '')}&base_date=${encodeURIComponent(dateBase)}&reference_date=${encodeURIComponent(payload.reference_date || '')}`);
  s.currentPayload = {...payload, ...(data.payload || {}), record_code: payload.record_code || data.payload?.record_code || ''};
  renderSGMFMForm();
  setSGMFMStatus('Pré-preenchimento aplicado.');
}

async function duplicateSGMFMRecord() {
  const s = sgmfmCurrent();
  if (!s.currentId) return setSGMFMStatus('Salve ou abra um registro antes de duplicar.', true);
  const res = await j(`${API}/sgmfm/${s.recordType}/${s.currentId}/duplicate`, {method:'POST'});
  await openSGMFMRecord(res.id);
  await loadSGMFMRecords();
  await loadSGMFMSummary();
  setSGMFMStatus('Registro duplicado.');
}

async function deleteSGMFMRecord() {
  const s = sgmfmCurrent();
  if (!s.currentId) return setSGMFMStatus('Nenhum registro selecionado para exclusão.', true);
  if (!confirm('Excluir este registro do SGM-FM?')) return;
  await j(`${API}/sgmfm/${s.recordType}/${s.currentId}`, {method:'DELETE'});
  s.currentId = null;
  s.currentPayload = null;
  s.currentRecord = null;
  await loadSGMFMRecords();
  await loadSGMFMSummary();
  await newSGMFMRecord();
  setSGMFMStatus('Registro excluído.');
}

async function generateSGMFMHtml() {
  const s = sgmfmCurrent();
  if (!s.currentId) {
    await saveSGMFMRecord();
  }
  if (!sgmfmCurrent().currentId) return;
  await j(`${API}/sgmfm/${s.recordType}/${sgmfmCurrent().currentId}/generate-html`, {method:'POST'});
  await openSGMFMRecord(sgmfmCurrent().currentId);
  await loadSGMFMSummary();
  setSGMFMStatus('HTML gerado com sucesso.');
}

function openSGMFMHtml(printMode) {
  const s = sgmfmCurrent();
  if (!s.currentId) return setSGMFMStatus('Salve ou abra um registro antes de gerar o HTML.', true);
  const suffix = printMode ? '?print=1' : '';
  window.open(`${API}/sgmfm/${s.recordType}/${s.currentId}/html${suffix}`, '_blank');
}

function addSGMFMRepeatableRow(sectionId) {
  const s = sgmfmCurrent();
  const payload = collectSGMFMFormPayload();
  payload[sectionId] = payload[sectionId] || [];
  payload[sectionId].push({});
  s.currentPayload = payload;
  renderSGMFMForm();
}

function removeSGMFMRepeatableRow(sectionId, index) {
  const s = sgmfmCurrent();
  const payload = collectSGMFMFormPayload();
  payload[sectionId] = (payload[sectionId] || []).filter((_, idx) => idx !== index);
  s.currentPayload = payload;
  renderSGMFMForm();
}

function toggleSGMFMVisibilityPanel(show) {
  document.getElementById('sgmVisibilityModal')?.classList.toggle('show', !!show);
  if (show) renderSGMFMVisibilityPanel();
}

function renderSGMFMVisibilityPanel() {
  const s = sgmfmCurrent();
  const schema = sgmfmSchemaFor(s.recordType);
  const visible = new Set((s.visibility?.[s.recordType]?.visible_keys || []));
  const grid = document.getElementById('sgmVisibilityGrid');
  if (!grid || !schema) return;
  grid.innerHTML = (schema.visibility_items || []).map((item) => `
    <label class="chk-row">
      <input type="checkbox" data-sgm-visible="${sgmfmEsc(item.key)}" ${visible.size === 0 || visible.has(item.key) ? 'checked' : ''}>
      <span>${sgmfmEsc(item.label)}</span>
    </label>
  `).join('');
}

function selectAllSGMFMVisibility(flag) {
  document.querySelectorAll('#sgmVisibilityGrid input[type="checkbox"]').forEach((input) => { input.checked = !!flag; });
}

async function saveSGMFMVisibility() {
  const s = sgmfmCurrent();
  const visibleKeys = Array.from(document.querySelectorAll('#sgmVisibilityGrid input[type="checkbox"]:checked')).map((input) => input.dataset.sgmVisible);
  await j(`${API}/sgmfm/visibility/${s.recordType}`, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({visible_keys: visibleKeys})});
  s.visibility[s.recordType] = {visible_keys: visibleKeys};
  toggleSGMFMVisibilityPanel(false);
  renderSGMFMForm();
  setSGMFMStatus('Preferências de visibilidade salvas.');
}

function setSGMFMStatus(message, isError = false) {
  const el = document.getElementById('sgmStatusLine');
  if (!el) return;
  el.textContent = message;
  el.classList.toggle('error', !!isError);
}

async function setSGMFMType(type) {
  const s = sgmfmCurrent();
  s.recordType = type;
  s.currentId = null;
  s.currentPayload = null;
  s.currentRecord = null;
  await ensureSGMFMSchema(type);
  renderSGMFMFilters();
  await loadSGMFMRecords();
  await newSGMFMRecord();
}

window.loadSGMFM = loadSGMFM;
window.setSGMFMType = setSGMFMType;
window.newSGMFMRecord = newSGMFMRecord;
window.openSGMFMRecord = openSGMFMRecord;
window.saveSGMFMRecord = saveSGMFMRecord;
window.prefillSGMFMRecord = prefillSGMFMRecord;
window.duplicateSGMFMRecord = duplicateSGMFMRecord;
window.deleteSGMFMRecord = deleteSGMFMRecord;
window.generateSGMFMHtml = generateSGMFMHtml;
window.openSGMFMHtml = openSGMFMHtml;
window.addSGMFMRepeatableRow = addSGMFMRepeatableRow;
window.removeSGMFMRepeatableRow = removeSGMFMRepeatableRow;
window.toggleSGMFMVisibilityPanel = toggleSGMFMVisibilityPanel;
window.selectAllSGMFMVisibility = selectAllSGMFMVisibility;
window.saveSGMFMVisibility = saveSGMFMVisibility;
