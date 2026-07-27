'use strict';

const painelOperadorState = {
  loaded: false,
  activeTab: 'overview',
  status: null,
  fileSummary: null,
  anpSummary: null,
  stagingSummary: null,
  productionSummary: null,
  xmlValidationSummary: null,
  checklistSummary: null,
  technicalSummary: null,
  dataSources: null,
  technicalChart: null,
  tankBalanceChart: null,
  offspecTankChart: null,
  qualityChart: null,
  mpfmFiscalOilChart: null,
  gasBalanceChart: null,
  radarChart: null,
  radarMeasurementChart: null,
  radarData: null,
  radarContract: null,
  radarSources: null,
  radarActiveView: 'medicao',
  checklistSection: 'overview',
  configuredLimits: [],
  dossiers: null,
  xmlValidationRows: [],
  flowTraceItems: [],
};

function poEl(id) {
  return document.getElementById(id);
}

function poText(value, fallback = '—') {
  if (value === null || value === undefined || value === '') return fallback;
  return String(value);
}

function poNum(value, digits = 0) {
  const num = Number(value || 0);
  return new Intl.NumberFormat('pt-BR', {maximumFractionDigits: digits}).format(num);
}

function poBytes(value) {
  const bytes = Number(value || 0);
  if (!bytes) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  let amount = bytes;
  let index = 0;
  while (amount >= 1024 && index < units.length - 1) {
    amount /= 1024;
    index += 1;
  }
  return `${new Intl.NumberFormat('pt-BR', {maximumFractionDigits: amount >= 100 ? 0 : 1}).format(amount)} ${units[index]}`;
}

function poSetStatus(message, kind = 'muted') {
  const host = poEl('poActionStatus');
  if (!host) return;
  host.className = `po-actionbar__status po-status--${kind}`;
  host.textContent = message;
}

function poBadge(text, kind = 'info') {
  return `<span class="badge ${kind}">${escapeHtml(text)}</span>`;
}

function poTag(text) {
  return text ? tagChip(text) : '<span class="muted">—</span>';
}

function poResizeChart(chart) {
  if (chart && typeof chart.resize === 'function') chart.resize();
  if (chart?.chart && typeof chart.chart.resize === 'function') chart.chart.resize();
}

function poSetActiveTab(tab) {
  painelOperadorState.activeTab = tab;
  document.querySelectorAll('[data-po-tab]').forEach((button) => {
    const active = button.dataset.poTab === tab;
    button.classList.toggle('active', active);
    button.setAttribute('aria-selected', String(active));
  });
  document.querySelectorAll('.po-panel').forEach((panel) => {
    panel.classList.toggle('active', panel.id === `poPanel${tab[0].toUpperCase()}${tab.slice(1)}`);
  });
  if (tab === 'radar') loadPainelOperadorRadar();
  if (tab === 'ingestion') loadPainelOperadorIngestion();
  if (tab === 'files') loadPainelOperadorFiles();
  if (tab === 'anp') loadPainelOperadorAnp();
  if (tab === 'xmlValidation') loadPainelOperadorXmlValidation();
  if (tab === 'measured') loadPainelOperadorMeasured();
  if (tab === 'checklist') loadPainelOperadorChecklist();
  if (tab === 'technical') loadPainelOperadorTechnical();
  if (tab === 'dossiers') loadPainelOperadorDossiers();
  if (tab === 'compare') loadPainelOperadorCompare();
  if (tab === 'calendar') loadPainelOperadorCalendar();
  if (tab === 'proposals') loadPainelOperadorProposals();
  if (tab === 'staging') loadPainelOperadorStaging();
  if (tab === 'ihm') loadPainelOperadorIhm();
}

function poSetChecklistSection(section) {
  painelOperadorState.checklistSection = section || 'overview';
  document.querySelectorAll('[data-po-checklist-section]').forEach((button) => {
    const active = button.dataset.poChecklistSection === painelOperadorState.checklistSection;
    button.classList.toggle('active', active);
    button.setAttribute('aria-selected', String(active));
  });
  document.querySelectorAll('[data-po-checklist-panel]').forEach((panel) => {
    panel.classList.toggle('active', panel.dataset.poChecklistPanel === painelOperadorState.checklistSection);
  });
  window.setTimeout(() => {
    poResizeChart(painelOperadorState.tankBalanceChart);
    poResizeChart(painelOperadorState.offspecTankChart);
    poResizeChart(painelOperadorState.qualityChart);
    poResizeChart(painelOperadorState.mpfmFiscalOilChart);
    poResizeChart(painelOperadorState.gasBalanceChart);
  }, 0);
}

async function loadPainelOperador(silent = false) {
  if (!silent) setLoading('page-painel-operador', true);
  try {
    // Carrega apenas endpoints leves no init. production-days, xml-validation e
    // technical-monitor são pesados (N+1 queries / JSON grande) e carregam sob demanda.
    const [status, fileSummary, anpSummary, stagingSummary, flowTrace, checklistSummary] = await Promise.all([
      j(`${API}/painel-operador/status`).catch((err) => ({ok: false, error: err.message || String(err)})),
      j(`${API}/painel-operador/file-index-summary`).catch((err) => ({error: err.message || String(err)})),
      j(`${API}/painel-operador/anp-exports-summary`).catch((err) => ({error: err.message || String(err)})),
      j(`${API}/painel-operador/staging-summary`).catch((err) => ({error: err.message || String(err)})),
      j(`${API}/methodology-flow/items?limit=120`).catch(() => ({items: []})),
      j(`${API}/painel-operador/daily-checklist-summary`).catch((err) => ({error: err.message || String(err), totals: {}, sheets: []})),
    ]);
    painelOperadorState.status = status;
    painelOperadorState.fileSummary = fileSummary;
    painelOperadorState.anpSummary = anpSummary;
    painelOperadorState.stagingSummary = stagingSummary;
    painelOperadorState.flowTraceItems = flowTrace.items || [];
    painelOperadorState.checklistSummary = checklistSummary;
    // Mantém valores anteriores se já carregados (e.g. silent refresh), senão usa defaults
    if (!painelOperadorState.productionSummary) painelOperadorState.productionSummary = {totals: {}, items: []};
    if (!painelOperadorState.xmlValidationSummary) painelOperadorState.xmlValidationSummary = {summary: {}, items: []};
    if (!painelOperadorState.technicalSummary) painelOperadorState.technicalSummary = {summary: {}, cv_diagnostics: {}};
    painelOperadorState.loaded = true;
    await renderPainelOperadorOverview();
    poFillSelectFromGroups('poFileCategory', (fileSummary.categories || []).map((row) => row.category));
    poFillSelectFromGroups('poFileKind', (fileSummary.categories || []).map((row) => row.document_kind));
    poFillSelectFromGroups('poAnpFamily', (anpSummary.groups || []).map((row) => row.family));
    poFillSelectFromGroups('poAnpKind', (anpSummary.groups || []).map((row) => row.record_kind));
    poFillSelectFromGroups('poXmlKind', (fileSummary.categories || []).filter((row) => String(row.document_kind || '').includes('xml')).map((row) => row.document_kind));
    poFillSelectFromGroups('poCompareFamily', (anpSummary.groups || []).map((row) => row.family));
    poFillSelectFromGroups('poCompareKind', (anpSummary.groups || []).map((row) => row.record_kind));
    poSetStatus(status.ok ? 'Módulo carregado e pronto para consulta.' : 'Módulo carregado com pendências de fonte.', status.ok ? 'ok' : 'warn');
  } finally {
    if (!silent) setLoading('page-painel-operador', false);
  }
}

async function renderPainelOperadorOverview() {
  const status = painelOperadorState.status || {};
  const fileSummary = painelOperadorState.fileSummary || {};
  const anpSummary = painelOperadorState.anpSummary || {};
  const stagingSummary = painelOperadorState.stagingSummary || {};
  const productionSummary = painelOperadorState.productionSummary || {};
  const xmlValidationSummary = painelOperadorState.xmlValidationSummary || {};
  const checklistSummary = painelOperadorState.checklistSummary || {};
  const technicalSummary = painelOperadorState.technicalSummary || {};
  const flowItems = painelOperadorState.flowTraceItems || [];
  const flowOpen = flowItems.filter((item) => !['resolvido', 'cancelado'].includes(String(item.status || 'aberto')));
  const flowCritical = flowOpen.filter((item) => ['pendencia', 'revisao'].includes(String(item.item_type || '')));
  const root = poText(status.module_root, 'não localizado');
  const health = status.ok ? 'Pronto' : 'Atenção';
  if (poEl('poModuleRoot')) poEl('poModuleRoot').textContent = root;
  if (poEl('poModuleHealth')) poEl('poModuleHealth').textContent = health;

  // Buscar dados do dashboard principal
  let dashboardData = null;
  let nfsmData = null;
  try {
    // Usar mês selecionado no globalMonth select, ou mês atual como fallback
    const monthSelect = document.querySelector('#globalMonth');
    const selectedMonth = monthSelect?.value || new Date().toISOString().substring(0, 7);
    const [dashRes, nfsmRes] = await Promise.all([
      fetch(`/api/painel-operador/dashboard-principal?month=${selectedMonth}`),
      fetch('/api/painel-operador/nfsm-abertas-excel')
    ]);
    dashboardData = dashRes.ok ? await dashRes.json() : null;
    nfsmData = nfsmRes.ok ? await nfsmRes.json() : null;
  } catch (err) {
    console.warn('Erro ao buscar dados do dashboard:', err);
  }

  const latestFile = fileSummary.latest_run || {};
  const latestAnp = anpSummary.latest_import || {};
  const latestSync = stagingSummary.latest_sync || {};
  const fileRows = Number(fileSummary.tables?.painel_operador_file_index || 0);
  const anpRows = Number(anpSummary.tables?.painel_operador_anp_export_rows || 0);
  const stagingTables = stagingSummary.tables || {};
  const stagingRows = Object.values(stagingTables).reduce((sum, value) => sum + Number(value || 0), 0);
  const productionTotals = productionSummary.totals || {};
  const xmlSummary = xmlValidationSummary.summary || {};
  const checklistTotals = checklistSummary.totals || {};
  const checklistSheets = checklistSummary.sheets || [];
  const technical = technicalSummary.summary || {};
  const cvDiagnostics = technicalSummary.cv_diagnostics || {};
  const officialXmlCount = poCategoryCount(fileSummary, ['anp_fiscal_xml', 'anp_failure_or_bsw_xml', 'anp_fiscal_archive']);
  const xmlFamilyText = poAnpXmlFamilyText(anpSummary.groups || []);
  const measuredMeta = [
    `${poNum(productionTotals.fiscal_volume_m3, 1)} m3 fiscal`,
    `${poNum(productionTotals.anp_volume_m3, 1)} m3 ANP`,
  ].join(' · ');

  // 1. BANNER DE ALERTAS (topo)
  const alertas = dashboardData?.alertas || [];
  const alertasHtml = alertas.length > 0 ? `
    <div class="po-alerts-banner">
      ${alertas.map(a => `
        <div class="po-alert po-alert--${a.tipo}">
          <strong>${escapeHtml(a.titulo)}</strong>
          <span>${escapeHtml(a.mensagem)}</span>
        </div>
      `).join('')}
    </div>
  ` : '';

  // 2. CARDS KPI (resumo operacional)
  const nfsmTotal = nfsmData?.total_abertas || 0;
  poEl('poSummaryGrid').innerHTML = `
    <div class="po-summary-card po-summary-card--primary"><span>NFSMs abertas</span><strong>${poNum(nfsmTotal)}</strong><small>Notificações pendentes de aprovação ANP</small></div>
    <div class="po-summary-card po-summary-card--primary"><span>Dias de produção</span><strong>${poNum(productionTotals.days)}</strong><small>${poNum(productionTotals.complete_days)} completos · ${poNum(productionTotals.attention_days)} em atenção</small></div>
    <div class="po-summary-card po-summary-card--primary"><span>XML/ANP oficiais</span><strong>${poNum(officialXmlCount || xmlSummary.cataloged_total)}</strong><small>${xmlFamilyText || `${poNum(xmlSummary.evaluated)} avaliados`}</small></div>
    <div class="po-summary-card po-summary-card--primary"><span>Dados medidos</span><strong>${poNum(productionTotals.mpfm_hc_t, 1)} t</strong><small>${measuredMeta}</small></div>
    <div class="po-summary-card po-summary-card--primary"><span>Pendências abertas</span><strong>${poNum(productionTotals.open_pending_count || flowOpen.length)}</strong><small>${poNum(flowCritical.length)} críticas/revisão no fluxo</small></div>
    <div class="po-summary-card po-summary-card--primary"><span>Checklist diário</span><strong>${poNum(checklistTotals.rows)}</strong><small>${poNum(checklistTotals.runs)} importações · ${poNum(checklistSheets.length)} abas</small></div>
  `;

  // 3. SUBSTITUIR MANUAL POR NOVO LAYOUT (alertas + gráfico + nfsm + tabelas)
  const manual = poEl('poOperatorManual');
  if (manual) {
    manual.innerHTML = `
      ${alertasHtml}
      <div style="display:grid; grid-template-columns: 2fr 1fr; gap:20px; margin-bottom:20px;">
        <div class="po-card">
          <h4 class="section-title">Produção do Mês Vigente</h4>
          <div id="poDashboardProductionChart" style="height:300px;"></div>
          <div id="poDashboardChartControls" style="margin-top:12px;"></div>
        </div>
        <div class="po-card">
          <h4 class="section-title">NFSMs Abertas (${poNum(nfsmTotal)})</h4>
          <div id="poDashboardNfsmList" style="max-height:360px; overflow-y:auto;"></div>
        </div>
      </div>
      <div class="po-card" style="margin-bottom:20px;">
        <h4 class="section-title">Comparação Fiscal x MPFM (Mês Vigente)</h4>
        <div id="poDashboardComparacaoTable"></div>
      </div>
      <div class="po-card" style="margin-bottom:20px;">
        <h4 class="section-title">Balanço de Gás Diário (Mês Vigente)</h4>
        <div id="poDashboardBalancoTable"></div>
      </div>
    `;
    
    // Renderizar componentes
    renderPoDashboardNfsmList(nfsmData);
    renderPoDashboardComparacaoTable(dashboardData);
    renderPoDashboardBalancoTable(dashboardData);
    renderPoDashboardProductionChart(dashboardData);
  }

  // 4. MANTER INVENTÁRIO TÉCNICO NO FINAL
  const inventory = poEl('poAuditInventory');
  if (inventory) inventory.innerHTML = `
    <div class="po-inventory-card"><span>Arquivos catalogados</span><strong>${poNum(fileRows)}</strong><small>${poBytes(latestFile.total_size_bytes)} em fontes locais</small></div>
    <div class="po-inventory-card"><span>Duplicados leves</span><strong>${poNum(latestFile.duplicate_files)}</strong><small>higiene de ingestão; não é KPI de medição</small></div>
    <div class="po-inventory-card"><span>Linhas de export ANP</span><strong>${poNum(anpRows)}</strong><small>${poNum(latestAnp.total_files)} arquivos; use família/período na apuração</small></div>
    <div class="po-inventory-card"><span>Dados processados</span><strong>${poNum(stagingRows)}</strong><small>${Object.keys(stagingTables).length || 0} conjuntos de dados</small></div>
  `;

  poEl('poFileRunMeta').textContent = latestFile.finished_at ? `run #${latestFile.id} · ${fmtDate(latestFile.finished_at)}` : 'sem varredura';
  poEl('poAnpRunMeta').textContent = latestAnp.finished_at ? `import #${latestAnp.id} · ${fmtDate(latestAnp.finished_at)}` : 'sem importação';
  poEl('poStagingRunMeta').textContent = latestSync.finished_at ? `sync #${latestSync.id} · ${fmtDate(latestSync.finished_at)}` : 'sem sincronização';

  poEl('poFileGroups').innerHTML = renderPoCompactRows(
    (fileSummary.categories || []).slice(0, 12),
    (row) => `<strong>${escapeHtml(row.category)}</strong><span>${escapeHtml(row.document_kind)} · ${poNum(row.count)} · ${poBytes(row.size_bytes)}</span>`
  );
  poEl('poAnpGroups').innerHTML = renderPoCompactRows(
    anpSummary.groups || [],
    (row) => `<strong>${escapeHtml(row.family)} · ${escapeHtml(row.record_kind)}</strong><span>${poNum(row.count)} linhas · ${poText(row.first_date)} a ${poText(row.last_date)} · ${poNum(row.tags_count)} tags</span>`
  );
  poEl('poStagingTables').innerHTML = Object.entries(stagingTables).map(([name, count]) => `
    <div class="po-stage-count"><span>${escapeHtml(name.replace('painel_operador_', ''))}</span><strong>${poNum(count)}</strong></div>
  `).join('') || '<div class="po-empty">Sincronize o contrato para processar os dados.</div>';

  const traceMeta = poEl('poFlowTraceMeta');
  if (traceMeta) traceMeta.textContent = `${poNum(flowOpen.length)} aberto(s) · ${poNum(flowItems.length)} total`;
  const traceList = poEl('poFlowTraceList');
  if (traceList) {
    traceList.innerHTML = flowOpen.slice(0, 8).map((item) => {
      const payload = poParseJson(item.payload_json, item.payload || {});
      const step = payload.step_id || payload.methodology_flow_context?.active_step || item.item_key || '';
      const hour = payload.hour ?? payload.methodology_flow_context?.active_hour;
      const suffix = [item.item_type || 'registro', item.status || 'aberto', step ? `etapa ${step}` : '', hour !== undefined && hour !== null && hour !== '' ? `${String(hour).padStart(2, '0')}:00` : ''].filter(Boolean).join(' · ');
      return `<div class="po-compact-row"><strong>${escapeHtml(item.title || 'Registro da trilha')}</strong><span>${escapeHtml(suffix)} · run #${escapeHtml(item.run_id || '-')}</span></div>`;
    }).join('') || '<div class="po-empty">Sem fila rastreável aberta.</div>';
  }
}

function poCategoryCount(fileSummary, documentKinds) {
  const wanted = new Set(documentKinds || []);
  return (fileSummary.categories || []).reduce((sum, row) => wanted.has(row.document_kind) ? sum + Number(row.count || 0) : sum, 0);
}

function poAnpXmlFamilyText(groups) {
  const labels = {
    a001: '001 óleo',
    a002: '002 gás',
    a003: '003 gás dif.',
    a039: '039 falhas',
    a040: '040 BSW',
  };
  const parts = (groups || []).slice(0, 5).map((row) => `${labels[row.family] || row.family}: ${poNum(row.count)}`);
  return parts.join(' · ');
}

function renderPoOperatorManual() {
  return `
    <div class="po-manual-head">
      <div>
        <h3 class="section-title modal-h3">Manual de preenchimento operacional</h3>
        <p class="muted fs12 mt6">Regra da tela: o topo mostra o que ajuda a fechar, comparar ou auditar a medição. Contagem bruta de arquivos fica como saúde da integração.</p>
      </div>
      <span class="po-manual-pill">Painel Operador</span>
    </div>
    <div class="po-manual-grid">
      <div class="po-manual-step"><b>1</b><strong>Período e fonte</strong><span>Escolha mês/dia de produção e confirme se XML 001/002/003/039/040, checklist e MPFM existem para o mesmo recorte.</span></div>
      <div class="po-manual-step"><b>2</b><strong>Dados medidos</strong><span>Use Dados Medidos e Comparação para ver fiscal x ANP x MPFM por tag/família, com volume, HC, BSW, falhas e lacunas.</span></div>
      <div class="po-manual-step"><b>3</b><strong>Checklist Diário</strong><span>Importe o xlsm apenas quando a aplicação ainda não tiver o dado por XML/MPFM. As abas viram tabelas, gráficos e resumo diário.</span></div>
      <div class="po-manual-step"><b>4</b><strong>Limites, PAM e CV</strong><span>Parametrize faixa calibrada/PAM por tag e revise snapshots de CV para mudanças entre dias, alarmes e operação fora da faixa.</span></div>
      <div class="po-manual-step"><b>5</b><strong>Ação rastreável</strong><span>Achado operacional deve virar proposta, pendência, revisão de limite/CV ou nota técnica de fechamento diário.</span></div>
    </div>
    <div class="po-manual-note"><strong>O que não deve comandar a decisão:</strong> arquivos catalogados, duplicados leves e dados processados indicam saúde da integração. Eles só importam quando explicam ausência, duplicidade ou risco de usar fonte errada.</div>
  `;
}

function renderPoDashboardNfsmList(nfsmData) {
  const container = poEl('poDashboardNfsmList');
  if (!container) return;
  
  if (!nfsmData || !nfsmData.abertas || nfsmData.abertas.length === 0) {
    container.innerHTML = '<div class="po-empty">Nenhuma NFSM aberta no momento.</div>';
    return;
  }

  const items = nfsmData.abertas.slice(0, 20); // Limitar a 20 mais recentes
  container.innerHTML = items.map(item => {
    const dias = Number(item.dias_abertos || 0);
    const badge = dias > 30 ? '<span class="badge badge--error">Crítico</span>' : 
                  dias > 15 ? '<span class="badge badge--warn">Atenção</span>' : '';
    return `
      <div class="po-nfsm-item">
        <div class="po-nfsm-header">
          <strong>${escapeHtml(item.codigo_falha)}</strong>
          ${badge}
        </div>
        <div class="po-nfsm-meta">
          <span>Tag: ${escapeHtml(item.tag || '-')}</span>
          <span>${escapeHtml(item.tipo_falha || 'Tipo não especificado')}</span>
          <span>${dias} dia${dias !== 1 ? 's' : ''} aberto${dias !== 1 ? 's' : ''}</span>
        </div>
        <div class="po-nfsm-date">${escapeHtml(item.data_ocorrencia || '-')}</div>
      </div>
    `;
  }).join('');
}

function renderPoDashboardComparacaoTable(dashboardData) {
  const container = poEl('poDashboardComparacaoTable');
  if (!container) return;

  if (!dashboardData || !dashboardData.comparacoes || dashboardData.comparacoes.total === 0) {
    container.innerHTML = '<div class="po-empty">Sem dados de comparação para o mês vigente.</div>';
    return;
  }

  const items = dashboardData.comparacoes.items || [];
  if (items.length === 0) {
    container.innerHTML = '<div class="po-empty">Sem registros de comparação disponíveis.</div>';
    return;
  }

  // Calcular totais
  const totalFiscal = items.reduce((sum, item) => sum + (Number(item.fiscal) || 0), 0);
  const totalMpfm = items.reduce((sum, item) => sum + (Number(item.mpfm) || 0), 0);
  const totalDeltaPct = totalFiscal > 0 ? ((totalMpfm - totalFiscal) / totalFiscal * 100) : 0;

  container.innerHTML = `
    <div class="table-wrapper" style="overflow-x:auto; width:100%; margin:0;">
      <table class="data-table" style="width:100%; min-width:600px; border-collapse:collapse;">
        <thead>
          <tr>
            <th style="padding:10px 12px; text-align:left; border-bottom:2px solid var(--line); font-weight:600; font-size:12px; color:var(--muted);">Data</th>
            <th class="text-right" style="padding:10px 12px; text-align:right; border-bottom:2px solid var(--line); font-weight:600; font-size:12px; color:var(--muted);">Fiscal (m³)</th>
            <th class="text-right" style="padding:10px 12px; text-align:right; border-bottom:2px solid var(--line); font-weight:600; font-size:12px; color:var(--muted);">MPFM (m³)</th>
            <th class="text-right" style="padding:10px 12px; text-align:right; border-bottom:2px solid var(--line); font-weight:600; font-size:12px; color:var(--muted);">Delta (m³)</th>
            <th class="text-right" style="padding:10px 12px; text-align:right; border-bottom:2px solid var(--line); font-weight:600; font-size:12px; color:var(--muted);">Delta (%)</th>
          </tr>
        </thead>
        <tbody>
          ${items.map(item => {
            const delta = Number(item.delta_pct || 0);
            const deltaClass = Math.abs(delta) > 5 ? 'text-error' : (Math.abs(delta) > 2 ? 'text-warn' : '');
            return `
              <tr style="border-bottom:1px solid rgba(255,255,255,.04);">
                <td style="padding:8px 12px; font-size:12px; color:var(--text);">${escapeHtml(item.data || '-')}</td>
                <td class="text-right" style="padding:8px 12px; text-align:right; font-size:12px; color:var(--text);">${poNum(item.fiscal, 2)}</td>
                <td class="text-right" style="padding:8px 12px; text-align:right; font-size:12px; color:var(--text);">${poNum(item.mpfm, 2)}</td>
                <td class="text-right" style="padding:8px 12px; text-align:right; font-size:12px; color:var(--text);">${poNum(item.delta_m3, 2)}</td>
                <td class="text-right ${deltaClass}" style="padding:8px 12px; text-align:right; font-size:12px;"><strong>${poNum(delta, 2)}%</strong></td>
              </tr>
            `;
          }).join('')}
        </tbody>
        <tfoot>
          <tr class="table-footer-total" style="border-top:2px solid var(--line); background:rgba(38,160,255,.08);">
            <td style="padding:10px 12px; font-size:12px;"><strong>TOTAL</strong></td>
            <td class="text-right" style="padding:10px 12px; text-align:right; font-size:12px;"><strong>${poNum(totalFiscal, 2)}</strong></td>
            <td class="text-right" style="padding:10px 12px; text-align:right; font-size:12px;"><strong>${poNum(totalMpfm, 2)}</strong></td>
            <td class="text-right" style="padding:10px 12px; text-align:right; font-size:12px;"><strong>${poNum(totalMpfm - totalFiscal, 2)}</strong></td>
            <td class="text-right" style="padding:10px 12px; text-align:right; font-size:12px;"><strong>${poNum(totalDeltaPct, 2)}%</strong></td>
          </tr>
        </tfoot>
      </table>
    </div>
    <div class="po-table-footer" style="padding:10px 0; font-size:11px; color:var(--muted);">
      <span>${items.length} dia${items.length !== 1 ? 's' : ''} no mês vigente • Comparação: Total FPSO (Subsea MPFM x Fiscal Óleo)</span>
    </div>
  `;
}

function renderPoDashboardBalancoTable(dashboardData) {
  const container = poEl('poDashboardBalancoTable');
  if (!container) return;

  if (!dashboardData || !dashboardData.gas_balance || dashboardData.gas_balance.total === 0) {
    container.innerHTML = '<div class="po-empty">Sem dados de balanço de gás para o mês vigente.</div>';
    return;
  }

  const items = dashboardData.gas_balance.items || [];
  if (items.length === 0) {
    container.innerHTML = '<div class="po-empty">Sem registros de balanço disponíveis.</div>';
    return;
  }

  // Calcular totais
  let totalEntrada = 0, totalSaida = 0, totalConsumo = 0, totalFlare = 0, totalBalanco = 0;
  items.forEach(item => {
    totalEntrada += Number(item.entrada || 0);
    totalSaida += Number(item.saida || 0);
    totalConsumo += Number(item.consumo || 0);
    totalFlare += Number(item.flare || 0);
    totalBalanco += Number(item.balanco || 0);
  });
  const desvioTotal = totalEntrada !== 0 ? (totalBalanco / totalEntrada) * 100 : 0;

  container.innerHTML = `
    <div class="table-wrapper" style="overflow-x:auto; width:100%; margin:0;">
      <table class="data-table" style="width:100%; min-width:750px; border-collapse:collapse;">
        <thead>
          <tr>
            <th style="padding:10px 12px; text-align:left; border-bottom:2px solid var(--line); font-weight:600; font-size:12px; color:var(--muted);">Data</th>
            <th class="text-right" style="padding:10px 12px; text-align:right; border-bottom:2px solid var(--line); font-weight:600; font-size:12px; color:var(--muted);">Entrada (m³)</th>
            <th class="text-right" style="padding:10px 12px; text-align:right; border-bottom:2px solid var(--line); font-weight:600; font-size:12px; color:var(--muted);">Saída (m³)</th>
            <th class="text-right" style="padding:10px 12px; text-align:right; border-bottom:2px solid var(--line); font-weight:600; font-size:12px; color:var(--muted);">Consumo (m³)</th>
            <th class="text-right" style="padding:10px 12px; text-align:right; border-bottom:2px solid var(--line); font-weight:600; font-size:12px; color:var(--muted);">Flare (m³)</th>
            <th class="text-right" style="padding:10px 12px; text-align:right; border-bottom:2px solid var(--line); font-weight:600; font-size:12px; color:var(--muted);">Balanço (m³)</th>
            <th class="text-right" style="padding:10px 12px; text-align:right; border-bottom:2px solid var(--line); font-weight:600; font-size:12px; color:var(--muted);">Desvio (%)</th>
          </tr>
        </thead>
        <tbody>
          ${items.map(item => {
            const desvio = Number(item.desvio_pct || 0);
            const desvioClass = Math.abs(desvio) > 3 ? 'text-warn' : '';
            return `
              <tr style="border-bottom:1px solid rgba(255,255,255,.04);">
                <td style="padding:8px 12px; font-size:12px; color:var(--text);">${escapeHtml(item.data || '-')}</td>
                <td class="text-right" style="padding:8px 12px; text-align:right; font-size:12px; color:var(--text);">${poNum(item.entrada, 0)}</td>
                <td class="text-right" style="padding:8px 12px; text-align:right; font-size:12px; color:var(--text);">${poNum(item.saida, 0)}</td>
                <td class="text-right" style="padding:8px 12px; text-align:right; font-size:12px; color:var(--text);">${poNum(item.consumo, 0)}</td>
                <td class="text-right" style="padding:8px 12px; text-align:right; font-size:12px; color:var(--text);">${poNum(item.flare, 0)}</td>
                <td class="text-right" style="padding:8px 12px; text-align:right; font-size:12px; color:var(--text);">${poNum(item.balanco, 0)}</td>
                <td class="text-right ${desvioClass}" style="padding:8px 12px; text-align:right; font-size:12px;">${poNum(desvio, 2)}%</td>
              </tr>
            `;
          }).join('')}
        </tbody>
        <tfoot>
          <tr class="table-footer-total" style="border-top:2px solid var(--line); background:rgba(38,160,255,.08);">
            <td style="padding:10px 12px; font-size:12px;"><strong>TOTAL</strong></td>
            <td class="text-right" style="padding:10px 12px; text-align:right; font-size:12px;"><strong>${poNum(totalEntrada, 0)}</strong></td>
            <td class="text-right" style="padding:10px 12px; text-align:right; font-size:12px;"><strong>${poNum(totalSaida, 0)}</strong></td>
            <td class="text-right" style="padding:10px 12px; text-align:right; font-size:12px;"><strong>${poNum(totalConsumo, 0)}</strong></td>
            <td class="text-right" style="padding:10px 12px; text-align:right; font-size:12px;"><strong>${poNum(totalFlare, 0)}</strong></td>
            <td class="text-right" style="padding:10px 12px; text-align:right; font-size:12px;"><strong>${poNum(totalBalanco, 0)}</strong></td>
            <td class="text-right" style="padding:10px 12px; text-align:right; font-size:12px;"><strong>${poNum(desvioTotal, 2)}%</strong></td>
          </tr>
        </tfoot>
      </table>
    </div>
  `;
}

function renderPoDashboardProductionChart(dashboardData) {
  const container = poEl('poDashboardProductionChart');
  const controls = poEl('poDashboardChartControls');
  if (!container) return;

  if (!dashboardData || !dashboardData.comparacoes || dashboardData.comparacoes.items.length === 0) {
    container.innerHTML = '<div class="po-empty" style="padding:80px 20px;">Sem dados de produção para o mês vigente.</div>';
    if (controls) controls.innerHTML = '';
    return;
  }

  // Preparar dados para o gráfico
  const items = dashboardData.comparacoes.items || [];
  const dates = [...new Set(items.map(i => i.data))].sort();

  // Agrupar dados por data
  const dataByDate = {};
  items.forEach(item => {
    if (!dataByDate[item.data]) dataByDate[item.data] = { fiscal: 0, mpfm: 0, desvio: 0 };
    dataByDate[item.data].fiscal += Number(item.fiscal || 0);
    dataByDate[item.data].mpfm += Number(item.mpfm || 0);
    // Calcular desvio percentual por data
    if (dataByDate[item.data].fiscal > 0) {
      dataByDate[item.data].desvio = ((dataByDate[item.data].mpfm - dataByDate[item.data].fiscal) / dataByDate[item.data].fiscal) * 100;
    }
  });

  const fiscalData = dates.map(d => dataByDate[d]?.fiscal || 0);
  const mpfmData = dates.map(d => dataByDate[d]?.mpfm || 0);
  const desvioData = dates.map(d => dataByDate[d]?.desvio || 0);

  // Controles de variáveis
  if (controls) {
    controls.innerHTML = `
      <div style="display:flex; gap:15px; align-items:center; padding:8px 0; flex-wrap:wrap;">
        <label style="display:flex; align-items:center; gap:6px; cursor:pointer; user-select:none;">
          <input type="checkbox" id="poChartShowFiscal" checked style="accent-color:#0066cc;">
          <span style="color:#0066cc; font-weight:500; font-size:13px;">Fiscal</span>
        </label>
        <label style="display:flex; align-items:center; gap:6px; cursor:pointer; user-select:none;">
          <input type="checkbox" id="poChartShowMpfm" checked style="accent-color:#00aa66;">
          <span style="color:#00aa66; font-weight:500; font-size:13px;">MPFM</span>
        </label>
        <label style="display:flex; align-items:center; gap:6px; cursor:pointer; user-select:none;">
          <input type="checkbox" id="poChartShowDesvio" style="accent-color:#ff6b6b;">
          <span style="color:#ff6b6b; font-weight:500; font-size:13px;">Desvio (%)</span>
        </label>
        <label style="display:flex; align-items:center; gap:6px; cursor:pointer; user-select:none; margin-left:20px;">
          <input type="checkbox" id="poChartShowLimits" style="accent-color:#a855f7;">
          <span style="color:#a855f7; font-weight:500; font-size:13px;">Limites PAM (±10%)</span>
        </label>
        <button onclick="poUpdateProductionChart()" style="padding:6px 14px; background:#26a0ff; color:white; border:none; border-radius:4px; cursor:pointer; font-size:12px; font-weight:500;">Atualizar Gráfico</button>
        <button onclick="poReimportChecklist()" style="padding:6px 14px; background:#00aa66; color:white; border:none; border-radius:4px; cursor:pointer; font-size:12px; font-weight:500;">↻ Reimportar Checklist</button>
      </div>
    `;
  }

  // Renderizar placeholder inicial
  container.innerHTML = '<canvas id="poDashboardChart"></canvas>';

  // Armazenar dados no estado global para reutilização
  if (!painelOperadorState.chartData) painelOperadorState.chartData = {};
  painelOperadorState.chartData.dates = dates;
  painelOperadorState.chartData.fiscalData = fiscalData;
  painelOperadorState.chartData.mpfmData = mpfmData;
  painelOperadorState.chartData.desvioData = desvioData;

  // Criar gráfico inicial
  setTimeout(() => poUpdateProductionChart(), 100);
}

// Nova função para atualizar o gráfico baseado nos controles
window.poUpdateProductionChart = function() {
  const canvas = document.getElementById('poDashboardChart');
  if (!canvas || !painelOperadorState.chartData) return;

  const { dates, fiscalData, mpfmData, desvioData } = painelOperadorState.chartData;

  const showFiscal = document.getElementById('poChartShowFiscal')?.checked ?? true;
  const showMpfm = document.getElementById('poChartShowMpfm')?.checked ?? true;
  const showDesvio = document.getElementById('poChartShowDesvio')?.checked ?? false;
  const showLimits = document.getElementById('poChartShowLimits')?.checked ?? false;

  // Destruir gráfico anterior se existir
  if (painelOperadorState.productionChart) {
    painelOperadorState.productionChart.destroy();
  }

  const datasets = [];

  if (showFiscal) {
    datasets.push({
      label: 'Fiscal',
      data: fiscalData,
      borderColor: '#0066cc',
      backgroundColor: 'rgba(0, 102, 204, 0.1)',
      tension: 0.3,
      pointRadius: 3,
      pointHoverRadius: 5,
      yAxisID: 'y'
    });
  }

  if (showMpfm) {
    datasets.push({
      label: 'MPFM',
      data: mpfmData,
      borderColor: '#00aa66',
      backgroundColor: 'rgba(0, 170, 102, 0.1)',
      tension: 0.3,
      pointRadius: 3,
      pointHoverRadius: 5,
      yAxisID: 'y'
    });
  }

  if (showDesvio) {
    datasets.push({
      label: 'Desvio (%)',
      data: desvioData,
      borderColor: '#ff6b6b',
      backgroundColor: 'rgba(255, 107, 107, 0.1)',
      tension: 0.3,
      pointRadius: 2,
      pointHoverRadius: 4,
      yAxisID: 'yRight'
    });
  }

  // Adicionar limites PAM (±10% sobre valor de referência médio)
  if (showLimits && showMpfm) {
    const avgMpfm = mpfmData.reduce((a, b) => a + b, 0) / mpfmData.length;
    const upperLimit = mpfmData.map(() => avgMpfm * 1.10);
    const lowerLimit = mpfmData.map(() => avgMpfm * 0.90);

    datasets.push({
      label: '__limit_upper',
      data: upperLimit,
      borderColor: '#a855f7',
      backgroundColor: 'transparent',
      borderDash: [5, 5],
      borderWidth: 1.5,
      pointRadius: 0,
      tension: 0,
      yAxisID: 'y'
    });

    datasets.push({
      label: '__limit_lower',
      data: lowerLimit,
      borderColor: '#a855f7',
      backgroundColor: 'transparent',
      borderDash: [5, 5],
      borderWidth: 1.5,
      pointRadius: 0,
      tension: 0,
      yAxisID: 'y'
    });
  }

  painelOperadorState.productionChart = new Chart(canvas, {
    type: 'line',
    data: {
      labels: dates.map(d => d.substring(5)),
      datasets
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: {
        mode: 'index',
        intersect: false
      },
      plugins: {
        legend: {
          position: 'top',
          labels: {
            boxWidth: 12,
            padding: 10,
            filter: (item) => !item.text.startsWith('__limit')
          }
        },
        tooltip: {
          callbacks: {
            label: (ctx) => {
              if (ctx.dataset.label.startsWith('__limit')) return null;
              return `${ctx.dataset.label}: ${poNum(ctx.parsed.y, 2)}`;
            }
          }
        }
      },
      scales: {
        y: {
          beginAtZero: true,
          position: 'left',
          ticks: {
            callback: (value) => poNum(value, 0)
          }
        },
        yRight: {
          beginAtZero: false,
          position: 'right',
          ticks: {
            callback: (value) => `${poNum(value, 1)}%`
          },
          grid: {
            drawOnChartArea: false
          }
        }
      }
    }
  });
};

// Nova função para reimportar checklist e atualizar dados
window.poReimportChecklist = async function() {
  const btn = event?.target;
  if (btn) {
    btn.disabled = true;
    btn.textContent = '⏳ Importando...';
    btn.style.opacity = '0.6';
  }

  try {
    // Buscar arquivos de checklist disponíveis
    const checklistPath = 'Painel_Operador/Bacalhau - Checklist Diario_julho_26.xlsm';

    // Chamar endpoint de importação
    const response = await fetch(`${API}/painel-operador/daily-checklist/import`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        path: checklistPath,
        force_refresh: true
      })
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${await response.text()}`);
    }

    const result = await response.json();
    const rowsImported = result.imported_rows || result.rows_imported || 0;
    const sheetsCount = (result.sheets || []).length;

    // Mostrar feedback de sucesso
    if (btn) {
      btn.style.background = '#00aa66';
      btn.textContent = `✓ ${rowsImported} linhas importadas`;
      setTimeout(() => {
        btn.disabled = false;
        btn.textContent = '↻ Reimportar Checklist';
        btn.style.opacity = '1';
        btn.style.background = '#00aa66';
      }, 3000);
    }

    // Recarregar a página do Painel Operador para mostrar dados atualizados
    setTimeout(() => {
      loadPainelOperadorPage();
    }, 1000);

  } catch (error) {
    console.error('Erro ao reimportar checklist:', error);
    if (btn) {
      btn.style.background = '#ff6b6b';
      btn.textContent = '✗ Erro na importação';
      setTimeout(() => {
        btn.disabled = false;
        btn.textContent = '↻ Reimportar Checklist';
        btn.style.opacity = '1';
        btn.style.background = '#00aa66';
      }, 3000);
    }
    alert(`Erro ao reimportar checklist:\n${error.message}\n\nVerifique se o arquivo existe e o servidor está rodando.`);
  }
};

function poParseJson(value, fallback = {}) {
  if (!value) return fallback;
  if (typeof value === 'object') return value;
  try { return JSON.parse(value); } catch (_) { return fallback; }
}

function renderPoCompactRows(rows, renderer) {
  if (!rows.length) return '<div class="po-empty">Sem dados disponíveis.</div>';
  return rows.map((row) => `<div class="po-compact-row">${renderer(row)}</div>`).join('');
}

function poFillSelectFromGroups(id, values) {
  const select = poEl(id);
  if (!select) return;
  const current = select.value;
  const unique = [...new Set((values || []).filter(Boolean))].sort((a, b) => String(a).localeCompare(String(b), 'pt-BR'));
  select.innerHTML = '<option value="">Todos</option>' + unique.map((value) => `<option value="${escapeHtml(value)}">${escapeHtml(value)}</option>`).join('');
  if (unique.includes(current)) select.value = current;
}

function poSetFormValue(id, value) {
  const el = poEl(id);
  if (!el) return;
  const text = value === null || value === undefined ? '' : String(value);
  if (el.tagName === 'SELECT' && text && !Array.from(el.options).some((option) => option.value === text)) {
    const option = document.createElement('option');
    option.value = text;
    option.textContent = text;
    el.appendChild(option);
  }
  el.value = text;
}

function poQuery(params) {
  const qs = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') qs.set(key, value);
  });
  return qs.toString();
}

async function poRunAction(label, action) {
  poSetStatus(`${label} em andamento...`, 'warn');
  setLoading('page-painel-operador', true);
  try {
    const result = await action();
    poSetStatus(`${label} concluído.`, 'ok');
    await loadPainelOperador(true);
    return result;
  } catch (err) {
    poSetStatus(`${label} falhou: ${err.message || err}`, 'err');
    throw err;
  } finally {
    setLoading('page-painel-operador', false);
  }
}

function poSourceStatusLabel(status) {
  const labels = {
    ok: 'Válida',
    empty: 'Sem arquivos',
    not_found: 'Não encontrada',
    missing_path: 'Sem caminho',
  };
  return labels[status] || poText(status);
}

function poSourceStatusKind(status) {
  if (status === 'ok') return 'ok';
  if (status === 'empty') return 'warn';
  return 'err';
}

function poExtensionsText(extensions) {
  const entries = Object.entries(extensions || {}).slice(0, 5);
  return entries.length ? entries.map(([ext, count]) => `${ext} ${poNum(count)}`).join(' · ') : '—';
}

function poGetSourceInput(sourceId, field) {
  return document.querySelector(`[data-po-source-id="${CSS.escape(sourceId)}"][data-po-source-field="${field}"]`);
}

async function loadPainelOperadorIngestion(validate = true) {
  const data = await j(`${API}/painel-operador/data-sources?validate=${validate ? 'true' : 'false'}`);
  painelOperadorState.dataSources = data;
  const sources = data.sources || [];
  const validations = sources.map((source) => source.validation || {});
  const okCount = validations.filter((item) => item.status === 'ok').length;
  const missingCount = validations.filter((item) => ['not_found', 'missing_path'].includes(item.status)).length;
  const uniquePaths = new Map();
  validations.forEach((validation) => {
    (validation.paths || []).forEach((item) => {
      if (item.path && !uniquePaths.has(item.path)) uniquePaths.set(item.path, item);
    });
  });
  const totalFiles = [...uniquePaths.values()].reduce((sum, item) => sum + Number(item.file_count || 0), 0);
  const totalSize = [...uniquePaths.values()].reduce((sum, item) => sum + Number(item.total_size_bytes || 0), 0);
  poEl('poIngestionSummary').innerHTML = `
    <div class="po-stage-count"><span>Fontes</span><strong>${poNum(sources.length)}</strong></div>
    <div class="po-stage-count"><span>Válidas</span><strong>${poNum(okCount)}</strong></div>
    <div class="po-stage-count"><span>Sem caminho</span><strong>${poNum(missingCount)}</strong></div>
    <div class="po-stage-count"><span>Arquivos únicos</span><strong>${poNum(totalFiles)}</strong></div>
  `;
  poEl('poIngestionMeta').textContent = `${sources.length} fonte(s) configuradas · ${poNum(uniquePaths.size)} caminho(s) único(s) · ${poBytes(totalSize)} visíveis nos caminhos atuais.`;
  poEl('poIngestionRows').innerHTML = sources.map((source) => {
    const validation = source.validation || {};
    return `
      <tr>
        <td class="po-path-cell" title="${escapeHtml(source.description || '')}">
          <strong>${escapeHtml(source.label || source.id)}</strong><br><span class="muted">${escapeHtml(source.id)}</span>
        </td>
        <td><textarea class="input po-source-paths" data-po-source-id="${escapeHtml(source.id)}" data-po-source-field="paths" rows="2">${escapeHtml((source.paths || []).join('\n'))}</textarea></td>
        <td><input type="checkbox" data-po-source-id="${escapeHtml(source.id)}" data-po-source-field="recursive" ${source.recursive ? 'checked' : ''}></td>
        <td>${validation.status ? poBadge(poSourceStatusLabel(validation.status), poSourceStatusKind(validation.status)) : poBadge('Não validada', 'info')}</td>
        <td class="num">${poNum(validation.file_count)}</td>
        <td class="po-path-cell" title="${escapeHtml(poExtensionsText(validation.extensions))}">${escapeHtml(poExtensionsText(validation.extensions))}</td>
        <td><button class="btn sm" type="button" data-po-source-save="${escapeHtml(source.id)}">Salvar</button></td>
      </tr>
    `;
  }).join('') || '<tr><td colspan="7" class="muted">Nenhuma fonte configurada.</td></tr>';
}

async function poSaveDataSource(sourceId) {
  const current = (painelOperadorState.dataSources?.sources || []).find((source) => source.id === sourceId) || {id: sourceId};
  const pathsInput = poGetSourceInput(sourceId, 'paths');
  const recursiveInput = poGetSourceInput(sourceId, 'recursive');
  const payload = {
    label: current.label || sourceId,
    description: current.description || '',
    kind: current.kind || 'folder',
    recursive: Boolean(recursiveInput?.checked),
    paths: (pathsInput?.value || '').split(/\r?\n/).map((line) => line.trim()).filter(Boolean),
  };
  await poRunAction(`Fonte ${sourceId}`, () => j(`${API}/painel-operador/data-sources/${encodeURIComponent(sourceId)}`, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(payload),
  }));
  await loadPainelOperadorIngestion(true);
}

async function loadPainelOperadorFiles() {
  const qs = poQuery({
    category: poEl('poFileCategory')?.value,
    document_kind: poEl('poFileKind')?.value,
    family: poEl('poFileFamily')?.value,
    tag: poEl('poFileTag')?.value,
    is_duplicate: poEl('poFileDuplicate')?.value,
    q: poEl('poFileSearch')?.value,
    limit: 120,
  });
  const data = await j(`${API}/painel-operador/file-index?${qs}`);
  poEl('poFilesMeta').textContent = `${poNum(data.total)} arquivo(s) encontrados · exibindo ${poNum(data.returned)}.`;
  poEl('poFilesRows').innerHTML = (data.items || []).map((row) => `
    <tr>
      <td class="po-path-cell" title="${escapeHtml(row.relative_path)}">${escapeHtml(row.filename || row.relative_path)}</td>
      <td>${escapeHtml(row.category || '')}</td>
      <td>${escapeHtml(row.document_kind || '')}</td>
      <td>${poTag(row.inferred_family)}</td>
      <td>${poTag(row.inferred_tag)}</td>
      <td class="mono">${fmtDate(row.inferred_date)}</td>
      <td class="num">${poBytes(row.file_size_bytes)}</td>
      <td>${row.is_duplicate ? poBadge('Duplicado', 'warn') : poBadge('Único', 'ok')}</td>
    </tr>
  `).join('') || '<tr><td colspan="8" class="muted">Nenhuma fonte encontrada para os filtros.</td></tr>';
}

async function loadPainelOperadorAnp() {
  const qs = poQuery({
    family: poEl('poAnpFamily')?.value,
    record_kind: poEl('poAnpKind')?.value,
    tag: poEl('poAnpTag')?.value,
    date_from: poEl('poAnpDateFrom')?.value,
    date_to: poEl('poAnpDateTo')?.value,
    q: poEl('poAnpSearch')?.value,
    limit: 120,
  });
  const data = await j(`${API}/painel-operador/anp-exports?${qs}`);
  poEl('poAnpMeta').textContent = `${poNum(data.total)} linha(s) ANP encontradas · exibindo ${poNum(data.returned)}.`;
  poEl('poAnpRows').innerHTML = (data.items || []).map((row) => `
    <tr>
      <td class="mono">${fmtDate(row.reference_date)}</td>
      <td>${poTag(row.family)}</td>
      <td>${poTag(row.tag)}</td>
      <td>${escapeHtml(row.record_kind || '')}</td>
      <td class="num">${fmt(row.volume_corrigido)}</td>
      <td class="num">${fmt(row.bsw_percent)}</td>
      <td>${escapeHtml(row.failure_code || row.failure_type || '') || '<span class="muted">—</span>'}</td>
      <td class="po-path-cell" title="${escapeHtml(row.source_path || '')}">${escapeHtml(row.source_file || '')}</td>
    </tr>
  `).join('') || '<tr><td colspan="8" class="muted">Nenhuma linha ANP encontrada para os filtros.</td></tr>';
}

function poXmlStatusLabel(status) {
  const labels = {ok: 'OK', warning: 'Atenção', critical: 'Crítico'};
  return labels[status] || poText(status);
}

function poXmlLinksText(row) {
  const related = row.related || {};
  return [
    `comparações ${poNum(related.comparison_rows)}`,
    `ANP ${poNum(related.anp_export_rows)}`,
    `CV ${poNum(related.cv_snapshot_rows)}`,
  ].join(' · ');
}

function poXmlShapeText(row) {
  const xml = row.xml || {};
  if (!xml.exists) return 'não localizado';
  if (!xml.well_formed) return xml.error ? `erro: ${xml.error}` : 'malformado';
  if (xml.shallow_check) return `${poText(xml.root, 'raiz sem nome')} · raiz OK`;
  return `${poText(xml.root, 'raiz sem nome')} · ${poNum(xml.elements)} nós`;
}

function poXmlActionsHtml(row) {
  const actions = row.recommended_actions || [];
  if (!actions.length) return '<span class="muted">—</span>';
  return actions.map((action) => {
    const style = action.priority === 'primary' ? 'btn sm' : 'btn secondary sm';
    return `<button class="${style}" type="button" data-po-xml-action="${escapeHtml(action.code)}" data-po-xml-id="${escapeHtml(row.id)}" title="${escapeHtml(action.detail || '')}">${escapeHtml(action.label)}</button>`;
  }).join(' ');
}

async function loadPainelOperadorXmlValidation() {
  const qs = poQuery({
    date_from: poEl('poXmlDateFrom')?.value,
    date_to: poEl('poXmlDateTo')?.value,
    kind: poEl('poXmlKind')?.value,
    status: poEl('poXmlStatus')?.value,
    family: poEl('poXmlFamily')?.value,
    tag: poEl('poXmlTag')?.value,
    q: poEl('poXmlSearch')?.value,
    limit: 160,
  });
  const data = await j(`${API}/painel-operador/xml-validation?${qs}`);
  painelOperadorState.xmlValidationRows = data.items || [];
  const summary = data.summary || {};
  poEl('poXmlValidationSummary').innerHTML = `
    <div class="po-summary-card"><span>XMLs catalogados</span><strong>${poNum(summary.cataloged_total ?? data.total)}</strong><small>${poNum(summary.evaluated)} avaliados nesta consulta</small></div>
    <div class="po-summary-card"><span>Críticos</span><strong>${poNum(summary.critical)}</strong><small>na página/lote avaliado</small></div>
    <div class="po-summary-card"><span>Atenção</span><strong>${poNum(summary.warning)}</strong><small>sem vínculo, data, família ou processamento</small></div>
    <div class="po-summary-card"><span>OK</span><strong>${poNum(summary.ok)}</strong><small>arquivo coerente com os vínculos atuais</small></div>
  `;
  const byKind = (summary.by_kind || []).slice(0, 5).map((row) => `${row.document_kind}: ${poNum(row.count)}`).join(' · ');
  poEl('poXmlValidationMeta').textContent = `${poNum(data.total)} XML(s) encontrados · ${byKind || 'sem agrupamentos'}.`;
  poEl('poXmlValidationRows').innerHTML = (data.items || []).map((row) => `
    <tr class="row-${poStatusKind(row.status)}">
      <td class="mono">${fmtDate(row.inferred_date)}</td>
      <td>${escapeHtml(row.document_kind || '')}</td>
      <td>${poTag(row.inferred_family)}</td>
      <td>${poTag(row.inferred_tag)}</td>
      <td class="po-path-cell" title="${escapeHtml(row.full_path || row.relative_path || '')}">${escapeHtml(row.filename || row.relative_path || '')}</td>
      <td class="po-path-cell" title="${escapeHtml(row.xml?.error || '')}">${escapeHtml(poXmlShapeText(row))}</td>
      <td>${escapeHtml(poXmlLinksText(row))}</td>
      <td>${row.is_duplicate ? poBadge('Duplicado', 'warn') : poBadge('Único', 'ok')}</td>
      <td>${poBadge(poXmlStatusLabel(row.status), poStatusKind(row.status))}</td>
      <td class="po-path-cell" title="${escapeHtml(row.note || '')}">${escapeHtml(row.note || '')}</td>
      <td class="po-actions-cell">${poXmlActionsHtml(row)}</td>
    </tr>
  `).join('') || '<tr><td colspan="11" class="muted">Nenhum XML encontrado para os filtros.</td></tr>';
}

async function poHandleXmlAction(actionCode, rowId) {
  const row = (painelOperadorState.xmlValidationRows || []).find((item) => String(item.id) === String(rowId));
  if (!row) return;
  if (actionCode === 'process_technical') {
    await poRunAction('Processamento Limites/CV', () => j(`${API}/painel-operador/technical-monitor/process`, {method: 'POST'}));
    await loadPainelOperadorXmlValidation();
    return;
  }
  if (actionCode === 'sync_contract') {
    await poRunAction('Sincronização do contrato', () => j(`${API}/painel-operador/sync`, {method: 'POST'}));
    await loadPainelOperadorXmlValidation();
    return;
  }
  if (actionCode === 'reindex_files') {
    await poRunAction('Reindexação de fontes', () => j(`${API}/painel-operador/file-index/scan?hash_files=false`, {method: 'POST'}));
    await loadPainelOperadorXmlValidation();
    return;
  }
  if (actionCode === 'open_technical') {
    poSetFormValue('poTechnicalDateFrom', row.inferred_date);
    poSetFormValue('poTechnicalDateTo', row.inferred_date);
    poSetFormValue('poTechnicalFamily', row.inferred_family);
    poSetFormValue('poTechnicalTag', row.inferred_tag);
    poSetActiveTab('technical');
    await loadPainelOperadorTechnical();
    return;
  }
  if (actionCode === 'open_compare') {
    poSetFormValue('poCompareFamily', row.inferred_family);
    poSetFormValue('poCompareDateFrom', row.inferred_date);
    poSetFormValue('poCompareDateTo', row.inferred_date);
    poSetFormValue('poCompareTag', row.inferred_tag);
    poSetActiveTab('compare');
    await loadPainelOperadorCompare();
    return;
  }
  if (actionCode === 'open_anp') {
    poSetFormValue('poAnpFamily', row.inferred_family);
    poSetFormValue('poAnpDateFrom', row.inferred_date);
    poSetFormValue('poAnpDateTo', row.inferred_date);
    poSetFormValue('poAnpSearch', row.filename);
    poSetActiveTab('anp');
    await loadPainelOperadorAnp();
    return;
  }
  if (actionCode === 'open_files') {
    poSetFormValue('poFileKind', row.document_kind);
    poSetFormValue('poFileFamily', row.inferred_family);
    poSetFormValue('poFileTag', row.inferred_tag);
    poSetFormValue('poFileSearch', row.filename);
    poSetActiveTab('files');
    await loadPainelOperadorFiles();
  }
}

function poCompareStatusLabel(status) {
  const labels = {
    matched: 'Compatível',
    value_mismatch: 'Divergente',
    anp_only: 'Só ANP',
    staging_only: 'Apenas processados',
    not_comparable: 'Sem comparação',
  };
  return labels[status] || poText(status);
}

function poCompareStatusKind(status) {
  if (status === 'matched') return 'ok';
  if (status === 'value_mismatch') return 'err';
  if (status === 'not_comparable') return 'warn';
  return 'info';
}

function poStatusKind(status) {
  if (['ok', 'loaded', 'resolved', 'matched', 'closed', 'approved', 'aprovado', 'imported_from_radar'].includes(status)) return 'ok';
  if (['critical', 'open', 'value_mismatch', 'not_loaded', 'falha'].includes(status)) return 'err';
  if (['warn', 'warning', 'changed', 'review', 'draft', 'deferred', 'ignored', 'not_comparable', 'atenção', 'atencao', 'pendente', 'offspec', 'reprocesso'].includes(status)) return 'warn';
  return 'info';
}

function poMeasuredSourceLabel(source) {
  const labels = {
    fiscal_radar: 'Fiscal/Radar',
    anp_export: 'Export ANP',
    mpfm_daily: 'MPFM diário',
  };
  return labels[source] || poText(source);
}

function poMeasuredMetric(row) {
  if (row.source === 'mpfm_daily') return poText(row.metric_name);
  if (row.source === 'anp_export') return poText(row.record_kind);
  return poText(row.fluid || row.record_kind, 'volume corrigido');
}

function poMeasuredFiscalText(row) {
  if (row.source !== 'fiscal_radar') return '—';
  return `raw ${fmt(row.raw_corrigido)} · xml ${fmt(row.xml_corrigido)} · anp ${fmt(row.anp_corrigido)}`;
}

function poMeasuredVolumeText(row) {
  if (row.source !== 'anp_export') return '—';
  const parts = [
    `corr ${fmt(row.volume_corrigido)}`,
    `bruto ${fmt(row.volume_bruto)}`,
    `liq ${fmt(row.volume_liquido)}`,
  ];
  if (row.bsw_percent !== null && row.bsw_percent !== undefined) parts.push(`BSW ${fmt(row.bsw_percent)}`);
  return parts.join(' · ');
}

function poMeasuredMpfmText(row) {
  if (row.source !== 'mpfm_daily') return '—';
  return `${fmt(row.metric_value)} ${escapeHtml(row.metric_unit || '')}`.trim();
}

function poProductionStatusLabel(status) {
  const labels = {
    complete: 'Completo',
    partial: 'Parcial',
    attention: 'Atenção',
    empty: 'Sem dado',
  };
  return labels[status] || poText(status);
}

function poProductionStatusKind(status) {
  if (status === 'complete') return 'ok';
  if (status === 'attention') return 'warn';
  if (status === 'empty') return 'err';
  return 'info';
}

function poProductionFilesText(row) {
  return [
    `daily ${poNum(row.daily_report_files)}`,
    `fiscal ${poNum(row.fiscal_document_files)}`,
    `ANP ${poNum(row.anp_export_files + row.anp_xml_files)}`,
  ].join(' · ');
}

function poProductionTagsText(row) {
  const tags = Math.max(
    Number(row.file_tags_count || 0),
    Number(row.fiscal_tags_count || 0),
    Number(row.anp_tags_count || 0),
    Number(row.mpfm_tags_count || 0),
  );
  return poNum(tags);
}

function poProductionSamplesText(samples) {
  const rows = (samples || []).slice(0, 3);
  return rows.length ? rows.map((row) => row.filename || row.document_kind || row.category).join(' · ') : '—';
}

async function loadPainelOperadorMeasured() {
  const common = {
    date_from: poEl('poMeasuredDateFrom')?.value,
    date_to: poEl('poMeasuredDateTo')?.value,
    family: poEl('poMeasuredFamily')?.value,
    tag: poEl('poMeasuredTag')?.value,
  };
  const measuredQs = poQuery({
    ...common,
    source: poEl('poMeasuredSource')?.value,
    limit: 160,
  });
  const productionQs = poQuery({
    ...common,
    limit: 90,
  });
  const [production, data] = await Promise.all([
    j(`${API}/painel-operador/production-days?${productionQs}`),
    j(`${API}/painel-operador/measured-data?${measuredQs}`),
  ]);
  const totals = data.totals || {};
  const productionTotals = production.totals || {};
  poEl('poMeasuredSummary').innerHTML = `
    <div class="po-stage-count"><span>Dias apuração</span><strong>${poNum(productionTotals.days)}</strong></div>
    <div class="po-stage-count"><span>Dias completos</span><strong>${poNum(productionTotals.complete_days)}</strong></div>
    <div class="po-stage-count"><span>Arquivos do recorte</span><strong>${poNum(productionTotals.file_count)}</strong></div>
    <div class="po-stage-count"><span>Pendências abertas</span><strong>${poNum(productionTotals.open_pending_count)}</strong></div>
    <div class="po-stage-count"><span>Fiscal/Radar m3</span><strong>${poNum(totals.fiscal_volume_m3, 2)}</strong></div>
    <div class="po-stage-count"><span>Export ANP m3</span><strong>${poNum(totals.anp_volume_m3, 2)}</strong></div>
    <div class="po-stage-count"><span>MPFM HC t</span><strong>${poNum(totals.mpfm_corr_hc_t, 2)}</strong></div>
  `;
  poEl('poProductionDayMeta').textContent = `${poNum(production.total)} dia(s) de produção encontrados · exibindo ${poNum(production.returned)}. Status completo exige Fiscal/Radar, ANP e MPFM no mesmo dia.`;
  poEl('poProductionDayRows').innerHTML = (production.items || []).map((row) => `
    <tr>
      <td class="mono">${fmtDate(row.production_date)}</td>
      <td>${poBadge(poProductionStatusLabel(row.status), poProductionStatusKind(row.status))}</td>
      <td class="num">${poNum(row.file_count)}</td>
      <td class="po-path-cell">${escapeHtml(poProductionFilesText(row))}</td>
      <td class="num">${fmt(row.fiscal_volume_m3)}</td>
      <td class="num">${fmt(row.anp_volume_m3)}</td>
      <td class="num">${fmt(row.mpfm_hc_t)}</td>
      <td class="num">${poProductionTagsText(row)}</td>
      <td>${Number(row.open_pending_count || 0) ? poBadge(poNum(row.open_pending_count), 'warn') : poBadge('0', 'ok')}</td>
      <td class="po-path-cell" title="${escapeHtml(poProductionSamplesText(row.file_samples))}">${escapeHtml(poProductionSamplesText(row.file_samples))}</td>
    </tr>
  `).join('') || '<tr><td colspan="10" class="muted">Nenhum dia de produção encontrado para os filtros.</td></tr>';
  poEl('poMeasuredDailyMeta').textContent = `${poNum((data.daily || []).length)} dia(s) agregados. Fiscal/ANP em m3; MPFM em t.`;
  poEl('poMeasuredDailyRows').innerHTML = (data.daily || []).map((row) => `
    <tr>
      <td class="mono">${fmtDate(row.measurement_date)}</td>
      <td class="num">${poNum(row.sources_count)}</td>
      <td class="num">${poNum(row.tags_count)}</td>
      <td class="num">${fmt(row.fiscal_volume_m3)}</td>
      <td class="num">${fmt(row.anp_volume_m3)}</td>
      <td class="num">${fmt(row.mpfm_corr_hc_t)}</td>
      <td class="num">${poNum(row.row_count)}</td>
      <td>${Number(row.warning_rows || 0) ? poBadge(poNum(row.warning_rows), 'warn') : poBadge('0', 'ok')}</td>
    </tr>
  `).join('') || '<tr><td colspan="8" class="muted">Nenhum dado medido encontrado para os filtros.</td></tr>';
  poEl('poMeasuredMeta').textContent = `${poNum(data.total)} registro(s) medidos · exibindo ${poNum(data.returned)}.`;
  poEl('poMeasuredRows').innerHTML = (data.rows || []).map((row) => `
    <tr>
      <td class="mono">${fmtDate(row.measurement_date)}</td>
      <td>${poBadge(poMeasuredSourceLabel(row.source), row.source === 'mpfm_daily' ? 'info' : 'ok')}</td>
      <td>${poTag(row.family)}</td>
      <td>${poTag(row.tag || row.instrument)}</td>
      <td class="po-path-cell" title="${escapeHtml(poMeasuredMetric(row))}">${escapeHtml(poMeasuredMetric(row))}</td>
      <td class="po-path-cell">${escapeHtml(poMeasuredFiscalText(row))}</td>
      <td class="po-path-cell">${escapeHtml(poMeasuredVolumeText(row))}</td>
      <td class="po-path-cell">${poMeasuredMpfmText(row)}</td>
      <td>${row.status ? poBadge(poText(row.status), poStatusKind(row.status)) : '<span class="muted">—</span>'}</td>
      <td class="po-path-cell" title="${escapeHtml(row.source_path || '')}">${escapeHtml(row.source_path || '—')}</td>
    </tr>
  `).join('') || '<tr><td colspan="10" class="muted">Nenhum registro medido encontrado para os filtros.</td></tr>';
}

async function loadPainelOperadorDossiers() {
  const qs = poQuery({
    date_from: poEl('poDossierDateFrom')?.value,
    date_to: poEl('poDossierDateTo')?.value,
    family: poEl('poDossierFamily')?.value,
    tag: poEl('poDossierTag')?.value,
    q: poEl('poDossierSearch')?.value,
    limit: 80,
  });
  const data = await j(`${API}/painel-operador/measurement-point-dossiers?${qs}`);
  painelOperadorState.dossiers = data;
  const summary = data.summary || {};
  const items = data.items || [];
  poEl('poDossierSummary').innerHTML = `
    <div class="po-stage-count"><span>Pontos</span><strong>${poNum(summary.points)}</strong></div>
    <div class="po-stage-count"><span>Críticos</span><strong>${poNum(summary.critical)}</strong></div>
    <div class="po-stage-count"><span>Atenção</span><strong>${poNum(summary.warning)}</strong></div>
    <div class="po-stage-count"><span>OK</span><strong>${poNum(summary.ok)}</strong></div>
    <div class="po-stage-count"><span>Com Fiscal/ANP</span><strong>${poNum(Math.min(Number(summary.with_fiscal || 0), Number(summary.with_anp || 0)))}</strong></div>
    <div class="po-stage-count"><span>Com MPFM</span><strong>${poNum(summary.with_mpfm)}</strong></div>
  `;
  poEl('poDossierMeta').textContent = `${poNum(data.returned)} dossiê(s) retornados. Fiscal/Radar e ANP em m3; MPFM em t sem normalização automática.`;
  poEl('poDossierCards').innerHTML = items.slice(0, 8).map(poDossierCard).join('') || '<div class="po-empty">Sem dossiê para o filtro.</div>';
  poEl('poDossierRows').innerHTML = items.map((row) => `
    <tr>
      <td>${poTag(row.tag)}<br><span class="muted mono">${fmtDate(row.latest_date)}</span></td>
      <td>${poBadge(poDossierHealthLabel(row.health), poDossierHealthKind(row.health))}</td>
      <td class="po-path-cell">${escapeHtml(poDossierCadastroText(row))}</td>
      <td class="po-path-cell">${escapeHtml(poDossierLimitsText(row.limits))}</td>
      <td class="po-path-cell">${escapeHtml(poDossierFiscalText(row.fiscal))}</td>
      <td class="po-path-cell">${escapeHtml(poDossierAnpText(row.anp))}</td>
      <td class="po-path-cell">${escapeHtml(poDossierMpfmText(row.mpfm))}</td>
      <td class="po-path-cell">${escapeHtml(poDossierFilesText(row.files))}</td>
      <td class="po-path-cell">${escapeHtml(poDossierProposalText(row.proposals))}</td>
      <td class="po-path-cell">${escapeHtml(poDossierEvidenceText(row.evidence))}</td>
    </tr>
  `).join('') || '<tr><td colspan="10" class="muted">Nenhum dossiê encontrado para os filtros.</td></tr>';
}

function poDossierCard(row) {
  return `
    <div class="po-radar-card">
      <div class="po-radar-card__top"><span>${escapeHtml(row.family || 'sem família')}</span>${poBadge(poDossierHealthLabel(row.health), poDossierHealthKind(row.health))}</div>
      <strong>${escapeHtml(row.tag || 'Ponto')}</strong>
      <p>${escapeHtml(poDossierCadastroText(row))}</p>
      <div class="po-dossier-card-grid">
        <span>Fiscal ${poNum(row.fiscal?.rows)}</span>
        <span>ANP ${poNum(row.anp?.rows)}</span>
        <span>MPFM ${poNum(row.mpfm?.rows)}</span>
        <span>Limites ${poNum(row.limits?.count)}</span>
      </div>
    </div>
  `;
}

function poDossierHealthLabel(status) {
  const labels = {critical: 'Crítico', warning: 'Atenção', ok: 'OK', partial: 'Parcial'};
  return labels[status] || poText(status);
}

function poDossierHealthKind(status) {
  if (status === 'critical') return 'err';
  if (status === 'warning') return 'warn';
  if (status === 'ok') return 'ok';
  return 'info';
}

function poDossierCadastroText(row) {
  const parts = [
    row.family_name || row.family || '',
    row.fluid || '',
    row.meter_type || '',
    row.computador_vazao ? `CV ${row.computador_vazao}` : '',
  ].filter(Boolean);
  return parts.length ? parts.join(' · ') : 'Cadastro parcial';
}

function poDossierLimitsText(limits = {}) {
  const items = limits.items || [];
  if (!Number(limits.count || 0)) return 'sem limite cadastrado';
  const head = `${poNum(limits.count)} limite(s), ${poNum(limits.critical)} crítico(s), ${poNum(limits.warning)} atenção`;
  const sample = items.slice(0, 3).map((row) => `${row.metric_name}: ${poDossierRange(row)}`).join(' · ');
  return sample ? `${head} · ${sample}` : head;
}

function poDossierRange(row) {
  const unit = row.value_unit ? ` ${row.value_unit}` : '';
  if (row.pam_min !== null && row.pam_min !== undefined || row.pam_max !== null && row.pam_max !== undefined) {
    return `PAM ${fmt(row.pam_min)}-${fmt(row.pam_max)}${unit}`;
  }
  return `${fmt(row.calibrated_min)}-${fmt(row.calibrated_max)}${unit}`;
}

function poDossierFiscalText(fiscal = {}) {
  if (!Number(fiscal.rows || 0)) return 'sem Fiscal/Radar';
  return `${poNum(fiscal.rows)} linha(s), ANP ${fmt(fiscal.anp_m3)} m3, XML ${fmt(fiscal.xml_m3)} m3, alertas ${poNum(fiscal.warnings)}`;
}

function poDossierAnpText(anp = {}) {
  if (!Number(anp.rows || 0)) return 'sem export ANP';
  return `${poNum(anp.rows)} linha(s), ${fmt(anp.volume_m3)} m3, BSW ${poNum(anp.bsw_rows)}, falhas ${poNum(anp.failure_rows)}`;
}

function poDossierMpfmText(mpfm = {}) {
  if (mpfm.coverage === 'not_checked_without_explicit_tag') return 'filtre uma TAG para checar MPFM';
  if (!Number(mpfm.rows || 0)) return 'sem MPFM por TAG exata';
  return `${poNum(mpfm.rows)} linha(s), HC ${fmt(mpfm.hc_t)} t, óleo ${fmt(mpfm.oil_t)} t`;
}

function poDossierFilesText(files = {}) {
  if (!Number(files.count || 0)) return 'sem arquivo tagueado';
  const names = (files.samples || []).slice(0, 2).map((row) => row.filename).filter(Boolean).join(' · ');
  return `${poNum(files.count)} arquivo(s)${names ? ` · ${names}` : ''}`;
}

function poDossierProposalText(proposals = {}) {
  if (!Number(proposals.count || 0)) return 'sem proposta';
  const first = (proposals.items || [])[0] || {};
  return `${poNum(proposals.count)} proposta(s), ${poNum(proposals.pending)} pendente(s)${first.title ? ` · ${first.title}` : ''}`;
}

function poDossierEvidenceText(evidence = {}) {
  if (!Number(evidence.count || 0)) return 'sem evidência direta';
  const first = (evidence.items || [])[0] || {};
  return `${poNum(evidence.count)} evidência(s)${first.title ? ` · ${first.title}` : ''}`;
}

const PO_RADAR_BLOCKS = [
  'meta', 'kpis', 'families', 'files', 'closing', 'comparisons', 'latestPoints',
  'limitMonitors', 'uncertaintyMonitor', 'analytical', 'measurementModels',
  'operatorPanelHealth', 'ai', 'regulatoryMatrix', 'eventEvidenceRadar',
  'changeProposals', 'operationalCalendar', 'bsw', 'failures', 'mpfm', 'alerts',
  'database',
];

async function loadPainelOperadorRadar(force = false) {
  if (painelOperadorState.radarData && !force) {
    renderPainelOperadorRadar();
    return;
  }
  poEl('poRadarStatus').textContent = 'Carregando contrato consolidado do Radar ANP...';
  const qs = poQuery({blocks: PO_RADAR_BLOCKS.join(','), max_list_items: 5000});
  const [contract, sources] = await Promise.all([
    j(`${API}/painel-operador/data?${qs}`),
    j(`${API}/painel-operador/data-sources?validate=false`).catch(() => null),
  ]);
  painelOperadorState.radarData = contract.data || {};
  painelOperadorState.radarContract = contract || {};
  painelOperadorState.radarSources = sources;
  poPopulateRadarFilters(painelOperadorState.radarData);
  renderPainelOperadorRadar();
}

function poPopulateRadarFilters(data) {
  const dateSelect = poEl('poRadarDate');
  const tagSelect = poEl('poRadarTag');
  if (dateSelect) {
    const current = dateSelect.value;
    const dates = new Set();
    (data.operationalCalendar?.days || []).forEach((row) => { if (row.date) dates.add(row.date); });
    (data.closing || []).forEach((row) => { if (row.date) dates.add(row.date); });
    (data.comparisons || []).forEach((row) => { if (row.date) dates.add(row.date); });
    const ordered = [...dates].sort();
    dateSelect.innerHTML = '<option value="">Último disponível</option>' + ordered.map((date) => `<option value="${escapeHtml(date)}">${fmtDate(date)}</option>`).join('');
    if (ordered.includes(current)) dateSelect.value = current;
  }
  if (tagSelect) {
    const current = tagSelect.value;
    const tags = new Set();
    (data.latestPoints || []).forEach((row) => { if (row.tag) tags.add(row.tag); });
    (data.comparisons || []).forEach((row) => { if (row.tag) tags.add(row.tag); });
    (data.limitMonitors || []).forEach((row) => { if (row.tag) tags.add(row.tag); });
    const ordered = [...tags].sort((a, b) => String(a).localeCompare(String(b), 'pt-BR'));
    tagSelect.innerHTML = '<option value="">Todos</option>' + ordered.map((tag) => `<option value="${escapeHtml(tag)}">${escapeHtml(tag)}</option>`).join('');
    if (ordered.includes(current)) tagSelect.value = current;
  }
}

function poRadarFilteredRows(rows, opts = {}) {
  const data = painelOperadorState.radarData || {};
  const date = poEl('poRadarDate')?.value || opts.date || '';
  const tag = poEl('poRadarTag')?.value || opts.tag || '';
  const query = String(poEl('poRadarSearch')?.value || '').trim().toLowerCase();
  const latestDate = poRadarLatestDate(data);
  return (rows || []).filter((row) => {
    if (!row || typeof row !== 'object') return false;
    const rowDate = String(row.date || row.createdAt || row.created_at || row.timestamp || row.eventAt || '').slice(0, 10);
    if (date && rowDate && rowDate !== date) return false;
    if (!date && opts.onlyLatest && latestDate && rowDate && rowDate !== latestDate) return false;
    if (tag) {
      const rowTag = String(row.tag || row.targetId || row.target_id || '');
      const tags = Array.isArray(row.tags) ? row.tags.map(String) : [];
      if (rowTag !== tag && !tags.includes(tag)) return false;
    }
    if (query && !JSON.stringify(row).toLowerCase().includes(query)) return false;
    return true;
  });
}

function poRadarLatestDate(data, rows = null) {
  if (Array.isArray(rows) && rows.length) {
    const rowDates = rows.map((row) => String(row.date || row.createdAt || row.created_at || row.timestamp || '').slice(0, 10)).filter(Boolean).sort();
    if (rowDates.length) return rowDates[rowDates.length - 1];
  }
  const explicit = data.meta?.latestAnpDate || data.operationalCalendar?.end;
  if (explicit) return String(explicit).slice(0, 10);
  const dates = [
    ...(data.closing || []).map((row) => row.date),
    ...(data.comparisons || []).map((row) => row.date),
    ...(data.latestPoints || []).map((row) => row.date),
  ].filter(Boolean).sort();
  return dates[dates.length - 1] || '';
}

function poRadarSetView(view) {
  painelOperadorState.radarActiveView = view || 'medicao';
  document.querySelectorAll('[data-po-radar-view]').forEach((button) => {
    const active = button.dataset.poRadarView === painelOperadorState.radarActiveView;
    button.classList.toggle('active', active);
    button.setAttribute('aria-selected', String(active));
  });
  renderPainelOperadorRadar();
}

function renderPainelOperadorRadar() {
  const data = painelOperadorState.radarData || {};
  if (!Object.keys(data).length) return;
  const meta = data.meta || {};
  const sourceDate = poRadarLatestDate(data);
  const contract = painelOperadorState.radarContract || {};
  poEl('poRadarStatus').textContent = `Contrato ${fmtDate(meta.generatedAt || '') || 'carregado'} · dia de referência ${fmtDate(sourceDate)} · módulo ${poText(contract.module_root || contract.source || 'dashboard-data.json')}.`;
  const kpis = data.kpis || {};
  poEl('poRadarSummary').innerHTML = `
    <div class="po-stage-count"><span>XMLs</span><strong>${poNum(kpis.xmlFiles)}</strong></div>
    <div class="po-stage-count"><span>Comparações</span><strong>${poNum(kpis.comparisonRows)}</strong></div>
    <div class="po-stage-count"><span>ANP ok</span><strong>${poNum(kpis.xmlAnpOk)}</strong></div>
    <div class="po-stage-count"><span>Falhas abertas</span><strong>${poNum(data.failures?.open)}</strong></div>
    <div class="po-stage-count"><span>Alertas</span><strong>${poNum((data.alerts || []).length)}</strong></div>
    <div class="po-stage-count"><span>Propostas</span><strong>${poNum((data.changeProposals || []).length)}</strong></div>
  `;
  const view = painelOperadorState.radarActiveView || 'operacao';
  const renderers = {
    medicao: renderPoRadarMedicao,
    operacao: renderPoRadarOperacao,
    trilha: renderPoRadarTrilha,
    calendario: renderPoRadarCalendario,
    prazos: renderPoRadarPrazos,
    propostas: renderPoRadarPropostas,
    config: renderPoRadarConfig,
    pergunte: renderPoRadarPergunte,
    dossie: renderPoRadarDossie,
  };
  (renderers[view] || renderPoRadarOperacao)(data);
}

function renderPoRadarMedicao(data) {
  const meta = data.meta || {};
  const selectedDate = poEl('poRadarDate')?.value || poRadarLatestDate(data, data.closing || []) || poRadarLatestDate(data);
  const closingRows = [...(data.closing || [])].sort((a, b) => String(a.date || '').localeCompare(String(b.date || '')));
  const dayClosing = closingRows.find((row) => row.date === selectedDate) || closingRows[closingRows.length - 1] || {};
  const comparisons = poRadarFilteredRows(data.comparisons || [], {date: dayClosing.date || selectedDate});
  const points = poRadarFilteredRows(data.latestPoints || [], {date: dayClosing.date || selectedDate});
  const kpis = data.kpis || {};
  const failures = data.failures || {};
  const calendarSummary = data.operationalCalendar?.summary || {};
  const alerts = poRadarFilteredRows(data.alerts || []).slice(0, 12);
  const limits = poRadarFilteredRows(data.limitMonitors || []).slice(0, 8);
  const validCount = comparisons.filter((row) => String(row.status || '').toLowerCase() === 'ok').length;
  const invalidCount = Math.max(comparisons.length - validCount, 0);
  const alertCount = alerts.length + comparisons.filter((row) => String(row.status || '').toLowerCase() !== 'ok').length;
  const criticalCount = Number(failures.open || 0);
  const e2eTotal = 6;
  const e2eDone = [
    comparisons.some((row) => row.rawOk),
    true,
    comparisons.some((row) => row.xmlCorrigido !== null && row.xmlCorrigido !== undefined),
    Number(kpis.xmlFiles || 0) > 0,
    Number(kpis.anpRows || 0) > 0,
    comparisons.some((row) => row.anpOk),
  ].filter(Boolean).length;
  const conformidade = Math.round((e2eDone / e2eTotal) * 100);
  poEl('poRadarBody').innerHTML = `
    <div class="po-medicao-shell">
      <aside class="po-medicao-rail" aria-label="Atalhos do Radar Medição">
        ${poMedicaoRailItem('Visão geral', true)}
        ${poMedicaoRailItem('Raw CV/IHM')}
        ${poMedicaoRailItem('Checklist interno')}
        ${poMedicaoRailItem('XML gerado')}
        ${poMedicaoRailItem('ZIP enviado')}
        ${poMedicaoRailItem('Painel ANP')}
        ${poMedicaoRailItem('Prazos ANP')}
        ${poMedicaoRailItem('Limites e especificações')}
        ${poMedicaoRailDivider()}
        ${['BSW', 'PMO', 'PMGL', 'PMGD', 'PMAE'].map((item) => poMedicaoRailItem(item)).join('')}
      </aside>
      <section class="po-medicao-main">
        <div class="po-medicao-topline">
          <div><strong>Radar ANP Medição</strong><span>Data operacional: ${fmtDate(dayClosing.date || selectedDate || meta.latestAnpDate)}</span></div>
          <div><span>Fechamento diário</span>${poBadge(dayClosing.status === 'ok' ? 'Concluído' : 'Atenção', dayClosing.status === 'ok' ? 'ok' : 'warn')}</div>
          <div><span>Última atualização</span><strong>${fmtDate(meta.generatedAt || '') || '—'}</strong></div>
        </div>
        <div class="po-medicao-kpis">
          ${poMedicaoKpi('Produção total (m³)', fmt(dayClosing.totalOil || 0), `${poNum(dayClosing.points || points.length)} pontos no fechamento`, 'ok')}
          ${poMedicaoKpi('Medições válidas', poNum(validCount), `${poPercent(validCount, Math.max(comparisons.length, 1))}% do total`, 'ok')}
          ${poMedicaoKpi('Medições com alerta', poNum(alertCount), `${poNum(invalidCount)} divergência(s) raw/XML/ANP`, alertCount ? 'warn' : 'ok')}
          ${poMedicaoKpi('Falhas críticas', poNum(criticalCount), `${poNum(failures.total || 0)} falhas no histórico`, criticalCount ? 'bad' : 'ok')}
          ${poMedicaoKpi('XML gerado', poNum(kpis.xmlFiles), `${poNum(kpis.xmlRecords)} registros`, 'info')}
          ${poMedicaoKpi('ANP recebido', poNum(kpis.anpRows ? 1 : 0), `${poNum(kpis.anpRows)} linhas importadas`, 'info')}
        </div>
        <div class="po-medicao-e2e">
          ${poMedicaoE2eStep('Raw CV/IHM', comparisons.some((row) => row.rawOk), 'CV/IHM')}
          ${poMedicaoE2eStep('Checklist interno', true, 'importado')}
          ${poMedicaoE2eStep('XML gerado', Number(kpis.xmlFiles || 0) > 0, `${poNum(kpis.xmlFiles)} arquivo(s)`)}
          ${poMedicaoE2eStep('ZIP enviado', Number(kpis.xmlFiles || 0) > 0, 'pacote local')}
          ${poMedicaoE2eStep('Painel ANP', Number(kpis.anpRows || 0) > 0, 'processado')}
          ${poMedicaoE2eStep('ANP recebido', comparisons.some((row) => row.anpOk), `${poNum(kpis.anpRows)} linhas`)}
          <div class="po-medicao-conformidade"><span>Conformidade E2E</span><strong>${poNum(conformidade)}%</strong></div>
        </div>
        <div class="po-medicao-grid">
          <section class="po-medicao-panel po-medicao-panel--table">
            <div class="po-radar-section-title">Medições do dia por TAG</div>
            <div class="tablewrap po-tablewrap">
              <table class="table">
                <thead><tr><th>TAG</th><th>Família</th><th>Produto</th><th>Medição (m³)</th><th>Válida</th><th>Alerta</th><th>Status</th></tr></thead>
                <tbody>${comparisons.slice(0, 10).map((row) => {
                  const ok = String(row.status || '').toLowerCase() === 'ok';
                  return `<tr><td>${poTag(row.tag)}</td><td>${escapeHtml(row.familyName || row.family || '')}</td><td>${escapeHtml(row.fluid || '')}</td><td class="num">${fmt(row.anpCorrigido ?? row.xmlCorrigido ?? row.rawCorrigido)}</td><td class="num">${ok ? 1 : 0}</td><td class="num">${ok ? 0 : 1}</td><td>${poBadge(ok ? 'OK' : 'Alerta', ok ? 'ok' : 'warn')}</td></tr>`;
                }).join('') || '<tr><td colspan="7" class="muted">Sem medições para o dia selecionado.</td></tr>'}</tbody>
              </table>
            </div>
          </section>
          <section class="po-medicao-panel">
            <div class="po-radar-section-title">Volume de produção (m³)</div>
            <div class="po-trend-wrap po-medicao-chart"><canvas id="poRadarMeasurementChart"></canvas></div>
          </section>
          <section class="po-medicao-panel">
            <div class="po-radar-section-title">Radar de alertas</div>
            <div class="po-medicao-alert-layout">
              <div class="po-medicao-radar-mini">${poMedicaoRadarMini([
                ['Não envio', Number(calendarSummary.notLoaded || 0)],
                ['XML', Number(kpis.xmlFiles || 0)],
                ['Schema', invalidCount],
                ['Dados', alertCount],
                ['Prazos', Number(calendarSummary.openPendencies || 0)],
                ['NFSM', criticalCount],
              ])}</div>
              <div class="po-radar-list">${alerts.slice(0, 6).map(poRadarAlertItem).join('') || '<div class="po-empty">Sem alerta no filtro.</div>'}</div>
            </div>
          </section>
          <section class="po-medicao-panel">
            <div class="po-radar-section-title">Prazos ANP</div>
            <div class="po-radar-list">
              ${poMedicaoPrazo('Envio diário (D-1)', dayClosing.date || selectedDate, comparisons.length ? 'OK' : 'Atenção')}
              ${poMedicaoPrazo('Calendário operacional', data.operationalCalendar?.end, `${poNum(calendarSummary.openPendencies || 0)} abertas`)}
              ${poMedicaoPrazo('Falhas NFSM', failures.latestOpen?.[0]?.dueDate, `${poNum(failures.open || 0)} abertas`)}
            </div>
          </section>
          <section class="po-medicao-panel po-medicao-panel--wide">
            <div class="po-radar-section-title">Limites e especificações</div>
            <div class="tablewrap po-tablewrap">
              <table class="table">
                <thead><tr><th>TAG</th><th>Parâmetro</th><th>Mínimo</th><th>Máximo</th><th>Último valor</th><th>Status</th></tr></thead>
                <tbody>${limits.map((row) => poMedicaoLimitRows(row)).join('') || '<tr><td colspan="6" class="muted">Sem limite/PAM no filtro.</td></tr>'}</tbody>
              </table>
            </div>
          </section>
        </div>
      </section>
    </div>
  `;
  renderPoRadarMeasurementChart(comparisons, closingRows);
}

function poMedicaoRailDivider() {
  return '<div class="po-medicao-rail-divider" aria-hidden="true"></div>';
}

function poMedicaoRailItem(label, active = false) {
  return `<div class="po-medicao-rail-item ${active ? 'active' : ''}"><span>${escapeHtml(label)}</span></div>`;
}

function poMedicaoKpi(title, value, detail, kind = 'info') {
  return `<div class="po-medicao-kpi po-medicao-kpi--${kind}"><span>${escapeHtml(title)}</span><strong>${escapeHtml(String(value))}</strong><small>${escapeHtml(detail)}</small></div>`;
}

function poMedicaoE2eStep(title, done, detail) {
  return `<div class="po-medicao-e2e-step ${done ? 'done' : 'warn'}"><i></i><strong>${escapeHtml(title)}</strong><span>${done ? 'Concluído' : 'Atenção'}</span><small>${escapeHtml(detail)}</small></div>`;
}

function poMedicaoPrazo(title, date, status) {
  return `<div class="po-radar-list-item"><strong>${escapeHtml(title)}</strong><span>${fmtDate(date)} · ${escapeHtml(status || '')}</span></div>`;
}

function poMedicaoLimitRows(row) {
  const items = [
    ['PAM', row.pam],
    ['Pressão', row.pressure],
    ['Temperatura', row.temperature],
  ];
  return items.map(([name, value]) => {
    if (!value || typeof value !== 'object') return '';
    return `<tr><td>${poTag(row.tag)}</td><td>${escapeHtml(name)}</td><td class="num">${fmt(value.lower ?? value.min)}</td><td class="num">${fmt(value.upper ?? value.max)}</td><td class="num">${fmt(value.value)}</td><td>${poBadge(poText(value.status), poStatusKind(value.status))}</td></tr>`;
  }).join('');
}

function poMedicaoRadarMini(items) {
  const max = Math.max(...items.map(([, value]) => Number(value || 0)), 1);
  return items.map(([label, value]) => `<div><span>${escapeHtml(label)}</span><i style="--v:${Math.max(8, Math.round((Number(value || 0) / max) * 100))}%"></i><strong>${poNum(value)}</strong></div>`).join('');
}

function renderPoRadarMeasurementChart(comparisons, closingRows) {
  const canvas = poEl('poRadarMeasurementChart');
  if (!canvas || !window.Chart) return;
  if (painelOperadorState.radarMeasurementChart) {
    painelOperadorState.radarMeasurementChart.destroy();
    painelOperadorState.radarMeasurementChart = null;
  }
  const byTag = (comparisons || []).slice(0, 12);
  const labels = byTag.map((row) => row.tag || row.family || 'tag');
  const values = byTag.map((row) => Number(row.anpCorrigido ?? row.xmlCorrigido ?? row.rawCorrigido ?? 0));
  const trendRows = [...(closingRows || [])].sort((a, b) => String(a.date || '').localeCompare(String(b.date || ''))).slice(-12);
  painelOperadorState.radarMeasurementChart = new Chart(canvas.getContext('2d'), {
    data: {
      labels: labels.length ? labels : trendRows.map((row) => String(row.date || '').slice(5)),
      datasets: [
        {type: 'bar', label: 'Por TAG (m³)', data: labels.length ? values : trendRows.map((row) => Number(row.totalOil || 0)), backgroundColor: '#38bdf8'},
        {type: 'line', label: 'Total óleo (m³)', data: labels.length ? values.map((_, idx) => values.slice(0, idx + 1).reduce((a, b) => a + b, 0)) : trendRows.map((row) => Number(row.totalOil || 0)), borderColor: '#0f766e', backgroundColor: 'transparent', borderWidth: 2, pointRadius: 2, tension: 0.25},
      ],
    },
    options: {responsive: true, maintainAspectRatio: false},
  });
}

function renderPoRadarOperacao(data) {
  const closing = poRadarFilteredRows(data.closing || []);
  const points = poRadarFilteredRows(data.latestPoints || []);
  const alerts = poRadarFilteredRows(data.alerts || []).slice(0, 12);
  const limits = poRadarFilteredRows(data.limitMonitors || []).slice(0, 8);
  const health = data.operatorPanelHealth || {};
  poEl('poRadarBody').innerHTML = `
    <div class="po-radar-two-col">
      <div>
        <div class="po-radar-section-title">Fechamento diário</div>
        <div class="po-trend-wrap po-radar-chart"><canvas id="poRadarClosingChart"></canvas></div>
      </div>
      <div>
        <div class="po-radar-section-title">Saúde do Painel ANP</div>
        <div class="po-radar-health">
          ${poRadarHealthLine('Status', health.status || 'n/d', poStatusKind(health.status))}
          ${poRadarHealthLine('Pronto', `${poNum(health.ready)} de ${poNum(health.required)}`, Number(health.ready) >= Number(health.required || 0) ? 'ok' : 'warn')}
          ${poRadarHealthLine('Mensagem', health.message || 'Sem mensagem', 'info')}
        </div>
        <div class="po-radar-section-title mt14">Alertas recentes</div>
        <div class="po-radar-list">${alerts.map(poRadarAlertItem).join('') || '<div class="po-empty">Sem alerta no filtro atual.</div>'}</div>
      </div>
    </div>
    <div class="po-radar-section-title mt14">Pontos de medição</div>
    <div class="tablewrap po-tablewrap mb14">
      <table class="table">
        <thead><tr><th>Data</th><th>Família</th><th>Tag</th><th>Fluido</th><th>Volume corr.</th><th>Pressão</th><th>Temperatura</th><th>Status</th></tr></thead>
        <tbody>${points.slice(0, 80).map((row) => `
          <tr><td class="mono">${fmtDate(row.date)}</td><td>${poTag(row.family)}</td><td>${poTag(row.tag)}</td><td>${escapeHtml(row.fluid || '')}</td><td class="num">${fmt(row.volumeCorrigido)}</td><td class="num">${fmt(row.pressao)}</td><td class="num">${fmt(row.temperatura)}</td><td>${poBadge(row.inRange ? 'Em faixa' : 'Atenção', row.inRange ? 'ok' : 'warn')}</td></tr>
        `).join('') || '<tr><td colspan="8" class="muted">Sem ponto para o filtro atual.</td></tr>'}</tbody>
      </table>
    </div>
    <div class="po-radar-section-title">Envelope de limites/PAM</div>
    <div class="po-radar-card-grid">${limits.map(poRadarLimitCard).join('') || '<div class="po-empty">Sem limite/PAM no filtro atual.</div>'}</div>
  `;
  renderPoRadarClosingChart(closing.length ? closing : data.closing || []);
}

function renderPoRadarTrilha(data) {
  const selectedDate = poEl('poRadarDate')?.value || poRadarLatestDate(data, data.comparisons || []);
  const comparisons = poRadarFilteredRows(data.comparisons || [], {date: selectedDate});
  poEl('poRadarBody').innerHTML = `
    <div class="po-radar-section-title">Trilha end-to-end ${fmtDate(selectedDate)}</div>
    <div class="po-radar-flow">
      ${poRadarFlowStep('Raw', comparisons.filter((row) => row.rawOk).length, 'CV/IHM/dados de origem')}
      ${poRadarFlowStep('XML', comparisons.filter((row) => row.xmlCorrigido !== null && row.xmlCorrigido !== undefined).length, 'pacote enviado')}
      ${poRadarFlowStep('Painel ANP', comparisons.filter((row) => row.anpOk).length, 'export recebido')}
      ${poRadarFlowStep('Radar', comparisons.length, 'comparação auditável')}
    </div>
    <div class="tablewrap po-tablewrap mt14">
      <table class="table">
        <thead><tr><th>Data</th><th>Família</th><th>Tag</th><th>Fluido</th><th>Raw</th><th>XML</th><th>ANP</th><th>Status</th><th>Fonte</th></tr></thead>
        <tbody>${comparisons.map((row) => `
          <tr><td class="mono">${fmtDate(row.date)}</td><td>${poTag(row.family)}</td><td>${poTag(row.tag)}</td><td>${escapeHtml(row.fluid || '')}</td><td class="num">${fmt(row.rawCorrigido)}</td><td class="num">${fmt(row.xmlCorrigido)}</td><td class="num">${fmt(row.anpCorrigido)}</td><td>${poBadge(poText(row.status), poStatusKind(row.status))}</td><td class="po-path-cell" title="${escapeHtml(row.xmlSource || row.rawSource || '')}">${escapeHtml((row.xmlSource || row.rawSource || '—').split(/[\\/]/).pop())}</td></tr>
        `).join('') || '<tr><td colspan="9" class="muted">Sem comparação para o filtro atual.</td></tr>'}</tbody>
      </table>
    </div>
  `;
}

function renderPoRadarCalendario(data) {
  const days = poRadarFilteredRows(data.operationalCalendar?.days || []);
  poEl('poRadarBody').innerHTML = `
    <div class="po-radar-section-title">Calendário operacional do Radar</div>
    <div class="po-calendar-board po-radar-calendar">
      ${days.map((row) => {
        const open = Number(row.openPendingCount || 0);
        const kind = row.loaded ? (open ? 'warn' : 'ok') : 'missing';
        return `<div class="po-calendar-day po-calendar-day--${kind}" title="${escapeHtml(row.status || '')}"><span>${escapeHtml(String(row.date || '').slice(8) || '—')}</span><strong>${row.loaded ? 'Carga' : 'Falta'}</strong><small>${poNum(open)} abertas</small></div>`;
      }).join('') || '<div class="po-empty">Sem dias no calendário.</div>'}
    </div>
    <div class="tablewrap po-tablewrap mt14">
      <table class="table">
        <thead><tr><th>Data</th><th>Status</th><th>Carga</th><th>Pontos</th><th>XML</th><th>Faltantes</th><th>Abertas</th><th>Resolvidas</th></tr></thead>
        <tbody>${days.map((row) => `<tr><td class="mono">${fmtDate(row.date)}</td><td>${poBadge(poText(row.status), poStatusKind(row.status))}</td><td>${row.loaded ? poBadge('Sim', 'ok') : poBadge('Não', 'err')}</td><td class="num">${poNum(row.points)}</td><td>${poListCell(row.xmlFamilies)}</td><td>${poListCell(row.missingXmlFamilies)}</td><td class="num">${poNum(row.openPendingCount)}</td><td class="num">${poNum(row.resolvedPendingCount)}</td></tr>`).join('') || '<tr><td colspan="8" class="muted">Sem dia para o filtro.</td></tr>'}</tbody>
      </table>
    </div>
  `;
}

function renderPoRadarPrazos(data) {
  const failures = data.failures || {};
  const matrixRows = data.regulatoryMatrix?.rows || [];
  const alerts = (data.alerts || []).filter((row) => ['Prazo', 'NFSM', 'Regulatório', 'regulatorio'].some((word) => JSON.stringify(row).toLowerCase().includes(word.toLowerCase())));
  poEl('poRadarBody').innerHTML = `
    <div class="po-radar-two-col">
      <div>
        <div class="po-radar-section-title">Falhas e prazos</div>
        <div class="po-status-grid">
          <div class="po-stage-count"><span>Falhas totais</span><strong>${poNum(failures.total)}</strong></div>
          <div class="po-stage-count"><span>Falhas abertas</span><strong>${poNum(failures.open)}</strong></div>
          <div class="po-stage-count"><span>Retornadas</span><strong>${poNum(failures.returned)}</strong></div>
        </div>
        <div class="po-radar-list mt14">${(failures.latestOpen || []).slice(0, 12).map((row) => `<div class="po-radar-list-item"><strong>${escapeHtml(row.title || row.failureType || 'Falha')}</strong><span>${escapeHtml(row.detail || row.status || '')}</span></div>`).join('') || '<div class="po-empty">Sem falha aberta no contrato.</div>'}</div>
      </div>
      <div>
        <div class="po-radar-section-title">Checklist regulatório</div>
        <div class="po-radar-list">${matrixRows.slice(0, 18).map((row) => `<div class="po-radar-list-item"><strong>${escapeHtml(row.ID || row.id || row.requirement_id || 'Requisito')}</strong><span>${escapeHtml(row['Requisito / Atividade'] || row.title || row.Categoria || JSON.stringify(row).slice(0, 160))}</span></div>`).join('') || '<div class="po-empty">Matriz regulatória não carregada.</div>'}</div>
      </div>
    </div>
    <div class="po-radar-section-title mt14">Alertas regulatórios</div>
    <div class="po-radar-list">${alerts.slice(0, 20).map(poRadarAlertItem).join('') || '<div class="po-empty">Sem alerta regulatório no filtro.</div>'}</div>
  `;
}

function renderPoRadarPropostas(data) {
  const rows = poRadarFilteredRows(data.changeProposals || []);
  poEl('poRadarBody').innerHTML = `
    <div class="po-radar-section-title">Fila de propostas auditáveis</div>
    <div class="tablewrap po-tablewrap">
      <table class="table">
        <thead><tr><th>Status</th><th>Risco</th><th>Domínio</th><th>Alvo</th><th>Campo</th><th>Atual</th><th>Proposto</th><th>Evidência/recomendação</th></tr></thead>
        <tbody>${rows.map((row) => `<tr><td>${poBadge(poText(row.status), poStatusKind(row.status))}</td><td>${poBadge(poText(row.risk), poStatusKind(row.risk === 'alto' ? 'critical' : row.risk))}</td><td>${escapeHtml(row.domain || '')}</td><td>${poTag(row.targetId)}</td><td>${escapeHtml(row.field || '')}</td><td class="po-path-cell">${escapeHtml(poJsonValue(row.currentValue))}</td><td class="po-path-cell">${escapeHtml(poJsonValue(row.proposedValue))}</td><td class="po-path-cell" title="${escapeHtml(row.evidenceText || row.recommendedAction || '')}">${escapeHtml(row.recommendedAction || row.evidenceText || '')}</td></tr>`).join('') || '<tr><td colspan="8" class="muted">Sem proposta para o filtro.</td></tr>'}</tbody>
      </table>
    </div>
  `;
}

function renderPoRadarConfig(data) {
  const sources = painelOperadorState.radarSources?.sources || [];
  const db = data.database || {};
  const ai = data.ai || {};
  poEl('poRadarBody').innerHTML = `
    <div class="po-radar-two-col">
      <div>
        <div class="po-radar-section-title">Fontes configuradas</div>
        <div class="po-radar-list">${sources.map((source) => `<div class="po-radar-list-item"><strong>${escapeHtml(source.label || source.id)}</strong><span>${escapeHtml((source.paths || []).join(' · ') || 'sem caminho')}</span></div>`).join('') || '<div class="po-empty">Fontes não carregadas.</div>'}</div>
      </div>
      <div>
        <div class="po-radar-section-title">Banco e IA</div>
        <div class="po-radar-health">
          ${poRadarHealthLine('SQLite Radar', db.path || 'n/d', 'info')}
          ${poRadarHealthLine('Tabelas', poNum(Object.keys(db.tableCounts || {}).length), 'info')}
          ${poRadarHealthLine('Modo IA', ai.mode || 'read-only', 'ok')}
          ${poRadarHealthLine('Princípio', ai.principle || 'proposta auditável antes de gravar', 'info')}
        </div>
      </div>
    </div>
  `;
}

function renderPoRadarPergunte(data) {
  poEl('poRadarBody').innerHTML = `
    <div class="po-radar-ask">
      <textarea id="poRadarAskInput" class="input" rows="4" placeholder="Pergunte sobre medições, falhas, XMLs, certificados, análises, normas, prazos ou dossiê de um ponto..."></textarea>
      <div class="po-filter-actions"><button class="btn sm" type="button" id="poRadarAskBtn">Perguntar</button></div>
      <div id="poRadarAskAnswer" class="po-radar-answer muted">A resposta usa o Assistente IA do MPFM com contexto do Painel do Operador/Radar ANP. Escritas continuam bloqueadas sem proposta e aprovação.</div>
    </div>
  `;
  poEl('poRadarAskBtn')?.addEventListener('click', poRadarAsk);
}

async function poRadarAsk() {
  const input = poEl('poRadarAskInput');
  const answer = poEl('poRadarAskAnswer');
  const question = String(input?.value || '').trim();
  if (!question) return;
  answer.textContent = 'Consultando o Radar...';
  try {
    const resp = await j(`${API}/ai/ask`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        question,
        include_app_context: true,
        app_context: {
          current_page: 'painel-operador',
          module: 'dashboard-anp-radar',
          radar_view: painelOperadorState.radarActiveView,
          filters: {
            date: poEl('poRadarDate')?.value || '',
            tag: poEl('poRadarTag')?.value || '',
          },
        },
      }),
    });
    answer.textContent = resp.content || 'Sem resposta.';
  } catch (err) {
    answer.textContent = `Erro ao consultar IA: ${err.message || err}`;
  }
}

function renderPoRadarDossie(data) {
  const tag = poEl('poRadarTag')?.value || (data.latestPoints || [])[0]?.tag || '';
  const point = (data.latestPoints || []).find((row) => row.tag === tag) || {};
  const comparisons = (data.comparisons || []).filter((row) => !tag || row.tag === tag).slice(0, 20);
  const limits = (data.limitMonitors || []).filter((row) => !tag || row.tag === tag);
  const uncertainties = (data.uncertaintyMonitor || []).filter((row) => !tag || row.tag === tag);
  const proposals = (data.changeProposals || []).filter((row) => !tag || row.targetId === tag);
  const events = (data.eventEvidenceRadar?.events || []).filter((row) => !tag || (row.tags || []).includes(tag) || String(row.parameter || '').includes(tag));
  poEl('poRadarBody').innerHTML = `
    <div class="po-radar-section-title">Dossiê do ponto ${poTag(tag)}</div>
    <div class="po-radar-dossier-grid">
      ${poRadarDossierCard('Cadastro', [`Família: ${point.family || 'n/d'}`, `Fluido: ${point.fluid || 'n/d'}`, `Medidor: ${point.meterType || 'n/d'}`, `CV: ${point.computadorVazao || 'n/d'}`])}
      ${poRadarDossierCard('Última medição', [`Data: ${fmtDate(point.date)}`, `Volume corr.: ${fmt(point.volumeCorrigido)}`, `Pressão: ${fmt(point.pressao)}`, `Temperatura: ${fmt(point.temperatura)}`])}
      ${poRadarDossierCard('Limites/PAM', [`Monitores: ${poNum(limits.length)}`, `Status: ${limits.map((row) => row.status).filter(Boolean).join(', ') || 'n/d'}`])}
      ${poRadarDossierCard('Incerteza', [`Linhas: ${poNum(uncertainties.length)}`, `Cobertura: ${uncertainties.map((row) => row.coverage).filter(Boolean).slice(0, 3).join(', ') || 'n/d'}`])}
      ${poRadarDossierCard('Eventos/evidências', [`Eventos: ${poNum(events.length)}`, `Propostas: ${poNum(proposals.length)}`])}
    </div>
    <div class="po-radar-section-title mt14">Histórico raw/XML/ANP</div>
    <div class="tablewrap po-tablewrap">
      <table class="table">
        <thead><tr><th>Data</th><th>Família</th><th>Raw</th><th>XML</th><th>ANP</th><th>Status</th><th>Fonte</th></tr></thead>
        <tbody>${comparisons.map((row) => `<tr><td class="mono">${fmtDate(row.date)}</td><td>${poTag(row.family)}</td><td class="num">${fmt(row.rawCorrigido)}</td><td class="num">${fmt(row.xmlCorrigido)}</td><td class="num">${fmt(row.anpCorrigido)}</td><td>${poBadge(poText(row.status), poStatusKind(row.status))}</td><td class="po-path-cell">${escapeHtml((row.xmlSource || row.rawSource || '—').split(/[\\/]/).pop())}</td></tr>`).join('') || '<tr><td colspan="7" class="muted">Sem histórico para o ponto.</td></tr>'}</tbody>
      </table>
    </div>
  `;
}

function poRadarHealthLine(label, value, kind = 'info') {
  return `<div class="po-stage-count"><span>${escapeHtml(label)}</span><strong class="po-health-value po-health-value--${kind}">${escapeHtml(String(value || '—'))}</strong></div>`;
}

function poRadarAlertItem(row) {
  return `<div class="po-radar-list-item"><strong>${escapeHtml(row.title || 'Alerta')}</strong><span>${fmtDate(row.date)} · ${escapeHtml(row.area || '')} · ${escapeHtml(row.detail || '')}</span></div>`;
}

function poRadarLimitCard(row) {
  return `<div class="po-radar-mini-card"><strong>${escapeHtml(row.tag || 'Ponto')}</strong><span>${escapeHtml(row.family || '')} · ${escapeHtml(row.fluid || '')}</span><small>PAM ${escapeHtml(poTechnicalRangeText(row.pam))}</small><small>Pressão ${escapeHtml(poTechnicalRangeText(row.pressure))}</small><em>${escapeHtml(row.status || 'n/d')}</em></div>`;
}

function poRadarFlowStep(label, count, detail) {
  return `<div class="po-radar-flow-step"><span>${escapeHtml(label)}</span><strong>${poNum(count)}</strong><small>${escapeHtml(detail)}</small></div>`;
}

function poRadarDossierCard(title, lines) {
  return `<div class="po-radar-mini-card"><strong>${escapeHtml(title)}</strong>${(lines || []).map((line) => `<span>${escapeHtml(line)}</span>`).join('')}</div>`;
}

function renderPoRadarClosingChart(rows) {
  const canvas = poEl('poRadarClosingChart');
  if (!canvas || !window.Chart) return;
  if (painelOperadorState.radarChart) {
    painelOperadorState.radarChart.destroy();
    painelOperadorState.radarChart = null;
  }
  const ordered = [...(rows || [])].sort((a, b) => String(a.date || '').localeCompare(String(b.date || '')));
  painelOperadorState.radarChart = new Chart(canvas.getContext('2d'), {
    type: 'line',
    data: {
      labels: ordered.map((row) => String(row.date || '').slice(5) || '—'),
      datasets: [
        {label: 'Óleo', data: ordered.map((row) => Number(row.totalOil || 0) || null), borderColor: '#22c55e', backgroundColor: 'transparent', borderWidth: 2, pointRadius: 2, spanGaps: true},
        {label: 'Gás', data: ordered.map((row) => Number(row.totalGas || 0) || null), borderColor: '#38bdf8', backgroundColor: 'transparent', borderWidth: 2, pointRadius: 2, spanGaps: true},
        {label: 'Críticos', data: ordered.map((row) => Number(row.critical || 0) || null), borderColor: '#ef4444', backgroundColor: 'transparent', borderWidth: 1, borderDash: [4, 3], pointRadius: 3, spanGaps: true},
      ],
    },
    options: {responsive: true, maintainAspectRatio: false},
  });
}

async function loadPainelOperadorChecklist() {
  const qs = poQuery({
    sheet_name: poEl('poChecklistSheet')?.value,
    date_from: poEl('poChecklistDateFrom')?.value,
    date_to: poEl('poChecklistDateTo')?.value,
    tag: poEl('poChecklistTag')?.value,
    q: poEl('poChecklistSearch')?.value,
    limit: 160,
  });
  const tankQs = poQuery({
    date_from: poEl('poChecklistDateFrom')?.value,
    date_to: poEl('poChecklistDateTo')?.value,
    q: poEl('poChecklistSearch')?.value,
    limit: 160,
  });
  const [summary, rows, tank, offspec, quality, mpfmFiscalOil, gasBalance] = await Promise.all([
    j(`${API}/painel-operador/daily-checklist-summary`),
    j(`${API}/painel-operador/daily-checklist?${qs}`),
    j(`${API}/painel-operador/tank-balance?${tankQs}`).catch((err) => ({error: err.message || String(err), summary: {}, items: [], trend: []})),
    j(`${API}/painel-operador/offspec-tank?${tankQs}`).catch((err) => ({error: err.message || String(err), summary: {}, items: [], trend: []})),
    j(`${API}/painel-operador/quality-samples?${tankQs}`).catch((err) => ({error: err.message || String(err), summary: {}, items: [], trend: [], api_weighted: {summary: {}, items: []}})),
    j(`${API}/painel-operador/mpfm-fiscal-oil?${tankQs}`).catch((err) => ({error: err.message || String(err), summary: {}, items: [], trend: []})),
    j(`${API}/painel-operador/gas-balance?${tankQs}`).catch((err) => ({error: err.message || String(err), summary: {}, items: [], trend: []})),
  ]);
  renderPainelOperadorChecklist(summary, rows);
  renderPainelOperadorTankBalance(tank);
  renderPainelOperadorOffspecTank(offspec);
  renderPainelOperadorQualitySamples(quality);
  renderPainelOperadorMpfmFiscalOil(mpfmFiscalOil);
  renderPainelOperadorGasBalance(gasBalance);
}

async function inspectPainelOperadorChecklist() {
  const path = poEl('poChecklistPath')?.value || '';
  if (!path.trim()) {
    poSetStatus('Informe o caminho do checklist diário.', 'warn');
    return;
  }
  const data = await poRunAction('Inspeção do checklist', () => j(`${API}/painel-operador/daily-checklist/inspect?${poQuery({path})}`));
  renderPainelOperadorChecklistInspect(data);
}

async function importPainelOperadorChecklist() {
  const path = poEl('poChecklistPath')?.value || '';
  if (!path.trim()) {
    poSetStatus('Informe o caminho do checklist diário.', 'warn');
    return;
  }
  await poRunAction('Importação do checklist', () => j(`${API}/painel-operador/daily-checklist/import`, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({path}),
  }));
  await loadPainelOperadorChecklist();
}

function renderPainelOperadorChecklist(summary, rows) {
  const latest = summary.latest_run || {};
  const totals = summary.totals || {};
  const sheetRows = summary.sheets || [];
  poFillSelectFromGroups('poChecklistSheet', sheetRows.map((row) => row.sheet_name));
  poEl('poChecklistSummary').innerHTML = `
    <div class="po-stage-count"><span>Importações</span><strong>${poNum(totals.runs)}</strong></div>
    <div class="po-stage-count"><span>Linhas checklist</span><strong>${poNum(totals.rows)}</strong></div>
    <div class="po-stage-count"><span>Abas importadas</span><strong>${poNum(sheetRows.length)}</strong></div>
    <div class="po-stage-count"><span>Última carga</span><strong>${latest.imported_at ? fmtDate(latest.imported_at) : '—'}</strong></div>
  `;
  poEl('poChecklistMeta').textContent = latest.source_file
    ? `Último arquivo: ${latest.source_file} · hash ${String(latest.file_hash || '').slice(0, 12)}`
    : 'Sem checklist importado no SQLite.';
  poEl('poChecklistSheetRows').innerHTML = sheetRows.map((row) => `
    <tr>
      <td>${escapeHtml(row.sheet_name || '')}</td>
      <td class="num">${poNum(row.rows_count)}</td>
      <td class="num">${poNum(row.date_count)}</td>
      <td class="mono">${fmtDate(row.first_date)} → ${fmtDate(row.last_date)}</td>
      <td>${escapeHtml(poChecklistSheetCoverage(row.sheet_name))}</td>
    </tr>
  `).join('') || '<tr><td colspan="5" class="muted">Nenhuma aba importada ainda.</td></tr>';
  poEl('poChecklistCoverageRows').innerHTML = renderPoCompactRows(poChecklistCoverageNotes(), (row) => `<strong>${escapeHtml(row.sheet)}</strong><span>${escapeHtml(row.note)}</span>`);
  poEl('poChecklistRowsMeta').textContent = `${poNum(rows.total)} linha(s) encontradas · exibindo ${poNum(rows.returned)}.`;
  poEl('poChecklistRows').innerHTML = (rows.items || []).map((row) => `
    <tr>
      <td class="mono">${fmtDate(row.record_date)}</td>
      <td>${escapeHtml(row.sheet_name || '')}</td>
      <td>${escapeHtml(row.record_domain || '')}</td>
      <td>${poTag(row.tag)}</td>
      <td>${row.status ? poBadge(row.status, poStatusKind(row.status)) : '<span class="muted">—</span>'}</td>
      <td class="po-path-cell" title="${escapeHtml(row.title || row.metric_name || '')}">${escapeHtml(row.title || row.metric_name || '')}</td>
      <td>${escapeHtml(row.responsible || '')}</td>
      <td class="num">${row.metric_value === null || row.metric_value === undefined ? '—' : fmt(row.metric_value)}</td>
    </tr>
  `).join('') || '<tr><td colspan="8" class="muted">Sem linhas para os filtros.</td></tr>';
}

function renderPainelOperadorTankBalance(data) {
  const summary = data.summary || {};
  const rows = data.items || [];
  const trend = data.trend || [];
  const host = poEl('poTankBalanceSummary');
  if (!host) return;
  host.innerHTML = data.error ? `
    <div class="po-stage-count"><span>Balanço Tank</span><strong>erro</strong></div>
    <div class="po-stage-count"><span>Detalhe</span><strong>${escapeHtml(data.error)}</strong></div>
  ` : `
    <div class="po-stage-count"><span>Dias Tank</span><strong>${poNum(summary.date_count)}</strong></div>
    <div class="po-stage-count"><span>Linhas Tank</span><strong>${poNum(summary.rows_count)}</strong></div>
    <div class="po-stage-count"><span>Delta fiscal-tanque</span><strong>${poNum(summary.total_fiscal_minus_tank_m3, 3)} m³</strong></div>
    <div class="po-stage-count"><span>Atenções</span><strong>${poNum(summary.attention_count)}</strong></div>
  `;
  poEl('poTankBalanceMeta').textContent = summary.first_date
    ? `Período ${fmtDate(summary.first_date)} → ${fmtDate(summary.last_date)} · comparando variação de tanque e medidor fiscal.`
    : 'Sem linhas normalizadas da aba Tank. Importe o checklist para materializar o balanço.';
  renderPainelOperadorTankBalanceChart(trend);
  poEl('poTankBalanceRows').innerHTML = rows.map((row) => `
    <tr class="${poRowClass(row.status)}">
      <td class="mono">${fmtDate(row.tank_date)}</td>
      <td class="num">${poMaybeNum(row.opening_gsv_m3, 3)}</td>
      <td class="num">${poMaybeNum(row.closing_gsv_m3, 3)}</td>
      <td class="num">${poMaybeNum(row.delta_tank_m3, 3)}</td>
      <td class="num">${poMaybeNum(row.fiscal_meter_gsv_m3, 3)}</td>
      <td class="num">${poMaybeNum(row.fiscal_minus_tank_m3, 3)}</td>
      <td>${poBadge(row.status || '—', poStatusKind(row.status))}</td>
      <td class="po-path-cell" title="${escapeHtml(row.measurement_failure || row.observations || '')}">${escapeHtml(row.measurement_failure || row.observations || '') || '<span class="muted">—</span>'}</td>
    </tr>
  `).join('') || '<tr><td colspan="8" class="muted">Sem dados Tank para os filtros.</td></tr>';
}

function renderPainelOperadorTankBalanceChart(rows) {
  const canvas = poEl('poTankBalanceChart');
  if (!canvas || typeof Chart === 'undefined') return;
  if (painelOperadorState.tankBalanceChart) {
    painelOperadorState.tankBalanceChart.destroy();
  }
  const ordered = [...(rows || [])].filter((row) => row.tank_date).slice(-45);
  painelOperadorState.tankBalanceChart = new Chart(canvas.getContext('2d'), {
    type: 'line',
    data: {
      labels: ordered.map((row) => fmtDate(row.tank_date)),
      datasets: [
        {label: 'Delta tanque m³', data: ordered.map((row) => Number(row.delta_tank_m3 || 0)), borderColor: '#22c55e', backgroundColor: 'rgba(34,197,94,.14)', borderWidth: 2, pointRadius: 2, tension: .25},
        {label: 'Medidor fiscal m³', data: ordered.map((row) => Number(row.fiscal_meter_gsv_m3 || 0)), borderColor: '#38bdf8', backgroundColor: 'rgba(56,189,248,.10)', borderWidth: 2, pointRadius: 2, tension: .25},
        {label: 'Diferença m³', data: ordered.map((row) => Number(row.fiscal_minus_tank_m3 || 0)), borderColor: '#f59e0b', backgroundColor: 'transparent', borderDash: [5, 4], borderWidth: 2, pointRadius: 2, tension: .25},
      ],
    },
    options: {responsive: true, maintainAspectRatio: false},
  });
}

function renderPainelOperadorOffspecTank(data) {
  const summary = data.summary || {};
  const rows = data.items || [];
  const trend = data.trend || [];
  const host = poEl('poOffspecTankSummary');
  if (!host) return;
  host.innerHTML = data.error ? `
    <div class="po-stage-count"><span>Off Spec</span><strong>erro</strong></div>
    <div class="po-stage-count"><span>Detalhe</span><strong>${escapeHtml(data.error)}</strong></div>
  ` : `
    <div class="po-stage-count"><span>Dias Offspec</span><strong>${poNum(summary.offspec_days)}</strong></div>
    <div class="po-stage-count"><span>Volume Offspec</span><strong>${poNum(summary.total_directed_volume_m3, 3)} m³</strong></div>
    <div class="po-stage-count"><span>Dias Reprocesso</span><strong>${poNum(summary.reprocess_days)}</strong></div>
    <div class="po-stage-count"><span>Pendentes</span><strong>${poNum(summary.pending_days)}</strong></div>
  `;
  poEl('poOffspecTankMeta').textContent = summary.first_date
    ? `Período ${fmtDate(summary.first_date)} → ${fmtDate(summary.last_date)} · produção desviada para offspec e reprocessamento operacional.`
    : 'Sem linhas normalizadas da aba Off Spec Tank. Importe o checklist para materializar os desvios.';
  renderPainelOperadorOffspecTankChart(trend);
  poEl('poOffspecTankRows').innerHTML = rows.map((row) => `
    <tr class="${poRowClass(row.status)}">
      <td class="mono">${fmtDate(row.offspec_date)}</td>
      <td class="num">${poMaybeNum(row.opening_gsv_m3, 3)}</td>
      <td class="num">${poMaybeNum(row.closing_gsv_m3, 3)}</td>
      <td class="num">${poMaybeNum(row.delta_tank_m3, 3)}</td>
      <td class="num">${poMaybeNum(row.directed_volume_m3, 3)}</td>
      <td class="num">${poMaybeNum(row.reprocessed_volume_m3, 3)}</td>
      <td>${poBadge(row.status || '—', poStatusKind(row.status))}</td>
      <td class="po-path-cell" title="${escapeHtml(row.note || '')}">${escapeHtml(row.note || '') || '<span class="muted">—</span>'}</td>
    </tr>
  `).join('') || '<tr><td colspan="8" class="muted">Sem dados Off Spec para os filtros.</td></tr>';
}

function renderPainelOperadorOffspecTankChart(rows) {
  const canvas = poEl('poOffspecTankChart');
  if (!canvas || typeof Chart === 'undefined') return;
  if (painelOperadorState.offspecTankChart) {
    painelOperadorState.offspecTankChart.destroy();
  }
  const ordered = [...(rows || [])].filter((row) => row.offspec_date).slice(-45);
  painelOperadorState.offspecTankChart = new Chart(canvas.getContext('2d'), {
    type: 'bar',
    data: {
      labels: ordered.map((row) => fmtDate(row.offspec_date)),
      datasets: [
        {label: 'Offspec m³', data: ordered.map((row) => Number(row.directed_volume_m3 || 0)), backgroundColor: 'rgba(245,158,11,.72)', borderColor: '#f59e0b', borderWidth: 1},
        {label: 'Reprocesso m³', data: ordered.map((row) => Number(row.reprocessed_volume_m3 || 0)), backgroundColor: 'rgba(56,189,248,.55)', borderColor: '#38bdf8', borderWidth: 1},
      ],
    },
    options: {responsive: true, maintainAspectRatio: false, scales: {x: {stacked: true}, y: {stacked: true}}},
  });
}

function renderPainelOperadorQualitySamples(data) {
  const summary = data.summary || {};
  const rows = data.items || [];
  const apiWeighted = data.api_weighted || {};
  const host = poEl('poQualitySummary');
  if (!host) return;
  host.innerHTML = data.error ? `
    <div class="po-stage-count"><span>Qualidade</span><strong>erro</strong></div>
    <div class="po-stage-count"><span>Detalhe</span><strong>${escapeHtml(data.error)}</strong></div>
  ` : `
    <div class="po-stage-count"><span>Amostras Lab</span><strong>${poNum(summary.rows_count)}</strong></div>
    <div class="po-stage-count"><span>API médio</span><strong>${poMaybeNum(summary.avg_api_gravity, 2)}</strong></div>
    <div class="po-stage-count"><span>Dens. média</span><strong>${poMaybeNum(summary.avg_density_kg_m3, 2)} kg/m³</strong></div>
    <div class="po-stage-count"><span>BSW médio</span><strong>${poMaybeNum(summary.avg_bsw_percent, 3)}%</strong></div>
  `;
  poEl('poQualityMeta').textContent = summary.first_date
    ? `Período ${fmtDate(summary.first_date)} → ${fmtDate(summary.last_date)} · Lab-Report/API materializados para qualidade do óleo.`
    : 'Sem amostras de qualidade normalizadas. Importe o checklist para materializar Lab-Report/API.';
  renderPainelOperadorQualityChart(data.trend || []);
  poEl('poQualityRows').innerHTML = rows.map((row) => `
    <tr class="${poRowClass(row.status)}">
      <td class="mono">${fmtDate(row.sample_date)}</td>
      <td>${escapeHtml(row.lab_report_id || '')}</td>
      <td class="num">${poMaybeNum(row.api_gravity, 3)}</td>
      <td class="num">${poMaybeNum(row.density_kg_m3, 3)}</td>
      <td class="num">${poMaybeNum(row.density_cv_g_cm3, 5)}</td>
      <td class="num">${poMaybeNum(row.bsw_percent, 4)}</td>
      <td>${escapeHtml(row.method || '') || '<span class="muted">—</span>'}</td>
      <td>${poBadge(row.status || '—', poStatusKind(row.status))}</td>
    </tr>
  `).join('') || '<tr><td colspan="8" class="muted">Sem amostras para os filtros.</td></tr>';
  const apiSummary = apiWeighted.summary || {};
  poEl('poApiWeightedMeta').textContent = `${poNum(apiSummary.rows_count)} linha(s) da aba API · ${apiSummary.first_date ? `${fmtDate(apiSummary.first_date)} → ${fmtDate(apiSummary.last_date)}` : 'sem período ponderado'}.`;
  poEl('poApiWeightedRows').innerHTML = (apiWeighted.items || []).map((row) => `
    <tr class="${poRowClass(row.status)}">
      <td class="mono">${fmtDate(row.api_date)}</td>
      <td class="num">${poMaybeNum(row.weighted_api, 3)}</td>
      <td class="num">${poMaybeNum(row.net_volume_m3, 3)}</td>
      <td class="num">${poMaybeNum(row.weighted_bsw_percent, 4)}</td>
      <td class="num">${poMaybeNum(row.total_volume_m3, 3)}</td>
      <td>${poBadge(row.status || '—', poStatusKind(row.status))}</td>
    </tr>
  `).join('') || '<tr><td colspan="6" class="muted">Sem resumo ponderado da aba API.</td></tr>';
}

function renderPainelOperadorQualityChart(rows) {
  const canvas = poEl('poQualityChart');
  if (!canvas || typeof Chart === 'undefined') return;
  if (painelOperadorState.qualityChart) {
    painelOperadorState.qualityChart.destroy();
  }
  const ordered = [...(rows || [])].filter((row) => row.sample_date).slice(-60);
  painelOperadorState.qualityChart = new Chart(canvas.getContext('2d'), {
    type: 'line',
    data: {
      labels: ordered.map((row) => fmtDate(row.sample_date)),
      datasets: [
        {label: 'API', data: ordered.map((row) => Number(row.api_gravity || 0) || null), borderColor: '#22c55e', backgroundColor: 'transparent', borderWidth: 2, pointRadius: 2, yAxisID: 'y'},
        {label: 'BSW %', data: ordered.map((row) => Number(row.bsw_percent || 0) || null), borderColor: '#f59e0b', backgroundColor: 'transparent', borderDash: [5, 4], borderWidth: 2, pointRadius: 2, yAxisID: 'y1'},
        {label: 'Densidade kg/m³', data: ordered.map((row) => Number(row.density_kg_m3 || 0) || null), borderColor: '#38bdf8', backgroundColor: 'transparent', borderWidth: 1, pointRadius: 1, yAxisID: 'y2'},
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        y: {type: 'linear', position: 'left'},
        y1: {type: 'linear', position: 'right', grid: {drawOnChartArea: false}},
        y2: {display: false},
      },
    },
  });
}

function renderPainelOperadorMpfmFiscalOil(data) {
  const summary = data.summary || {};
  const rows = data.items || [];
  const host = poEl('poMpfmFiscalOilSummary');
  if (!host) return;
  host.innerHTML = data.error ? `
    <div class="po-stage-count"><span>MPFM x Fiscal</span><strong>erro</strong></div>
    <div class="po-stage-count"><span>Detalhe</span><strong>${escapeHtml(data.error)}</strong></div>
  ` : `
    <div class="po-stage-count"><span>Dias comparados</span><strong>${poNum(summary.date_count)}</strong></div>
    <div class="po-stage-count"><span>Óleo fiscal</span><strong>${poNum(summary.total_fiscal_oil_m3, 3)} m³</strong></div>
    <div class="po-stage-count"><span>Óleo MPFM</span><strong>${poMaybeNum(summary.total_mpfm_oil_m3, 3)} m³</strong></div>
    <div class="po-stage-count"><span>Falhas/pendências</span><strong>${poNum(Number(summary.failure_count || 0) + Number(summary.pending_count || 0))}</strong></div>
  `;
  poEl('poMpfmFiscalOilMeta').textContent = summary.first_date
    ? `Período ${fmtDate(summary.first_date)} → ${fmtDate(summary.last_date)} · comparação óleo MPFM Subsea x fiscal preservada do checklist.`
    : 'Sem comparação MPFM Subsea x Fiscal-Óleo normalizada. Importe o checklist para materializar a aba.';
  renderPainelOperadorMpfmFiscalOilChart(data.trend || []);
  poEl('poMpfmFiscalOilRows').innerHTML = rows.map((row) => `
    <tr class="${poRowClass(row.status)}">
      <td class="mono">${fmtDate(row.production_date)}</td>
      <td class="num">${poMaybeNum(row.pe4_oil_m3, 3)}</td>
      <td class="num">${poMaybeNum(row.pe2_bank10_oil_m3, 3)}</td>
      <td class="num">${poMaybeNum(row.pe2_bank15_oil_m3, 3)}</td>
      <td class="num">${poMaybeNum(row.reprocess_oil_m3, 3)}</td>
      <td class="num">${poMaybeNum(row.total_mpfm_oil_m3, 3)}</td>
      <td class="num">${poMaybeNum(row.fiscal_oil_m3, 3)}</td>
      <td class="num">${poMaybeNum(row.variance_percent, 3)}</td>
      <td>${poBadge(row.status || '—', poStatusKind(row.status))}<br><span class="muted">${escapeHtml(row.source_status || '')}</span></td>
      <td class="po-path-cell" title="${escapeHtml(row.comment || '')}">${escapeHtml(row.comment || '') || '<span class="muted">—</span>'}</td>
    </tr>
  `).join('') || '<tr><td colspan="10" class="muted">Sem comparação MPFM x Fiscal para os filtros.</td></tr>';
}

function renderPainelOperadorMpfmFiscalOilChart(rows) {
  const canvas = poEl('poMpfmFiscalOilChart');
  if (!canvas || typeof Chart === 'undefined') return;
  if (painelOperadorState.mpfmFiscalOilChart) {
    painelOperadorState.mpfmFiscalOilChart.destroy();
  }
  const ordered = [...(rows || [])].filter((row) => row.production_date).slice(-60);
  painelOperadorState.mpfmFiscalOilChart = new Chart(canvas.getContext('2d'), {
    type: 'line',
    data: {
      labels: ordered.map((row) => fmtDate(row.production_date)),
      datasets: [
        {label: 'MPFM óleo m³', data: ordered.map((row) => Number(row.total_mpfm_oil_m3 || 0) || null), borderColor: '#22c55e', backgroundColor: 'transparent', borderWidth: 2, pointRadius: 2, spanGaps: true, yAxisID: 'y'},
        {label: 'Fiscal óleo m³', data: ordered.map((row) => Number(row.fiscal_oil_m3 || 0) || null), borderColor: '#38bdf8', backgroundColor: 'transparent', borderWidth: 2, pointRadius: 2, spanGaps: true, yAxisID: 'y'},
        {label: 'Desvio %', data: ordered.map((row) => Number(row.variance_percent || 0) || null), borderColor: '#f59e0b', backgroundColor: 'transparent', borderDash: [5, 4], borderWidth: 2, pointRadius: 2, spanGaps: true, yAxisID: 'y1'},
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        y: {type: 'linear', position: 'left'},
        y1: {type: 'linear', position: 'right', grid: {drawOnChartArea: false}},
      },
    },
  });
}

function renderPainelOperadorGasBalance(data) {
  const summary = data.summary || {};
  const rows = data.items || [];
  const host = poEl('poGasBalanceSummary');
  if (!host) return;
  host.innerHTML = data.error ? `
    <div class="po-stage-count"><span>Balanço gás</span><strong>erro</strong></div>
    <div class="po-stage-count"><span>Detalhe</span><strong>${escapeHtml(data.error)}</strong></div>
  ` : `
    <div class="po-stage-count"><span>Dias gás</span><strong>${poNum(summary.date_count)}</strong></div>
    <div class="po-stage-count"><span>Entradas operacionais</span><strong>${poNum(summary.total_operational_mm3, 3)} Mm³</strong></div>
    <div class="po-stage-count"><span>Fiscal + injeção</span><strong>${poNum(summary.total_fiscal_injection_mm3, 3)} Mm³</strong></div>
    <div class="po-stage-count"><span>Delta acumulado</span><strong>${poNum(summary.total_delta_mm3, 3)} Mm³</strong></div>
  `;
  poEl('poGasBalanceMeta').textContent = summary.first_date
    ? `Período ${fmtDate(summary.first_date)} → ${fmtDate(summary.last_date)} · entradas operacionais comparadas com saídas fiscais/injeção.`
    : 'Sem balanço de gás normalizado. Importe o checklist para materializar a aba Balanço de Gás.';
  renderPainelOperadorGasBalanceChart(data.trend || []);
  poEl('poGasBalanceRows').innerHTML = rows.map((row) => `
    <tr class="${poRowClass(row.status)}">
      <td class="mono">${fmtDate(row.gas_date)}</td>
      <td class="num">${poMaybeNum(row.operational_total_mm3, 3)}</td>
      <td class="num">${poMaybeNum(row.fiscal_injection_total_mm3, 3)}</td>
      <td class="num">${poMaybeNum(row.delta_mm3, 3)}</td>
      <td class="num">${poMaybeNum(row.delta_percent, 2)}</td>
      <td class="num">${poMaybeNum(row.hp_separator_mm3, 3)}</td>
      <td class="num">${poMaybeNum(row.test_separator_mm3, 3)}</td>
      <td class="num">${poMaybeNum(row.fwko_drum_mm3, 3)}</td>
      <td>${poBadge(row.status || '—', poStatusKind(row.status))}</td>
      <td class="po-path-cell" title="${escapeHtml(row.comment || '')}">${escapeHtml(row.comment || '') || '<span class="muted">—</span>'}</td>
    </tr>
  `).join('') || '<tr><td colspan="10" class="muted">Sem balanço de gás para os filtros.</td></tr>';
}

function renderPainelOperadorGasBalanceChart(rows) {
  const canvas = poEl('poGasBalanceChart');
  if (!canvas || typeof Chart === 'undefined') return;
  if (painelOperadorState.gasBalanceChart) {
    painelOperadorState.gasBalanceChart.destroy();
  }
  const ordered = [...(rows || [])].filter((row) => row.gas_date).slice(-60);
  painelOperadorState.gasBalanceChart = new Chart(canvas.getContext('2d'), {
    type: 'line',
    data: {
      labels: ordered.map((row) => fmtDate(row.gas_date)),
      datasets: [
        {label: 'Entradas operacionais Mm³', data: ordered.map((row) => Number(row.operational_total_mm3 || 0)), borderColor: '#22c55e', backgroundColor: 'transparent', borderWidth: 2, pointRadius: 2, tension: .25, yAxisID: 'y'},
        {label: 'Fiscal + injeção Mm³', data: ordered.map((row) => Number(row.fiscal_injection_total_mm3 || 0)), borderColor: '#38bdf8', backgroundColor: 'transparent', borderWidth: 2, pointRadius: 2, tension: .25, yAxisID: 'y'},
        {label: 'Delta %', data: ordered.map((row) => Number(row.delta_percent || 0)), borderColor: '#f59e0b', backgroundColor: 'transparent', borderDash: [5, 4], borderWidth: 2, pointRadius: 2, tension: .25, yAxisID: 'y1'},
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        y: {type: 'linear', position: 'left'},
        y1: {type: 'linear', position: 'right', grid: {drawOnChartArea: false}},
      },
    },
  });
}

function poMaybeNum(value, digits = 2) {
  return value === null || value === undefined || value === '' ? '—' : poNum(value, digits);
}

function poTechnicalRangePair(minValue, maxValue, unit = '') {
  const hasMin = minValue !== null && minValue !== undefined && minValue !== '';
  const hasMax = maxValue !== null && maxValue !== undefined && maxValue !== '';
  if (!hasMin && !hasMax) return '—';
  const suffix = unit ? ` ${unit}` : '';
  if (hasMin && hasMax) return `${poNum(minValue, 3)} a ${poNum(maxValue, 3)}${suffix}`;
  if (hasMin) return `mín. ${poNum(minValue, 3)}${suffix}`;
  return `máx. ${poNum(maxValue, 3)}${suffix}`;
}

function poConfiguredLimitPayload() {
  return {
    id: poEl('poLimitFormId')?.value || '',
    tag: poEl('poLimitFormTag')?.value || '',
    family: poEl('poLimitFormFamily')?.value || '',
    metric_name: poEl('poLimitFormMetric')?.value || '',
    value_unit: poEl('poLimitFormUnit')?.value || '',
    calibrated_min: poEl('poLimitFormCalMin')?.value || '',
    calibrated_max: poEl('poLimitFormCalMax')?.value || '',
    pam_min: poEl('poLimitFormPamMin')?.value || '',
    pam_max: poEl('poLimitFormPamMax')?.value || '',
    valid_from: poEl('poLimitFormValidFrom')?.value || '',
    valid_to: poEl('poLimitFormValidTo')?.value || '',
    approval_status: poEl('poLimitFormApproval')?.value || 'approved',
    active: poEl('poLimitFormActive')?.value || '1',
    source_type: poEl('poLimitFormSourceType')?.value || 'manual_approved',
    evidence_ref: poEl('poLimitFormEvidence')?.value || '',
    source_path: poEl('poLimitFormSource')?.value || '',
    notes: poEl('poLimitFormNotes')?.value || '',
  };
}

function poClearConfiguredLimitForm() {
  [
    'poLimitFormId', 'poLimitFormSourceType', 'poLimitFormTag', 'poLimitFormFamily', 'poLimitFormMetric', 'poLimitFormUnit',
    'poLimitFormCalMin', 'poLimitFormCalMax', 'poLimitFormPamMin', 'poLimitFormPamMax',
    'poLimitFormValidFrom', 'poLimitFormValidTo', 'poLimitFormEvidence', 'poLimitFormSource', 'poLimitFormNotes',
  ].forEach((id) => { const el = poEl(id); if (el) el.value = ''; });
  if (poEl('poLimitFormApproval')) poEl('poLimitFormApproval').value = 'approved';
  if (poEl('poLimitFormActive')) poEl('poLimitFormActive').value = '1';
  if (poEl('poLimitFormSourceType')) poEl('poLimitFormSourceType').value = 'manual_approved';
}

function poFillConfiguredLimitForm(row) {
  if (!row) return;
  const values = {
    poLimitFormId: row.id,
    poLimitFormTag: row.tag,
    poLimitFormFamily: row.family,
    poLimitFormMetric: row.metric_name,
    poLimitFormUnit: row.value_unit,
    poLimitFormSourceType: row.source_type || 'manual_approved',
    poLimitFormCalMin: row.calibrated_min,
    poLimitFormCalMax: row.calibrated_max,
    poLimitFormPamMin: row.pam_min,
    poLimitFormPamMax: row.pam_max,
    poLimitFormValidFrom: row.valid_from,
    poLimitFormValidTo: row.valid_to,
    poLimitFormApproval: row.approval_status || 'approved',
    poLimitFormActive: String(row.active ?? 1),
    poLimitFormEvidence: row.evidence_ref,
    poLimitFormSource: row.source_path,
    poLimitFormNotes: row.notes,
  };
  Object.entries(values).forEach(([id, value]) => {
    const el = poEl(id);
    if (el) el.value = value === null || value === undefined ? '' : String(value);
  });
  poEl('poLimitFormTag')?.focus();
}

async function poSaveConfiguredLimit() {
  const payload = poConfiguredLimitPayload();
  await poRunAction('Parametrização de limite/PAM', () => j(`${API}/painel-operador/measurement-limits`, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(payload),
  }));
  poClearConfiguredLimitForm();
  if (painelOperadorState.activeTab === 'technical') await loadPainelOperadorTechnical();
}

function poRowClass(status) {
  const kind = poStatusKind(status);
  if (kind === 'ok') return 'row-ok';
  if (kind === 'err') return 'row-err';
  if (kind === 'warn') return 'row-warn';
  return '';
}

function renderPainelOperadorChecklistInspect(data) {
  const sheets = data.sheets || [];
  const critical = sheets.filter((row) => row.default_import);
  poFillSelectFromGroups('poChecklistSheet', critical.map((row) => row.name));
  poEl('poChecklistSummary').innerHTML = `
    <div class="po-stage-count"><span>Abas no arquivo</span><strong>${poNum(data.sheet_count)}</strong></div>
    <div class="po-stage-count"><span>Abas críticas</span><strong>${poNum(data.critical_sheet_count)}</strong></div>
    <div class="po-stage-count"><span>Abas XML-ref</span><strong>${poNum(data.xml_reference_sheet_count)}</strong></div>
    <div class="po-stage-count"><span>Tamanho</span><strong>${poBytes(data.size_bytes)}</strong></div>
  `;
  poEl('poChecklistMeta').textContent = `Arquivo inspecionado: ${data.source_file} · hash ${String(data.file_hash || '').slice(0, 12)}.`;
  poEl('poChecklistSheetRows').innerHTML = critical.map((row) => `
    <tr>
      <td>${escapeHtml(row.name || '')}</td>
      <td class="num">${poNum(row.max_row)}</td>
      <td class="num">${poNum(row.non_empty_cells)}</td>
      <td>${poNum(row.formula_cells)} fórmula(s)</td>
      <td>${escapeHtml(poChecklistSheetCoverage(row.name))}</td>
    </tr>
  `).join('') || '<tr><td colspan="5" class="muted">Nenhuma aba crítica reconhecida.</td></tr>';
  poEl('poChecklistCoverageRows').innerHTML = renderPoCompactRows(data.coverage || poChecklistCoverageNotes(), (row) => `<strong>${escapeHtml(row.sheet)}</strong><span>${escapeHtml(row.note)}</span>`);
}

function poChecklistCoverageNotes() {
  return [
    {sheet: 'Ocurrences', note: 'Tratativas, NFSM, SAP, responsável e ação executada; XML não substitui.'},
    {sheet: 'Lab-Report/API', note: 'API, densidade e BSW entram como análise/qualidade e apoiam volume ponderado.'},
    {sheet: 'Tank/Off Spec', note: 'Balanço tanque x medidor fiscal e motivo operacional precisam de ingestão própria.'},
    {sheet: 'MPFM Subsea x Fiscal-Óleo', note: 'A aplicação já tem MPFM e fiscal; falta preservar a comparação e comentários do checklist.'},
    {sheet: 'Balanço de Gás', note: 'Recriar entradas operacionais x saídas fiscais/injeção em gráfico contínuo.'},
  ];
}

function poChecklistSheetCoverage(sheet) {
  const value = String(sheet || '');
  if (value.includes('Ocurr')) return 'importar como ocorrência/tratativa';
  if (value.includes('Lab') || value === 'API') return 'parcial: análises + volumes';
  if (value.includes('Tank')) return 'importar para balanço de tanques';
  if (value.includes('MPFM')) return 'comparação MPFM x fiscal';
  if (value.includes('Gás')) return 'balanço operacional x fiscal';
  if (value.endsWith('-Fx')) return 'faixa/PAM por medidor';
  if (/^\d{2}d?$/.test(value)) return 'verificação diária consolidada';
  return 'referência';
}

async function loadPainelOperadorTechnical() {
  const qs = poQuery({
    date_from: poEl('poTechnicalDateFrom')?.value,
    date_to: poEl('poTechnicalDateTo')?.value,
    family: poEl('poTechnicalFamily')?.value,
    tag: poEl('poTechnicalTag')?.value,
    limit: 120,
  });
  const data = await j(`${API}/painel-operador/technical-monitor?${qs}`);
  const summary = data.summary || {};
  const registryTables = data.registry?.tables || {};
  const limitRows = data.limit_monitors || [];
  const uncertaintyRows = data.uncertainty_monitor || [];
  const cvFiles = data.cv_files?.files || [];
  const eventChanges = data.event_changes || [];
  const persistedChanges = data.persisted_changes || [];
  const checklistRanges = data.checklist_ranges || [];
  const configuredLimits = data.configured_limits || [];
  const cvDiagnostics = data.cv_diagnostics || {};
  painelOperadorState.configuredLimits = configuredLimits;
  const configuredRows = registryTables.painel_operador_measurement_limits?.rows || 0;
  const snapshotRows = registryTables.painel_operador_cv_config_snapshots?.rows || 0;
  poEl('poTechnicalSummary').innerHTML = `
    <div class="po-stage-count"><span>Limites Radar</span><strong>${poNum(summary.limit_monitors)}</strong></div>
    <div class="po-stage-count"><span>Limites cadastrados</span><strong>${poNum(configuredRows)}</strong></div>
    <div class="po-stage-count"><span>Faixas checklist</span><strong>${poNum(summary.checklist_ranges)}</strong></div>
    <div class="po-stage-count"><span>Snapshots CV</span><strong>${poNum(snapshotRows)}</strong></div>
    <div class="po-stage-count"><span>Diffs CV</span><strong>${poNum(summary.cv_changed_pairs || summary.persisted_changes)}</strong></div>
    <div class="po-stage-count"><span>Incerteza</span><strong>${poNum(summary.uncertainty_rows)}</strong></div>
    <div class="po-stage-count"><span>Dias tendência</span><strong>${poNum(summary.trend_days)}</strong></div>
  `;
  poEl('poTechnicalMeta').textContent = `${poText(data.parameterization?.module)} · cadastro técnico em painel_operador_measurement_limits; snapshots CV em painel_operador_cv_config_snapshots.`;
  poEl('poConfiguredLimitMeta').textContent = `${poNum(configuredLimits.length)} limite(s) parametrizado(s) no SQLite; registros manuais são preservados ao reprocessar Limites/CV.`;
  poEl('poConfiguredLimitRows').innerHTML = configuredLimits.map((row) => `
    <tr class="${Number(row.active || 0) ? '' : 'row-warn'}">
      <td>${poTag(row.tag)}</td>
      <td><strong>${escapeHtml(row.metric_name || '')}</strong><br><span class="muted">${escapeHtml(row.value_unit || '')}</span></td>
      <td class="po-path-cell">${escapeHtml(poTechnicalRangePair(row.calibrated_min, row.calibrated_max, row.value_unit || ''))}</td>
      <td class="po-path-cell">${escapeHtml(poTechnicalRangePair(row.pam_min, row.pam_max, row.value_unit || ''))}</td>
      <td class="po-path-cell">${escapeHtml(fmtDate(row.valid_from))} → ${escapeHtml(fmtDate(row.valid_to))}</td>
      <td>${poBadge(Number(row.active || 0) ? poText(row.approval_status) : 'inativo', poStatusKind(Number(row.active || 0) ? row.approval_status : 'review'))}</td>
      <td class="po-path-cell" title="${escapeHtml(row.evidence_ref || row.source_path || '')}">${escapeHtml(row.evidence_ref || row.source_path || '—')}</td>
      <td><button class="btn secondary sm" type="button" data-po-limit-id="${escapeHtml(row.id)}">Editar</button></td>
    </tr>
  `).join('') || '<tr><td colspan="8" class="muted">Sem limite aprovado parametrizado para o filtro.</td></tr>';
  renderPainelOperadorTechnicalRadar(data);
  renderPainelOperadorTechnicalChart(data.trend || []);
  poEl('poLimitMeta').textContent = `${poNum(limitRows.length)} monitor(es) de faixa/PAM gerados pelo Radar.`;
  poEl('poLimitRows').innerHTML = limitRows.map((row) => `
    <tr>
      <td class="mono">${fmtDate(row.date)}</td>
      <td>${poTag(row.family)}</td>
      <td>${poTag(row.tag)}</td>
      <td>${escapeHtml(row.fluid || '')}</td>
      <td class="po-path-cell">${escapeHtml(poTechnicalRangeText(row.pam))}</td>
      <td class="po-path-cell">${escapeHtml(poTechnicalRangeText(row.pressure))}</td>
      <td class="po-path-cell">${escapeHtml(poTechnicalRangeText(row.temperature))}</td>
      <td>${poBadge(poText(row.status), poStatusKind(row.status))}</td>
    </tr>
  `).join('') || '<tr><td colspan="8" class="muted">Sem monitor de limite/PAM para o filtro.</td></tr>';

  const changedChecklistRanges = checklistRanges.filter((row) => row.range_changed).length;
  poEl('poFxRangeMeta').textContent = `${poNum(checklistRanges.length)} faixa(s) das abas *-Fx do checklist · ${poNum(changedChecklistRanges)} mudança(s) entre dias do mesmo medidor.`;
  poEl('poFxRangeRows').innerHTML = checklistRanges.map((row) => `
    <tr class="${poRowClass(row.status)}">
      <td class="mono">${fmtDate(row.date)}</td>
      <td>${poTag(row.tag)}</td>
      <td class="po-path-cell">${escapeHtml(poTechnicalRangePair(row.pressure_min, row.pressure_max, 'kPa'))}</td>
      <td class="po-path-cell">${escapeHtml(poTechnicalRangePair(row.temperature_min, row.temperature_max, '°C'))}</td>
      <td class="po-path-cell">${escapeHtml(poTechnicalRangePair(row.qcorr_min, row.qcorr_max, ''))}</td>
      <td class="po-path-cell">${escapeHtml(poTechnicalRangePair(row.bsw_min, row.bsw_max, '%'))}</td>
      <td>${row.range_changed ? poBadge(`desde ${fmtDate(row.previous_date)}`, 'warn') : poBadge('sem alteração', 'ok')}</td>
      <td class="po-path-cell" title="${escapeHtml(row.comment || '')}">${escapeHtml(row.comment || '') || '<span class="muted">—</span>'}</td>
    </tr>
  `).join('') || '<tr><td colspan="8" class="muted">Sem faixas *-Fx do checklist para o filtro.</td></tr>';

  const cvRows = [
    ...persistedChanges.map((row) => ({kind: 'Diff diário CV', date: row.current_date, tag: row.flow_computer || row.tag, name: `${row.parameter_name}: ${row.previous_value} -> ${row.current_value}`, status: row.severity || row.change_type || ''})),
    ...eventChanges.map((row) => ({kind: 'Evento CV', date: row.timestamp, tag: (row.tags || [])[0] || row.flowComputer || '', name: row.parameter, status: row.status || row.evidenceState || ''})),
    ...cvFiles.slice(0, Math.max(0, 80 - eventChanges.length)).map((row) => ({kind: row.document_kind, date: row.inferred_date, tag: row.inferred_tag, name: row.filename, status: row.file_hash ? 'hash' : 'catalogado'})),
  ].slice(0, 80);
  const cvComparisonText = Number(cvDiagnostics.compared_pairs || 0)
    ? `${poNum(cvDiagnostics.compared_pairs)} comparação(ões) de snapshot · ${poNum(cvDiagnostics.changed_pairs)} alteração(ões) detectada(s)`
    : 'comparação de snapshot ainda sem pares suficientes';
  poEl('poCvMeta').textContent = `${poNum(snapshotRows)} snapshot(s) de parâmetro · ${cvComparisonText} · ${poNum(eventChanges.length)} evento(s) de alteração.`;
  poEl('poCvRows').innerHTML = cvRows.map((row) => `
    <tr>
      <td class="mono">${fmtDate(row.date)}</td>
      <td>${escapeHtml(row.kind || '')}</td>
      <td>${poTag(row.tag)}</td>
      <td class="po-path-cell" title="${escapeHtml(row.name || '')}">${escapeHtml(row.name || '')}</td>
      <td>${row.status ? poBadge(poText(row.status), poStatusKind(row.status)) : '<span class="muted">—</span>'}</td>
    </tr>
  `).join('') || '<tr><td colspan="5" class="muted">Sem arquivo ou alteração CV para o filtro.</td></tr>';

  poEl('poUncertaintyMeta').textContent = `${poNum(uncertaintyRows.length)} linha(s) de incerteza/cobertura.`;
  poEl('poUncertaintyRows').innerHTML = uncertaintyRows.map((row) => `
    <tr>
      <td class="mono">${fmtDate(row.date)}</td>
      <td>${poTag(row.family)}</td>
      <td>${poTag(row.tag)}</td>
      <td class="num">${fmt(row.uncertaintyMax)}</td>
      <td class="num">${fmt(row.dailyUncertainty)}</td>
      <td>${escapeHtml(row.coverage || '')}</td>
      <td>${poBadge(poText(row.status), poStatusKind(row.status))}</td>
      <td class="po-path-cell" title="${escapeHtml(row.source || '')}">${escapeHtml((row.source || '').split(/[\\/]/).pop() || '—')}</td>
    </tr>
  `).join('') || '<tr><td colspan="8" class="muted">Sem incerteza para o filtro.</td></tr>';
}

function poIsRiskStatus(status) {
  const value = String(status || '').toLowerCase();
  if (!value) return false;
  return !['ok', 'loaded', 'resolved', 'matched', 'closed', 'valid', 'valido', 'hash', 'catalogado', 'in_range'].includes(value);
}

function poPercent(part, total) {
  const denominator = Number(total || 0);
  if (!denominator) return 0;
  return Math.max(0, Math.min(100, Math.round((Number(part || 0) / denominator) * 100)));
}

function poRadarCard(title, value, detail, percent, kind = 'info') {
  return `
    <div class="po-radar-card po-radar-card--${kind}">
      <div class="po-radar-card__top"><span>${escapeHtml(title)}</span><strong>${escapeHtml(String(value))}</strong></div>
      <div class="po-health-meter" aria-hidden="true"><i style="width:${poPercent(percent, 100)}%"></i></div>
      <small>${escapeHtml(detail)}</small>
    </div>
  `;
}

function renderPainelOperadorTechnicalRadar(data) {
  const host = poEl('poTechnicalRadar');
  if (!host) return;
  const limitRows = data.limit_monitors || [];
  const uncertaintyRows = data.uncertainty_monitor || [];
  const eventChanges = data.event_changes || [];
  const persistedChanges = data.persisted_changes || [];
  const proposals = data.change_proposals || [];
  const rules = data.rules || [];
  const limitRisk = limitRows.filter((row) => poIsRiskStatus(row.status)).length;
  const uncertaintyRisk = uncertaintyRows.filter((row) => poIsRiskStatus(row.status)).length;
  const changes = eventChanges.length + persistedChanges.length;
  const pendingProposals = proposals.filter((row) => !['authorized', 'rejected', 'resolved'].includes(String(row.status || '').toLowerCase())).length;
  const guardrails = data.parameterization?.guardrails || [];
  host.innerHTML = `
    ${poRadarCard('Faixa/PAM em atenção', poNum(limitRisk), `${poNum(limitRows.length)} monitores avaliados`, poPercent(limitRisk, Math.max(limitRows.length, 1)), limitRisk ? 'warn' : 'ok')}
    ${poRadarCard('Incerteza em atenção', poNum(uncertaintyRisk), `${poNum(uncertaintyRows.length)} linhas de cobertura`, poPercent(uncertaintyRisk, Math.max(uncertaintyRows.length, 1)), uncertaintyRisk ? 'warn' : 'ok')}
    ${poRadarCard('Mudanças CV/eventos', poNum(changes), `${poNum(persistedChanges.length)} diffs persistidos · ${poNum(eventChanges.length)} eventos`, Math.min(changes * 8, 100), changes ? 'info' : 'ok')}
    ${poRadarCard('Propostas pendentes', poNum(pendingProposals), `${poNum(proposals.length)} propostas técnicas rastreadas`, poPercent(pendingProposals, Math.max(proposals.length, 1)), pendingProposals ? 'bad' : 'ok')}
    <div class="po-radar-card po-radar-card--rules">
      <div class="po-radar-card__top"><span>Base de regra</span><strong>${poNum(rules.length)}</strong></div>
      <small>${escapeHtml((guardrails[0] || 'Regras técnicas ficam no SQLite e propostas exigem aprovação.'))}</small>
    </div>
  `;
}

function poTechnicalRangeText(value) {
  if (value === null || value === undefined || value === '') return '—';
  if (typeof value === 'object') {
    const parts = [];
    ['min', 'max', 'low', 'high', 'value', 'unit'].forEach((key) => {
      if (value[key] !== undefined && value[key] !== null && value[key] !== '') parts.push(`${key}: ${value[key]}`);
    });
    return parts.length ? parts.join(' · ') : JSON.stringify(value);
  }
  return String(value);
}

function renderPainelOperadorTechnicalChart(rows) {
  const canvas = poEl('poTechnicalTrendChart');
  if (!canvas || !window.Chart) return;
  if (painelOperadorState.technicalChart) {
    painelOperadorState.technicalChart.destroy();
    painelOperadorState.technicalChart = null;
  }
  const ordered = [...(rows || [])].sort((a, b) => String(a.measurement_date || '').localeCompare(String(b.measurement_date || '')));
  const labels = ordered.map((row) => String(row.measurement_date || '').slice(5) || '—');
  const fiscal = ordered.map((row) => Number(row.fiscal_volume_m3 || 0) || null);
  const anp = ordered.map((row) => Number(row.anp_volume_m3 || 0) || null);
  const mpfm = ordered.map((row) => Number(row.mpfm_corr_hc_t || 0) || null);
  const markers = ordered.map((row) => Number(row.config_change_count || 0) + Number(row.limit_alert_count || 0) + Number(row.out_of_range_points || 0));
  painelOperadorState.technicalChart = new Chart(canvas.getContext('2d'), {
    type: 'line',
    data: {
      labels,
      datasets: [
        {label: 'Fiscal/Radar m3', data: fiscal, borderColor: '#38bdf8', backgroundColor: 'transparent', borderWidth: 2, pointRadius: 2, spanGaps: true},
        {label: 'Export ANP m3', data: anp, borderColor: '#22c55e', backgroundColor: 'transparent', borderWidth: 2, pointRadius: 2, spanGaps: true},
        {label: 'MPFM HC t', data: mpfm, borderColor: '#f59e0b', backgroundColor: 'transparent', borderWidth: 2, pointRadius: 2, spanGaps: true},
        {label: 'Mudanças/alertas', data: markers, borderColor: '#ef4444', backgroundColor: 'transparent', borderWidth: 1, borderDash: [4, 3], pointRadius: 3, spanGaps: true},
      ],
    },
    options: {responsive: true, maintainAspectRatio: false},
  });
}

function poListCell(value) {
  if (Array.isArray(value)) return value.length ? value.map((item) => poTag(item)).join(' ') : '<span class="muted">—</span>';
  if (!value) return '<span class="muted">—</span>';
  try {
    const parsed = JSON.parse(value);
    if (Array.isArray(parsed)) return parsed.length ? parsed.map((item) => poTag(item)).join(' ') : '<span class="muted">—</span>';
  } catch {
    return escapeHtml(String(value));
  }
  return escapeHtml(String(value));
}

function poJsonValue(value) {
  if (value === null || value === undefined || value === '') return '—';
  let parsed = value;
  if (typeof value === 'string') {
    try {
      parsed = JSON.parse(value);
    } catch {
      return value;
    }
  }
  if (parsed === null || parsed === undefined || parsed === '') return '—';
  if (typeof parsed === 'object') return Object.entries(parsed).map(([key, val]) => `${key}: ${val}`).join(' · ');
  return String(parsed);
}

async function loadPainelOperadorCompare() {
  const qs = poQuery({
    family: poEl('poCompareFamily')?.value,
    record_kind: poEl('poCompareKind')?.value,
    status: poEl('poCompareStatus')?.value,
    tag: poEl('poCompareTag')?.value,
    date_from: poEl('poCompareDateFrom')?.value,
    date_to: poEl('poCompareDateTo')?.value,
    limit: 120,
  });
  const data = await j(`${API}/painel-operador/anp-comparison?${qs}`);
  poEl('poCompareMeta').textContent = `${poNum(data.total)} comparação(ões) ANP x Dados processados · exibindo ${poNum(data.returned)} · tolerância ${fmt(data.tolerance)}.`;
  poEl('poCompareSummary').innerHTML = (data.summary || []).map((row) => `
    <div class="po-stage-count">
      <span>${escapeHtml(poCompareStatusLabel(row.match_status))}</span>
      <strong>${poNum(row.count)}</strong>
    </div>
  `).join('') || '<div class="po-empty">Sem resumo para os filtros atuais.</div>';
  poEl('poCompareRows').innerHTML = (data.items || []).map((row) => `
    <tr>
      <td class="mono">${fmtDate(row.reference_date)}</td>
      <td>${poTag(row.family)}</td>
      <td>${poTag(row.tag)}</td>
      <td>${escapeHtml(row.record_kind || 'staging')}</td>
      <td>${poBadge(poCompareStatusLabel(row.match_status), poCompareStatusKind(row.match_status))}</td>
      <td class="num">${fmt(row.anp_value)}</td>
      <td class="num">${fmt(row.staging_value)}</td>
      <td class="num">${fmt(row.delta)}</td>
      <td class="po-path-cell" title="${escapeHtml(row.source_path || '')}">${escapeHtml(row.source_file || row.staging_note || '—')}</td>
    </tr>
  `).join('') || '<tr><td colspan="9" class="muted">Nenhuma comparação encontrada para os filtros.</td></tr>';
}

async function loadPainelOperadorCalendar() {
  const common = {
    date_from: poEl('poCalendarDateFrom')?.value,
    date_to: poEl('poCalendarDateTo')?.value,
  };
  const calendarQs = poQuery({
    ...common,
    status: poEl('poCalendarStatus')?.value,
    loaded: poEl('poCalendarLoaded')?.value,
    limit: 90,
  });
  const pendencyQs = poQuery({
    ...common,
    status: poEl('poPendencyStatus')?.value,
    severity: poEl('poPendencySeverity')?.value,
    limit: 120,
  });
  const [calendar, pendencies] = await Promise.all([
    j(`${API}/painel-operador/staging/calendar?${calendarQs}`),
    j(`${API}/painel-operador/staging/pendencies?${pendencyQs}`),
  ]);
  const days = calendar.items || [];
  const openCount = days.reduce((sum, row) => sum + Number(row.open_pending_count || 0), 0);
  const resolvedCount = days.reduce((sum, row) => sum + Number(row.resolved_pending_count || 0), 0);
  const loadedCount = days.filter((row) => Number(row.loaded || 0) === 1).length;
  poEl('poCalendarSummary').innerHTML = `
    <div class="po-stage-count"><span>Dias exibidos</span><strong>${poNum(calendar.returned)}</strong></div>
    <div class="po-stage-count"><span>Com carga</span><strong>${poNum(loadedCount)}</strong></div>
    <div class="po-stage-count"><span>Pendências abertas</span><strong>${poNum(openCount)}</strong></div>
    <div class="po-stage-count"><span>Pendências resolvidas</span><strong>${poNum(resolvedCount)}</strong></div>
  `;
  poEl('poCalendarMeta').textContent = `${poNum(calendar.total)} dia(s) operacionais · exibindo ${poNum(calendar.returned)}.`;
  poEl('poPendencyMeta').textContent = `${poNum(pendencies.total)} pendência(s) do calendário · exibindo ${poNum(pendencies.returned)}.`;
  renderPainelOperadorCalendarBoard(days, pendencies.items || []);
  poEl('poCalendarRows').innerHTML = days.map((row) => `
    <tr>
      <td class="mono">${fmtDate(row.calendar_date)}</td>
      <td>${poBadge(poText(row.status), poStatusKind(row.status))}</td>
      <td>${Number(row.loaded || 0) ? poBadge('Com carga', 'ok') : poBadge('Sem carga', 'err')}</td>
      <td class="num">${poNum(row.points_count)}</td>
      <td>${poListCell(row.xml_families_json)}</td>
      <td>${poListCell(row.missing_xml_families_json)}</td>
      <td class="num">${poNum(row.open_pending_count)}</td>
      <td class="num">${poNum(row.resolved_pending_count)}</td>
    </tr>
  `).join('') || '<tr><td colspan="8" class="muted">Nenhum dia operacional encontrado para os filtros.</td></tr>';
  poEl('poPendencyRows').innerHTML = (pendencies.items || []).map((row) => `
    <tr>
      <td class="mono">${fmtDate(row.calendar_date)}</td>
      <td>${poTag(row.pendency_id)}</td>
      <td>${escapeHtml(row.pendency_type || '')}</td>
      <td>${poBadge(poText(row.severity), poStatusKind(row.severity))}</td>
      <td>${poBadge(poText(row.status), poStatusKind(row.status))}</td>
      <td class="po-path-cell" title="${escapeHtml(row.detail || '')}">${escapeHtml(row.title || '')}</td>
      <td class="po-path-cell" title="${escapeHtml(row.recommended_action || '')}">${escapeHtml(row.recommended_action || '')}</td>
      <td>${poPendencyDecisionActions(row)}</td>
    </tr>
  `).join('') || '<tr><td colspan="8" class="muted">Nenhuma pendência encontrada para os filtros.</td></tr>';
}

function renderPainelOperadorCalendarBoard(days, pendencies) {
  const host = poEl('poCalendarBoard');
  if (!host) return;
  const pendencyByDate = (pendencies || []).reduce((acc, row) => {
    const date = String(row.calendar_date || '');
    if (!date) return acc;
    acc[date] = acc[date] || {total: 0, open: 0, critical: 0};
    acc[date].total += 1;
    if (String(row.status || '').toLowerCase() !== 'resolved') acc[date].open += 1;
    if (['critical', 'alta', 'alto'].includes(String(row.severity || '').toLowerCase())) acc[date].critical += 1;
    return acc;
  }, {});
  const ordered = [...(days || [])].sort((a, b) => String(a.calendar_date || '').localeCompare(String(b.calendar_date || '')));
  host.innerHTML = ordered.map((row) => {
    const date = String(row.calendar_date || '');
    const pend = pendencyByDate[date] || {};
    const loaded = Number(row.loaded || 0) === 1;
    const open = Number(row.open_pending_count || pend.open || 0);
    const kind = !loaded ? 'missing' : (open ? 'warn' : 'ok');
    const title = `${date} · ${poText(row.status)} · abertas ${poNum(open)}`;
    return `
      <div class="po-calendar-day po-calendar-day--${kind}" title="${escapeHtml(title)}">
        <span>${escapeHtml(date.slice(8) || '—')}</span>
        <strong>${loaded ? 'Carga' : 'Falta'}</strong>
        <small>${poNum(open)} abertas</small>
      </div>
    `;
  }).join('') || '<div class="po-empty">Sem dias para montar o calendário visual.</div>';
}

function poPendencyDecisionActions(row) {
  const id = row.id || row.pendency_id;
  const status = String(row.status || '').toLowerCase();
  if (!id) return '<span class="muted">—</span>';
  if (['resolved', 'deferred', 'ignored'].includes(status)) return `<span class="muted">${escapeHtml(poText(status))}</span>`;
  return `
    <div class="po-decision-actions">
      <button class="btn sm secondary" type="button" data-po-pendency-id="${escapeHtml(String(id))}" data-po-pendency-status="resolved">Baixar</button>
      <button class="btn sm secondary" type="button" data-po-pendency-id="${escapeHtml(String(id))}" data-po-pendency-status="deferred">Adiar</button>
      <button class="btn sm secondary" type="button" data-po-pendency-id="${escapeHtml(String(id))}" data-po-pendency-status="ignored">Ignorar</button>
    </div>
  `;
}

async function poDecidePendency(pendencyId, status) {
  const label = status === 'resolved' ? 'baixa' : (status === 'ignored' ? 'marcação como ignorada' : 'adiamento');
  const note = window.prompt(`Nota para ${label} da pendência ${pendencyId}:`, '');
  if (note === null) return;
  await poRunAction(`Registro de ${label}`, () => j(`${API}/painel-operador/calendar-pendencies/${encodeURIComponent(pendencyId)}/decision`, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      status,
      resolution_mode: status === 'resolved' ? 'manual_app_close' : (status === 'ignored' ? 'manual_app_ignore' : 'manual_app_defer'),
      closed_by: 'usuario_local',
      decision_note: note,
    }),
  }));
  if (painelOperadorState.activeTab === 'calendar') await loadPainelOperadorCalendar();
}

async function loadPainelOperadorProposals() {
  const qs = poQuery({
    status: poEl('poProposalStatus')?.value,
    severity: poEl('poProposalRisk')?.value,
    evidence_state: poEl('poProposalEvidence')?.value,
    area: poEl('poProposalDomain')?.value,
    target_id: poEl('poProposalTarget')?.value,
    q: poEl('poProposalSearch')?.value,
    limit: 120,
  });
  const data = await j(`${API}/painel-operador/staging/proposals?${qs}`);
  const rows = data.items || [];
  const byStatus = rows.reduce((acc, row) => {
    const key = row.status || 'sem_status';
    acc[key] = (acc[key] || 0) + 1;
    return acc;
  }, {});
  const highRisk = rows.filter((row) => row.risk === 'alto').length;
  poEl('poProposalSummary').innerHTML = `
    <div class="po-stage-count"><span>Exibidas</span><strong>${poNum(data.returned)}</strong></div>
    <div class="po-stage-count"><span>Pendentes</span><strong>${poNum(byStatus.pending_authorization)}</strong></div>
    <div class="po-stage-count"><span>Adiadas</span><strong>${poNum(byStatus.deferred)}</strong></div>
    <div class="po-stage-count"><span>Risco alto</span><strong>${poNum(highRisk)}</strong></div>
  `;
  poEl('poProposalMeta').textContent = `${poNum(data.total)} proposta(s) auditáveis · exibindo ${poNum(data.returned)}.`;
  poEl('poProposalRows').innerHTML = rows.map((row) => `
    <tr>
      <td>${poBadge(poText(row.status), poStatusKind(row.status))}</td>
      <td>${poBadge(poText(row.risk), poStatusKind(row.risk === 'alto' ? 'critical' : row.risk))}</td>
      <td>${poTag(row.proposal_id)}</td>
      <td>${escapeHtml(row.domain || '')}</td>
      <td>${poTag(row.target_id)}</td>
      <td>${escapeHtml(row.field_name || '')}</td>
      <td class="po-path-cell" title="${escapeHtml(poJsonValue(row.current_value_json))}">${escapeHtml(poJsonValue(row.current_value_json))}</td>
      <td class="po-path-cell" title="${escapeHtml(poJsonValue(row.proposed_value_json))}">${escapeHtml(poJsonValue(row.proposed_value_json))}</td>
      <td>${poBadge(poText(row.evidence_state), poStatusKind(row.evidence_state))}</td>
      <td class="po-path-cell" title="${escapeHtml(row.recommended_action || row.evidence_text || '')}">${escapeHtml(row.recommended_action || row.evidence_text || '')}</td>
      <td>${poProposalDecisionActions(row)}</td>
    </tr>
  `).join('') || '<tr><td colspan="11" class="muted">Nenhuma proposta encontrada para os filtros.</td></tr>';
}

function poProposalDecisionActions(row) {
  const id = row.id || row.proposal_id;
  const status = String(row.status || '').toLowerCase();
  if (!id) return '<span class="muted">—</span>';
  if (['authorized', 'rejected', 'deferred'].includes(status)) return `<span class="muted">${escapeHtml(poText(status))}</span>`;
  return `
    <div class="po-decision-actions">
      <button class="btn sm secondary" type="button" data-po-proposal-id="${escapeHtml(String(id))}" data-po-proposal-status="authorized">Autorizar</button>
      <button class="btn sm secondary" type="button" data-po-proposal-id="${escapeHtml(String(id))}" data-po-proposal-status="rejected">Rejeitar</button>
      <button class="btn sm secondary" type="button" data-po-proposal-id="${escapeHtml(String(id))}" data-po-proposal-status="deferred">Adiar</button>
    </div>
  `;
}

async function poDecideProposal(proposalId, status) {
  const labels = {authorized: 'autorização', rejected: 'rejeição', deferred: 'adiamento'};
  const label = labels[status] || 'decisão';
  const note = window.prompt(`Nota para ${label} da proposta ${proposalId}:`, '');
  if (note === null) return;
  await poRunAction(`Registro de ${label}`, () => j(`${API}/painel-operador/proposals/${encodeURIComponent(proposalId)}/decision`, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      status,
      decision_mode: `manual_app_${status}`,
      decided_by: 'usuario_local',
      decision_note: note,
    }),
  }));
  if (painelOperadorState.activeTab === 'proposals') await loadPainelOperadorProposals();
}

async function loadPainelOperadorIhm() {
  const qs = poQuery({
    date_from: poEl('poIhmDateFrom')?.value,
    date_to: poEl('poIhmDateTo')?.value,
    fluid: poEl('poIhmFluid')?.value,
    tag: poEl('poIhmTag')?.value,
    limit: 500,
  });
  const data = await j(`${API}/painel-operador/ihm-reports?${qs}`).catch((err) => ({rows: [], days: [], summary: {}, error: err.message}));
  const summary = data.summary || {};
  const FLUID_LABEL = {oil: 'Óleo', gas: 'Gás', water: 'Água'};
  const FLUID_BADGE = {oil: 'ok', gas: 'info', water: 'muted'};
  poEl('poIhmSummary').innerHTML = `
    <div class="po-stage-count"><span>Dias com dados</span><strong>${poNum(summary.days)}</strong></div>
    <div class="po-stage-count"><span>Registros totais</span><strong>${poNum(summary.total_records)}</strong></div>
    ${Object.entries(summary.by_fluid || {}).map(([f, n]) => `<div class="po-stage-count"><span>${FLUID_LABEL[f] || f}</span><strong>${poNum(n)}</strong></div>`).join('')}
    ${summary.errors ? `<div class="po-stage-count" style="color:var(--color-warn)"><span>Erros parse</span><strong>${poNum(summary.errors)}</strong></div>` : ''}
  `;
  poEl('poIhmDayRows').innerHTML = (data.days || []).map((day) => `
    <tr>
      <td class="mono">${fmtDate(day.date)}</td>
      <td class="num">${poNum(day.oil_gsv_sm3, 1)}</td>
      <td class="num">${poNum(day.gas_gv_m3, 1)}</td>
      <td class="num">${poNum(day.water_gv_m3, 1)}</td>
    </tr>
  `).join('') || '<tr><td colspan="4" class="muted">Sem dados de dias disponíveis. Rode o build script e sincronize.</td></tr>';
  poEl('poIhmMeta').textContent = `${poNum(data.total)} registro(s) encontrados.`;
  poEl('poIhmRows').innerHTML = (data.rows || []).map((row) => `
    <tr>
      <td class="mono">${fmtDate(row.production_date)}</td>
      <td>${poBadge(FLUID_LABEL[row.fluid] || row.fluid, FLUID_BADGE[row.fluid] || 'muted')}</td>
      <td>${poTag(row.tag)}</td>
      <td class="po-path-cell" title="${escapeHtml(row.skid || '')}">${escapeHtml(row.skid || '—')}</td>
      <td class="num">${poNum(row.gross_volume, 3)}</td>
      <td class="num">${poNum(row.gross_standard_volume, 3)}</td>
      <td class="num">${poNum(row.mass, 3)}</td>
      <td class="num">${poNum(row.flow_time, 1)}</td>
    </tr>
  `).join('') || '<tr><td colspan="8" class="muted">Nenhum dado IHM encontrado. Verifique se o build script já processou os IHM Reports.</td></tr>';
}

async function loadPainelOperadorStaging() {
  const type = poEl('poStageType')?.value || 'comparisons';
  const qs = poQuery({
    family: poEl('poStageFamily')?.value,
    tag: poEl('poStageTag')?.value,
    status: poEl('poStageStatus')?.value,
    q: poEl('poStageSearch')?.value,
    limit: 120,
  });
  const data = await j(`${API}/painel-operador/staging/${type}?${qs}`);
  poEl('poStageMeta').textContent = `${poNum(data.total)} registro(s) em ${type} · exibindo ${poNum(data.returned)}.`;
  const schema = poStagingSchema(type);
  poEl('poStageHead').innerHTML = `<tr>${schema.map((col) => `<th>${escapeHtml(col.label)}</th>`).join('')}</tr>`;
  poEl('poStageRows').innerHTML = (data.items || []).map((row) => `
    <tr>${schema.map((col) => `<td class="${col.cls || ''}">${col.render(row)}</td>`).join('')}</tr>
  `).join('') || `<tr><td colspan="${schema.length}" class="muted">Nenhum registro encontrado para os filtros.</td></tr>`;
}

function poStagingSchema(type) {
  const text = (key) => (row) => escapeHtml(poText(row[key]));
  const date = (key) => (row) => fmtDate(row[key]);
  const badge = (key) => (row) => row[key] ? poBadge(row[key], row[key] === 'ok' ? 'ok' : 'warn') : '<span class="muted">—</span>';
  const tag = (key) => (row) => poTag(row[key]);
  const source = (key) => (row) => `<span class="po-path-cell" title="${escapeHtml(row[key] || '')}">${escapeHtml((row[key] || '').split(/[\\/]/).pop() || '—')}</span>`;
  if (type === 'sources') {
    return [
      {label: 'Data', render: date('source_date'), cls: 'mono'},
      {label: 'Família', render: tag('family')},
      {label: 'Tipo', render: text('source_kind')},
      {label: 'Arquivo', render: source('local_path')},
      {label: 'Existe', render: (row) => row.file_exists ? poBadge('sim', 'ok') : poBadge('não', 'err')},
    ];
  }
  if (type === 'points') {
    return [
      {label: 'Data', render: date('point_date'), cls: 'mono'},
      {label: 'Família', render: tag('family')},
      {label: 'Tag', render: tag('tag')},
      {label: 'Fluido', render: text('fluid')},
      {label: 'Tipo', render: text('meter_type')},
      {label: 'Volume corr.', render: (row) => fmt(row.volume_corrigido), cls: 'num'},
    ];
  }
  if (type === 'evidence') {
    return [
      {label: 'Evento', render: date('event_at'), cls: 'mono'},
      {label: 'Tipo', render: text('evidence_kind')},
      {label: 'Requisito', render: tag('requirement_id')},
      {label: 'Título', render: text('title')},
      {label: 'Status', render: text('status')},
      {label: 'Fonte', render: source('local_path')},
    ];
  }
  if (type === 'alerts') {
    return [
      {label: 'Data', render: date('alert_date'), cls: 'mono'},
      {label: 'Tipo', render: text('alert_kind')},
      {label: 'Severidade', render: badge('severity')},
      {label: 'Área', render: text('area')},
      {label: 'Alvo', render: tag('target_id')},
      {label: 'Título', render: text('title')},
      {label: 'Status', render: text('status')},
    ];
  }
  if (type === 'proposals') {
    return [
      {label: 'Data', render: date('created_at_source'), cls: 'mono'},
      {label: 'Status', render: (row) => poBadge(poText(row.status), poStatusKind(row.status))},
      {label: 'Risco', render: (row) => poBadge(poText(row.risk), poStatusKind(row.risk === 'alto' ? 'critical' : row.risk))},
      {label: 'ID', render: tag('proposal_id')},
      {label: 'Domínio', render: text('domain')},
      {label: 'Alvo', render: tag('target_id')},
      {label: 'Campo', render: text('field_name')},
      {label: 'Evidência', render: (row) => poBadge(poText(row.evidence_state), poStatusKind(row.evidence_state))},
    ];
  }
  if (type === 'calendar') {
    return [
      {label: 'Data', render: date('calendar_date'), cls: 'mono'},
      {label: 'Status', render: (row) => poBadge(poText(row.status), poStatusKind(row.status))},
      {label: 'Carga', render: (row) => Number(row.loaded || 0) ? poBadge('sim', 'ok') : poBadge('não', 'err')},
      {label: 'Pontos', render: (row) => poNum(row.points_count), cls: 'num'},
      {label: 'XML', render: (row) => poListCell(row.xml_families_json)},
      {label: 'Faltantes', render: (row) => poListCell(row.missing_xml_families_json)},
      {label: 'Abertas', render: (row) => poNum(row.open_pending_count), cls: 'num'},
      {label: 'Resolvidas', render: (row) => poNum(row.resolved_pending_count), cls: 'num'},
    ];
  }
  if (type === 'pendencies') {
    return [
      {label: 'Data', render: date('calendar_date'), cls: 'mono'},
      {label: 'ID', render: tag('pendency_id')},
      {label: 'Tipo', render: text('pendency_type')},
      {label: 'Severidade', render: (row) => poBadge(poText(row.severity), poStatusKind(row.severity))},
      {label: 'Status', render: (row) => poBadge(poText(row.status), poStatusKind(row.status))},
      {label: 'Título', render: text('title')},
      {label: 'Ação', render: text('recommended_action')},
    ];
  }
  return [
    {label: 'Data', render: date('comparison_date'), cls: 'mono'},
    {label: 'Família', render: tag('family')},
    {label: 'Tag', render: tag('tag')},
    {label: 'Fluido', render: text('fluid')},
    {label: 'Status', render: badge('status')},
    {label: 'Raw', render: (row) => fmt(row.raw_corrigido), cls: 'num'},
    {label: 'ANP', render: (row) => fmt(row.anp_corrigido), cls: 'num'},
    {label: 'Nota', render: text('note')},
  ];
}

function bindPainelOperadorEvents() {
  document.querySelectorAll('[data-po-tab]').forEach((button) => {
    button.addEventListener('click', () => poSetActiveTab(button.dataset.poTab));
  });
  document.querySelectorAll('[data-po-checklist-section]').forEach((button) => {
    button.addEventListener('click', () => poSetChecklistSection(button.dataset.poChecklistSection));
  });
  poEl('poRefreshBtn')?.addEventListener('click', () => loadPainelOperador());
  poEl('poScanFilesBtn')?.addEventListener('click', () => poRunAction('Reindexação de fontes', () => j(`${API}/painel-operador/file-index/scan?hash_files=false`, {method: 'POST'})));
  poEl('poSyncContractBtn')?.addEventListener('click', () => poRunAction('Sincronização do contrato', () => j(`${API}/painel-operador/sync`, {method: 'POST'})));
  poEl('poImportAnpBtn')?.addEventListener('click', () => poRunAction('Importação dos exports ANP', () => j(`${API}/painel-operador/anp-exports/import`, {method: 'POST'})));
  poEl('poProcessTechnicalBtn')?.addEventListener('click', async () => {
    await poRunAction('Processamento Limites/CV', () => j(`${API}/painel-operador/technical-monitor/process`, {method: 'POST'}));
    if (painelOperadorState.activeTab === 'technical') await loadPainelOperadorTechnical();
  });
  poEl('poValidateSourcesBtn')?.addEventListener('click', () => loadPainelOperadorIngestion(true));
  poEl('poReloadSourcesBtn')?.addEventListener('click', () => loadPainelOperadorIngestion(false));
  poEl('poPanelIngestion')?.addEventListener('click', (event) => {
    const button = event.target.closest('[data-po-source-save]');
    if (!button) return;
    poSaveDataSource(button.dataset.poSourceSave);
  });
  poEl('poPanelCalendar')?.addEventListener('click', (event) => {
    const button = event.target.closest('[data-po-pendency-id]');
    if (!button) return;
    poDecidePendency(button.dataset.poPendencyId, button.dataset.poPendencyStatus);
  });
  poEl('poPanelProposals')?.addEventListener('click', (event) => {
    const button = event.target.closest('[data-po-proposal-id]');
    if (!button) return;
    poDecideProposal(button.dataset.poProposalId, button.dataset.poProposalStatus);
  });
  poEl('poPanelRadar')?.addEventListener('click', (event) => {
    const button = event.target.closest('[data-po-radar-view]');
    if (!button) return;
    poRadarSetView(button.dataset.poRadarView);
  });
  poEl('poPanelTechnical')?.addEventListener('click', (event) => {
    const button = event.target.closest('[data-po-limit-id]');
    if (!button) return;
    const row = (painelOperadorState.configuredLimits || []).find((item) => String(item.id) === String(button.dataset.poLimitId));
    poFillConfiguredLimitForm(row);
  });
  poEl('poPanelXmlValidation')?.addEventListener('click', (event) => {
    const button = event.target.closest('[data-po-xml-action]');
    if (!button) return;
    poHandleXmlAction(button.dataset.poXmlAction, button.dataset.poXmlId);
  });
  poEl('poRadarRefreshBtn')?.addEventListener('click', () => loadPainelOperadorRadar(true));
  ['poRadarDate', 'poRadarTag'].forEach((id) => {
    poEl(id)?.addEventListener('change', () => renderPainelOperadorRadar());
  });
  poEl('poRadarSearch')?.addEventListener('keydown', (event) => {
    if (event.key === 'Enter') renderPainelOperadorRadar();
  });
  poEl('poLoadFilesBtn')?.addEventListener('click', loadPainelOperadorFiles);
  poEl('poLoadAnpBtn')?.addEventListener('click', loadPainelOperadorAnp);
  poEl('poLoadXmlValidationBtn')?.addEventListener('click', loadPainelOperadorXmlValidation);
  poEl('poLoadMeasuredBtn')?.addEventListener('click', loadPainelOperadorMeasured);
  poEl('poLoadChecklistBtn')?.addEventListener('click', loadPainelOperadorChecklist);
  poEl('poInspectChecklistBtn')?.addEventListener('click', inspectPainelOperadorChecklist);
  poEl('poImportChecklistBtn')?.addEventListener('click', importPainelOperadorChecklist);
  poEl('poLoadTechnicalBtn')?.addEventListener('click', loadPainelOperadorTechnical);
  poEl('poSaveLimitBtn')?.addEventListener('click', poSaveConfiguredLimit);
  poEl('poClearLimitFormBtn')?.addEventListener('click', poClearConfiguredLimitForm);
  poEl('poLoadDossiersBtn')?.addEventListener('click', loadPainelOperadorDossiers);
  poEl('poLoadCompareBtn')?.addEventListener('click', loadPainelOperadorCompare);
  poEl('poLoadCalendarBtn')?.addEventListener('click', loadPainelOperadorCalendar);
  poEl('poLoadProposalsBtn')?.addEventListener('click', loadPainelOperadorProposals);
  poEl('poLoadStagingBtn')?.addEventListener('click', loadPainelOperadorStaging);
  poEl('poLoadIhmBtn')?.addEventListener('click', loadPainelOperadorIhm);
  poEl('poClearIhmBtn')?.addEventListener('click', () => {
    ['poIhmDateFrom', 'poIhmDateTo', 'poIhmFluid', 'poIhmTag'].forEach((id) => { const el = poEl(id); if (el) el.value = ''; });
    loadPainelOperadorIhm();
  });
  poEl('poClearFilesBtn')?.addEventListener('click', () => {
    ['poFileCategory', 'poFileKind', 'poFileFamily', 'poFileTag', 'poFileDuplicate', 'poFileSearch'].forEach((id) => { const el = poEl(id); if (el) el.value = ''; });
    loadPainelOperadorFiles();
  });
  poEl('poClearAnpBtn')?.addEventListener('click', () => {
    ['poAnpFamily', 'poAnpKind', 'poAnpTag', 'poAnpDateFrom', 'poAnpDateTo', 'poAnpSearch'].forEach((id) => { const el = poEl(id); if (el) el.value = ''; });
    loadPainelOperadorAnp();
  });
  poEl('poClearXmlValidationBtn')?.addEventListener('click', () => {
    ['poXmlDateFrom', 'poXmlDateTo', 'poXmlKind', 'poXmlStatus', 'poXmlFamily', 'poXmlTag', 'poXmlSearch'].forEach((id) => { const el = poEl(id); if (el) el.value = ''; });
    loadPainelOperadorXmlValidation();
  });
  poEl('poClearMeasuredBtn')?.addEventListener('click', () => {
    ['poMeasuredDateFrom', 'poMeasuredDateTo', 'poMeasuredSource', 'poMeasuredFamily', 'poMeasuredTag'].forEach((id) => { const el = poEl(id); if (el) el.value = ''; });
    loadPainelOperadorMeasured();
  });
  poEl('poClearChecklistBtn')?.addEventListener('click', () => {
    ['poChecklistSheet', 'poChecklistDateFrom', 'poChecklistDateTo', 'poChecklistTag', 'poChecklistSearch'].forEach((id) => { const el = poEl(id); if (el) el.value = ''; });
    loadPainelOperadorChecklist();
  });
  poEl('poClearTechnicalBtn')?.addEventListener('click', () => {
    ['poTechnicalDateFrom', 'poTechnicalDateTo', 'poTechnicalFamily', 'poTechnicalTag'].forEach((id) => { const el = poEl(id); if (el) el.value = ''; });
    loadPainelOperadorTechnical();
  });
  poEl('poClearDossiersBtn')?.addEventListener('click', () => {
    ['poDossierDateFrom', 'poDossierDateTo', 'poDossierFamily', 'poDossierTag', 'poDossierSearch'].forEach((id) => { const el = poEl(id); if (el) el.value = ''; });
    loadPainelOperadorDossiers();
  });
  poEl('poClearCompareBtn')?.addEventListener('click', () => {
    ['poCompareFamily', 'poCompareKind', 'poCompareStatus', 'poCompareTag', 'poCompareDateFrom', 'poCompareDateTo'].forEach((id) => { const el = poEl(id); if (el) el.value = ''; });
    loadPainelOperadorCompare();
  });
  poEl('poClearCalendarBtn')?.addEventListener('click', () => {
    ['poCalendarDateFrom', 'poCalendarDateTo', 'poCalendarStatus', 'poCalendarLoaded', 'poPendencyStatus', 'poPendencySeverity'].forEach((id) => { const el = poEl(id); if (el) el.value = ''; });
    loadPainelOperadorCalendar();
  });
  poEl('poClearProposalsBtn')?.addEventListener('click', () => {
    ['poProposalStatus', 'poProposalRisk', 'poProposalEvidence', 'poProposalDomain', 'poProposalTarget', 'poProposalSearch'].forEach((id) => { const el = poEl(id); if (el) el.value = ''; });
    loadPainelOperadorProposals();
  });
  poEl('poClearStagingBtn')?.addEventListener('click', () => {
    ['poStageFamily', 'poStageTag', 'poStageStatus', 'poStageSearch'].forEach((id) => { const el = poEl(id); if (el) el.value = ''; });
    loadPainelOperadorStaging();
  });
  ['poFileSearch', 'poAnpSearch', 'poMeasuredTag', 'poChecklistSearch', 'poChecklistTag', 'poTechnicalTag', 'poDossierTag', 'poDossierSearch', 'poCompareTag', 'poProposalSearch', 'poStageSearch'].forEach((id) => {
    poEl(id)?.addEventListener('keydown', (event) => {
      if (event.key !== 'Enter') return;
      if (id === 'poFileSearch') loadPainelOperadorFiles();
      if (id === 'poAnpSearch') loadPainelOperadorAnp();
      if (id === 'poMeasuredTag') loadPainelOperadorMeasured();
      if (id === 'poChecklistSearch' || id === 'poChecklistTag') loadPainelOperadorChecklist();
      if (id === 'poTechnicalTag') loadPainelOperadorTechnical();
      if (id === 'poDossierTag' || id === 'poDossierSearch') loadPainelOperadorDossiers();
      if (id === 'poCompareTag') loadPainelOperadorCompare();
      if (id === 'poProposalSearch') loadPainelOperadorProposals();
      if (id === 'poStageSearch') loadPainelOperadorStaging();
    });
  });

  // Recarregar dashboard quando mudar o mês (apenas para aba overview)
  document.querySelector('#globalMonth')?.addEventListener('change', () => {
    const activeTab = document.querySelector('[data-po-tab].active')?.getAttribute('data-po-tab');
    if (activeTab === 'overview') {
      renderPainelOperadorOverview();
    }
  });
}

bindPainelOperadorEvents();
