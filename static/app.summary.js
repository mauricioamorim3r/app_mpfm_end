'use strict';

// ── SUMMARY (mês) ─────────────────────────────────────────────────────────────
function summaryMonthLabel(month) {
  const MESES_PT = {1:'Jan',2:'Fev',3:'Mar',4:'Abr',5:'Mai',6:'Jun',7:'Jul',8:'Ago',9:'Set',10:'Out',11:'Nov',12:'Dez'};
  const [yr, mo] = (month || '2026-01').split('-').map(Number);
  return `${MESES_PT[mo] || mo}/${yr}`;
}

function summaryDisplayUnit(unit) {
  return String(unit || '').replace(/Sm³/g, 'sm³');
}

function summaryConversionText(conversion) {
  const unit = summaryDisplayUnit(conversion?.gas_input_unit || 'Sm³');
  return `Critério: gás ÷ ${fmt(conversion?.gas_sm3_per_boe_factor || 170)} ${unit}/boe`;
}

function summarySelectOptions(selectEl, items, stateKey, formatLabel) {
  if (!selectEl) return '';
  const normalized = (items || []).map(item => {
    if (typeof item === 'string') {
      return { value: item, label: formatLabel ? formatLabel(item) : item };
    }
    return item;
  }).filter(item => item && item.value && item.label);

  if (!normalized.length) {
    selectEl.innerHTML = '<option value="">Sem dados</option>';
    selectEl.value = '';
    state.summary[stateKey] = '';
    return '';
  }

  selectEl.innerHTML = normalized.map(item => `<option value="${item.value}">${item.label}</option>`).join('');
  const current = state.summary?.[stateKey] || '';
  const selected = normalized.some(item => item.value === current) ? current : normalized[0].value;
  state.summary[stateKey] = selected;
  selectEl.value = selected;
  if (selectEl.selectedIndex < 0) {
    selectEl.selectedIndex = 0;
    state.summary[stateKey] = selectEl.value;
  }
  return state.summary[stateKey];
}

function summaryCardMarkup(label, value, subtitle, accentVar, mesLabel, iconMap, extra = {}) {
  const criterion = extra.criterion ? `<div class="summary-kpi-foot">${extra.criterion}</div>` : '';
  const titleAttr = extra.tooltip ? ` title="${extra.tooltip.replace(/"/g, '&quot;')}"` : '';
  return `<div class="card summary-kpi-card" style="padding:14px 16px"${titleAttr}>
    <div class="summary-kpi-head"><span class="summary-kpi-icon" title="Clique para trocar o ícone" onclick="editSummaryIcon('${jsStr(label)}')">${renderIconMarkup(iconMap[label],'summary','summary-kpi-glyph')}</span><span>${label}, <span style="color:var(${accentVar})">${mesLabel}</span></span></div>
    <div class="summary-kpi-value" style="color:var(${accentVar})">${value}</div>
    <div class="summary-kpi-sub">${subtitle}</div>
    ${criterion}
  </div>`;
}

function fmtMilSm3(value) {
  return fmt((Number(value) || 0) / 1000);
}

let _summaryDailyChart = null;
const SUMMARY_LAYOUT_DEFAULTS = { cards: true, bank: true, tag: true, daily: true };
const SUMMARY_DAILY_SERIES = [
  { key: 'mpfm_oil', label: 'MPFM Óleo (t)', color: '#22c55e' },
  { key: 'mpfm_gas', label: 'MPFM Gás (t)', color: '#f59e0b' },
  { key: 'mpfm_water', label: 'MPFM Água (t)', color: '#94a3b8' },
  { key: 'mpfm_hc', label: 'MPFM HC (t)', color: '#26a0ff' },
  { key: 'mpfm_total', label: 'MPFM Total (t)', color: '#0ea5e9' },
  { key: 'sep_oil', label: 'Separador Óleo (t)', color: '#8b5cf6' },
  { key: 'sep_gas', label: 'Separador Gás (t)', color: '#ec4899' },
  { key: 'sep_water', label: 'Separador Água (t)', color: '#c084fc' },
  { key: 'sep_hc', label: 'Separador HC (t)', color: '#a855f7' },
  { key: 'sep_total', label: 'Separador Total (t)', color: '#7c3aed' },
];
const SUMMARY_DAILY_SERIES_DEFAULT = ['mpfm_hc', 'mpfm_total', 'sep_hc', 'sep_total'];

function summaryColorAlpha(hex, alpha) {
  const base = String(hex || '').trim();
  const normalized = base.startsWith('#') ? base.slice(1) : base;
  if (!/^[0-9a-f]{6}$/i.test(normalized)) return hex;
  const r = parseInt(normalized.slice(0, 2), 16);
  const g = parseInt(normalized.slice(2, 4), 16);
  const b = parseInt(normalized.slice(4, 6), 16);
  return `rgba(${r},${g},${b},${alpha})`;
}

function summaryLayoutState() {
  const saved = (state.prefs && state.prefs.summary_layout) || {};
  state.summaryLayout = Object.assign({}, SUMMARY_LAYOUT_DEFAULTS, saved, state.summaryLayout || {});
  return state.summaryLayout;
}

function summaryDailyChartState() {
  const saved = (state.prefs && state.prefs.summary_daily_chart) || {};
  const current = state.summaryDailyChart || {};
  const source = Array.isArray(current.visibleSeries)
    ? current.visibleSeries
    : Array.isArray(saved.visibleSeries)
      ? saved.visibleSeries
      : SUMMARY_DAILY_SERIES_DEFAULT;
  const visibleSeries = Array.from(new Set(source.filter(key => SUMMARY_DAILY_SERIES.some(series => series.key === key))));
  state.summaryDailyChart = { visibleSeries: visibleSeries.length || source.length === 0 ? visibleSeries : SUMMARY_DAILY_SERIES_DEFAULT.slice() };
  return state.summaryDailyChart;
}

function persistSummaryUiPrefs() {
  state.prefs = state.prefs || {};
  state.prefs.summary_layout = Object.assign({}, summaryLayoutState());
  state.prefs.summary_daily_chart = { visibleSeries: summaryDailyChartState().visibleSeries.slice() };
  j(`${API}/user-prefs`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(state.prefs)
  }).catch(() => null);
}

function summaryApplyVisibility() {
  const layout = summaryLayoutState();
  const mapping = [
    { key: 'cards', targetId: 'summaryCards', buttonId: 'btnToggleSummaryCards', noun: 'cards' },
    { key: 'bank', targetId: 'sumBankCardBody', buttonId: 'btnToggleBankTables', noun: 'tabela' },
    { key: 'tag', targetId: 'sumTagCardBody', buttonId: 'btnToggleTagTables', noun: 'tabela' },
    { key: 'daily', targetId: 'sumDailyCardBody', buttonId: 'btnToggleDailyProduction', noun: 'painel' },
  ];
  mapping.forEach(item => {
    const target = document.getElementById(item.targetId);
    const button = document.getElementById(item.buttonId);
    const visible = layout[item.key] !== false;
    if (target) target.hidden = !visible;
    if (button) {
      button.textContent = visible ? `Ocultar ${item.noun}` : `Mostrar ${item.noun}`;
      button.setAttribute('aria-expanded', String(visible));
    }
  });
  const btnAll = document.getElementById('btnToggleSummaryAll');
  if (btnAll) {
    const allVisible = mapping.every(item => layout[item.key] !== false);
    btnAll.textContent = allVisible ? 'Recolher tudo' : 'Expandir tudo';
    btnAll.setAttribute('aria-expanded', String(allVisible));
  }
}

function bindSummaryVisibilityControls() {
  if (window.__summaryVisibilityControlsBound) return;
  window.__summaryVisibilityControlsBound = true;
  [
    ['btnToggleSummaryAll', 'all'],
    ['btnToggleSummaryCards', 'cards'],
    ['btnToggleBankTables', 'bank'],
    ['btnToggleTagTables', 'tag'],
    ['btnToggleDailyProduction', 'daily'],
  ].forEach(([buttonId, key]) => {
    const button = document.getElementById(buttonId);
    if (!button) return;
    button.onclick = () => {
      const layout = summaryLayoutState();
      if (key === 'all') {
        const nextVisible = !['cards', 'bank', 'tag', 'daily'].every(panelKey => layout[panelKey] !== false);
        ['cards', 'bank', 'tag', 'daily'].forEach(panelKey => { layout[panelKey] = nextVisible; });
        summaryApplyVisibility();
        persistSummaryUiPrefs();
        return;
      }
      layout[key] = !(layout[key] !== false);
      summaryApplyVisibility();
      persistSummaryUiPrefs();
    };
  });
}

function summaryEnsureDailyChartPlugins() {
  if (!window.Chart || window.__summaryDailyChartPluginsRegistered) return;
  Chart.register({
    id: 'summaryDailySelectedDayBand',
    beforeDatasetsDraw(chart, _args, pluginOptions) {
      if (!pluginOptions?.enabled || !chart?.chartArea || !chart?.scales?.x) return;
      const index = Number(pluginOptions.selectedIndex);
      if (!Number.isFinite(index) || index < 0) return;
      const xScale = chart.scales.x;
      const center = xScale.getPixelForValue(index);
      if (!Number.isFinite(center)) return;
      const prev = index > 0 ? xScale.getPixelForValue(index - 1) : chart.chartArea.left;
      const next = index < pluginOptions.labelCount - 1 ? xScale.getPixelForValue(index + 1) : chart.chartArea.right;
      const halfLeft = index > 0 ? (center - prev) / 2 : (next - center) / 2;
      const halfRight = index < pluginOptions.labelCount - 1 ? (next - center) / 2 : (center - prev) / 2;
      const left = Math.max(chart.chartArea.left, center - halfLeft);
      const right = Math.min(chart.chartArea.right, center + halfRight);
      const { ctx } = chart;
      ctx.save();
      ctx.fillStyle = pluginOptions.fill || 'rgba(38,160,255,.08)';
      ctx.strokeStyle = pluginOptions.stroke || 'rgba(38,160,255,.28)';
      ctx.lineWidth = 1;
      ctx.fillRect(left, chart.chartArea.top, Math.max(0, right - left), chart.chartArea.bottom - chart.chartArea.top);
      ctx.strokeRect(left + 0.5, chart.chartArea.top + 0.5, Math.max(0, right - left - 1), Math.max(0, chart.chartArea.bottom - chart.chartArea.top - 1));
      ctx.restore();
    }
  });
  window.__summaryDailyChartPluginsRegistered = true;
}

function summaryDailySeriesMarkup(def, checked, disabled) {
  return `<label class="summary-series-toggle${disabled ? ' is-disabled' : ''}">
    <input type="checkbox" data-series-key="${def.key}" ${checked ? 'checked' : ''} ${disabled ? 'disabled' : ''}>
    <i style="background:${def.color}"></i>
    <span>${def.label}</span>
  </label>`;
}

function summaryDailySeriesGroupMarkup(title, defs, rows, chartState) {
  const items = defs.map(def => {
    const hasData = rows.some(row => row?.[def.key] != null);
    const checked = chartState.visibleSeries.includes(def.key);
    return summaryDailySeriesMarkup(def, checked, !hasData);
  }).join('');
  return `<div class="summary-series-group">
    <div class="summary-series-group__title">${title}</div>
    <div class="summary-series-group__items">${items}</div>
  </div>`;
}

function summaryDailyChartHoverHtml(dayRow, defs) {
  if (!dayRow) return 'Passe o mouse nas barras para ver os valores do dia. Clique em um dia para sincronizar a composição abaixo.';
  const values = defs
    .map(def => dayRow?.[def.key] == null ? '' : `<span><i style="background:${def.color}"></i>${def.label}: <strong>${fmt(Number(dayRow[def.key]) || 0)}</strong></span>`)
    .filter(Boolean)
    .join('');
  return `<span class="summary-chart-hover__day">${fmtDate(dayRow.day)}</span>${values ? `<span class="summary-chart-hover__values">${values}</span>` : '<span class="summary-chart-hover__empty">Sem séries visíveis com valor neste dia.</span>'}`;
}

function summaryBindDailyChartInteractions(chart, daily, defs) {
  const canvas = document.getElementById('sumDailyChart');
  const hover = document.getElementById('sumDailyChartHover');
  if (!canvas || !hover || !chart?.scales?.x || !daily.length) return;
  const resolveIndex = (event) => {
    const rect = canvas.getBoundingClientRect();
    const offsetX = event.clientX - rect.left;
    let bestIndex = -1;
    let bestDistance = Infinity;
    for (let i = 0; i < daily.length; i += 1) {
      const px = chart.scales.x.getPixelForValue(i);
      const distance = Math.abs(px - offsetX);
      if (distance < bestDistance) {
        bestDistance = distance;
        bestIndex = i;
      }
    }
    const threshold = Math.max(18, rect.width / Math.max(10, daily.length * 1.4));
    return bestDistance <= threshold ? bestIndex : -1;
  };
  const updateHover = (index) => {
    const row = index >= 0 ? daily[index] : null;
    hover.innerHTML = summaryDailyChartHoverHtml(row, defs);
    canvas.style.cursor = row ? 'pointer' : 'default';
  };
  canvas.onmousemove = (event) => {
    updateHover(resolveIndex(event));
  };
  canvas.onmouseleave = () => {
    updateHover(-1);
  };
  canvas.onclick = (event) => {
    const index = resolveIndex(event);
    if (index < 0) return;
    selectSummaryDay(daily[index].day);
    updateHover(index);
  };
  const selectedIndex = Math.max(0, daily.findIndex(row => row.day === (state.summary?.day || '')));
  updateHover(selectedIndex >= 0 ? selectedIndex : -1);
}

function renderSummaryDailySeriesControls(rows) {
  const host = document.getElementById('sumDailyChartSeries');
  if (!host) return;
  const chartState = summaryDailyChartState();
  const mpfmDefs = SUMMARY_DAILY_SERIES.filter(def => def.key.startsWith('mpfm_'));
  const sepDefs = SUMMARY_DAILY_SERIES.filter(def => def.key.startsWith('sep_'));
  host.innerHTML = [
    summaryDailySeriesGroupMarkup('MPFM', mpfmDefs, rows, chartState),
    summaryDailySeriesGroupMarkup('Separador', sepDefs, rows, chartState),
  ].join('');
  host.querySelectorAll('input[data-series-key]').forEach(input => {
    input.onchange = () => {
      const key = input.dataset.seriesKey || '';
      const next = new Set(summaryDailyChartState().visibleSeries);
      if (input.checked) next.add(key);
      else next.delete(key);
      state.summaryDailyChart.visibleSeries = SUMMARY_DAILY_SERIES.map(series => series.key).filter(seriesKey => next.has(seriesKey));
      persistSummaryUiPrefs();
      renderSummaryDailyChart();
    };
  });
  const setVisible = (keys) => {
    state.summaryDailyChart = { visibleSeries: keys.slice() };
    persistSummaryUiPrefs();
    renderSummaryDailyChart();
  };
  const btnAll = document.getElementById('btnSumDailySeriesAll');
  const btnCore = document.getElementById('btnSumDailySeriesCore');
  const btnNone = document.getElementById('btnSumDailySeriesNone');
  if (btnAll) btnAll.onclick = () => setVisible(SUMMARY_DAILY_SERIES.filter(def => rows.some(row => row?.[def.key] != null)).map(def => def.key));
  if (btnCore) btnCore.onclick = () => setVisible(SUMMARY_DAILY_SERIES_DEFAULT.filter(key => rows.some(row => row?.[key] != null)));
  if (btnNone) btnNone.onclick = () => setVisible([]);
}

function renderSummaryDailyChart() {
  const wrap = document.getElementById('sumDailyChartWrap');
  const stage = document.getElementById('sumDailyChartStage');
  const canvas = document.getElementById('sumDailyChart');
  const empty = document.getElementById('sumDailyChartEmpty');
  const legend = document.getElementById('sumDailyChartLegend');
  const hover = document.getElementById('sumDailyChartHover');
  const daily = ((state.summaryMonthData || {}).daily || []).filter(row => row && row.has_data);
  if (!wrap || !stage || !canvas || !empty || !legend || !hover) return;
  summaryEnsureDailyChartPlugins();

  renderSummaryDailySeriesControls(daily);
  if (_summaryDailyChart) {
    _summaryDailyChart.destroy();
    _summaryDailyChart = null;
  }
  canvas.onmousemove = null;
  canvas.onmouseleave = null;
  canvas.onclick = null;
  if (!window.Chart || !daily.length) {
    empty.style.display = 'flex';
    legend.textContent = 'Sem dados diários para montar o gráfico.';
    hover.innerHTML = 'Passe o mouse nas barras para ver os valores do dia. Clique em um dia para sincronizar a composição abaixo.';
    return;
  }

  const chartState = summaryDailyChartState();
  const selectedDay = state.summary?.day || '';
  const selectedDefs = SUMMARY_DAILY_SERIES
    .filter(def => chartState.visibleSeries.includes(def.key))
    .filter(def => daily.some(row => row?.[def.key] != null));
  if (!selectedDefs.length) {
    empty.style.display = 'flex';
    legend.textContent = 'Selecione ao menos uma série com dados para montar o gráfico.';
    hover.innerHTML = 'Nenhuma série visível no momento. Marque ao menos uma opção em MPFM ou Separador.';
    return;
  }

  const labels = daily.map(row => fmtDate(row.day));
  const slotWidth = Math.max(58, selectedDefs.length * 18);
  stage.style.width = `${Math.max(wrap.clientWidth || 0, labels.length * slotWidth)}px`;
  stage.style.height = `${Math.max(wrap.clientHeight || 0, 320)}px`;
  stage.style.minHeight = `${Math.max(wrap.clientHeight || 0, 320)}px`;
  canvas.style.width = '100%';
  canvas.style.height = '100%';

  const bodyStyle = getComputedStyle(document.body);
  const cMuted = bodyStyle.getPropertyValue('--muted').trim() || '#8ea3ba';
  const cGrid = bodyStyle.getPropertyValue('--line').trim() || '#20324d';
  const datasets = selectedDefs.map(def => ({
    type: 'bar',
    label: def.label,
    data: daily.map(row => row?.[def.key] == null ? null : Number(row[def.key])),
    borderColor: daily.map(row => row.day === selectedDay ? summaryColorAlpha(def.color, 1) : summaryColorAlpha(def.color, 0.92)),
    backgroundColor: daily.map(row => row.day === selectedDay ? summaryColorAlpha(def.color, 1) : summaryColorAlpha(def.color, 0.55)),
    borderWidth: daily.map(row => row.day === selectedDay ? 3 : 1),
  }));

  _summaryDailyChart = new Chart(canvas.getContext('2d'), {
    type: 'bar',
    data: { labels, datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        summaryDailySelectedDayBand: {
          enabled: !!selectedDay,
          selectedIndex: daily.findIndex(row => row.day === selectedDay),
          labelCount: labels.length,
          fill: 'rgba(38,160,255,.10)',
          stroke: 'rgba(38,160,255,.28)'
        }
      },
      scales: {
        x: {
          grid: { color: cGrid },
          ticks: { color: cMuted, font: { size: 11 }, autoSkip: false, maxRotation: 0, minRotation: 0 },
          title: { display: true, text: 'Dia do mês', color: cMuted, font: { size: 11 } }
        },
        y: {
          beginAtZero: true,
          grid: { color: cGrid },
          ticks: {
            color: cMuted,
            font: { size: 11 },
            callback: value => fmt(Number(value) || 0)
          },
          title: { display: true, text: 'Produção diária (t)', color: cMuted, font: { size: 11 } }
        }
      },
      animation: { duration: (typeof prefersReducedMotion === 'function' && prefersReducedMotion()) ? 0 : 250 }
    }
  });
  requestAnimationFrame(() => {
    if (_summaryDailyChart) _summaryDailyChart.resize();
  });
  empty.style.display = 'none';
  const selectedLabel = selectedDay ? fmtDate(selectedDay) : 'nenhum';
  legend.innerHTML = `${daily.length} dia(s) com dados &nbsp;·&nbsp; <strong>${selectedDefs.length}</strong> série(s) visíveis &nbsp;·&nbsp; dia selecionado: <strong>${selectedLabel}</strong>`;
  summaryBindDailyChartInteractions(_summaryDailyChart, daily, selectedDefs);
}

function renderSummaryBankDaily() {
  const host = document.getElementById('sumByBankDaily');
  const data = state.summaryMonthData || {};
  const bank = state.summary?.bank || '';
  const rows = (data.bank_daily || []).filter(r => r.bank === bank);
  if (!host) return;
  host.innerHTML = rows.length ? `
    <table class="table">
      <thead><tr>
        <th>Dia</th><th>Horas</th><th>TAGs</th><th>HC (t)</th><th>Total (t)</th><th>Óleo (t)</th><th>Gás (t)</th><th>Água (t)</th><th>Óleo (m³)</th><th>Gás (mil sm³)</th><th>Água (m³)</th><th>Óleo (bbl)</th><th>BOE Total</th>
      </tr></thead>
      <tbody>
        ${rows.map(r => `<tr>
          <td class="mono">${fmtDate(r.day)}</td>
          <td class="mono">${r.hours}</td>
          <td class="mono">${r.tags_count}</td>
          <td class="num" style="color:var(--accent);font-weight:600">${fmt(r.hc_t)}</td>
          <td class="num">${fmt(r.total_t)}</td>
          <td class="num">${fmt(r.oil_t)}</td>
          <td class="num">${fmt(r.gas_t)}</td>
          <td class="num">${fmt(r.water_t)}</td>
          <td class="num">${fmt(r.oil_m3)}</td>
          <td class="num">${fmtMilSm3(r.gas_sm3)}</td>
          <td class="num">${fmt(r.water_m3)}</td>
          <td class="num">${fmt(r.oil_bbl)}</td>
          <td class="num">${fmt(r.boe_total)}</td>
        </tr>`).join('')}
      </tbody>
    </table>` : '<div class="muted" style="padding:12px 0">Selecione um banco com dados para ver a evolução diária.</div>';
}

function renderSummaryTagDaily() {
  const host = document.getElementById('sumByTagDaily');
  const data = state.summaryMonthData || {};
  const tagKey = state.summary?.tag || '';
  const rows = (data.tag_daily || []).filter(r => `${r.bank}||${r.tag}` === tagKey);
  if (!host) return;
  host.innerHTML = rows.length ? `
    <table class="table">
      <thead><tr>
        <th>Dia</th><th>Horas</th><th>HC (t)</th><th>Total (t)</th><th>Óleo (t)</th><th>Gás (t)</th><th>Água (t)</th><th>Óleo (m³)</th><th>Gás (mil sm³)</th><th>Água (m³)</th><th>Óleo (bbl)</th><th>BOE Total</th>
      </tr></thead>
      <tbody>
        ${rows.map(r => `<tr>
          <td class="mono">${fmtDate(r.day)}</td>
          <td class="mono">${r.hours}</td>
          <td class="num" style="color:var(--accent);font-weight:600">${fmt(r.hc_t)}</td>
          <td class="num">${fmt(r.total_t)}</td>
          <td class="num">${fmt(r.oil_t)}</td>
          <td class="num">${fmt(r.gas_t)}</td>
          <td class="num">${fmt(r.water_t)}</td>
          <td class="num">${fmt(r.oil_m3)}</td>
          <td class="num">${fmtMilSm3(r.gas_sm3)}</td>
          <td class="num">${fmt(r.water_m3)}</td>
          <td class="num">${fmt(r.oil_bbl)}</td>
          <td class="num">${fmt(r.boe_total)}</td>
        </tr>`).join('')}
      </tbody>
    </table>` : '<div class="muted" style="padding:12px 0">Selecione uma TAG para ver a composição diária.</div>';
}

function renderSummaryDayDetail() {
  const host = document.getElementById('sumDailyDetail');
  const meta = document.getElementById('sumDailyDetailMeta');
  const data = state.summaryMonthData || {};
  const day = state.summary?.day || '';
  const dayRow = (data.daily || []).find(r => r.day === day);
  const tagRows = (data.tag_daily || []).filter(r => r.day === day).sort((a, b) => `${a.bank}${a.tag}`.localeCompare(`${b.bank}${b.tag}`));
  if (!host || !meta) return;
  if (!dayRow) {
    meta.textContent = 'Selecione um dia com dados.';
    host.innerHTML = '<div class="muted" style="padding:12px 0">Sem decomposição carregada.</div>';
    return;
  }
  const sepSourceLabelBase = dayRow.sep_source === 'consolidado' ? 'consolidação oficial do separador' : dayRow.sep_source === 'detalhe_manual' ? 'detalhe do separador cadastrado na aplicação' : 'sem dados do separador';
  const sepSourceLabel = dayRow.sep_zero_day ? `${sepSourceLabelBase} · dia zerado` : sepSourceLabelBase;
  meta.textContent = `${fmtDate(dayRow.day)} · separador: ${sepSourceLabel}`;
  host.innerHTML = `
    <div class="summary-decomp-grid">
      <div class="summary-mini-card">
        <div class="summary-mini-card__label">MPFM do dia</div>
        <div class="summary-mini-card__value">${fmt(dayRow.mpfm_total)}</div>
        <div class="summary-mini-card__meta">Total (t) · HC ${fmt(dayRow.mpfm_hc)}</div>
      </div>
      <div class="summary-mini-card">
        <div class="summary-mini-card__label">Separador do dia</div>
        <div class="summary-mini-card__value">${dayRow.sep_total == null ? '—' : fmt(dayRow.sep_total)}</div>
        <div class="summary-mini-card__meta">HC ${dayRow.sep_hc == null ? '—' : fmt(dayRow.sep_hc)} · ${sepSourceLabel}</div>
      </div>
      <div class="summary-mini-card">
        <div class="summary-mini-card__label">Equivalência</div>
        <div class="summary-mini-card__value">${fmt(dayRow.mpfm_boe)}</div>
        <div class="summary-mini-card__meta">Óleo (bbl) ${fmt(dayRow.mpfm_oil_bbl)} · Gás (boe) ${fmt(dayRow.mpfm_gas_boe)}</div>
      </div>
    </div>
    <div class="tablewrap summary-scroll-box" style="margin-top:12px">
      <table class="table">
        <thead><tr>
          <th>Banco</th><th>TAG</th><th>Horas</th><th>Óleo (t)</th><th>Gás (t)</th><th>Água (t)</th><th>HC (t)</th><th>Total (t)</th><th>Óleo (m³)</th><th>Gás (mil sm³)</th><th>Água (m³)</th>
        </tr></thead>
        <tbody>
          ${tagRows.map(r => `<tr>
            <td>${tagChip(r.bank)}</td>
            <td class="mono">${r.tag}</td>
            <td class="mono">${r.hours}</td>
            <td class="num">${fmt(r.oil_t)}</td>
            <td class="num">${fmt(r.gas_t)}</td>
            <td class="num">${fmt(r.water_t)}</td>
            <td class="num" style="color:var(--accent);font-weight:600">${fmt(r.hc_t)}${(()=>{const calc=r.hc_calc??r.oil_t+r.gas_t;const diff=Math.abs(r.hc_t-calc);return r.hc_t>0&&diff>0.5?` <span title="HC do PDF (${fmt(r.hc_t)} t) ≠ Óleo+Gás (${fmt(calc)} t) · diff: ${fmt(diff)} t — possível inconsistência no parsing do PDF" style="color:var(--amber);cursor:help;font-size:10px;font-weight:400">⚠</span>`:''})()}</td>
            <td class="num">${fmt(r.total_t)}</td>
            <td class="num">${fmt(r.oil_m3)}</td>
            <td class="num">${fmtMilSm3(r.gas_sm3)}</td>
            <td class="num">${fmt(r.water_m3)}</td>
          </tr>`).join('') || '<tr><td colspan="11" class="muted">Sem TAGs detalhadas para este dia.</td></tr>'}
        </tbody>
      </table>
    </div>
    <div class="tablewrap summary-scroll-box" style="margin-top:12px">
      <table class="table">
        <thead><tr><th>Origem</th><th>Óleo (t)</th><th>Gás (t)</th><th>Água (t)</th><th>HC (t)</th><th>Total (t)</th><th>Óleo (m³)</th><th>Gás (mil sm³)</th><th>Água (sm³)</th></tr></thead>
        <tbody><tr>
          <td>${sepSourceLabel}</td>
          <td class="num">${dayRow.sep_oil == null ? '—' : fmt(dayRow.sep_oil)}</td>
          <td class="num">${dayRow.sep_gas == null ? '—' : fmt(dayRow.sep_gas)}</td>
          <td class="num">${dayRow.sep_water == null ? '—' : fmt(dayRow.sep_water)}</td>
          <td class="num">${dayRow.sep_hc == null ? '—' : fmt(dayRow.sep_hc)}</td>
          <td class="num">${dayRow.sep_total == null ? '—' : fmt(dayRow.sep_total)}</td>
          <td class="num">${dayRow.sep_oil_m3 == null ? '—' : fmt(dayRow.sep_oil_m3)}</td>
          <td class="num">${dayRow.sep_gas_sm3 == null ? '—' : fmtMilSm3(dayRow.sep_gas_sm3)}</td>
          <td class="num">${dayRow.sep_water_sm3 == null ? '—' : fmt(dayRow.sep_water_sm3)}</td>
        </tr></tbody>
      </table>
    </div>`;
}

window.selectSummaryDay = (day) => {
  state.summary = state.summary || {};
  state.summary.day = day || '';
  const sel = document.getElementById('sumDailyDetailSelect');
  if (sel) sel.value = state.summary.day;
  renderSummaryDayDetail();
  renderSummaryDailyChart();
};

async function loadSummary(silent = false) {
  if (!silent) setLoading('page-resumo', true);
  try {
  const month = document.getElementById('globalMonth')?.value || '';
  const d = await j(`${API}/ops/month-summary?month=${month}`).catch(() => ({}));
  state.summaryMonthData = d;
  const p = d.production || {};
  const mesLabel = summaryMonthLabel(month || d.month);
  const conversion = d.conversion || {
    oil_m3_to_bbl_factor: 6.28981,
    gas_sm3_per_boe_factor: 170,
    gas_input_unit: 'Sm³',
    gas_boe_mode: 'Padrão corporativo',
    show_boe_criterion: true,
  };

  // Always sync month selector from server list (catches newly imported months)
  const sel = document.getElementById('globalMonth');
  if (sel && d.months_available && d.months_available.length) {
    const current = sel.value;
    sel.innerHTML = d.months_available.map(m => {
      const [y2, m2] = m.split('-');
      return `<option value="${m}">${summaryMonthLabel(m)}</option>`;
    }).join('');
    // Restore previously selected month if still available, else pick latest
    if (current && [...sel.options].some(o => o.value === current)) {
      sel.value = current;
    } else if (d.month) {
      sel.value = d.month;
    }
  }

  // KPI cards — production data
  const savedIcons = (state.prefs && state.prefs.summary_icons) || {};
  const iconMap = {
    'Óleo (m³)': savedIcons['Óleo (m³)'] || 'oil',
    'Gás (mil sm³)': savedIcons['Gás (mil sm³)'] || savedIcons['Gás (Mil sm³)'] || savedIcons['Gás (sm³)'] || savedIcons['Gás (Sm³)'] || 'gas',
    'Água (m³)': savedIcons['Água (m³)'] || 'water',
    'Óleo (bbl/d)': savedIcons['Óleo (bbl/d)'] || savedIcons['Barris/dia'] || savedIcons['Óleo (bbl)'] || 'barrel',
    'BOE': savedIcons['BOE'] || savedIcons['BOE Total'] || 'boe',
    'Óleo (t)': savedIcons['Óleo (t)'] || 'oil',
    'Gás (t)': savedIcons['Gás (t)'] || 'gas',
    'Água (t)': savedIcons['Água (t)'] || 'water',
    'HC Total (t)': savedIcons['HC Total (t)'] || savedIcons['HC (t)'] || 'hc',
    'Total (t)': savedIcons['Total (t)'] || 'pipeline',
  };
  const boeTooltip = `BOE Total = (Óleo m³ × ${fmt(conversion.oil_m3_to_bbl_factor)}) + (Gás ${summaryDisplayUnit(conversion.gas_input_unit)} ÷ ${fmt(conversion.gas_sm3_per_boe_factor)})`;
  document.getElementById('summaryCards').innerHTML = [
    summaryCardMarkup('Óleo (t)', fmt(p.oil_t || 0), 'óleo corrigido', '--green', mesLabel, iconMap),
    summaryCardMarkup('Gás (t)', fmt(p.gas_t || 0), 'gás corrigido', '--amber', mesLabel, iconMap),
    summaryCardMarkup('Água (t)', fmt(p.water_t || 0), 'água corrigida', '--muted', mesLabel, iconMap),
    summaryCardMarkup('HC Total (t)', fmt(p.hc_t || 0), 'hidrocarboneto corrigido', '--accent', mesLabel, iconMap),
    summaryCardMarkup('Total (t)', fmt(p.total_t || 0), 'óleo + gás + água', '--purple', mesLabel, iconMap),
    summaryCardMarkup('Óleo (m³)', fmt(p.oil_m3 || 0), 'PVT @20 volume', '--green', mesLabel, iconMap),
    summaryCardMarkup('Gás (mil sm³)', fmtMilSm3(p.gas_sm3 || 0), 'PVT @20 volume', '--amber', mesLabel, iconMap),
    summaryCardMarkup('Água (m³)', fmt(p.water_m3 || 0), 'PVT @20 volume', '--muted', mesLabel, iconMap),
    summaryCardMarkup('Óleo (bbl/d)', fmt(p.oil_bbl || 0), `convertido de m³ × ${fmt(conversion.oil_m3_to_bbl_factor)}`, '--green', mesLabel, iconMap),
    summaryCardMarkup('BOE', fmt(p.boe_total || p.boe || 0), 'óleo em bbl + gás em boe', '--accent', mesLabel, iconMap, {
      criterion: conversion.show_boe_criterion ? summaryConversionText(conversion) : '',
      tooltip: boeTooltip,
    }),
  ].join('');

  loadDeadlinesSummary();
  // By bank table
  document.getElementById('sumByBank').innerHTML =
    (d.by_bank||[]).map(r =>
      `<tr>
        <td>${tagChip(r.bank)}</td>
        <td class="mono">${r.days}</td>
        <td class="mono">${r.hours}</td>
        <td class="num" style="color:var(--accent);font-weight:600">${fmt(r.hc_t)}</td>
        <td class="num">${fmt(r.total_t)}</td>
        <td class="num">${fmt(r.oil_t)}</td>
        <td class="num">${fmt(r.gas_t)}</td>
        <td class="num">${fmt(r.water_t)}</td>
        <td class="num">${fmt(r.oil_m3)}</td>
        <td class="num">${fmtMilSm3(r.gas_sm3)}</td>
        <td class="num">${fmt(r.water_m3)}</td>
        <td class="num">${fmt(r.oil_bbl)}</td>
        <td class="num">${fmt(r.boe_total || r.boe)}</td>
      </tr>`
    ).join('') || '<tr><td colspan="13" class="muted">Sem dados para o mês.</td></tr>';

  // By TAG table
  document.getElementById('sumByTag').innerHTML =
    (d.by_tag||[]).map(r =>
      `<tr>
        <td>${tagChip(r.bank)}</td>
        <td class="mono" style="font-size:12px">${r.tag}</td>
        <td class="mono">${r.days}</td>
        <td class="num" style="color:var(--accent);font-weight:600">${fmt(r.hc_t)}</td>
        <td class="num">${fmt(r.total_t)}</td>
        <td class="num">${fmt(r.oil_t)}</td>
        <td class="num">${fmt(r.gas_t)}</td>
        <td class="num">${fmt(r.water_t)}</td>
        <td class="num">${fmt(r.oil_m3)}</td>
        <td class="num">${fmtMilSm3(r.gas_sm3)}</td>
        <td class="num">${fmt(r.water_m3)}</td>
        <td class="num">${fmt(r.oil_bbl)}</td>
        <td class="num">${fmt(r.boe_total || r.boe)}</td>
      </tr>`
    ).join('') || '<tr><td colspan="13" class="muted">Sem dados.</td></tr>';

  const daily = d.daily || [];
  document.getElementById('summaryRefreshInfo').textContent =
    `Atualizado ${new Date().toLocaleTimeString('pt-BR')} · auto ${state.autoRefresh?'ligado':'desligado'}`;

  const bankSel = document.getElementById('sumBankDetailSelect');
  const banks = [...new Set((d.by_bank || []).map(r => String(r.bank || '').trim()).filter(Boolean))];
  summarySelectOptions(bankSel, banks, 'bank', bank => bank);
  bankSel.onchange = () => { state.summary.bank = bankSel.value; renderSummaryBankDaily(); };
  renderSummaryBankDaily();

  const tagSel = document.getElementById('sumTagDetailSelect');
  const tags = (d.by_tag || [])
    .map(r => ({ value: `${r.bank}||${r.tag}`, label: `${r.bank} · ${r.tag}` }))
    .filter(item => item.value !== '||');
  summarySelectOptions(tagSel, tags, 'tag');
  tagSel.onchange = () => { state.summary.tag = tagSel.value; renderSummaryTagDaily(); };
  renderSummaryTagDaily();

  const daySel = document.getElementById('sumDailyDetailSelect');
  const days = daily.filter(x => x.has_data).map(x => x.day);
  summarySelectOptions(daySel, days.slice().reverse(), 'day', dayRef => fmtDate(dayRef));
  daySel.onchange = () => { state.summary.day = daySel.value; renderSummaryDayDetail(); renderSummaryDailyChart(); };
  renderSummaryDayDetail();
  bindSummaryVisibilityControls();
  summaryApplyVisibility();
  renderSummaryDailyChart();

  // Draw deviation chart
  await loadDesvioChart(month, d);

  // Wire chart mode toggle (radio) and limit toggles (checkboxes)
  const _rewireDesvio = () => loadDesvioChart(month, d);
  document.querySelectorAll('input[name="desvioMode"]').forEach(r => { r.onchange = _rewireDesvio; });
  const _hcCb  = document.getElementById('sumChartShowHc');
  const _totCb = document.getElementById('sumChartShowTotal');
  if (_hcCb)  _hcCb.onchange  = () => { (state.summaryChart = state.summaryChart || {}).showHcLimit    = _hcCb.checked;  _rewireDesvio(); };
  if (_totCb) _totCb.onchange = () => { (state.summaryChart = state.summaryChart || {}).showTotalLimit = _totCb.checked; _rewireDesvio(); };

  // Render monthly calendar
  renderMonthCalendar(month, d.daily || []);

  // Poço x Riser daily table
  initPocoRiserTable(month);
  } finally {
    if (!silent) setLoading('page-resumo', false);
  }
}

// ─── MONTHLY CALENDAR ─────────────────────────────────────────────────────────
function renderMonthCalendar(month, daily) {
  const el = document.getElementById('monthCalendar');
  if (!el) return;

  state.summaryDailyData = daily || [];

  const [yr, mo] = (month || '2026-01').split('-').map(Number);
  const daysInMonth = new Date(yr, mo, 0).getDate();
  const firstWeekday = new Date(yr, mo - 1, 1).getDay(); // 0=Sun
  // Convert Sunday-first to Monday-first (European)
  const startOffset = (firstWeekday + 6) % 7;

  // Build lookup: day_ref → row
  const lookup = {};
  (daily || []).forEach(x => { lookup[x.day] = x; });

  const DAYS_PT = ['Seg','Ter','Qua','Qui','Sex','Sáb','Dom'];
  let cells = DAYS_PT.map(d =>
    `<div class="calhead">${d}</div>`
  ).join('');

  // Empty leading cells
  for (let i = 0; i < startOffset; i++) {
    cells += `<div class="calday empty" style="background:transparent;border-color:transparent"></div>`;
  }

  const today = new Date().toISOString().slice(0, 10);
  const [, , todayD] = today.split('-').map(Number);
  const isThisMonth = today.slice(0, 7) === month;

  for (let d = 1; d <= daysInMonth; d++) {
    const dayRef = `${yr}-${String(mo).padStart(2,'0')}-${String(d).padStart(2,'0')}`;
    const row    = lookup[dayRef] || {};
    const hasMpfm = row.mpfm_hc != null && row.mpfm_hc > 0;
    const hasSep  = !!row.sep_present;
    const isToday = isThisMonth && d === todayD;

    let bg = 'var(--panel2)', bc = 'var(--line)';

    if (hasMpfm && hasSep) {
      bg = 'rgba(35,193,107,.14)'; bc = 'rgba(35,193,107,.45)';
    } else if (hasMpfm) {
      bg = 'rgba(38,160,255,.12)'; bc = 'rgba(38,160,255,.4)';
    } else if (hasSep) {
      bg = 'rgba(168,85,247,.12)'; bc = 'rgba(168,85,247,.4)';
    }

    const hasAny = hasMpfm || hasSep;
    const hcVal = hasMpfm ? row.mpfm_hc : row.sep_hc;
    const valStr = hasAny && hcVal != null ? `${new Intl.NumberFormat('pt-BR', {maximumFractionDigits:0}).format(hcVal)} t` : '';

    // Separador phase flags with fallback
    const sepDet = row.sep_details || {
      oleo: { tag: "20FT0247", label: "Óleo", present: hasSep },
      gas:  { tag: "20FT0244", label: "Gás", present: hasSep },
      agua: { tag: "20FT0251", label: "Água", present: hasSep },
      present_count: hasSep ? 3 : 0
    };
    const sepOleo = sepDet.oleo?.present;
    const sepGas  = sepDet.gas?.present;
    const sepAgua = sepDet.agua?.present;

    // MPFM details with fallback
    let mpfmDet = row.mpfm_details;
    if (!mpfmDet || (!mpfmDet.topside?.length && !mpfmDet.subsea?.length)) {
      mpfmDet = {
        topside: [
          { bank: 'B08', tag: 'Riser_P2', sensor_tag: '13FT0217', daily: hasMpfm, hourly: hasMpfm, hours: hasMpfm ? 24 : 0 },
          { bank: 'B13', tag: 'Riser_P4', sensor_tag: '13FT0317', daily: hasMpfm, hourly: hasMpfm, hours: hasMpfm ? 24 : 0 },
          { bank: 'B03', tag: 'Riser_P5', sensor_tag: '13FT0367', daily: hasMpfm, hourly: hasMpfm, hours: hasMpfm ? 24 : 0 },
        ],
        subsea: [
          { bank: 'B10', tag: 'PE_2', sensor_tag: '18FT0506', daily: hasMpfm, hourly: hasMpfm, hours: hasMpfm ? 24 : 0 },
          { bank: 'B15', tag: 'PW-104DA', sensor_tag: '18FT1106', daily: hasMpfm, hourly: hasMpfm, hours: hasMpfm ? 24 : 0 },
          { bank: 'B05', tag: 'PE_4', sensor_tag: '18FT1506', daily: hasMpfm, hourly: hasMpfm, hours: hasMpfm ? 24 : 0 },
        ]
      };
    }
    const topside = mpfmDet.topside || [];
    const subsea  = mpfmDet.subsea  || [];

    const renderMpfmRow = (items, title, icon) => {
      if (!items || !items.length) return '';
      const chips = items.map(item => {
        const dOk = item.daily;
        const hHrs = item.hours || 0;
        const col = dOk ? '#22c55e' : hHrs > 0 ? '#f59e0b' : '#ef4444';
        const tagShort = (item.tag || '').replace('Riser_', 'P').replace('PW-', '');
        return `<span class="cal-mini-chip" style="border-left: 2px solid ${col};" title="${item.tag} (${item.bank}): Diário ${dOk?'OK':'Ausente'} | Horário ${hHrs}h/24h">
          <strong style="color:var(--text);">${tagShort}</strong><span style="color:${col};font-weight:600">${dOk?'D✓':'D✗'}${hHrs?` ${hHrs}h`:''}</span>
        </span>`;
      }).join('');
      return `<div class="cal-sec-sub"><span class="cal-sec-title">${icon} ${title}:</span><div class="cal-chips-wrap">${chips}</div></div>`;
    };

    const todayBorder = isToday ? ';outline:2px solid var(--accent);outline-offset:1px' : '';

    cells += `
      <div class="calday calday-enhanced ${hasAny?'has-data':''}" style="background:${bg};border-color:${bc}${todayBorder};" onclick="openCaldayDetails('${dayRef}')" title="Clique para detalhar o cadastro de ${fmtDate(dayRef)}">
        <div class="calday-hdr">
          <span class="n" style="color:${isToday?'var(--accent)':hasAny?'var(--text)':'var(--muted)'}">${d}</span>
          ${valStr ? `<span class="calday-val">${valStr}</span>` : '<span class="calday-hint">🔍 Detalhar</span>'}
        </div>

        <!-- SEPARADOR -->
        <div class="calday-sec calday-sec-sep">
          <div class="cal-sec-title-row">
            <span class="cal-sec-title">🧪 SEP:</span>
            <span class="cal-sep-phase ${sepOleo?'ok':'missing'}" title="Óleo (20FT0247): ${sepOleo?'Presente':'Ausente'}">Ó${sepOleo?'✓':'✗'}</span>
            <span class="cal-sep-phase ${sepGas?'ok':'missing'}" title="Gás (20FT0244): ${sepGas?'Presente':'Ausente'}">G${sepGas?'✓':'✗'}</span>
            <span class="cal-sep-phase ${sepAgua?'ok':'missing'}" title="Água (20FT0251): ${sepAgua?'Presente':'Ausente'}">Á${sepAgua?'✓':'✗'}</span>
          </div>
        </div>

        <!-- MPFM TOPSIDE -->
        <div class="calday-sec">
          ${renderMpfmRow(topside, 'Topside', '🚢')}
        </div>

        <!-- MPFM SUBSEA -->
        <div class="calday-sec">
          ${renderMpfmRow(subsea, 'Subsea', '🌊')}
        </div>
      </div>
    `;
  }

  el.innerHTML = cells;
}

window.openCaldayDetails = function(dayRef) {
  const dailyList = state.summaryDailyData || [];
  const row = dailyList.find(x => x.day === dayRef) || { day: dayRef };
  const host = document.getElementById('caldayDetailBody');
  const titleEl = document.getElementById('caldayDetailTitle');

  if (titleEl) {
    titleEl.textContent = `📅 Detalhamento de Cobertura de Dados — ${fmtDate(dayRef)}`;
  }

  const hasMpfm = row.mpfm_hc != null && row.mpfm_hc > 0;
  const hasSep  = !!row.sep_present;

  const sepDet = row.sep_details || {
    oleo: { tag: "20FT0247", label: "Óleo", present: hasSep },
    gas:  { tag: "20FT0244", label: "Gás", present: hasSep },
    agua: { tag: "20FT0251", label: "Água", present: hasSep },
    present_count: hasSep ? 3 : 0
  };

  let mpfmDet = row.mpfm_details;
  if (!mpfmDet || (!mpfmDet.topside?.length && !mpfmDet.subsea?.length)) {
    mpfmDet = {
      topside: [
        { bank: 'B08', tag: 'Riser_P2', sensor_tag: '13FT0217', daily: hasMpfm, hourly: hasMpfm, hours: hasMpfm ? 24 : 0 },
        { bank: 'B13', tag: 'Riser_P4', sensor_tag: '13FT0317', daily: hasMpfm, hourly: hasMpfm, hours: hasMpfm ? 24 : 0 },
        { bank: 'B03', tag: 'Riser_P5', sensor_tag: '13FT0367', daily: hasMpfm, hourly: hasMpfm, hours: hasMpfm ? 24 : 0 },
      ],
      subsea: [
        { bank: 'B10', tag: 'PE_2', sensor_tag: '18FT0506', daily: hasMpfm, hourly: hasMpfm, hours: hasMpfm ? 24 : 0 },
        { bank: 'B15', tag: 'PW-104DA', sensor_tag: '18FT1106', daily: hasMpfm, hourly: hasMpfm, hours: hasMpfm ? 24 : 0 },
        { bank: 'B05', tag: 'PE_4', sensor_tag: '18FT1506', daily: hasMpfm, hourly: hasMpfm, hours: hasMpfm ? 24 : 0 },
      ]
    };
  }

  let html = `
    <!-- RESUMO DO DIA -->
    <div class="row row--sb-ac mb12" style="background:var(--panel2); padding:12px 16px; border-radius:10px; border:1px solid var(--line); flex-wrap:wrap; gap:16px;">
      <div>
        <div class="muted fs11">Data de Produção</div>
        <strong class="fs15">${fmtDate(dayRef)}</strong>
      </div>
      <div>
        <div class="muted fs11">Produção MPFM (HC)</div>
        <strong class="fs15" style="color:var(--accent);">${row.mpfm_hc != null ? fmt(row.mpfm_hc) + ' t' : '—'}</strong>
      </div>
      <div>
        <div class="muted fs11">Produção Separador (HC)</div>
        <strong class="fs15" style="color:var(--purple);">${row.sep_hc != null ? fmt(row.sep_hc) + ' t' : '—'}</strong>
      </div>
      <div>
        <div class="muted fs11">Horas Monit. Max</div>
        <strong class="fs15">${row.max_hrs || 0}h / 24h</strong>
      </div>
    </div>

    <!-- SEPARADOR DE TESTE -->
    <div class="card ops-card mb12">
      <h4 class="section-title modal-h3" style="color:var(--purple); margin-bottom:10px;">
        🧪 Separador de Teste — Medidores por Fase
      </h4>
      <div class="tablewrap">
        <table class="table">
          <thead>
            <tr>
              <th>Fase de Medição</th>
              <th>Tag / Medidor</th>
              <th>Status do Cadastro</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>🛢️ <strong>Óleo</strong></td>
              <td class="mono">${sepDet.oleo?.tag || '20FT0247'}</td>
              <td>
                ${sepDet.oleo?.present
                  ? '<span class="badge ok">🟢 Cadastrado (Presente)</span>'
                  : '<span class="badge missing">🔴 Ausente / Não Encontrado</span>'}
              </td>
            </tr>
            <tr>
              <td>💨 <strong>Gás</strong></td>
              <td class="mono">${sepDet.gas?.tag || '20FT0244'}</td>
              <td>
                ${sepDet.gas?.present
                  ? '<span class="badge ok">🟢 Cadastrado (Presente)</span>'
                  : '<span class="badge missing">🔴 Ausente / Não Encontrado</span>'}
              </td>
            </tr>
            <tr>
              <td>💧 <strong>Água</strong></td>
              <td class="mono">${sepDet.agua?.tag || '20FT0251'}</td>
              <td>
                ${sepDet.agua?.present
                  ? '<span class="badge ok">🟢 Cadastrado (Presente)</span>'
                  : '<span class="badge missing">🔴 Ausente / Não Encontrado</span>'}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- MPFM TOPSIDE -->
    <div class="card ops-card mb12">
      <h4 class="section-title modal-h3" style="color:var(--accent); margin-bottom:10px;">
        🚢 MPFM Topside — Risers em Operação
      </h4>
      <div class="tablewrap">
        <table class="table">
          <thead>
            <tr>
              <th>Sistema / Riser</th>
              <th>Banco</th>
              <th>Tag do Sensor</th>
              <th>Dado Diário</th>
              <th>Dado Horário</th>
            </tr>
          </thead>
          <tbody>
            ${(mpfmDet.topside || []).map(item => `
              <tr>
                <td class="mono"><strong>${item.tag}</strong></td>
                <td>${tagChip(item.bank)}</td>
                <td class="mono">${item.sensor_tag || '—'}</td>
                <td>
                  ${item.daily
                    ? '<span class="badge ok">🟢 Presente</span>'
                    : '<span class="badge missing">🔴 Ausente</span>'}
                </td>
                <td>
                  ${item.hourly
                    ? `<span class="badge ${item.hours>=24?'ok':'warn'}">${item.hours>=24?'🟢 24h':'🟡 '+item.hours+'h/24h'}</span>`
                    : '<span class="badge missing">🔴 Ausente (0h)</span>'}
                </td>
              </tr>
            `).join('') || '<tr><td colspan="5" class="muted text-center">Nenhum MPFM Topside cadastrado.</td></tr>'}
          </tbody>
        </table>
      </div>
    </div>

    <!-- MPFM SUBSEA -->
    <div class="card ops-card mb12">
      <h4 class="section-title modal-h3" style="color:var(--green); margin-bottom:10px;">
        🌊 MPFM Subsea — Poços em Operação
      </h4>
      <div class="tablewrap">
        <table class="table">
          <thead>
            <tr>
              <th>Poço / Sistema</th>
              <th>Banco</th>
              <th>Tag do Sensor</th>
              <th>Dado Diário</th>
              <th>Dado Horário</th>
            </tr>
          </thead>
          <tbody>
            ${(mpfmDet.subsea || []).map(item => `
              <tr>
                <td class="mono"><strong>${item.tag}</strong></td>
                <td>${tagChip(item.bank)}</td>
                <td class="mono">${item.sensor_tag || '—'}</td>
                <td>
                  ${item.daily
                    ? '<span class="badge ok">🟢 Presente</span>'
                    : '<span class="badge missing">🔴 Ausente</span>'}
                </td>
                <td>
                  ${item.hourly
                    ? `<span class="badge ${item.hours>=24?'ok':'warn'}">${item.hours>=24?'🟢 24h':'🟡 '+item.hours+'h/24h'}</span>`
                    : '<span class="badge missing">🔴 Ausente (0h)</span>'}
                </td>
              </tr>
            `).join('') || '<tr><td colspan="5" class="muted text-center">Nenhum MPFM Subsea cadastrado.</td></tr>'}
          </tbody>
        </table>
      </div>
    </div>
  `;

  if (host) host.innerHTML = html;
  const modal = document.getElementById('caldayDetailModal');
  if (modal) {
    modal.classList.add('show');
    modal.onclick = (e) => {
      if (e.target === modal) modal.classList.remove('show');
    };
  }
};

window.closeCaldayDetailsModal = function() {
  const modal = document.getElementById('caldayDetailModal');
  if (modal) modal.classList.remove('show');
};

// ─── DESVIO CHART ─────────────────────────────────────────────────────────────
let _desvioChart = null;
let _desvioPointLabelsRegistered = false;

function summaryEscapeHtml(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function summaryPctLabel(value) {
  if (value == null || Number.isNaN(Number(value))) return '—';
  const numeric = Number(value);
  return `${numeric > 0 ? '+' : ''}${numeric.toFixed(1)}%`;
}

function summaryLimitStatus(value, limit) {
  if (value == null || Number.isNaN(Number(value))) return '—';
  return Math.abs(Number(value)) <= Number(limit) ? 'Dentro do limite' : 'Fora do limite';
}

function summaryPairKey(subTag, topTag) {
  return `${subTag}__${topTag}`;
}

function summaryEnsureDesvioPlugins() {
  if (_desvioPointLabelsRegistered || !window.Chart) return;
  Chart.register({
    id: 'desvioPointLabels',
    afterDatasetsDraw(chart, _args, pluginOptions) {
      if (!pluginOptions?.enabled || !chart?.chartArea) return;
      const { ctx, chartArea } = chart;
      ctx.save();
      chart.data.datasets.forEach((dataset, datasetIndex) => {
        if (dataset.isLimitLine || dataset.hidePointLabels || !chart.isDatasetVisible(datasetIndex)) return;
        const meta = chart.getDatasetMeta(datasetIndex);
        const offsetY = Number.isFinite(dataset.pointLabelOffset) ? dataset.pointLabelOffset : -12;
        meta.data.forEach((element, pointIndex) => {
          const rawValue = dataset.data?.[pointIndex];
          if (rawValue == null || Number.isNaN(Number(rawValue))) return;
          const position = element.getProps(['x', 'y'], true);
          if (!Number.isFinite(position.x) || !Number.isFinite(position.y)) return;

          const text = summaryPctLabel(rawValue);
          ctx.font = '10px "IBM Plex Mono", monospace';
          const boxWidth = ctx.measureText(text).width + 8;
          const boxHeight = 16;
          const boxLeft = Math.min(Math.max(position.x - boxWidth / 2, chartArea.left), chartArea.right - boxWidth);
          const rawTop = offsetY < 0 ? position.y + offsetY - boxHeight : position.y + offsetY;
          const boxTop = Math.min(Math.max(rawTop, chartArea.top), chartArea.bottom - boxHeight);
          const textColor = Array.isArray(dataset.pointBorderColor)
            ? dataset.pointBorderColor[pointIndex]
            : (dataset.pointBorderColor || dataset.borderColor || '#dbe7f5');

          ctx.fillStyle = 'rgba(9,18,31,.88)';
          ctx.strokeStyle = 'rgba(32,50,77,.92)';
          ctx.lineWidth = 1;
          ctx.fillRect(boxLeft, boxTop, boxWidth, boxHeight);
          ctx.strokeRect(boxLeft, boxTop, boxWidth, boxHeight);
          ctx.fillStyle = typeof textColor === 'string' ? textColor : '#dbe7f5';
          ctx.textAlign = 'center';
          ctx.textBaseline = 'middle';
          ctx.fillText(text, boxLeft + boxWidth / 2, boxTop + boxHeight / 2 + 0.5);
        });
      });
      ctx.restore();
    }
  });
  _desvioPointLabelsRegistered = true;
}

function summarySetDesvioReportEnabled(enabled) {
  const button = document.getElementById('btnDesvioChartReport');
  if (button) button.disabled = !enabled;
}

function summaryRenderDesvioPairFilter(chartMode, pairOptions, selectedKeys, month, summaryData) {
  const bar = document.getElementById('desvioPairFilterBar');
  const list = document.getElementById('desvioPairFilterList');
  const meta = document.getElementById('desvioPairFilterMeta');
  const btnAll = document.getElementById('btnDesvioPairsAll');
  const btnNone = document.getElementById('btnDesvioPairsNone');
  if (!bar || !list) return;

  const isAnpMode = chartMode === 'anp' && pairOptions.length > 0;
  bar.hidden = !isAnpMode;
  if (!isAnpMode) {
    list.innerHTML = '';
    if (meta) meta.textContent = 'Selecione os pares que devem aparecer no gráfico e na página imprimível.';
    return;
  }

  const selectedSet = new Set(selectedKeys);
  list.innerHTML = pairOptions.map(pair => `
    <label class="summary-pair-chip${selectedSet.has(pair.key) ? ' is-active' : ''}">
      <input type="checkbox" value="${summaryEscapeHtml(pair.key)}" ${selectedSet.has(pair.key) ? 'checked' : ''}>
      <span class="summary-pair-chip__swatch" style="background:${pair.color}"></span>
      <span class="summary-pair-chip__text">${summaryEscapeHtml(pair.subLabel)} × ${summaryEscapeHtml(pair.topLabel)}</span>
    </label>
  `).join('');

  if (meta) {
    meta.textContent = selectedKeys.length
      ? `${selectedKeys.length} de ${pairOptions.length} pares exibidos no gráfico.`
      : 'Nenhum par selecionado. Marque ao menos um grupo para plotar.';
  }

  list.querySelectorAll('input[type="checkbox"]').forEach(input => {
    input.onchange = () => {
      const nextKeys = [...list.querySelectorAll('input[type="checkbox"]:checked')].map(node => node.value);
      (state.summaryChart = state.summaryChart || {}).selectedPairKeys = nextKeys;
      loadDesvioChart(month, summaryData);
    };
  });

  if (btnAll) {
    btnAll.onclick = () => {
      (state.summaryChart = state.summaryChart || {}).selectedPairKeys = pairOptions.map(pair => pair.key);
      loadDesvioChart(month, summaryData);
    };
  }
  if (btnNone) {
    btnNone.onclick = () => {
      (state.summaryChart = state.summaryChart || {}).selectedPairKeys = [];
      loadDesvioChart(month, summaryData);
    };
  }
}

function openDesvioChartReport() {
  const payload = state.summaryChart?.currentPayload;
  if (!payload || !payload.tableRows?.length) {
    window.alert('Carregue um gráfico com dados antes de gerar a página de tabela + gráfico.');
    return;
  }

  const chartImage = typeof _desvioChart?.toBase64Image === 'function'
    ? _desvioChart.toBase64Image()
    : document.getElementById('desvioChart')?.toDataURL('image/png');

  const rowsHtml = payload.tableRows.map(row => `
    <tr>
      ${payload.tableColumns.map(col => `<td class="${col.align === 'right' ? 'num' : ''}">${summaryEscapeHtml(row[col.key])}</td>`).join('')}
    </tr>
  `).join('');

  const html = `<!doctype html>
  <html lang="pt-BR">
  <head>
    <meta charset="utf-8">
    <title>${summaryEscapeHtml(payload.title)} · ${summaryEscapeHtml(payload.monthLabel)}</title>
    <style>
      :root { color-scheme: light; }
      * { box-sizing: border-box; }
      body { margin: 0; font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; color: #3a3a3a; background: #f6f7fb; }
      .page { max-width: 1280px; margin: 0 auto; padding: 24px 28px 40px; }
      .toolbar { display: flex; justify-content: space-between; align-items: center; gap: 12px; margin-bottom: 20px; }
      .toolbar-buttons { display: flex; gap: 8px; flex-wrap: wrap; }
      .btn { border: 1px solid #e0e0e0; background: #ffffff; color: #002060; border-radius: 999px; padding: 9px 14px; font-size: 13px; cursor: pointer; }
      .hero { background: #ffffff; border: 1px solid #e0e0e0; border-radius: 14px; padding: 22px 24px; }
      .eyebrow { font-size: 11px; text-transform: uppercase; letter-spacing: .08em; color: #6b7280; font-weight: 700; }
      h1 { margin: 8px 0 6px; font-size: 28px; line-height: 1.1; }
      .subtitle { color: #6b7280; font-size: 13px; margin-bottom: 14px; }
      .chips { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 12px; }
      .chip { border-radius: 999px; background: #f8fafc; color: #002060; border: 1px solid #e0e0e0; padding: 7px 10px; font-size: 12px; }
      .layout { display: grid; gap: 18px; margin-top: 18px; }
      .chart-card, .table-card { background: #ffffff; border: 1px solid #e0e0e0; border-radius: 14px; padding: 18px 20px; }
      .section-title { font-size: 16px; font-weight: 700; margin: 0 0 12px; }
      .chart-card img { width: 100%; border-radius: 14px; border: 1px solid #e0e0e0; background: #08111c; }
      table { width: 100%; border-collapse: collapse; }
      th, td { padding: 10px 12px; border-bottom: 1px solid #e6edf5; font-size: 12px; text-align: left; }
      th { background: #f8fafc; color: #6b7280; position: sticky; top: 0; }
      td.num, th.num { text-align: right; font-variant-numeric: tabular-nums; }
      .legend { margin-top: 10px; color: #6b7280; font-size: 12px; }
      @media print {
        body { background: #fff; }
        .page { max-width: none; padding: 0; }
        .toolbar { display: none; }
        .hero, .chart-card, .table-card { box-shadow: none; border-color: #e0e0e0; }
      }
    </style>
  </head>
  <body>
    <div class="page">
      <div class="toolbar">
        <div><strong>${summaryEscapeHtml(payload.title)}</strong></div>
        <div class="toolbar-buttons">
          <button class="btn" onclick="window.print()">Imprimir</button>
          <button class="btn" onclick="window.close()">Fechar</button>
        </div>
      </div>

      <section class="hero">
        <div class="eyebrow">Resumo do gráfico</div>
        <h1>${summaryEscapeHtml(payload.title)}</h1>
        <div class="subtitle">${summaryEscapeHtml(payload.monthLabel)} · ${summaryEscapeHtml(payload.modeLabel)}</div>
        <div>${summaryEscapeHtml(payload.criteriaText)}</div>
        <div class="chips">
          ${payload.summaryChips.map(chip => `<span class="chip">${summaryEscapeHtml(chip)}</span>`).join('')}
        </div>
      </section>

      <div class="layout">
        <section class="chart-card">
          <div class="section-title">Gráfico atual</div>
          ${chartImage ? `<img src="${chartImage}" alt="Gráfico de desvio">` : '<div class="legend">Não foi possível capturar a imagem do gráfico.</div>'}
          <div class="legend">${summaryEscapeHtml(payload.legendText || 'Sem observações adicionais.')}</div>
        </section>

        <section class="table-card">
          <div class="section-title">Tabela dos dados plotados</div>
          <table>
            <thead>
              <tr>${payload.tableColumns.map(col => `<th class="${col.align === 'right' ? 'num' : ''}">${summaryEscapeHtml(col.label)}</th>`).join('')}</tr>
            </thead>
            <tbody>${rowsHtml}</tbody>
          </table>
        </section>
      </div>
    </div>
  </body>
  </html>`;

  const blob = new Blob([html], { type: 'text/html;charset=utf-8' });
  const blobUrl = URL.createObjectURL(blob);
  const newWin = window.open(blobUrl, '_blank');
  if (!newWin) {
    URL.revokeObjectURL(blobUrl);
    window.alert('O navegador bloqueou a abertura da nova janela. Libere pop-ups para este site e tente novamente.');
    return;
  }
  // Libera o Blob URL após a janela ter tempo de carregar
  setTimeout(() => URL.revokeObjectURL(blobUrl), 60000);
}

async function loadDesvioChart(month, summaryData) {
  const wrap = document.getElementById('desvioChartWrap');
  const stage = document.getElementById('desvioChartStage');
  const empty = document.getElementById('desvioChartEmpty');
  const canvas = document.getElementById('desvioChart');
  const legendEl = document.getElementById('desvioChartLegend');
  const criteria = summaryData?.criteria || { hc_pct: 10, total_pct: 7 };
  const limHC = Number(criteria.hc_pct || 10);
  const limTotal = Number(criteria.total_pct || 7);
  const showHcLimit = state.summaryChart?.showHcLimit !== false;
  const showTotalLimit = state.summaryChart?.showTotalLimit !== false;
  const showPointLabels = !!state.summaryChart?.showPointLabels;

  summaryEnsureDesvioPlugins();
  summarySetDesvioReportEnabled(false);
  if (state.summaryChart) state.summaryChart.currentPayload = null;

  const chartMode = document.getElementById('desvioModeAnp')?.checked ? 'anp' : 'sep';
  const titleEl = document.getElementById('desvioChartTitle');
  const criteriaEl = document.getElementById('desvioChartCriteria');
  const hcToggle = document.getElementById('sumChartShowHc');
  const totalToggle = document.getElementById('sumChartShowTotal');
  const pointToggle = document.getElementById('sumChartShowPointLabels');
  if (hcToggle) hcToggle.checked = showHcLimit;
  if (totalToggle) totalToggle.checked = showTotalLimit;
  if (pointToggle) pointToggle.checked = showPointLabels;
  if (criteriaEl) {
    criteriaEl.innerHTML = `Linhas de limite: <span style="color:#f3b33d">± HC ${fmt(limHC)}%</span> &nbsp;·&nbsp; <span style="color:#ef5a5a">± Total ${fmt(limTotal)}%</span>`;
  }
  if (wrap) wrap.style.height = showPointLabels ? (chartMode === 'anp' ? '420px' : '360px') : '320px';

  const [yr, mo] = (month || '2026-01').split('-').map(Number);
  const daysInMonth = new Date(yr, mo, 0).getDate();
  const allDays = Array.from({ length: daysInMonth }, (_, index) => {
    const day = index + 1;
    return `${yr}-${String(mo).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
  });
  const labels = allDays.map(dayRef => Number(dayRef.split('-')[2]));

  let hcArr = [];
  let totalArr = [];
  let anpPairDatasets = null;
  let pairOptions = [];
  let selectedPairKeys = [];
  let selectedPairs = [];
  let tableColumns = [];
  let tableRows = [];

  const showEmptyState = (message, legendHtml) => {
    canvas.style.display = 'none';
    empty.style.display = 'flex';
    empty.textContent = message;
    if (stage) stage.style.width = '100%';
    if (_desvioChart) { _desvioChart.destroy(); _desvioChart = null; }
    if (legendEl) legendEl.innerHTML = legendHtml || `<span style="color:var(--muted)">${message}</span>`;
    summarySetDesvioReportEnabled(false);
    if (state.summaryChart) state.summaryChart.currentPayload = null;
  };

  if (chartMode === 'sep') {
    if (titleEl) titleEl.textContent = 'Desvio MPFM vs Separador por dia';
    summaryRenderDesvioPairFilter(chartMode, [], [], month, summaryData);
    const dailyRows = (summaryData?.daily || []).filter(row =>
      row?.has_data &&
      row?.mpfm_hc != null && row?.sep_hc != null &&
      Math.abs(Number(row.sep_hc || 0)) > 0.000001 &&
      row?.mpfm_total != null && row?.sep_total != null &&
      Math.abs(Number(row.sep_total || 0)) > 0.000001
    );
    if (!dailyRows.length) {
      showEmptyState('Sem dias comparáveis entre MPFM e separador no mês.', '<span style="color:var(--muted)">Sem dias comparáveis entre MPFM e separador no mês.</span>');
      return;
    }
    const byDay = {};
    dailyRows.forEach(row => {
      const hcValue = Number((((row.mpfm_hc || 0) - (row.sep_hc || 0)) / row.sep_hc) * 100);
      const totalValue = Number((((row.mpfm_total || 0) - (row.sep_total || 0)) / row.sep_total) * 100);
      byDay[row.day] = { desvio_hc: hcValue, desvio_total: totalValue };
      tableRows.push({
        day: fmtDate(row.day),
        hc: summaryPctLabel(hcValue),
        hcStatus: summaryLimitStatus(hcValue, limHC),
        total: summaryPctLabel(totalValue),
        totalStatus: summaryLimitStatus(totalValue, limTotal),
      });
    });
    hcArr = allDays.map(dayRef => byDay[dayRef]?.desvio_hc ?? null);
    totalArr = allDays.map(dayRef => byDay[dayRef]?.desvio_total ?? null);
    tableColumns = [
      { key: 'day', label: 'Dia' },
      { key: 'hc', label: 'Desvio HC (%)', align: 'right' },
      { key: 'hcStatus', label: `Status HC (±${fmt(limHC)}%)` },
      { key: 'total', label: 'Desvio Total (%)', align: 'right' },
      { key: 'totalStatus', label: `Status Total (±${fmt(limTotal)}%)` },
    ];
  } else {
    if (titleEl) titleEl.textContent = 'Desvio Subsea vs Topside por par, por dia (CEP)';
    const normTag = value => String(value || '').replace(/ /g, '_');
    if (!(cadData?.subsea?.length)) {
      try {
        const cd = await j(`${API}/cadastro`);
        cadData = { subsea: cd.banks_subsea || cd.subsea || [], topside: cd.banks_topside || cd.topside || [] };
      } catch (e) {
        // handled below
      }
    }

    pairOptions = (cadData?.subsea || [])
      .filter(row => row.ativo !== false && row.chega_riser)
      .map((row, index) => ({
        key: summaryPairKey(normTag(row.sistema), normTag(row.chega_riser)),
        subTag: normTag(row.sistema),
        topTag: normTag(row.chega_riser),
        subLabel: String(row.sistema).replace(/_/g, '-'),
        topLabel: String(row.chega_riser).replace(/_/g, ' '),
        label: `${String(row.sistema).replace(/_/g, '-')} × ${String(row.chega_riser).replace(/_/g, ' ')}`,
        color: ['#26a0ff', '#23c16b', '#ff9f40', '#c084fc', '#fb923c', '#38bdf8'][index % 6],
      }));

    const storedKeys = Array.isArray(state.summaryChart?.selectedPairKeys) ? state.summaryChart.selectedPairKeys : null;
    const validKeys = new Set(pairOptions.map(pair => pair.key));
    selectedPairKeys = storedKeys === null
      ? pairOptions.map(pair => pair.key)
      : storedKeys.filter(key => validKeys.has(key));
    if (storedKeys && storedKeys.length > 0 && !selectedPairKeys.length) {
      selectedPairKeys = pairOptions.map(pair => pair.key);
    }
    if (state.summaryChart) state.summaryChart.selectedPairKeys = selectedPairKeys;
    summaryRenderDesvioPairFilter(chartMode, pairOptions, selectedPairKeys, month, summaryData);

    if (!pairOptions.length) {
      showEmptyState('Nenhum par Subsea×Topside configurado no cadastro.', '<span style="color:var(--muted)">Nenhum par Subsea×Topside configurado no cadastro.</span>');
      return;
    }

    selectedPairs = pairOptions.filter(pair => selectedPairKeys.includes(pair.key));
    if (!selectedPairs.length) {
      showEmptyState('Selecione ao menos um par Subsea×Topside para plotar.', '<span style="color:var(--muted)">Nenhum par selecionado para plotagem.</span>');
      return;
    }

    const tagDayMap = {};
    (summaryData?.tag_daily || []).forEach(item => { tagDayMap[`${item.day}|${item.tag}`] = item; });

    const allHcVals = [];
    const allTotVals = [];
    anpPairDatasets = [];

    selectedPairs.forEach(pair => {
      const hcSeries = [];
      const totSeries = [];
      allDays.forEach(dayRef => {
        const sub = tagDayMap[`${dayRef}|${pair.subTag}`];
        const top = tagDayMap[`${dayRef}|${pair.topTag}`];
        const hcValue = (!sub || !top || (top.hc_t || 0) <= 0.001)
          ? null
          : Number((((sub.hc_t || 0) / top.hc_t - 1) * 100).toFixed(2));
        const totalValue = (!sub || !top || (top.total_t || 0) <= 0.001)
          ? null
          : Number((((sub.total_t || 0) / top.total_t - 1) * 100).toFixed(2));
        hcSeries.push(hcValue);
        totSeries.push(totalValue);
        if (hcValue !== null || totalValue !== null) {
          tableRows.push({
            day: fmtDate(dayRef),
            pair: pair.label,
            subsea: pair.subLabel,
            topside: pair.topLabel,
            hc: summaryPctLabel(hcValue),
            hcStatus: summaryLimitStatus(hcValue, limHC),
            total: summaryPctLabel(totalValue),
            totalStatus: summaryLimitStatus(totalValue, limTotal),
          });
        }
      });
      hcSeries.forEach(value => value !== null && allHcVals.push(value));
      totSeries.forEach(value => value !== null && allTotVals.push(value));
      anpPairDatasets.push({
        label: `HC% ${pair.label}`,
        data: hcSeries,
        borderColor: pair.color,
        backgroundColor: pair.color,
        borderWidth: 2.5,
        pointRadius: hcSeries.map(value => value !== null ? 5 : 0),
        pointBackgroundColor: hcSeries.map(value => value === null ? 'transparent' : (Math.abs(value) <= limHC ? '#23c16b' : '#ef5a5a')),
        pointBorderColor: hcSeries.map(value => value === null ? 'transparent' : (Math.abs(value) <= limHC ? '#23c16b' : '#ef5a5a')),
        pointLabelOffset: -12,
        tension: 0.28,
        spanGaps: true,
      });
      anpPairDatasets.push({
        label: `Tot% ${pair.label}`,
        data: totSeries,
        borderColor: pair.color,
        backgroundColor: pair.color,
        borderWidth: 1.8,
        borderDash: [5, 3],
        pointRadius: totSeries.map(value => value !== null ? 4 : 0),
        pointBackgroundColor: totSeries.map(value => value === null ? 'transparent' : (Math.abs(value) <= limTotal ? '#23c16b' : '#ef5a5a')),
        pointBorderColor: totSeries.map(value => value === null ? 'transparent' : (Math.abs(value) <= limTotal ? '#23c16b' : '#ef5a5a')),
        pointLabelOffset: 12,
        tension: 0.28,
        spanGaps: true,
      });
    });

    if (!allHcVals.length && !allTotVals.length) {
      showEmptyState('Sem dados Subsea/Topside simultâneos para os pares selecionados no mês.', '<span style="color:var(--muted)">Sem dados Subsea/Topside simultâneos para os pares selecionados no mês.</span>');
      return;
    }

    hcArr = allHcVals;
    totalArr = allTotVals;
    tableColumns = [
      { key: 'day', label: 'Dia' },
      { key: 'pair', label: 'Par' },
      { key: 'subsea', label: 'Subsea' },
      { key: 'topside', label: 'Topside' },
      { key: 'hc', label: 'Desvio HC (%)', align: 'right' },
      { key: 'hcStatus', label: `Status HC (±${fmt(limHC)}%)` },
      { key: 'total', label: 'Desvio Total (%)', align: 'right' },
      { key: 'totalStatus', label: `Status Total (±${fmt(limTotal)}%)` },
    ];
  }

  canvas.style.display = 'block';
  empty.style.display = 'none';
  empty.textContent = 'Sem dados para o período selecionado.';

  const hcLabel = chartMode === 'anp' ? 'Desvio % HC (Subsea/Topside)' : 'Desvio % HC';
  const totalLabel = chartMode === 'anp' ? 'Desvio % Total (Subsea/Topside)' : 'Desvio total %';
  const baseDatasets = [
    {
      label: hcLabel,
      data: hcArr,
      borderColor: '#26a0ff',
      backgroundColor: '#26a0ff',
      borderWidth: 2.5,
      pointRadius: hcArr.map(value => value !== null ? 5 : 0),
      pointBackgroundColor: hcArr.map(value => value === null ? 'transparent' : (Math.abs(value) <= limHC ? '#23c16b' : '#ef5a5a')),
      pointBorderColor: hcArr.map(value => value === null ? 'transparent' : (Math.abs(value) <= limHC ? '#23c16b' : '#ef5a5a')),
      pointLabelOffset: -12,
      tension: 0.28,
      spanGaps: true,
    },
    {
      label: totalLabel,
      data: totalArr,
      borderColor: '#a855f7',
      backgroundColor: '#a855f7',
      borderWidth: 2.5,
      borderDash: [6, 4],
      pointRadius: totalArr.map(value => value !== null ? 4 : 0),
      pointBackgroundColor: totalArr.map(value => value === null ? 'transparent' : (Math.abs(value) <= limTotal ? '#23c16b' : '#ef5a5a')),
      pointBorderColor: totalArr.map(value => value === null ? 'transparent' : (Math.abs(value) <= limTotal ? '#23c16b' : '#ef5a5a')),
      pointLabelOffset: 12,
      tension: 0.28,
      spanGaps: true,
    },
  ];

  const makeLimitLine = (value, color, dash, label) => ({
    label,
    data: allDays.map(() => value),
    borderColor: color,
    borderWidth: 1.5,
    borderDash: dash,
    pointRadius: 0,
    isLimitLine: true,
    hidePointLabels: true,
    fill: false,
    tension: 0,
    backgroundColor: 'transparent',
  });

  if (stage && wrap) {
    const daySlotWidth = 42;
    stage.style.width = `${Math.max(wrap.clientWidth || 0, allDays.length * daySlotWidth)}px`;
  }

  if (_desvioChart) { _desvioChart.destroy(); _desvioChart = null; }

  const _bodyStyle = getComputedStyle(document.body);
  const _cMuted = _bodyStyle.getPropertyValue('--muted').trim() || '#8ea3ba';
  const _cGrid = _bodyStyle.getPropertyValue('--line').trim() || '#20324d';
  const _cPanel = _bodyStyle.getPropertyValue('--panel').trim() || '#0e1a2b';
  const _cText = _bodyStyle.getPropertyValue('--text').trim() || '#dbe7f5';
  const _isLight = document.body.dataset.theme === 'light';
  const _cTooltipBg = _isLight ? '#FFFFFF' : _cPanel;
  const _cTooltipBorder = _cGrid;
  const _cTooltipTitle = _cText;
  const _cTooltipBody = _cMuted;

  const datasetsToRender = anpPairDatasets ? anpPairDatasets.slice() : baseDatasets.slice(0, 2);
  if (showHcLimit) {
    datasetsToRender.push(makeLimitLine(limHC, '#f3b33d', [6, 4], `+${limHC}% HC`));
    datasetsToRender.push(makeLimitLine(-limHC, '#f3b33d', [6, 4], `-${limHC}% HC`));
  }
  if (showTotalLimit) {
    datasetsToRender.push(makeLimitLine(limTotal, '#ef5a5a', [4, 3], `+${limTotal}% Total`));
    datasetsToRender.push(makeLimitLine(-limTotal, '#ef5a5a', [4, 3], `-${limTotal}% Total`));
  }

  _desvioChart = new Chart(canvas.getContext('2d'), {
    type: 'line',
    data: { labels, datasets: datasetsToRender },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        desvioPointLabels: { enabled: showPointLabels },
        legend: {
          display: true,
          position: 'top',
          labels: {
            color: _cMuted,
            font: { size: 11 },
            boxWidth: 24,
            padding: 12,
            filter: item => !item.text.startsWith('+') && !item.text.startsWith('-'),
          }
        },
        tooltip: {
          backgroundColor: _cTooltipBg,
          borderColor: _cTooltipBorder,
          borderWidth: 1,
          titleColor: _cTooltipTitle,
          bodyColor: _cTooltipBody,
          callbacks: {
            title: ctx => `Dia ${ctx[0].label}`,
            label: ctx => {
              const datasetLabel = ctx.dataset.label || '';
              if (datasetLabel.startsWith('+') || datasetLabel.startsWith('-')) return null;
              const value = ctx.raw;
              if (value === null) return null;
              return ` ${datasetLabel}: ${value > 0 ? '+' : ''}${value.toFixed(1)}%`;
            }
          }
        }
      },
      scales: {
        x: {
          grid: { color: _cGrid },
          ticks: { color: _cMuted, font: { size: 11 }, autoSkip: false, maxRotation: 0, minRotation: 0 },
          title: { display: true, text: 'Dia do mês', color: _cMuted, font: { size: 11 } }
        },
        y: {
          grid: { color: _cGrid },
          grace: showPointLabels ? '18%' : '10%',
          ticks: {
            color: _cMuted,
            font: { size: 11 },
            callback: value => `${value > 0 ? '+' : ''}${value.toFixed(0)}%`
          },
          title: { display: true, text: 'Desvio (%)', color: _cMuted, font: { size: 11 } }
        }
      },
      animation: { duration: (typeof prefersReducedMotion === 'function' && prefersReducedMotion()) ? 0 : 250 }
    }
  });
  window._desvioChart = _desvioChart;

  const outHC = hcArr.filter(value => value != null && Math.abs(value) > limHC).length;
  const outTotal = totalArr.filter(value => value != null && Math.abs(value) > limTotal).length;
  const legendParts = [];
  if (chartMode === 'anp' && selectedPairs.length) {
    legendParts.push(`<span style="color:var(--muted)">${selectedPairs.length} par(es) exibido(s)</span>`);
  }
  if (outHC === 0 && outTotal === 0) {
    legendParts.push('<span style="color:var(--green)">✓ Todos os dias dentro dos limites</span>');
  } else {
    if (outHC > 0) legendParts.push(`<span style="color:var(--red)">${outHC} leitura(s) fora do limite HC ±${limHC}%</span>`);
    if (outTotal > 0) legendParts.push(`<span style="color:var(--red)">${outTotal} leitura(s) fora do limite Total ±${limTotal}%</span>`);
  }
  const legendHtml = legendParts.join(' · ');
  if (legendEl) legendEl.innerHTML = legendHtml;

  if (state.summaryChart) {
    state.summaryChart.currentPayload = {
      title: titleEl?.textContent || 'Gráfico de desvio',
      monthLabel: summaryMonthLabel(month),
      modeLabel: chartMode === 'anp' ? 'Subsea vs Topside (ANP)' : 'MPFM vs Separador',
      criteriaText: `Limites considerados: HC ±${fmt(limHC)}% e Total ±${fmt(limTotal)}%.`,
      summaryChips: [
        showPointLabels ? 'Valores por ponto: visíveis' : 'Valores por ponto: ocultos',
        showHcLimit ? `Linha HC: ±${fmt(limHC)}%` : 'Linha HC: oculta',
        showTotalLimit ? `Linha Total: ±${fmt(limTotal)}%` : 'Linha Total: oculta',
        chartMode === 'anp'
          ? (selectedPairs.length ? `Pares: ${selectedPairs.map(pair => pair.label).join(' · ')}` : 'Pares: nenhum selecionado')
          : 'Visão: consolidado diário MPFM × Separador',
      ],
      legendText: (legendEl?.textContent || '').trim(),
      tableColumns,
      tableRows,
    };
  }
  summarySetDesvioReportEnabled(tableRows.length > 0);
}

// ─── TABELA DIÁRIA POÇO × RISER ────────────────────────────────────────────────
let _pocoRiserInitialized = false;
let _pocoRiserHandlersBound = false;
let _pocoRiserPayload = null;
let _pocoRiserRangeInputsBound = false;
let _pocoRiserCepChart = null;
let _pocoRiserCepControlsBound = false;
let _pocoRiserDisplayedRows = [];

function pocoRiserDefaultMonth(month) {
  if (month) return month;
  const globalMonth = document.getElementById('globalMonth')?.value || '';
  if (globalMonth) return globalMonth;
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
}

function pocoRiserLatestDataDay(month) {
  const normalizedMonth = pocoRiserDefaultMonth(month);
  const summaryData = state.summaryMonthData || {};
  if (summaryData.month !== normalizedMonth) return '';
  const availableDays = (summaryData.daily || [])
    .filter(row => row?.has_data && row?.day && String(row.day).startsWith(`${normalizedMonth}-`))
    .map(row => String(row.day))
    .sort();
  return availableDays.length ? availableDays[availableDays.length - 1] : '';
}

function pocoRiserResolveDefaultRange(month) {
  const normalizedMonth = pocoRiserDefaultMonth(month);
  const { from, to } = getMonthRange(normalizedMonth);
  return {
    from,
    to: pocoRiserLatestDataDay(normalizedMonth) || to,
  };
}

function pocoRiserBindRangeInputs() {
  if (_pocoRiserRangeInputsBound) return;
  _pocoRiserRangeInputsBound = true;
  ['pocoRiserFrom', 'pocoRiserTo'].forEach((id) => {
    const input = document.getElementById(id);
    if (!input) return;
    input.addEventListener('change', () => {
      input.dataset.autoDefault = '';
    });
  });
}

function pocoRiserApplyDefaultRange(month) {
  const fromEl = document.getElementById('pocoRiserFrom');
  const toEl = document.getElementById('pocoRiserTo');
  const defaults = pocoRiserResolveDefaultRange(month);
  let changed = false;

  if (fromEl && (!fromEl.value || fromEl.dataset.autoDefault === '1')) {
    changed = fromEl.value !== defaults.from || changed;
    fromEl.value = defaults.from;
    fromEl.dataset.autoDefault = '1';
  }
  if (toEl && (!toEl.value || toEl.dataset.autoDefault === '1')) {
    changed = toEl.value !== defaults.to || changed;
    toEl.value = defaults.to;
    toEl.dataset.autoDefault = '1';
  }
  return changed;
}

function pocoRiserSourceKind() {
  return document.getElementById('pocoRiserSource')?.value === 'hourly' ? 'hourly' : 'daily';
}

function pocoRiserSourceLabel(kind = pocoRiserSourceKind()) {
  return kind === 'hourly' ? 'Horários (somatório do dia)' : 'Diários';
}

function pocoRiserExportQs() {
  const qs = new URLSearchParams();
  const from = document.getElementById('pocoRiserFrom')?.value || '';
  const to   = document.getElementById('pocoRiserTo')?.value || '';
  const sourceKind = pocoRiserSourceKind();
  if (from) qs.set('date_from', from);
  if (to)   qs.set('date_to', to);
  qs.set('source_kind', sourceKind);
  return qs;
}

function pocoRiserCellClass(isAlert) {
  return isAlert ? ' class="poco-riser-alert"' : '';
}

function pocoRiserAvailabilityBadge(status = {}) {
  const css = status.badge || 'warn';
  const label = summaryEscapeHtml(status.label || 'Sem dado');
  return `<span class="badge ${css}">${label}</span>`;
}

function pocoRiserDeviationCell(row, key, isAlert) {
  const value = row?.[key];
  if (value == null || Number.isNaN(Number(value))) {
    return row?.has_counterpart
      ? '<span class="badge warn">Sem métrica</span>'
      : '<span class="badge warn">Sem par</span>';
  }
  return `<span${isAlert ? ' class="poco-riser-alert"' : ''}>${summaryPctLabel(value)}</span>`;
}

function pocoRiserChartState() {
  if (!state.pocoRiserChart) {
    state.pocoRiserChart = { selectedPairKey: '', showHc: true, showTotal: true };
  }
  return state.pocoRiserChart;
}

function syncPocoRiserCepControls(payload, tableRows) {
  const chartState = pocoRiserChartState();
  const pairSel = document.getElementById('pocoRiserCepPair');
  const hcCb = document.getElementById('pocoRiserCepShowHc');
  const totalCb = document.getElementById('pocoRiserCepShowTotal');
  const chartPairs = Array.from(new Map((tableRows || payload.rows || [])
    .map(row => [row.pair_key, { key: row.pair_key, poco: row.poco_label, riser: row.riser_label }]))
    .values());
  if (pairSel) {
    const current = chartState.selectedPairKey || '';
    pairSel.innerHTML = '<option value="">Todos os conjuntos</option>' + chartPairs
      .map(pair => `<option value="${summaryEscapeHtml(pair.key)}">${summaryEscapeHtml(pair.poco)} × ${summaryEscapeHtml(pair.riser)}</option>`)
      .join('');
    const hasCurrent = chartPairs.some(pair => pair.key === current);
    pairSel.value = hasCurrent ? current : '';
    chartState.selectedPairKey = pairSel.value;
  }
  if (hcCb) hcCb.checked = chartState.showHc !== false;
  if (totalCb) totalCb.checked = chartState.showTotal !== false;

  if (_pocoRiserCepControlsBound) return;
  _pocoRiserCepControlsBound = true;
  if (pairSel) {
    pairSel.onchange = () => {
      pocoRiserChartState().selectedPairKey = pairSel.value || '';
      if (_pocoRiserPayload) renderPocoRiserCepChart(_pocoRiserDisplayedRows || [], _pocoRiserPayload);
    };
  }
  if (hcCb) {
    hcCb.onchange = () => {
      pocoRiserChartState().showHc = !!hcCb.checked;
      if (_pocoRiserPayload) renderPocoRiserCepChart(_pocoRiserDisplayedRows || [], _pocoRiserPayload);
    };
  }
  if (totalCb) {
    totalCb.onchange = () => {
      pocoRiserChartState().showTotal = !!totalCb.checked;
      if (_pocoRiserPayload) renderPocoRiserCepChart(_pocoRiserDisplayedRows || [], _pocoRiserPayload);
    };
  }
}

function summaryEnsurePocoRiserCepPlugins() {
  if (!window.Chart) return;
  const alreadyRegistered = !!window.__pocoRiserCepBandsRegistered;
  if (alreadyRegistered) return;
  Chart.register({
    id: 'pocoRiserCepBands',
    beforeDatasetsDraw(chart, _args, pluginOptions) {
      if (!pluginOptions?.enabled || !chart?.chartArea || !chart.scales?.y) return;
      const { ctx, chartArea, scales } = chart;
      const yScale = scales.y;
      const ranges = pluginOptions.ranges || [];
      ctx.save();
      ranges.forEach(range => {
        const yTop = yScale.getPixelForValue(range.to);
        const yBottom = yScale.getPixelForValue(range.from);
        const top = Math.max(chartArea.top, Math.min(yTop, yBottom));
        const bottom = Math.min(chartArea.bottom, Math.max(yTop, yBottom));
        if (bottom <= top) return;
        ctx.fillStyle = range.color;
        ctx.fillRect(chartArea.left, top, chartArea.right - chartArea.left, bottom - top);
      });
      ctx.restore();
    }
  }, {
    id: 'pocoRiserCepOverflowMarkers',
    afterDatasetsDraw(chart, _args, pluginOptions) {
      if (!pluginOptions?.enabled || !chart?.chartArea || !chart?.scales?.y) return;
      const { ctx, chartArea, scales } = chart;
      const yScale = scales.y;
      const limitMin = Number(yScale.min);
      const limitMax = Number(yScale.max);
      const topY = yScale.getPixelForValue(limitMax);
      const bottomY = yScale.getPixelForValue(limitMin);
      ctx.save();
      ctx.font = '10px sans-serif';
      ctx.textAlign = 'center';
      chart.data.datasets.forEach((dataset, datasetIndex) => {
        if (!dataset || dataset.isLimitLine || !Array.isArray(dataset.data)) return;
        const meta = chart.getDatasetMeta(datasetIndex);
        dataset.data.forEach((value, pointIndex) => {
          if (value == null || Number.isNaN(Number(value))) return;
          const numericValue = Number(value);
          if (numericValue <= limitMax && numericValue >= limitMin) return;
          const point = meta?.data?.[pointIndex];
          const pointProps = point?.getProps ? point.getProps(['x', 'y'], true) : point?.getProps?.() || point;
          const x = Number(pointProps?.x);
          if (!Number.isFinite(x) || x < chartArea.left || x > chartArea.right) return;
          const isAbove = numericValue > limitMax;
          const markerY = isAbove ? Math.max(chartArea.top + 8, topY + 8) : Math.min(chartArea.bottom - 8, bottomY - 8);
          const fill = dataset.pointBackgroundColor || dataset.borderColor || '#ef5a5a';
          ctx.beginPath();
          if (isAbove) {
            ctx.moveTo(x, markerY - 6);
            ctx.lineTo(x - 5, markerY + 4);
            ctx.lineTo(x + 5, markerY + 4);
          } else {
            ctx.moveTo(x, markerY + 6);
            ctx.lineTo(x - 5, markerY - 4);
            ctx.lineTo(x + 5, markerY - 4);
          }
          ctx.closePath();
          ctx.fillStyle = fill;
          ctx.fill();
          ctx.fillStyle = fill;
          ctx.textBaseline = isAbove ? 'top' : 'bottom';
          ctx.fillText(isAbove ? `>${Math.abs(limitMax)}%` : `<${limitMin}%`, x, isAbove ? markerY + 6 : markerY - 6);
        });
      });
      ctx.restore();
    }
  });
  window.__pocoRiserCepBandsRegistered = true;
}

function renderPocoRiserCepChart(rows, payload) {
  const wrap = document.getElementById('pocoRiserCepWrap');
  const stage = document.getElementById('pocoRiserCepStage');
  const canvas = document.getElementById('pocoRiserCepChart');
  const empty = document.getElementById('pocoRiserCepEmpty');
  const legend = document.getElementById('pocoRiserCepLegend');
  if (!wrap || !stage || !canvas || !empty || !legend) return;

  summaryEnsurePocoRiserCepPlugins();
  if (_pocoRiserCepChart) {
    _pocoRiserCepChart.destroy();
    _pocoRiserCepChart = null;
  }
  if (!window.Chart || !rows.length) {
    empty.style.display = 'flex';
    legend.textContent = 'Sem dados para montar o gráfico CEP.';
    return;
  }

  const chartState = pocoRiserChartState();
  const selectedPairKey = chartState.selectedPairKey || '';
  const filteredRows = rows.filter(row => !selectedPairKey || row.pair_key === selectedPairKey);
  const showHc = chartState.showHc !== false;
  const showTotal = chartState.showTotal !== false;
  const hasAnyCalculablePoint = filteredRows.some(row =>
    (showHc && row.desvio_hc_pct != null) || (showTotal && row.desvio_total_pct != null)
  );
  syncPocoRiserCepControls(payload, rows);
  if (!showHc && !showTotal) {
    empty.style.display = 'flex';
    legend.textContent = 'Selecione HC e/ou Total para montar o gráfico CEP.';
    return;
  }
  if (!filteredRows.length || !hasAnyCalculablePoint) {
    empty.style.display = 'flex';
    legend.textContent = selectedPairKey
      ? 'Sem desvios calculáveis para o conjunto Poço × Riser selecionado.'
      : 'Sem desvios calculáveis para o recorte atual.';
    return;
  }

  empty.style.display = 'none';
  const multiplePairs = new Set(filteredRows.map(row => row.pair_key)).size > 1;
  const labels = filteredRows.map(row => multiplePairs
    ? `${fmtDate(row.day)} · ${row.poco_label} × ${row.riser_label}`
    : fmtDate(row.day)
  );
  const hcData = filteredRows.map(row => row.desvio_hc_pct == null ? null : Number(row.desvio_hc_pct));
  const totalData = filteredRows.map(row => row.desvio_total_pct == null ? null : Number(row.desvio_total_pct));
  const limHC = Number(payload.limits?.hc_pct ?? 10);
  const limTotal = Number(payload.limits?.total_pct ?? 7);

  if (stage && wrap) {
    const slotWidth = multiplePairs ? 84 : 42;
    stage.style.width = `${Math.max(wrap.clientWidth || 0, labels.length * slotWidth)}px`;
    stage.style.height = `${Math.max(wrap.clientHeight || 0, 260)}px`;
    stage.style.minHeight = `${Math.max(wrap.clientHeight || 0, 260)}px`;
  }
  canvas.style.width = '100%';
  canvas.style.height = '100%';

  const bodyStyle = getComputedStyle(document.body);
  const cMuted = bodyStyle.getPropertyValue('--muted').trim() || '#8ea3ba';
  const cGrid = bodyStyle.getPropertyValue('--line').trim() || '#20324d';
  const cPanel = bodyStyle.getPropertyValue('--panel').trim() || '#0e1a2b';
  const cText = bodyStyle.getPropertyValue('--text').trim() || '#dbe7f5';
  const isLight = document.body.dataset.theme === 'light';
  const cTooltipBg = isLight ? '#FFFFFF' : cPanel;

  const makeLimitDataset = (label, value, color, dash) => ({
    label,
    data: labels.map(() => value),
    borderColor: color,
    backgroundColor: 'transparent',
    borderWidth: 1.5,
    borderDash: dash,
    pointRadius: 0,
    pointHoverRadius: 0,
    tension: 0,
    fill: false,
    clip: 0,
    isLimitLine: true,
  });

  const datasets = [];
  if (showHc) {
    datasets.push({
      label: '% Desvio HC',
      data: hcData,
      borderColor: '#f3b33d',
      backgroundColor: 'rgba(243,179,61,.18)',
      pointBackgroundColor: '#f3b33d',
      pointBorderColor: '#f3b33d',
      pointRadius: 3,
      pointHoverRadius: 4,
      borderWidth: 2,
      tension: 0.18,
      spanGaps: false,
      fill: false,
      clip: 0,
    });
    datasets.push(makeLimitDataset('+10% HC', limHC, '#f3b33d', [6, 4]));
    datasets.push(makeLimitDataset('-10% HC', -limHC, '#f3b33d', [6, 4]));
  }
  if (showTotal) {
    datasets.push({
      label: '% Desvio Total',
      data: totalData,
      borderColor: '#ef5a5a',
      backgroundColor: 'rgba(239,90,90,.16)',
      pointBackgroundColor: '#ef5a5a',
      pointBorderColor: '#ef5a5a',
      pointRadius: 3,
      pointHoverRadius: 4,
      borderWidth: 2,
      tension: 0.18,
      spanGaps: false,
      fill: false,
      clip: 0,
    });
    datasets.push(makeLimitDataset('+7% Total', limTotal, '#ef5a5a', [4, 3]));
    datasets.push(makeLimitDataset('-7% Total', -limTotal, '#ef5a5a', [4, 3]));
  }

  _pocoRiserCepChart = new Chart(canvas.getContext('2d'), {
    type: 'line',
    data: {
      labels,
      datasets
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        pocoRiserCepBands: {
          enabled: true,
          ranges: [
            { from: -15, to: -10, color: 'rgba(239,90,90,.16)' },
            { from: -10, to: -7, color: 'rgba(243,179,61,.14)' },
            { from: -7, to: 7, color: 'rgba(35,193,107,.10)' },
            { from: 7, to: 10, color: 'rgba(243,179,61,.14)' },
            { from: 10, to: 15, color: 'rgba(239,90,90,.16)' },
          ]
        },
        pocoRiserCepOverflowMarkers: {
          enabled: true
        },
        legend: {
          position: 'top',
          labels: {
            color: cMuted,
            font: { size: 11 },
            boxWidth: 24,
            padding: 12,
            filter: item => !item.text.startsWith('+') && !item.text.startsWith('-'),
          }
        },
        tooltip: {
          backgroundColor: cTooltipBg,
          borderColor: cGrid,
          borderWidth: 1,
          titleColor: cText,
          bodyColor: cMuted,
          callbacks: {
            title: ctx => labels[ctx[0].dataIndex] || '',
            label: ctx => {
              const rawValue = ctx.raw && typeof ctx.raw === 'object' ? ctx.raw.y : ctx.raw;
              if (rawValue == null) return ` ${ctx.dataset.label}: sem valor`;
              return ` ${ctx.dataset.label}: ${rawValue > 0 ? '+' : ''}${Number(rawValue).toFixed(1)}%`;
            }
          }
        }
      },
      scales: {
        x: {
          grid: { color: cGrid },
          ticks: { color: cMuted, font: { size: 11 }, autoSkip: !multiplePairs, maxRotation: 0, minRotation: 0 },
          title: { display: true, text: multiplePairs ? 'Dia · Par' : 'Dia do mês', color: cMuted, font: { size: 11 } }
        },
        y: {
          min: -15,
          max: 15,
          clip: true,
          grid: { color: cGrid },
          ticks: {
            color: cMuted,
            font: { size: 11 },
            callback: value => `${value > 0 ? '+' : ''}${Number(value).toFixed(0)}%`
          },
          title: { display: true, text: 'Desvio (%)', color: cMuted, font: { size: 11 } }
        }
      },
      animation: { duration: (typeof prefersReducedMotion === 'function' && prefersReducedMotion()) ? 0 : 250 }
    }
  });
  requestAnimationFrame(() => {
    if (_pocoRiserCepChart) _pocoRiserCepChart.resize();
  });

  const hcOutside = filteredRows.filter(row => row.desvio_hc_pct != null && Math.abs(Number(row.desvio_hc_pct)) > limHC).length;
  const totalOutside = filteredRows.filter(row => row.desvio_total_pct != null && Math.abs(Number(row.desvio_total_pct)) > limTotal).length;
  const selectedPair = (payload.pairs || []).find(pair => pair.key === selectedPairKey);
  legend.innerHTML = `${selectedPair ? `Conjunto: <strong>${summaryEscapeHtml(selectedPair.poco)} × ${summaryEscapeHtml(selectedPair.riser)}</strong> &nbsp;·&nbsp; ` : ''}Faixas CEP: verde até ±7%, amarelo entre 7% e 10%, vermelho acima de 10%`
    + ` &nbsp;·&nbsp; Eixo Y fixo em ±15% · pontos acima desse limite são recortados visualmente no topo/fundo do gráfico`
    + (showHc ? ` &nbsp;·&nbsp; HC fora: <strong>${hcOutside}</strong>` : '')
    + (showTotal ? ` &nbsp;·&nbsp; Total fora: <strong>${totalOutside}</strong>` : '');
}

function renderPocoRiserTable(payload) {
  _pocoRiserPayload = payload;
  const wrap = document.getElementById('pocoRiserTableWrap');
  const referenceWrap = document.getElementById('pocoRiserReferenceWrap');
  const meta = document.getElementById('pocoRiserMeta');
  const pairSel = document.getElementById('pocoRiserPair');
  if (!wrap || !referenceWrap) return;

  if (pairSel && !pairSel.dataset.filled) {
    pairSel.dataset.filled = '1';
    (payload.pairs || []).forEach(pair => {
      const opt = document.createElement('option');
      opt.value = pair.key;
      opt.textContent = `${pair.poco} × ${pair.riser}`;
      pairSel.appendChild(opt);
    });
  }

  const selectedPair = pairSel?.value || '';
  const rows = (payload.rows || []).filter(row => !selectedPair || row.pair_key === selectedPair);
  _pocoRiserDisplayedRows = rows.slice();

  if (!rows.length) {
    wrap.innerHTML = '<div class="soft-empty">Sem dados de poço × riser para o período selecionado.</div>';
    referenceWrap.innerHTML = '<div class="soft-empty">Sem dados de volume e condições de referência para o período selecionado.</div>';
    if (meta) meta.textContent = `Período ${fmtDate(payload.date_from)} a ${fmtDate(payload.date_to)} · nenhum registro encontrado.`;
    renderPocoRiserCepChart([], payload);
    return;
  }

  const limHC = Number(payload.limits?.hc_pct ?? 10);
  const limTotal = Number(payload.limits?.total_pct ?? 7);
  const numFmt = value => (value == null ? '—' : fmt(value));
  const sourceLabel = payload.source_label || pocoRiserSourceLabel(payload.source_kind);
  const missingCount = rows.filter(row => !row.has_counterpart).length;

  const mainRowsHtml = rows.map(row => `
    <tr>
      <td>${fmtDate(row.day)}</td>
      <td>${summaryEscapeHtml(row.poco_label)}</td>
      <td>${summaryEscapeHtml(row.riser_label)}</td>
      <td>${pocoRiserAvailabilityBadge(row.poco_source_status)}</td>
      <td>${pocoRiserAvailabilityBadge(row.riser_source_status)}</td>
      <td class="num poco-riser-subsea-cell">${numFmt(row.poco_mpfm?.oil_corr_t)}</td>
      <td class="num poco-riser-subsea-cell">${numFmt(row.poco_mpfm?.gas_corr_t)}</td>
      <td class="num poco-riser-subsea-cell">${numFmt(row.poco_mpfm?.water_corr_t)}</td>
      <td class="num poco-riser-subsea-cell">${numFmt(row.poco_mpfm?.hc_corr_t)}</td>
      <td class="num poco-riser-subsea-cell">${numFmt(row.poco_mpfm?.total_corr_t)}</td>
      <td class="num poco-riser-topside-cell">${numFmt(row.riser_mpfm?.oil_corr_t)}</td>
      <td class="num poco-riser-topside-cell">${numFmt(row.riser_mpfm?.gas_corr_t)}</td>
      <td class="num poco-riser-topside-cell">${numFmt(row.riser_mpfm?.water_corr_t)}</td>
      <td class="num poco-riser-topside-cell">${numFmt(row.riser_mpfm?.hc_corr_t)}</td>
      <td class="num poco-riser-topside-cell">${numFmt(row.riser_mpfm?.total_corr_t)}</td>
      <td class="num">${pocoRiserDeviationCell(row, 'desvio_hc_pct', row.alerta_hc)}</td>
      <td class="num">${pocoRiserDeviationCell(row, 'desvio_total_pct', row.alerta_total)}</td>
    </tr>
  `).join('');

  const referenceRowsHtml = rows.map(row => `
    <tr>
      <td>${fmtDate(row.day)}</td>
      <td>${summaryEscapeHtml(row.poco_label)}</td>
      <td>${summaryEscapeHtml(row.riser_label)}</td>
      <td class="num poco-riser-subsea-cell">${numFmt(row.reference_20c?.poco?.oil_vol20_m3)}</td>
      <td class="num poco-riser-subsea-cell">${numFmt(row.reference_20c?.poco?.oil_mass20_t)}</td>
      <td class="num poco-riser-subsea-cell">${numFmt(row.reference_20c?.poco?.gas_vol20_sm3)}</td>
      <td class="num poco-riser-subsea-cell">${numFmt(row.reference_20c?.poco?.gas_mass20_t)}</td>
      <td class="num poco-riser-subsea-cell">${numFmt(row.reference_20c?.poco?.water_vol20_m3)}</td>
      <td class="num poco-riser-subsea-cell">${numFmt(row.reference_20c?.poco?.water_mass20_t)}</td>
      <td class="num poco-riser-topside-cell">${numFmt(row.reference_20c?.riser?.oil_vol20_m3)}</td>
      <td class="num poco-riser-topside-cell">${numFmt(row.reference_20c?.riser?.oil_mass20_t)}</td>
      <td class="num poco-riser-topside-cell">${numFmt(row.reference_20c?.riser?.gas_vol20_sm3)}</td>
      <td class="num poco-riser-topside-cell">${numFmt(row.reference_20c?.riser?.gas_mass20_t)}</td>
      <td class="num poco-riser-topside-cell">${numFmt(row.reference_20c?.riser?.water_vol20_m3)}</td>
      <td class="num poco-riser-topside-cell">${numFmt(row.reference_20c?.riser?.water_mass20_t)}</td>
    </tr>
  `).join('');

  wrap.innerHTML = `
    <table class="table">
      <thead>
        <tr>
          <th rowspan="2">Data</th>
          <th rowspan="2">Poço</th>
          <th rowspan="2">Riser</th>
          <th rowspan="2">Arquivo Poço</th>
          <th rowspan="2">Arquivo Riser</th>
          <th colspan="5" class="poco-riser-subsea-head">Subsea / Poço — massa corrigida</th>
          <th colspan="5" class="poco-riser-topside-head">Topside / Riser — massa corrigida</th>
          <th rowspan="2">% Desvio HC<br><span class="text-muted-11">±${fmt(limHC)}%</span></th>
          <th rowspan="2">% Desvio Total<br><span class="text-muted-11">±${fmt(limTotal)}%</span></th>
        </tr>
        <tr>
          <th class="poco-riser-subsea-head">Óleo (t)</th><th class="poco-riser-subsea-head">Gás (t)</th><th class="poco-riser-subsea-head">Água (t)</th><th class="poco-riser-subsea-head">HC (t)</th><th class="poco-riser-subsea-head">Total (t)</th>
          <th class="poco-riser-topside-head">Óleo (t)</th><th class="poco-riser-topside-head">Gás (t)</th><th class="poco-riser-topside-head">Água (t)</th><th class="poco-riser-topside-head">HC (t)</th><th class="poco-riser-topside-head">Total (t)</th>
        </tr>
      </thead>
      <tbody>${mainRowsHtml}</tbody>
    </table>
  `;

  referenceWrap.innerHTML = `
    <div class="section-title section-title--mb10">Volumes e condições de referência @20°C/1atm</div>
    <table class="table">
      <thead>
        <tr>
          <th rowspan="2">Data</th>
          <th rowspan="2">Poço</th>
          <th rowspan="2">Riser</th>
          <th colspan="6" class="poco-riser-subsea-head">Subsea / Poço</th>
          <th colspan="6" class="poco-riser-topside-head">Topside / Riser</th>
        </tr>
        <tr>
          <th class="poco-riser-subsea-head">Óleo vol20 (m³)</th><th class="poco-riser-subsea-head">Óleo mass20 (t)</th>
          <th class="poco-riser-subsea-head">Gás vol20 (Sm³)</th><th class="poco-riser-subsea-head">Gás mass20 (t)</th>
          <th class="poco-riser-subsea-head">Água vol20 (m³)</th><th class="poco-riser-subsea-head">Água mass20 (t)</th>
          <th class="poco-riser-topside-head">Óleo vol20 (m³)</th><th class="poco-riser-topside-head">Óleo mass20 (t)</th>
          <th class="poco-riser-topside-head">Gás vol20 (Sm³)</th><th class="poco-riser-topside-head">Gás mass20 (t)</th>
          <th class="poco-riser-topside-head">Água vol20 (m³)</th><th class="poco-riser-topside-head">Água mass20 (t)</th>
        </tr>
      </thead>
      <tbody>${referenceRowsHtml}</tbody>
    </table>
  `;

  renderPocoRiserCepChart(rows, payload);

  const alertCount = rows.filter(row => row.alerta_hc || row.alerta_total).length;
  if (meta) {
    meta.textContent = `Fonte ${sourceLabel} · período ${fmtDate(payload.date_from)} a ${fmtDate(payload.date_to)} · ${rows.length} registro(s)`
      + (missingCount ? ` · ${missingCount} com ausência de arquivo em uma das pontas` : ' · pares completos no recorte')
      + (alertCount ? ` · ${alertCount} fora do limite (destacado(s) em vermelho)` : ' · todos dentro dos limites')
      + ` · fórmula do desvio: ${payload.deviation_formula || '((Poço / Riser) - 1) × 100'}`;
  }
}

async function loadPocoRiserTable() {
  const wrap = document.getElementById('pocoRiserTableWrap');
  const referenceWrap = document.getElementById('pocoRiserReferenceWrap');
  const meta = document.getElementById('pocoRiserMeta');
  const toEl = document.getElementById('pocoRiserTo');
  try {
    if (meta) meta.textContent = 'Carregando…';
    const qs = pocoRiserExportQs();
    const payload = await j(`${API}/ops/poco-riser-diario?${qs.toString()}`);
    const latestRowDay = (payload.rows || [])
      .map(row => String(row?.day || ''))
      .filter(Boolean)
      .sort()
      .pop() || '';
    let effectivePayload = payload;
    if (toEl && toEl.dataset.autoDefault === '1' && latestRowDay) {
      if (toEl.value !== latestRowDay) {
        toEl.value = latestRowDay;
      }
      effectivePayload = { ...payload, date_to: latestRowDay };
    }
    renderPocoRiserTable(effectivePayload);
  } catch (e) {
    if (wrap) wrap.innerHTML = '<div class="soft-empty">Não foi possível carregar a tabela poço × riser.</div>';
    if (referenceWrap) referenceWrap.innerHTML = '<div class="soft-empty">Não foi possível carregar a tabela de referência @20°C/1atm.</div>';
    if (meta) meta.textContent = `Erro: ${e.message}`;
    renderPocoRiserCepChart([], {});
  }
}

function initPocoRiserTable(month) {
  pocoRiserBindRangeInputs();
  const rangeChanged = pocoRiserApplyDefaultRange(month);
  const loadBtn = document.getElementById('btnPocoRiserLoad');
  const excelBtn = document.getElementById('btnPocoRiserExcel');
  const pairSel = document.getElementById('pocoRiserPair');
  const sourceSel = document.getElementById('pocoRiserSource');
  if (!_pocoRiserHandlersBound) {
    _pocoRiserHandlersBound = true;
    if (loadBtn) loadBtn.onclick = loadPocoRiserTable;
    if (excelBtn) excelBtn.onclick = () => window.open(`${API}/ops/poco-riser-diario/export-excel?${pocoRiserExportQs().toString()}`, '_blank');
    if (pairSel) pairSel.onchange = () => { if (_pocoRiserPayload) renderPocoRiserTable(_pocoRiserPayload); };
    if (sourceSel) sourceSel.onchange = () => initPocoRiserTable(document.getElementById('globalMonth')?.value || '');
  }

  if (!_pocoRiserInitialized) {
    _pocoRiserInitialized = true;
    loadPocoRiserTable();
  } else if (rangeChanged) {
    loadPocoRiserTable();
  }
}


// Shared inline edit for any measurement (mpfm or sep)
window.editMeasurement = async (id, cell, metricName, dayRef, hourRef, bank, source) => {
  if (!id) return;
  const current = cell.textContent.replace(',', '.').trim();
  const input = document.createElement('input');
  input.type = 'number'; input.step = 'any';
  input.value = current === '—' ? '' : current;
  input.style.cssText = 'width:90px;background:var(--bg);border:1px solid var(--accent);color:var(--text);padding:3px 6px;border-radius:4px;font-size:12px;text-align:right';
  cell.innerHTML = '';
  cell.appendChild(input);
  input.focus(); input.select();
  const save = async () => {
    const val = input.value.trim();
    if (val === '' || isNaN(parseFloat(val))) {
      cell.textContent = current === '' ? '—' : current;
      return;
    }
    const r = await j(`${API}/measurements/${id}`, {method:'PUT',
      headers:{'Content-Type':'application/json'}, body:JSON.stringify({value:val})});
    if (r.ok) {
      cell.textContent = new Intl.NumberFormat('pt-BR',{maximumFractionDigits:4}).format(r.value);
      cell.style.background = 'rgba(35,193,107,.15)';
      setTimeout(() => cell.style.background = '', 1200);
    }
  };
  input.onblur = save;
  input.onkeydown = e => { if (e.key==='Enter') { e.preventDefault(); save(); } if (e.key==='Escape') cell.textContent = current; };
};
function fillSelect(id, items, keepBlank) {
  const s = document.getElementById(id); if (!s) return;
  const cur = s.value;
  s.innerHTML = (keepBlank ? '<option value="">Todos</option>' : '') +
    (items||[]).map(x => `<option value="${x}">${x}</option>`).join('');
  if ((items||[]).includes(cur)) s.value = cur;
}

// ── SEPARADOR ─────────────────────────────────────────────────────────────────

// All available separator metric definitions with labels and groups
