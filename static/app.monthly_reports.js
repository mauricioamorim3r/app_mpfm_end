'use strict';

function monthlyReportMonth() {
  return document.getElementById('globalMonth')?.value || '';
}

function monthlyReportStatus(message, isError = false) {
  const host = document.getElementById('mrStatus');
  if (!host) return;
  host.textContent = message || '';
  host.style.color = isError ? 'var(--red)' : 'var(--muted)';
}

function monthlyReportToggleCustomFields() {
  const mode = document.getElementById('mrMode')?.value || 'default';
  const host = document.getElementById('mrCustomFields');
  if (host) host.style.display = mode === 'custom' ? 'flex' : 'none';
}

function monthlyReportBuildParams() {
  const params = new URLSearchParams({
    month: monthlyReportMonth(),
    mode: document.getElementById('mrMode')?.value || 'default',
    group_key: document.getElementById('mrGroup')?.value || '',
    date_from: document.getElementById('mrDateFrom')?.value || '',
    date_to: document.getElementById('mrDateTo')?.value || '',
    custom_title: document.getElementById('mrCustomTitle')?.value || '',
    subsea_bank: document.getElementById('mrSubseaBank')?.value || '',
    subsea_tag: document.getElementById('mrSubseaTag')?.value || '',
    topside_bank: document.getElementById('mrTopsideBank')?.value || '',
    topside_tag: document.getElementById('mrTopsideTag')?.value || '',
  });
  return params;
}

function monthlyReportRenderSummary(summary = {}) {
  const host = document.getElementById('mrSummary');
  if (!host) return;
  const cards = [
    ['Dias no recorte', summary.days_in_period ?? 0, 'recorte configurado'],
    ['Dias com MPFM', summary.days_with_mpfm ?? 0, 'medição diária disponível'],
    ['Dias com SEP', summary.days_with_sep ?? 0, 'separador com dados'],
    ['Dias com XML', summary.days_with_xml ?? 0, 'documento gerado/importado'],
    ['XMLs gerados', summary.xml_generated_count ?? 0, 'pela aplicação'],
    ['Exceções', summary.exception_count ?? 0, 'faltas e validações'],
  ];
  host.innerHTML = cards.map(([label, value, note]) => `
    <div class="upload-context-card">
      <div class="k">${label}</div>
      <div class="v">${value}</div>
      <div class="m">${note}</div>
    </div>
  `).join('');
}

function monthlyReportRenderGroups(groups = []) {
  const host = document.getElementById('mrGroups');
  if (!host) return;
  host.innerHTML = groups.map(group => `
    <div class="upload-context-card">
      <div class="k">${group.title}</div>
      <div class="v">${group.stats?.days_with_mpfm ?? 0}</div>
      <div class="m">MPFM ${group.stats?.days_with_mpfm ?? 0} · SEP ${group.stats?.days_with_sep ?? 0} · XML ${group.stats?.days_with_xml ?? 0}</div>
    </div>
  `).join('');
}

function monthlyReportApplyGroupPreset() {
  const select = document.getElementById('mrGroup');
  const option = select?.selectedOptions?.[0];
  if (!option) return;
  document.getElementById('mrCustomTitle').value = option.dataset.title || '';
  document.getElementById('mrSubseaBank').value = option.dataset.subseaBank || '';
  document.getElementById('mrSubseaTag').value = option.dataset.subseaTag || '';
  document.getElementById('mrTopsideBank').value = option.dataset.topsideBank || '';
  document.getElementById('mrTopsideTag').value = option.dataset.topsideTag || '';
}

async function loadMonthlyReportsContext() {
  const d = await j(`${API}/monthly-reports/context`);
  const select = document.getElementById('mrGroup');
  if (!select) return;
  const current = select.value;
  select.innerHTML = '<option value="">Escolher grupo</option>' + (d.groups || []).map(group => `
    <option value="${group.key}"
      data-title="${group.title}"
      data-subsea-bank="${group.subsea_bank}"
      data-subsea-tag="${group.subsea_tag}"
      data-topside-bank="${group.topside_bank}"
      data-topside-tag="${group.topside_tag}"
    >${group.title}</option>
  `).join('');
  if (current) select.value = current;
}

async function loadMonthlyReportsPage() {
  await loadMonthlyReportsContext();
  monthlyReportToggleCustomFields();
  const month = monthlyReportMonth();
  const {from, to} = getMonthRange(month);
  const fromEl = document.getElementById('mrDateFrom');
  const toEl = document.getElementById('mrDateTo');
  if (fromEl && !fromEl.value) fromEl.value = from;
  if (toEl && !toEl.value) toEl.value = to;
  if (typeof refreshDateInputDisplay === 'function') refreshDateInputDisplay(document);
}

async function generateMonthlyReport() {
  monthlyReportStatus('Gerando relatório mensal...');
  try {
    const params = monthlyReportBuildParams();
    const d = await j(`${API}/monthly-reports/preview?${params.toString()}`);
    monthlyReportRenderSummary(d.summary || {});
    monthlyReportRenderGroups(d.groups || []);
    const frame = document.getElementById('mrFrame');
    if (frame) frame.src = d.html_url || '';
    window.__monthlyReportUrls = {html: d.html_url || '', print: d.print_url || ''};
    monthlyReportStatus(`Relatório carregado para ${d.meta?.month_label || d.meta?.month || ''}.`);
  } catch (err) {
    monthlyReportStatus(`Falha ao gerar relatório: ${err.message || err}`, true);
  }
}

function openMonthlyReport() {
  const url = window.__monthlyReportUrls?.html;
  if (!url) {
    monthlyReportStatus('Gere o relatório antes de abrir em nova aba.', true);
    return;
  }
  window.open(url, '_blank', 'noopener');
}

function printMonthlyReport() {
  const url = window.__monthlyReportUrls?.print;
  if (!url) {
    monthlyReportStatus('Gere o relatório antes de exportar o PDF.', true);
    return;
  }
  window.open(url, '_blank', 'noopener');
}

document.getElementById('mrMode')?.addEventListener('change', monthlyReportToggleCustomFields);
document.getElementById('mrGroup')?.addEventListener('change', monthlyReportApplyGroupPreset);
document.getElementById('btnGenerateMonthlyReport')?.addEventListener('click', generateMonthlyReport);
document.getElementById('btnOpenMonthlyReport')?.addEventListener('click', openMonthlyReport);
document.getElementById('btnPrintMonthlyReport')?.addEventListener('click', printMonthlyReport);
