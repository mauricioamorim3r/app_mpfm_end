'use strict';

function xml042Escape(value) {
  return String(value ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
}

function xml042CurrentMonth() {
  return document.getElementById('globalMonth')?.value || '';
}

function xml042SelectedDayValue() {
  return document.getElementById('xml042Day')?.value || '';
}

function xml042StatusText(message, isError = false) {
  const host = document.getElementById('xml042StatusText');
  if (!host) return;
  host.textContent = message || '';
  host.style.color = isError ? 'var(--red)' : 'var(--muted)';
}

function xml042RenderSummary(summary = {}) {
  const host = document.getElementById('xml042Summary');
  const lblPending = document.getElementById('lblPendingCount');
  if (lblPending) {
    lblPending.textContent = summary.pending_eligible ?? 0;
  }
  if (!host) return;
  const cards = [
    {label:'Linhas', value: summary.rows ?? 0, note:'candidatos subsea no período'},
    {label:'Elegíveis', value: summary.eligible ?? 0, note:'match único no catálogo'},
    {label:'Gerados (Concluídos)', value: summary.generated ?? 0, note:'arquivos XML 042 criados', color:'var(--green)'},
    {label:'Pendente Elegível', value: summary.pending_eligible ?? 0, note:'aguardando geração em lote', color:'var(--orange)'},
    {label:'Não Elegíveis', value: summary.not_eligible ?? 0, note:'sem cadastro ou dados ausentes'},
  ];
  host.innerHTML = cards.map(card => `
    <div class="upload-context-card">
      <div class="k">${card.label}</div>
      <div class="v" style="${card.color ? 'color:' + card.color : ''}">${card.value}</div>
      <div class="m">${card.note}</div>
    </div>
  `).join('');
}

function xml042RenderCandidates(rows = []) {
  const head = document.getElementById('xml042CandidatesHead');
  const body = document.getElementById('xml042CandidatesRows');
  if (!head || !body) return;
  head.innerHTML = `<tr>
    <th>Dia</th><th>Banco</th><th>Poço</th><th>TAG subsea</th><th>Óleo (sm³)</th><th>Gás (sm³)</th><th>Gás (mil sm³)</th><th>Água (sm³)</th><th>Catálogo</th><th>Aprov.</th><th>XML 042 (Arquivo)</th><th>Ações</th>
  </tr>`;
  body.innerHTML = rows.map((row, idx) => {
    const selected = state.xml042Selected && row.production_day === state.xml042Selected.production_day && row.bank === state.xml042Selected.bank && row.well_operator_name === state.xml042Selected.well_operator_name && row.subsea_tag === state.xml042Selected.subsea_tag;

    let xmlStatusBadge = '<span class="badge missing">⚪ Não Elegível</span>';
    if (row.generated) {
      xmlStatusBadge = `<span class="badge ok" title="${escapeHtml(row.generated_filename || '')}">🟢 Gerado</span> <span class="mono fs11" style="color:var(--green)">${escapeHtml(row.generated_filename || '')}</span>`;
    } else if (row.eligible) {
      xmlStatusBadge = '<span class="badge warn">🟡 Pendente</span>';
    }

    return `<tr class="${selected ? 'row-selected' : ''}">
      <td class="mono">${escapeHtml(fmtDate(row.production_day))}</td>
      <td>${tagChip(row.bank)}</td>
      <td class="mono">${escapeHtml(row.well_operator_name || '—')}</td>
      <td class="mono">${escapeHtml(row.subsea_tag || '—')}</td>
      <td class="num">${fmt(row.oil_sm3)}</td>
      <td class="num">${fmt(row.gas_sm3)}</td>
      <td class="num">${fmt(row.gas_1000sm3)}</td>
      <td class="num">${fmt(row.water_sm3)}</td>
      <td>${badge(row.catalog_match_status === 'elegivel' ? 'ok' : row.catalog_match_status === 'valor critico ausente' ? 'warn' : 'missing')} <span class="muted" style="font-size:11px">${escapeHtml(row.catalog_match_status)}</span></td>
      <td>${row.approved ? '<span class="badge ok">Aprovado</span>' : '<span class="badge warn">Pendente</span>'}</td>
      <td>${xmlStatusBadge}</td>
      <td>
        <div class="row" style="gap:6px;flex-wrap:wrap">
          <button class="btn secondary sm" onclick="selectXml042Candidate(${idx})">Ver</button>
          <button class="btn secondary sm" onclick="approveXml042Candidate(${idx})" ${row.eligible ? '' : 'disabled'}>Aprovar</button>
          <button class="btn primary sm" onclick="generateSingleXml042Candidate(${idx})" ${row.eligible ? '' : 'disabled'}>${row.generated ? 'Regerar' : 'Gerar XML'}</button>
          ${row.document_id ? `<a class="btn secondary sm" href="${API}/xml042/download/${escapeHtml(row.document_id)}" target="_blank" rel="noopener">Baixar</a>` : ''}
        </div>
      </td>
    </tr>`;
  }).join('') || '<tr><td colspan="12" style="text-align:center;color:var(--muted);padding:24px">Sem candidatos para os filtros.</td></tr>';
}

function xml042RenderPreview(candidate) {
  const meta = document.getElementById('xml042PreviewMeta');
  const preview = document.getElementById('xml042Preview');
  if (!meta || !preview) return;
  if (!candidate) {
    meta.textContent = 'Selecione uma linha elegível para visualizar o XML.';
    preview.textContent = '';
    return;
  }
  meta.textContent = `${fmtDate(candidate.production_day)} · ${candidate.bank} · ${candidate.well_operator_name} · ${candidate.subsea_tag}`;
  preview.textContent = candidate.preview_xml || 'Linha não elegível para prévia.';
}

function xml042RenderCatalog(rows = []) {
  const body = document.getElementById('xml042CatalogRows');
  if (!body) return;
  body.innerHTML = rows.map((row, idx) => `
    <tr>
      <td class="mono">${xml042Escape(row.well_operator_name)}</td>
      <td class="mono">${xml042Escape(row.well_anp_name)}</td>
      <td class="mono">${xml042Escape(row.cod_cadastro_poco)}</td>
      <td class="mono">${xml042Escape(row.subsea_tag)}</td>
      <td>${row.active && row.enabled_042 ? '<span class="badge ok">Ativo</span>' : '<span class="badge warn">Desabilitado</span>'}</td>
      <td>
        <div class="row" style="gap:6px;flex-wrap:wrap">
          <button class="btn secondary sm" onclick="editXml042Catalog(${idx})">Editar</button>
          <button class="btn danger sm" onclick="deleteXml042Catalog(${row.id})">Excluir</button>
        </div>
      </td>
    </tr>
  `).join('') || '<tr><td colspan="6" style="text-align:center;color:var(--muted);padding:20px">Sem catálogo cadastrado.</td></tr>';
}

function xml042RenderDocuments(rows = []) {
  const body = document.getElementById('xml042DocsRows');
  if (!body) return;
  body.innerHTML = rows.map(row => `
    <tr>
      <td class="mono">${fmtDate(row.production_day)}</td>
      <td>${tagChip(row.bank)}</td>
      <td class="mono">${xml042Escape(row.well_operator_name)}</td>
      <td class="mono">${xml042Escape(row.cod_cadastro_poco)}</td>
      <td class="mono">${xml042Escape(row.filename)}</td>
      <td class="mono">${xml042Escape((row.generated_at || '').replace('T',' ').slice(0,16))}</td>
      <td>
        <div class="row" style="gap:6px;flex-wrap:wrap">
          <button class="btn secondary sm" onclick="previewXml042Document(${row.id})">Visualizar</button>
          <a class="btn secondary sm" href="${API}/xml042/download/${row.id}" target="_blank" rel="noopener">Baixar</a>
        </div>
      </td>
    </tr>
  `).join('') || '<tr><td colspan="7" style="text-align:center;color:var(--muted);padding:20px">Nenhum XML gerado.</td></tr>';
}

function xml042RenderImportedSummary(summary = {}) {
  const host = document.getElementById('xml042ImportedSummary');
  if (!host) return;
  const cards = [
    {label:'Linhas', value: summary.rows ?? 0, note:'registros tabulares do mês'},
    {label:'Poços', value: summary.codes ?? 0, note:'códigos de poço distintos'},
    {label:'Arquivos', value: summary.files ?? 0, note:'XMLs armazenados na base'},
    {label:'Último dia', value: summary.latest_day ? fmtDate(summary.latest_day) : '—', note:'maior data importada'},
  ];
  host.innerHTML = cards.map(card => `
    <div class="upload-context-card">
      <div class="k">${card.label}</div>
      <div class="v">${card.value}</div>
      <div class="m">${card.note}</div>
    </div>
  `).join('');
}

function xml042RenderImportedRows(rows = []) {
  const head = document.getElementById('xml042ImportedHead');
  const body = document.getElementById('xml042ImportedRows');
  if (!head || !body) return;
  head.innerHTML = `<tr>
    <th>Mês</th><th>Dia</th><th>Cód. poço</th><th>Poço</th><th>TAG subsea</th><th>Banco</th><th>Óleo (sm³)</th><th>Gás (mil sm³)</th><th>Água (sm³)</th><th>Arquivo</th><th>Importado em</th>
  </tr>`;
  body.innerHTML = rows.map(row => `
    <tr>
      <td class="mono">${xml042Escape(row.month_ref || '—')}</td>
      <td class="mono">${fmtDate(row.production_day)}</td>
      <td class="mono">${xml042Escape(row.cod_cadastro_poco || '—')}</td>
      <td class="mono">${xml042Escape(row.well_operator_name || '—')}</td>
      <td class="mono">${xml042Escape(row.subsea_tag || '—')}</td>
      <td>${row.bank ? tagChip(row.bank) : '—'}</td>
      <td class="num">${fmt(row.oil_sm3)}</td>
      <td class="num">${fmt(row.gas_1000sm3)}</td>
      <td class="num">${fmt(row.water_sm3)}</td>
      <td class="mono">${xml042Escape(row.filename || '—')}</td>
      <td class="mono">${xml042Escape((row.imported_at || '').replace('T',' ').slice(0,16) || '—')}</td>
    </tr>
  `).join('') || '<tr><td colspan="11" style="text-align:center;color:var(--muted);padding:20px">Nenhum XML importado para os filtros.</td></tr>';
}

function xml042RenderImportSelection(files = []) {
  const host = document.getElementById('xml042ImportPicked');
  if (!host) return;
  if (!files.length) {
    host.textContent = 'Nenhum arquivo selecionado.';
    return;
  }
  const names = files.slice(0, 3).map(file => file.name);
  const extra = files.length > 3 ? ` +${files.length - 3}` : '';
  host.textContent = `${files.length} arquivo(s): ${names.join(', ')}${extra}`;
}

function xml042FillCatalogForm(row = null) {
  state.xml042CatalogEditingId = row?.id || null;
  document.getElementById('xml042CatalogOperator').value = row?.well_operator_name || '';
  document.getElementById('xml042CatalogAnp').value = row?.well_anp_name || '';
  document.getElementById('xml042CatalogCode').value = row?.cod_cadastro_poco || '';
  document.getElementById('xml042CatalogTag').value = row?.subsea_tag || '';
  document.getElementById('xml042CatalogCampoCode').value = row?.cod_campo || '4735';
  document.getElementById('xml042CatalogCampo').value = row?.campo || 'BACALHAU';
  document.getElementById('xml042CatalogInstCode').value = row?.cod_instalacao || '38480';
  document.getElementById('xml042CatalogInst').value = row?.instalacao || 'FPSO BACALHAU';
  document.getElementById('xml042CatalogEnabled').checked = !!(row ? row.enabled_042 : true);
  document.getElementById('xml042CatalogActive').checked = !!(row ? row.active : true);
  document.getElementById('xml042CatalogNotes').value = row?.notes || '';
  document.getElementById('xml042CatalogStatus').textContent = row ? `Editando ${row.well_operator_name}.` : 'Nenhuma edição pendente.';
}

async function loadXml042Catalog() {
  const d = await j(`${API}/xml042/catalog`);
  state.xml042Catalog = d.rows || [];
  xml042RenderCatalog(state.xml042Catalog);
}

async function loadXml042Documents() {
  const month = xml042CurrentMonth();
  const d = await j(`${API}/xml042/documents?month=${encodeURIComponent(month)}`);
  state.xml042Docs = d.rows || [];
  xml042RenderDocuments(state.xml042Docs);
}

async function loadXml042Imported() {
  const month = xml042CurrentMonth();
  const cod = document.getElementById('xml042ImportedCode')?.value || '';
  const qs = new URLSearchParams({month, cod_cadastro_poco: cod});
  const d = await j(`${API}/xml042/imported?${qs}`);
  state.xml042ImportedRows = d.rows || [];
  state.xml042ImportedFiles = d.files || [];
  xml042RenderImportedSummary(d.summary || {});
  xml042RenderImportedRows(state.xml042ImportedRows);
}

async function loadXml042Candidates() {
  const month = xml042CurrentMonth();
  const qs = new URLSearchParams({
    month,
    day: xml042SelectedDayValue(),
    bank: document.getElementById('xml042Bank').value || '',
    status: document.getElementById('xml042Status').value || '',
  });
  const d = await j(`${API}/xml042/candidates?${qs}`);
  state.xml042Rows = d.rows || [];
  fillSelect('xml042Bank', d.banks || [], true);
  fillSelect('xml042Status', d.statuses || [], true);
  xml042RenderSummary(d.summary || {});
  xml042RenderCandidates(state.xml042Rows);
  if (state.xml042Selected) {
    const selected = state.xml042Rows.find(row => row.production_day === state.xml042Selected.production_day && row.bank === state.xml042Selected.bank && row.well_operator_name === state.xml042Selected.well_operator_name && row.subsea_tag === state.xml042Selected.subsea_tag) || null;
    state.xml042Selected = selected;
  }
  xml042RenderPreview(state.xml042Selected);
  xml042StatusText(`${state.xml042Rows.length} candidato(s) carregado(s).`);
}

async function loadXml042Page() {
  const month = xml042CurrentMonth();
  const {from} = getMonthRange(month);
  const dayInput = document.getElementById('xml042Day');
  const cnpjInput = document.getElementById('xml042Cnpj8');
  if (dayInput && !dayInput.value) dayInput.value = from;
  if (cnpjInput && state.prefs && state.prefs.xml042_cnpj8) cnpjInput.value = state.prefs.xml042_cnpj8;
  if (typeof refreshDateInputDisplay === 'function') refreshDateInputDisplay(document);
  await loadXml042Catalog();
  await loadXml042Candidates();
  await loadXml042Documents();
  await loadXml042Imported();
}

window.selectXml042Candidate = function(index) {
  state.xml042Selected = state.xml042Rows[index] || null;
  xml042RenderCandidates(state.xml042Rows);
  xml042RenderPreview(state.xml042Selected);
};

window.approveXml042Candidate = async function(index) {
  const row = state.xml042Rows[index];
  if (!row) return;
  await j(`${API}/xml042/approve`, {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({
      month: xml042CurrentMonth(),
      production_day: row.production_day,
      bank: row.bank,
      well_operator_name: row.well_operator_name,
      subsea_tag: row.subsea_tag,
    }),
  });
  xml042StatusText(`Linha ${row.well_operator_name} aprovada.`);
  await loadXml042Candidates();
};

window.editXml042Catalog = function(index) {
  xml042FillCatalogForm(state.xml042Catalog[index] || null);
};

window.deleteXml042Catalog = async function(id) {
  if (!confirm('Excluir este item do catálogo 042?')) return;
  try {
    const res = await fetch(`${API}/xml042/catalog/${id}`, {method:'DELETE'});
    if (!res.ok) {
      const payload = await res.json().catch(() => ({}));
      throw new Error(payload.detail || payload.error || `Falha HTTP ${res.status}`);
    }
    await loadXml042Catalog();
    await loadXml042Candidates();
  } catch(err) {
    alert(`Erro ao excluir catálogo 042: ${err.message}`);
  }
};

document.getElementById('btnLoadXml042')?.addEventListener('click', loadXml042Candidates);
document.getElementById('btnXml042CatalogNew')?.addEventListener('click', () => xml042FillCatalogForm(null));
document.getElementById('btnResetXml042Catalog')?.addEventListener('click', () => xml042FillCatalogForm(null));
document.getElementById('btnSaveXml042Catalog')?.addEventListener('click', async () => {
  const body = {
    id: state.xml042CatalogEditingId,
    well_operator_name: document.getElementById('xml042CatalogOperator').value,
    well_anp_name: document.getElementById('xml042CatalogAnp').value,
    cod_cadastro_poco: document.getElementById('xml042CatalogCode').value,
    subsea_tag: document.getElementById('xml042CatalogTag').value,
    cod_campo: document.getElementById('xml042CatalogCampoCode').value,
    campo: document.getElementById('xml042CatalogCampo').value,
    cod_instalacao: document.getElementById('xml042CatalogInstCode').value,
    instalacao: document.getElementById('xml042CatalogInst').value,
    enabled_042: document.getElementById('xml042CatalogEnabled').checked,
    active: document.getElementById('xml042CatalogActive').checked,
    notes: document.getElementById('xml042CatalogNotes').value,
  };
  await j(`${API}/xml042/catalog`, {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify(body),
  });
  document.getElementById('xml042CatalogStatus').textContent = 'Catálogo salvo.';
  xml042FillCatalogForm(null);
  await loadXml042Catalog();
  await loadXml042Candidates();
});

window.generateSingleXml042Candidate = async function(index) {
  const row = state.xml042Rows[index];
  if (!row || !row.eligible) return;
  const cnpj8 = document.getElementById('xml042Cnpj8')?.value?.trim() || '04028583';
  const target_dir = document.getElementById('xml042TargetDir')?.value?.trim() || '';

  try {
    if (!row.approved) {
      await j(`${API}/xml042/approve`, {
        method: 'POST',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify({
          month: xml042CurrentMonth(),
          production_day: row.production_day,
          bank: row.bank,
          well_operator_name: row.well_operator_name,
          subsea_tag: row.subsea_tag,
        }),
      });
    }

    const d = await j(`${API}/xml042/generate`, {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({
        month: xml042CurrentMonth(),
        production_day: row.production_day,
        bank: row.bank,
        well_operator_name: row.well_operator_name,
        subsea_tag: row.subsea_tag,
        cnpj8,
        target_dir,
      }),
    });

    let msg = `XML gerado com sucesso: ${d.filename}`;
    if (d.saved_to_target_dir) {
      msg += ` (salvo em SGM 3.7)`;
    }
    xml042StatusText(msg);
    await loadXml042Candidates();
    await loadXml042Documents();
  } catch(err) {
    xml042StatusText(`Erro ao gerar XML: ${err.message}`, true);
  }
};

window.batchGenerateXml042 = async function() {
  const btn = document.getElementById('btnBatchGenerateXml042');
  const batchStatus = document.getElementById('xml042BatchStatus');
  const targetDir = document.getElementById('xml042TargetDir')?.value?.trim() || '';
  const cnpj8 = document.getElementById('xml042Cnpj8')?.value?.trim() || '04028583';
  const overwrite = !!document.getElementById('chkOverwriteXml042')?.checked;
  const month = xml042CurrentMonth();

  if (batchStatus) {
    batchStatus.textContent = '⏳ Aprovando, gerando e salvando arquivos XML 042 em lote... Aguarde.';
    batchStatus.style.color = '#1f4e78';
  }
  if (btn) btn.disabled = true;

  try {
    const payload = {
      month,
      cnpj8,
      target_dir: targetDir,
      only_pending: !overwrite,
      bank: document.getElementById('xml042Bank')?.value || '',
    };

    const res = await j(`${API}/xml042/batch-process`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(payload),
    });

    if (res.ok) {
      let statusMsg = `✅ Processamento concluído! ${res.success_count} arquivo(s) XML 042 gerado(s) e salvo(s) na pasta SGM 3.7.`;
      if (res.error_count > 0) {
        statusMsg += ` (${res.error_count} erro(s))`;
      }
      if (batchStatus) {
        batchStatus.textContent = statusMsg;
        batchStatus.style.color = res.error_count > 0 ? 'var(--orange)' : 'var(--green)';
      }
      xml042StatusText(statusMsg);
      await loadXml042Candidates();
      await loadXml042Documents();
    } else {
      throw new Error(res.detail || 'Falha no processamento em lote');
    }
  } catch(err) {
    if (batchStatus) {
      batchStatus.textContent = `❌ Erro na geração em lote: ${err.message}`;
      batchStatus.style.color = 'var(--red)';
    }
    xml042StatusText(`Erro na geração em lote: ${err.message}`, true);
  } finally {
    if (btn) btn.disabled = false;
  }
};

window.downloadZipXml042 = function() {
  const month = xml042CurrentMonth();
  window.open(`${API}/xml042/download-batch-zip?month=${encodeURIComponent(month)}`, '_blank');
};

window.previewXml042Document = async function(id) {
  const meta = document.getElementById('xml042PreviewMeta');
  const preview = document.getElementById('xml042Preview');
  if (!meta || !preview) return;
  try {
    meta.textContent = 'Carregando XML gerado...';
    preview.textContent = '';
    const d = await j(`${API}/xml042/preview-document/${encodeURIComponent(id)}`);
    meta.textContent = `${fmtDate(d.production_day)} · ${d.bank || '—'} · ${d.well_operator_name || '—'} · ${d.cod_cadastro_poco || '—'} · ${d.filename || ''}`;
    preview.textContent = d.xml || 'XML vazio.';
    xml042StatusText(`XML visualizado: ${d.filename || id}`);
  } catch(err) {
    meta.textContent = 'Falha ao carregar XML gerado.';
    preview.textContent = err.message || String(err);
    xml042StatusText(`Erro ao visualizar XML: ${err.message || err}`, true);
  }
};

document.getElementById('btnBatchGenerateXml042')?.addEventListener('click', window.batchGenerateXml042);
document.getElementById('btnDownloadZipXml042')?.addEventListener('click', window.downloadZipXml042);

document.getElementById('btnGenerateXml042')?.addEventListener('click', async () => {
  const row = state.xml042Selected;
  if (!row) {
    xml042StatusText('Selecione uma linha antes de gerar.', true);
    return;
  }
  const cnpj8 = document.getElementById('xml042Cnpj8').value.trim() || '04028583';
  const target_dir = document.getElementById('xml042TargetDir')?.value?.trim() || '';
  try {
    state.prefs = state.prefs || {};
    state.prefs.xml042_cnpj8 = cnpj8;
    await j(`${API}/user-prefs`, {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify(state.prefs),
    }).catch(() => null);

    if (!row.approved) {
      await j(`${API}/xml042/approve`, {
        method: 'POST',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify({
          month: xml042CurrentMonth(),
          production_day: row.production_day,
          bank: row.bank,
          well_operator_name: row.well_operator_name,
          subsea_tag: row.subsea_tag,
        }),
      });
    }

    const d = await j(`${API}/xml042/generate`, {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({
        month: xml042CurrentMonth(),
        production_day: row.production_day,
        bank: row.bank,
        well_operator_name: row.well_operator_name,
        subsea_tag: row.subsea_tag,
        cnpj8,
        target_dir,
      }),
    });
    let msg = `XML gerado: ${d.filename}`;
    if (d.saved_to_target_dir) {
      msg += ` (salvo em SGM 3.7)`;
    }
    xml042StatusText(msg);
    await loadXml042Candidates();
    await loadXml042Documents();
  } catch(err) {
    xml042StatusText(`Erro ao gerar XML: ${err.message || err}`, true);
  }
});

document.getElementById('btnSeedXml042Catalog')?.addEventListener('click', async () => {
  await loadXml042Catalog();
  await loadXml042Candidates();
  xml042StatusText('Catálogo recarregado da base local.');
});

document.getElementById('btnPickXml042Import')?.addEventListener('click', () => {
  document.getElementById('xml042ImportFiles')?.click();
});

document.getElementById('xml042ImportFiles')?.addEventListener('change', (event) => {
  const files = Array.from(event.target?.files || []);
  state.xml042ImportFiles = files;
  xml042RenderImportSelection(files);
});

document.getElementById('btnLoadXml042Imported')?.addEventListener('click', async () => {
  await loadXml042Imported();
  const code = document.getElementById('xml042ImportedCode')?.value || '';
  document.getElementById('xml042ImportStatus').textContent = code ? `Tabela atualizada para código ${code}.` : 'Tabela mensal atualizada.';
});

document.getElementById('btnImportXml042Files')?.addEventListener('click', async () => {
  const files = state.xml042ImportFiles || [];
  const status = document.getElementById('xml042ImportStatus');
  if (!files.length) {
    if (status) status.textContent = 'Selecione pelo menos um XML antes de importar.';
    return;
  }
  const button = document.getElementById('btnImportXml042Files');
  const original = button?.textContent || '';
  try {
    if (button) {
      button.disabled = true;
      button.textContent = 'Importando...';
    }
    const form = new FormData();
    files.forEach(file => form.append('files', file));
    const res = await fetch(`${API}/xml042/import`, {method:'POST', body: form});
    const payload = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(payload.detail || payload.error || `Falha HTTP ${res.status}`);
    }
    state.xml042ImportFiles = [];
    const picker = document.getElementById('xml042ImportFiles');
    if (picker) picker.value = '';
    xml042RenderImportSelection([]);
    await loadXml042Imported();
    const summary = payload.summary || {};
    const bits = [
      `${summary.imported || 0} importado(s)`,
      `${summary.duplicates || 0} duplicado(s)`,
      `${summary.errors || 0} erro(s)`,
    ];
    if (status) status.textContent = bits.join(' · ');
  } catch (err) {
    if (status) status.textContent = `Falha na importação: ${err.message || err}`;
  } finally {
    if (button) {
      button.disabled = false;
      button.textContent = original;
    }
  }
});

document.getElementById('btnExportXml042Imported')?.addEventListener('click', () => {
  const month = xml042CurrentMonth();
  const cod = document.getElementById('xml042ImportedCode')?.value || '';
  const qs = new URLSearchParams({month, cod_cadastro_poco: cod});
  window.open(`${API}/xml042/imported-export?${qs}`, '_blank', 'noopener');
});
