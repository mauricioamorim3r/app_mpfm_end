'use strict';
const state = {
  queue: [],
  mpfmRows: [],
  monitoringRows: [],
  xml042Rows: [],
  xml042Catalog: [],
  xml042Docs: [],
  xml042Selected: null,
  xml042CatalogEditingId: null,
  chart: null,
  chartData: null,
  prefs: {},
  summary: { bank: '', tag: '', day: '' },
  summaryChart: { showHcLimit: true, showTotalLimit: true, showPointLabels: false, selectedPairKeys: null, currentPayload: null },
  deadlines: [],
  allMetrics: [],
  selectedCols: [],
  sepSelectedCols: [],
  sepRows: [],
  sepCols: [],
  sepAllDbCols: [],
  sepFluidRows: { oleo: [], gas: [], agua: [] },
  sepFluidMeta: {},
  sepActiveFluid: 'oleo',
  alarmWorkspace: { rows: [], selectedId: null, detail: null, summary: null, preview: null, catalog: {} },
  sgmfm: { recordType: 'rotina', schema: {}, currentId: null, currentPayload: null, currentRecord: null, visibility: {}, summary: null },
  dupDecisions: {},
  dirtyPages: {},
  lastDataChangedAt: '',
};

// ── Navigation ───────────────────────────────────────────────────────────────
const PAGE_TITLES = {
  resumo:'Resumo do Mês', upload:'Processar Arquivos', mpfm:'Dados MPFM',
  monitoramento:'Monitoramento MPFM',
  xml042:'XML 042',
  relatorios:'Relatórios Mensais',
  separador:'Dados Separador', cards:'Cards Diários', graficos:'Gráficos', alertas:'Alarmes MPFM', prazos:'Prazos & Contadores',
  'painel-operador':'Painel do Operador',
  cadastro:'Cadastro', sgmfm:'Registros do SGM-FM', exportar:'Exportar', recon:'Reconciliação ⚖', fluxo:'Fluxo Metodológico', twin:'Twin MPFM', assistente:'Assistente IA',
};
const PAGE_SUBTITLES = {
  resumo:'Visão operacional do mês, produção, equivalências e decomposição diária',
  upload:'Upload e parsing de TXTs MPFM e PDFs Separador',
  mpfm:'Tabela de dados processados dos medidores multifásicos',
  monitoramento:'Acompanhamento diário de medidores subsea e topside com CRUD operacional',
  xml042:'Emissão isolada de XML 042 por poço e por dia',
  relatorios:'Fechamento mensal executivo com MPFM, XML, Separador e exceções',
  separador:'Medições de produção do separador trifásico',
  cards:'Resumo diário em cards técnicos, com edição manual e PDF',
  graficos:'Visualização temporal de desvios e tendências',
  alertas:'Upload, análise operacional e gestão de ocorrências de alarme do MPFM',
  'painel-operador':'Catálogo de fontes, staging e exports ANP vindos da cópia local do Painel do Operador',
  cadastro:'Configuração de bancos, TAGs e parâmetros',
  sgmfm:'Registros estruturados do SGM-FM com pré-preenchimento a partir da base principal',
  exportar:'Arquivos Excel gerados',
  recon:'Validação PVT e balanço de massa MPFM × Separador',
  fluxo:'Fluxo visual com dados reais de reconciliação, PVT, separador e memorial de cálculo',
  twin:'Sinóptico operacional com assets do Twin MPFM e dados reais do run de reconciliação',
  assistente:'Chat técnico com IA especialista em sistemas de medição multifásica',
};
let _currentPage = null;
function setPage(name) {
  if (name === _currentPage) return;
  _currentPage = name;
  if (window.location.hash !== `#${name}`) {
    history.replaceState(null, '', `#${name}`);
  }
  document.querySelectorAll('.page').forEach(p => p.classList.toggle('active', p.id === `page-${name}`));
  document.querySelectorAll('.navbtn').forEach(b => {
    const isActive = b.dataset.page === name;
    b.classList.toggle('active', isActive);
    if (isActive) {
      b.setAttribute('aria-current', 'page');
    } else {
      b.removeAttribute('aria-current');
    }
  });
  document.getElementById('pageTitle').textContent = PAGE_TITLES[name] || name;
  document.getElementById('subtitle').textContent = PAGE_SUBTITLES[name] || '';
  if (name === 'exportar')  loadOutputs();
  if (name === 'alertas' && typeof loadAlarmWorkspace === 'function') loadAlarmWorkspace();
  if (name === 'mpfm')       { syncGlobal(); loadMPFM(); }
  if (name === 'monitoramento') { syncGlobal(); loadMonitoring(); }
  if (name === 'xml042')     { syncGlobal(); loadXml042Page(); }
  if (name === 'relatorios') { syncGlobal(); loadMonthlyReportsPage(); }
  if (name === 'separador')  { syncGlobal(); loadSep(); }
  if (name === 'cards')      { syncGlobal(); loadCards(); }
  if (name === 'prazos')     { loadDeadlines(); loadDeadlinesSummary(); }
  if (name === 'resumo')     {
    if (typeof initPocoRiserTable === 'function') initPocoRiserTable(document.getElementById('globalMonth')?.value || '');
    loadSummary();
  }
  if (name === 'graficos')   { syncGlobal(); loadChartsPage(); }
  if (name === 'cadastro')   loadCadastro();
  if (name === 'sgmfm')      loadSGMFM();
  if (name === 'recon')      loadRecon();
  if (name === 'fluxo' && typeof loadMethodologyFlow === 'function') loadMethodologyFlow();
  if (name === 'twin' && typeof loadTwinMPFM === 'function') {
    loadTwinMPFM();
    if (typeof loadDynamicDiagrams === 'function') loadDynamicDiagrams();
  }
  if (name === 'upload')     loadProcessHistory();
  if (name === 'assistente' && typeof loadAiPage === 'function') loadAiPage();
  if (name === 'painel-operador' && typeof loadPainelOperador === 'function') loadPainelOperador();
  delete state.dirtyPages[name];
}
document.querySelectorAll('.navbtn').forEach(b => b.onclick = () => setPage(b.dataset.page));

// ── Helpers ───────────────────────────────────────────────────────────────────
// ── Init ──────────────────────────────────────────────────────────────────────
// ── Month helpers ─────────────────────────────────────────────────────────────

async function initDates() {
  // Load available months from server, populate month selector
  const d = await j(`${API}/ops/month-summary`).catch(() => ({}));
  const months = d.months_available || [];
  const sel = document.getElementById('globalMonth');
  if (sel) {
    const MESES = {1:'Jan',2:'Fev',3:'Mar',4:'Abr',5:'Mai',6:'Jun',7:'Jul',8:'Ago',9:'Set',10:'Out',11:'Nov',12:'Dez'};
    const fallbackMonth = (() => {
      const now = new Date();
      const year = now.getFullYear();
      const month = String(now.getMonth() + 1).padStart(2, '0');
      return `${year}-${month}`;
    })();
    const monthOptions = months.length ? months : [fallbackMonth];
    sel.innerHTML = monthOptions.map(m => {
      const [yr, mo] = m.split('-');
      return `<option value="${m}">${MESES[parseInt(mo)]}/${yr}</option>`;
    }).join('');
    sel.value = monthOptions[0]; // latest month or current month on fresh DB
  }
  if (typeof enhanceBrazilianDateInputs === 'function') enhanceBrazilianDateInputs(document);
  syncGlobal();
  if (typeof refreshDateInputDisplay === 'function') refreshDateInputDisplay(document);
  await loadPrefs();
  renderBranding();
  await loadSummary();
  loadDeadlines();
  startAutoRefresh();
  setTimeout(() => {
    const summaryActive = document.getElementById('page-resumo')?.classList.contains('active');
    const monthReady = !!document.getElementById('globalMonth')?.value;
    const cardsReady = (document.getElementById('summaryCards')?.children.length || 0) > 0;
    if (summaryActive && (!monthReady || !cardsReady)) {
      syncGlobal();
      loadSummary();
    }
  }, 1200);
}

function syncGlobal() {
  const month = document.getElementById('globalMonth')?.value || '';
  const {from, to} = getMonthRange(month);
  ['mDateFrom','cDateFrom','aDateFrom','cdDateFrom'].forEach(id => { const el = document.getElementById(id); if (el) el.value = from; });
  ['mrDateFrom'].forEach(id => { const el = document.getElementById(id); if (el) el.value = from; });
  ['mDateTo','cDateTo','aDateTo','cdDateTo'].forEach(id => { const el = document.getElementById(id); if (el) el.value = to; });
  ['mrDateTo'].forEach(id => { const el = document.getElementById(id); if (el) el.value = to; });
  ['sDateFrom'].forEach(id => { const el = document.getElementById(id); if (el) el.value = from; });
  ['sDateTo'].forEach(id => { const el = document.getElementById(id); if (el) el.value = to; });
  if (typeof refreshDateInputDisplay === 'function') refreshDateInputDisplay(document);
}

function refreshActivePage(silent = false) {
  syncGlobal();
  const activePage = document.querySelector('.page.active')?.id || '';
  if (activePage === 'page-resumo') loadSummary(silent);
  else if (activePage === 'page-monitoramento') loadMonitoring(silent);
  else if (activePage === 'page-xml042') loadXml042Page();
  else if (activePage === 'page-relatorios') loadMonthlyReportsPage();
  else if (activePage === 'page-mpfm') loadMPFM(silent);
  else if (activePage === 'page-separador') loadSep(silent);
  else if (activePage === 'page-cards') loadCards();
  else if (activePage === 'page-graficos') loadChartsPage();
  else if (activePage === 'page-alertas' && typeof loadAlarmWorkspace === 'function') loadAlarmWorkspace();
  else if (activePage === 'page-prazos') { loadDeadlines(); loadDeadlinesSummary(); }
  else if (activePage === 'page-cadastro') loadCadastro();
  else if (activePage === 'page-sgmfm') loadSGMFM();
  else if (activePage === 'page-recon') loadRecon();
  else if (activePage === 'page-fluxo' && typeof loadMethodologyFlow === 'function') loadMethodologyFlow(true);
  else if (activePage === 'page-twin' && typeof loadTwinMPFM === 'function') {
    loadTwinMPFM(true);
    if (typeof loadDynamicDiagrams === 'function') loadDynamicDiagrams(true);
  }
  else if (activePage === 'page-exportar') loadOutputs();
  else if (activePage === 'page-upload') loadProcessHistory();
  else if (activePage === 'page-painel-operador' && typeof loadPainelOperador === 'function') loadPainelOperador(silent);
  const activeKey = activePage.replace(/^page-/, '');
  if (activeKey) delete state.dirtyPages[activeKey];
}

function markDataChanged(pages) {
  const affected = new Set(['resumo', ...(pages || [])]);
  affected.forEach(page => { state.dirtyPages[page] = true; });
  state.lastDataChangedAt = new Date().toISOString();
}

window.notifyDataChanged = async (pages) => {
  markDataChanged(pages);
  await refreshActivePage();
};

document.getElementById('globalMonth').onchange = () => {
  if (typeof initPocoRiserTable === 'function') {
    initPocoRiserTable(document.getElementById('globalMonth')?.value || '');
  }
  refreshActivePage();
};
document.getElementById('btnRefresh').onclick  = refreshActivePage;
document.getElementById('btnThemeMode').onclick = async () => {
  const nextMode = (document.body.dataset.theme || 'dark') === 'light' ? 'dark' : 'light';
  const status = document.getElementById('themeModeStatus');
  try {
    await persistThemePreference(nextMode);
    if (status) status.textContent = `Tema ${nextMode === 'light' ? 'claro' : 'escuro'} salvo.`;
  } catch (err) {
    if (status) status.textContent = `Falha ao salvar tema: ${err.message || err}`;
  }
};
document.getElementById('btnAutoRefresh').onclick = () => {
  state.autoRefresh = !state.autoRefresh;
  document.getElementById('btnAutoRefresh').textContent = `Auto: ${state.autoRefresh ? 'ON' : 'OFF'}`;
  if (state.autoRefresh) loadSummary();
};
if (typeof syncThemeControls === 'function') syncThemeControls(document.body.dataset.theme || 'dark');
function startAutoRefresh() {
  state.autoRefresh = true;
  if (state.refreshTimer) clearInterval(state.refreshTimer);
  let _inFlight = false;
  state.refreshTimer = setInterval(async () => {
    if (!state.autoRefresh || document.visibilityState !== 'visible') return;
    if (_inFlight) return;
    _inFlight = true;
    try {
      const activePage = document.querySelector('.page.active')?.id || '';
      if (activePage === 'page-resumo') await loadSummary(true);
      else if (activePage === 'page-monitoramento') await loadMonitoring(true);
      else if (activePage === 'page-xml042') loadXml042Page();
      else if (activePage === 'page-mpfm') await loadMPFM(true);
      else if (activePage === 'page-separador') await loadSep(true);
      else if (activePage === 'page-alertas' && typeof loadAlarmWorkspace === 'function') loadAlarmWorkspace();
      else if (activePage === 'page-upload') loadProcessHistory();
      else if (activePage === 'page-painel-operador' && typeof loadPainelOperador === 'function') loadPainelOperador(true);
    } finally {
      _inFlight = false;
    }
  }, 15000);
}
document.addEventListener('visibilitychange', () => {
  if (document.visibilityState === 'visible' && state.autoRefresh) {
    refreshActivePage(true);
  }
});
document.getElementById('sumChartShowHc')?.addEventListener('change', (ev) => {
  state.summaryChart.showHcLimit = !!ev.target.checked;
  if (state.summaryMonthData) loadDesvioChart(document.getElementById('globalMonth')?.value || '', state.summaryMonthData);
});
document.getElementById('sumChartShowTotal')?.addEventListener('change', (ev) => {
  state.summaryChart.showTotalLimit = !!ev.target.checked;
  if (state.summaryMonthData) loadDesvioChart(document.getElementById('globalMonth')?.value || '', state.summaryMonthData);
});
document.getElementById('sumChartShowPointLabels')?.addEventListener('change', (ev) => {
  state.summaryChart.showPointLabels = !!ev.target.checked;
  if (state.summaryMonthData) loadDesvioChart(document.getElementById('globalMonth')?.value || '', state.summaryMonthData);
});

// ── ALERTAS ───────────────────────────────────────────────────────────────────
async function loadAlerts() {
  if (typeof loadAlarmWorkspace === 'function') {
    return loadAlarmWorkspace();
  }
}
document.getElementById('aLoad')?.addEventListener('click', loadAlerts);

function initialPageFromUrl() {
  const allowed = new Set(Object.keys(PAGE_TITLES));
  const fromHash = (window.location.hash || '').replace(/^#/, '').trim();
  const fromQuery = new URLSearchParams(window.location.search).get('page') || '';
  const page = fromHash || fromQuery;
  return allowed.has(page) ? page : 'resumo';
}

const _initialPage = initialPageFromUrl();
if (_initialPage !== 'resumo') setPage(_initialPage);
if (_initialPage === 'resumo' && typeof initPocoRiserTable === 'function') {
  initPocoRiserTable(document.getElementById('globalMonth')?.value || '');
}
initDates()
  .catch((err) => {
    console.warn('Falha na inicializacao; aplicando pagina inicial mesmo assim.', err);
  })
  .finally(() => {
    if (_initialPage !== 'resumo' && _currentPage !== _initialPage) setPage(_initialPage);
  });
