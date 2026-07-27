'use strict';

const CH_PAL = ['#26a0ff', '#23c16b', '#f3b33d', '#a855f7', '#06b6d4', '#ec4899', '#84cc16', '#fb923c', '#6366f1', '#22d3ee'];
const CH_GROUP_COLORS = {
  prod: '#26a0ff',
  pvt: '#f3b33d',
  sep: '#a855f7',
  proc: '#23c16b',
  other: '#8ea3ba',
};
const CH_RIGHT = new Set([
  'Pressão (barg)',
  'Temperatura (°C)',
  'Dens. Gás (kg/m³)',
  'Dens. Óleo (kg/m³)',
  'Dens. Água (kg/m³)',
  'Pressure_kPa',
  'Pressure_kPa_g',
  'Pressure_barg',
  'Temperature_degC',
  'SD_kg_sm3',
  'MD_kg_m3',
  'DT_kg_m3',
  'BSW_pct',
  'CPL',
  'CTL',
  'DiffPress_kPa',
  'Flowtime_min',
]);
const CHART_PRESET_LABELS = {
  advanced: 'Modo avançado ativo.',
  subsea_topside: 'Comparando pares Subsea × Topside.',
  separator_test: 'Mostrando a tendência do Separador de Teste.',
  mpfm_sep: 'Comparando MPFM com o Separador de Teste.',
  recon: 'Comparando daily, soma hourly e desvio de reconciliação.',
};
const CHART_PRESET_DEFAULT_METRIC = {
  subsea_topside: 'hc',
  separator_test: 'oil',
  mpfm_sep: 'hc',
  recon: 'hc',
};

function chartState() {
  const temp = window.__chartTempState || (window.__chartTempState = {});
  if (typeof state !== 'undefined') {
    Object.keys(temp).forEach(key => {
      if (typeof state[key] === 'undefined') state[key] = temp[key];
    });
    return state;
  }
  return temp;
}

chartState().chartPreset = chartState().chartPreset || 'advanced';
chartState().chartPresetMeta = chartState().chartPresetMeta || null;
chartState().chartSeparatorMode = chartState().chartSeparatorMode || 'daily';

window.cGroup = function cGroup(group) {
  document.querySelectorAll('.cm-var').forEach(cb => {
    if (group === 'none') {
      cb.checked = false;
    } else if (group === 'all') {
      cb.checked = true;
    } else {
      cb.checked = cb.dataset.group === group;
    }
    styleMetricChk(cb);
  });
};

function styleMetricChk(cb) {
  const lbl = cb.closest('label');
  if (!lbl) return;
  if (cb.checked) {
    lbl.style.borderColor = 'var(--accent)';
    lbl.style.color = 'var(--text)';
    lbl.style.background = 'rgba(38,160,255,.1)';
  } else {
    const noData = lbl.classList.contains('sem-dados');
    lbl.style.borderColor = noData ? 'rgba(168,85,247,.35)' : 'var(--line)';
    lbl.style.color = 'var(--muted)';
    lbl.style.background = noData ? 'rgba(168,85,247,.08)' : 'var(--panel2)';
  }
}

function chartSetStatus(text) {
  const el = document.getElementById('cPresetStatus');
  if (el) el.textContent = text || '';
}

function chartSetEmpty(message) {
  const empty = document.getElementById('cEmpty');
  const wrap = document.getElementById('cWrap');
  const stats = document.getElementById('cStats');
  if (empty) {
    empty.style.display = 'flex';
    empty.innerHTML = `
      <span style="font-size:40px;opacity:.3">📈</span>
      <span style="color:var(--muted);font-size:13px;text-align:center">${message || 'Sem dados para o recorte selecionado.'}</span>
    `;
  }
  if (wrap) wrap.style.display = 'none';
  if (stats) stats.textContent = 'Sem séries carregadas';
  const appState = chartState();
  if (appState.chart) {
    appState.chart.destroy();
    appState.chart = null;
  }
}

function chartFillSelectOptions(id, items, keepBlank, blankLabel) {
  const select = document.getElementById(id);
  if (!select) return;
  const current = select.value;
  const normalized = (items || []).map(item => {
    if (typeof item === 'string') return { value: item, label: item };
    return item;
  });
  select.innerHTML = '';
  if (keepBlank) {
    const option = document.createElement('option');
    option.value = '';
    option.textContent = blankLabel || 'Todos';
    select.appendChild(option);
  }
  normalized.forEach(item => {
    const option = document.createElement('option');
    option.value = item.value;
    option.textContent = item.label;
    select.appendChild(option);
  });
  if (normalized.some(item => item.value === current)) {
    select.value = current;
  } else if (keepBlank) {
    select.value = '';
  } else if (normalized[0]) {
    select.value = normalized[0].value;
  }
}

function chartMonthRange() {
  const month = document.getElementById('globalMonth')?.value || '';
  if (month && typeof getMonthRange === 'function') return getMonthRange(month);
  return { from: '', to: '' };
}

function chartEnsureDefaultDates() {
  const dateFrom = document.getElementById('cDateFrom');
  const dateTo = document.getElementById('cDateTo');
  if (!dateFrom || !dateTo) return;
  if (dateFrom.value && dateTo.value) return;
  const { from, to } = chartMonthRange();
  if (!dateFrom.value) dateFrom.value = from;
  if (!dateTo.value) dateTo.value = to;
  if (typeof refreshDateInputDisplay === 'function') refreshDateInputDisplay(document);
}

function chartCurrentRange() {
  return {
    dateFrom: document.getElementById('cDateFrom')?.value || document.getElementById('cDateFrom')?.dataset.isoValue || '',
    dateTo: document.getElementById('cDateTo')?.value || document.getElementById('cDateTo')?.dataset.isoValue || '',
  };
}

function chartCurrentKind() {
  return document.getElementById('cKind')?.value || 'daily';
}

function chartSyncPresetButtons() {
  const appState = chartState();
  document.querySelectorAll('.charts-preset-chip').forEach(button => {
    const active = button.dataset.preset === appState.chartPreset;
    button.classList.toggle('active', active);
    button.setAttribute('aria-pressed', active ? 'true' : 'false');
  });
}

function chartSyncModeUi() {
  const appState = chartState();
  const isAdvanced = appState.chartPreset === 'advanced';
  document.querySelectorAll('.charts-advanced-only').forEach(el => el.classList.toggle('is-hidden', !isAdvanced));
  const controls = document.getElementById('cPresetControls');
  if (controls) controls.style.display = isAdvanced ? 'none' : 'grid';
  const separatorModeWrap = document.getElementById('cSeparatorModeWrap');
  if (separatorModeWrap) separatorModeWrap.style.display = appState.chartPreset === 'separator_test' ? 'block' : 'none';
  chartSetStatus(CHART_PRESET_LABELS[appState.chartPreset] || 'Preset selecionado.');
  chartSyncPresetButtons();
}

async function buildMetricGrid(metrics) {
  const host = document.getElementById('cMetricGrid');
  if (!host) return;
  const key = JSON.stringify(metrics || []);
  if (host.dataset.metricsKey === key) return;
  host.dataset.metricsKey = key;
  host.innerHTML = (metrics || []).map(item => {
    const metric = typeof item === 'string' ? { value: item, label: item, group: 'other', has_data: true } : item;
    const dot = CH_GROUP_COLORS[metric.group] || CH_GROUP_COLORS.other;
    const hint = metric.has_data ? '' : '<span class="chart-metric-chip__hint">· sem dados</span>';
    const noDataClass = metric.has_data ? '' : ' sem-dados';
    return `<label class="chart-metric-chip${noDataClass}">
      <input type="checkbox" class="cm-var" data-group="${metric.group || 'other'}" data-metric="${metric.value}" style="width:12px;height:12px;accent-color:${dot}" onchange="styleMetricChk(this)">
      <span style="display:inline-block;width:7px;height:7px;border-radius:50%;background:${dot};flex-shrink:0"></span>
      <span>${metric.label}</span>
      ${hint}
    </label>`;
  }).join('');
  const preferredGroups = ['prod', 'pvt', 'sep', 'proc', 'other'];
  const firstGroup = preferredGroups.find(group => (metrics || []).some(item => (typeof item === 'string' ? 'other' : (item.group || 'other')) === group)) || 'all';
  cGroup(firstGroup);
}

async function chartLoadAdvancedMeta() {
  const { dateFrom, dateTo } = chartCurrentRange();
  const kind = chartCurrentKind();
  const baseMeta = await j(`${API}/ops/chart-meta?${new URLSearchParams({ date_from: dateFrom, date_to: dateTo, row_kind: kind })}`);
  chartFillSelectOptions('cBank', baseMeta.banks || [], true, 'Todos');
  const bank = document.getElementById('cBank')?.value || '';
  const tagMeta = await j(`${API}/ops/chart-meta?${new URLSearchParams({ date_from: dateFrom, date_to: dateTo, row_kind: kind, bank })}`);
  chartFillSelectOptions('cTag', tagMeta.tags || [], true, bank === 'SEP' && kind === 'hourly' ? 'Selecione o medidor' : 'Todas');
  const tagSelect = document.getElementById('cTag');
  if (bank === 'SEP' && kind === 'hourly' && tagSelect && !tagSelect.value && (tagMeta.tags || []).length) {
    tagSelect.value = (tagMeta.tags || [])[0].value || '';
  }
  const tag = tagSelect?.value || '';
  const metricMeta = await j(`${API}/ops/chart-meta?${new URLSearchParams({ date_from: dateFrom, date_to: dateTo, row_kind: kind, bank, tag })}`);
  chartState().allMetrics = metricMeta.metrics || [];
  await buildMetricGrid(metricMeta.metrics || []);
}

async function chartLoadPresetMeta() {
  const { dateFrom, dateTo } = chartCurrentRange();
  chartState().chartPresetMeta = await j(`${API}/ops/chart-presets-meta?${new URLSearchParams({ date_from: dateFrom, date_to: dateTo })}`);
}

function chartPresetTargetOptions() {
  const appState = chartState();
  const meta = appState.chartPresetMeta || {};
  if (appState.chartPreset === 'subsea_topside') return (meta.focus_pairs || []).filter(item => item.available);
  if (appState.chartPreset === 'separator_test') return [{ value: 'separator', label: 'Separador de Teste' }];
  if (appState.chartPreset === 'mpfm_sep') return meta.aligned_targets || [];
  if (appState.chartPreset === 'recon') return meta.recon_targets || [];
  return [];
}

function chartPresetMetricOptions() {
  const appState = chartState();
  const meta = appState.chartPresetMeta || {};
  if (appState.chartPreset === 'separator_test') {
    return appState.chartSeparatorMode === 'hourly'
      ? (meta.separator_metrics_hourly || [])
      : (meta.separator_metrics_daily || []);
  }
  return meta.compare_metrics || [];
}

function chartRefreshPresetControls() {
  const appState = chartState();
  if (appState.chartPreset === 'advanced') return;
  const separatorModeSelect = document.getElementById('cSeparatorMode');
  if (separatorModeSelect) separatorModeSelect.value = appState.chartSeparatorMode || 'daily';
  const targetOptions = chartPresetTargetOptions();
  const metricOptions = chartPresetMetricOptions();
  chartFillSelectOptions('cPresetTarget', targetOptions, false, 'Selecione');
  chartFillSelectOptions('cPresetMetric', metricOptions, false, 'Selecione');
  const metricSelect = document.getElementById('cPresetMetric');
  const defaultMetric = CHART_PRESET_DEFAULT_METRIC[appState.chartPreset];
  if (metricSelect && defaultMetric && (!metricSelect.value || !metricOptions.some(item => item.value === metricSelect.value)) && metricOptions.some(item => item.value === defaultMetric)) {
    metricSelect.value = defaultMetric;
  } else if (metricSelect && metricOptions[0] && !metricSelect.value) {
    metricSelect.value = metricOptions[0].value;
  }
  const targetSelect = document.getElementById('cPresetTarget');
  if (targetSelect && !targetOptions.length) {
    targetSelect.innerHTML = '<option value="">Sem dados no período</option>';
    targetSelect.value = '';
  }
}

function chartMode() {
  return chartState().chartPreset === 'advanced' ? 'advanced' : 'preset';
}

function chartSeriesPayload(series, labels, kind, deviationKey) {
  return {
    labels,
    datasets: series,
    kind,
    deviationKey: deviationKey || '',
    mode: chartMode(),
  };
}

function formatChartValue(value) {
  return new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 4 }).format(value);
}

function chartLastValue(values) {
  const clean = [...(values || [])].reverse().find(value => value != null);
  return clean == null ? '' : formatChartValue(clean);
}

const chartValueLabelsPlugin = {
  id: 'chartValueLabels',
  afterDatasetsDraw(chart, _args, options) {
    if (!options || !options.enabled) return;
    const labelCount = chart.data?.labels?.length || 0;
    if (!labelCount) return;
    const step = labelCount > 96 ? 8 : labelCount > 48 ? 4 : labelCount > 24 ? 2 : 1;
    const { ctx } = chart;
    ctx.save();
    ctx.font = '10px "IBM Plex Mono", monospace';
    ctx.textAlign = 'center';
    chart.data.datasets.forEach((dataset, datasetIndex) => {
      if (!chart.isDatasetVisible(datasetIndex) || String(dataset.label || '').startsWith('__band')) return;
      const meta = chart.getDatasetMeta(datasetIndex);
      ctx.fillStyle = dataset.borderColor || '#9ca3af';
      meta.data.forEach((point, pointIndex) => {
        if (pointIndex % step !== 0) return;
        const rawValue = dataset.data?.[pointIndex];
        if (rawValue == null || !Number.isFinite(rawValue)) return;
        const pos = point.tooltipPosition();
        ctx.fillText(formatChartValue(rawValue), pos.x, pos.y - 10);
      });
    });
    ctx.restore();
  },
};

function formatChartXAxisLabel(label, kind) {
  const raw = String(label || '');
  if (!raw) return '';
  if (kind === 'daily' && /^\d{4}-\d{2}-\d{2}$/.test(raw)) {
    const [, mo, day] = raw.split('-');
    return `${day}/${mo}`;
  }
  if (kind === 'hourly') {
    const m = raw.match(/^(\d{4})-(\d{2})-(\d{2})[ T](\d{2})/);
    if (m) return `${m[3]}/${m[2]} ${m[4]}h`;
  }
  return raw;
}

function addDevBands(datasets, vals, pct, color, axId) {
  const p = `${(pct * 100).toFixed(0)}%`;
  const base = { yAxisID: axId, borderColor: color, borderWidth: 1.5, borderDash: [7, 4], pointRadius: 0, tension: 0.3, spanGaps: true };
  datasets.push({ ...base, label: `__band +${p}`, data: vals.map(v => (v == null ? null : v * (1 + pct))), backgroundColor: `${color}18`, fill: '+1', order: 99 });
  datasets.push({ ...base, label: `__band -${p}`, data: vals.map(v => (v == null ? null : v * (1 - pct))), backgroundColor: 'transparent', fill: false, order: 99 });
}

function renderChart() {
  const appState = chartState();
  const payload = appState.chartData;
  if (!payload || !payload.labels || !payload.labels.length || !payload.datasets || !payload.datasets.length) {
    chartSetEmpty('Sem dados para o recorte selecionado.');
    return;
  }
  const wrap = document.getElementById('cWrap');
  const stage = document.getElementById('mainChartStage');
  const dualY = document.getElementById('cDualY')?.checked;
  const filled = document.getElementById('cFill')?.checked;
  const showValues = document.getElementById('cShowValues')?.checked;
  const devHC = document.getElementById('devHC')?.checked;
  const devTot = document.getElementById('devTotal')?.checked;
  const kind = payload.kind || 'daily';

  const slotWidth = kind === 'hourly' ? 52 : 40;
  const minStageWidth = Math.max(wrap?.clientWidth || 0, payload.labels.length * slotWidth);
  if (stage) stage.style.width = `${minStageWidth}px`;

  const datasets = [];
  payload.datasets.forEach((entry, index) => {
    const color = CH_PAL[index % CH_PAL.length];
    const axId = (dualY && CH_RIGHT.has(entry.metric || entry.label)) ? 'yR' : 'yL';
    const lastValue = chartLastValue(entry.data || entry.values || []);
    const legendLabel = showValues && lastValue ? `${entry.label} · ${lastValue}` : entry.label;
    datasets.push({
      label: legendLabel,
      data: entry.data || entry.values || [],
      yAxisID: axId,
      borderColor: color,
      backgroundColor: filled ? `${color}22` : 'transparent',
      borderWidth: 2,
      pointRadius: payload.labels.length > 60 ? 1 : payload.labels.length > 24 ? 2 : 3,
      pointBackgroundColor: color,
      pointHoverRadius: 5,
      tension: 0.3,
      spanGaps: true,
      fill: filled ? 'origin' : false,
    });
  });

  const baseline = datasets[0]?.data || [];
  if (devHC && baseline.length) addDevBands(datasets, baseline, 0.10, '#ef5a5a', 'yL');
  if (devTot && baseline.length) addDevBands(datasets, baseline, 0.07, '#a855f7', 'yL');

  const tBase = { color: '#6b7280', font: { family: 'Inter,sans-serif', size: 9 } };
  const scales = {
    x: {
      ticks: {
        ...tBase,
        autoSkip: false,
        maxRotation: kind === 'hourly' ? 60 : 0,
        minRotation: kind === 'hourly' ? 60 : 0,
        callback: (_, idx) => formatChartXAxisLabel(payload.labels[idx], kind),
      },
      grid: { color: 'rgba(255,255,255,.04)' },
    },
    yL: {
      type: 'linear',
      position: 'left',
      ticks: tBase,
      grid: { color: 'rgba(255,255,255,.06)' },
    },
  };
  if (dualY) {
    scales.yR = {
      type: 'linear',
      position: 'right',
      ticks: { ...tBase, color: '#6ee7b7' },
      grid: { drawOnChartArea: false },
    };
  }

  if (appState.chart) {
    appState.chart.destroy();
    appState.chart = null;
  }
  document.getElementById('cEmpty').style.display = 'none';
  wrap.style.display = 'block';
  document.getElementById('cStats').textContent = `${payload.labels.length} pts · ${payload.datasets.length} série(s)`;

  const ctx = document.getElementById('mainChart').getContext('2d');
  appState.chart = new Chart(ctx, {
    type: 'line',
    data: { labels: payload.labels, datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        chartValueLabels: { enabled: !!showValues },
        legend: {
          position: 'top',
          labels: {
            color: '#9ca3af',
            font: { family: 'Inter,sans-serif', size: 10 },
            boxWidth: 12,
            padding: 14,
            filter: item => !item.text.startsWith('__band'),
          },
        },
        tooltip: {
          backgroundColor: 'rgba(8,17,28,.97)',
          titleColor: '#e2e8f0',
          bodyColor: '#9ca3af',
          borderColor: 'rgba(38,160,255,.2)',
          borderWidth: 1,
          padding: 10,
          callbacks: {
            label: ctx => {
              if (ctx.dataset.label.startsWith('__band')) return null;
              const value = ctx.parsed.y;
              if (value == null) return null;
              return ` ${ctx.dataset.label}: ${formatChartValue(value)}`;
            },
          },
        },
      },
      scales,
      animation: { duration: (typeof prefersReducedMotion === 'function' && prefersReducedMotion()) ? 0 : 250 },
    },
    plugins: [chartValueLabelsPlugin],
  });
}

async function plotAdvancedChart() {
  const { dateFrom, dateTo } = chartCurrentRange();
  const kind = chartCurrentKind();
  const bank = document.getElementById('cBank')?.value || '';
  const tag = document.getElementById('cTag')?.value || '';
  await chartLoadAdvancedMeta();
  const selected = [...document.querySelectorAll('.cm-var:checked')].map(cb => cb.dataset.metric);
  if (!selected.length) {
    chartSetEmpty('Selecione pelo menos uma métrica no modo avançado.');
    return;
  }
  const series = await Promise.all(selected.map(async metric => {
    const query = new URLSearchParams({ date_from: dateFrom, date_to: dateTo, row_kind: kind, bank, tag, metric });
    const data = await j(`${API}/ops/chart-series?${query}`);
    return { label: metric, metric, data: data.values || [], labels: data.labels || [] };
  }));
  const labels = [...new Set(series.flatMap(item => item.labels))].sort();
  const normalizedSeries = series.map(item => {
    const valueMap = Object.fromEntries(item.labels.map((label, idx) => [label, item.data[idx]]));
    return {
      label: item.label,
      metric: item.metric,
      data: labels.map(label => valueMap[label] ?? null),
    };
  });
  chartState().chartData = chartSeriesPayload(normalizedSeries, labels, kind, '');
  renderChart();
}

async function plotPresetChart() {
  const appState = chartState();
  const target = document.getElementById('cPresetTarget')?.value || '';
  const metricKey = document.getElementById('cPresetMetric')?.value || CHART_PRESET_DEFAULT_METRIC[appState.chartPreset] || 'hc';
  if (appState.chartPreset !== 'separator_test' && !target) {
    chartSetEmpty('Selecione um alvo para o preset escolhido.');
    return;
  }
  const { dateFrom, dateTo } = chartCurrentRange();
  const query = new URLSearchParams({
    date_from: dateFrom,
    date_to: dateTo,
    preset: appState.chartPreset,
    target,
    metric_key: metricKey,
  });
  if (appState.chartPreset === 'separator_test') {
    query.set('separator_mode', appState.chartSeparatorMode || 'daily');
  }
  const data = await j(`${API}/ops/chart-preset-series?${query}`);
  chartSetStatus(data.message || CHART_PRESET_LABELS[appState.chartPreset]);
  if (!data.labels || !data.labels.length) {
    chartSetEmpty(data.message || 'Sem dados para o preset e período selecionados.');
    return;
  }
  chartState().chartData = chartSeriesPayload(
    (data.datasets || []).map(dataset => ({ label: dataset.label, data: dataset.values || [] })),
    data.labels || [],
    data.kind || 'daily',
    data.deviation_key || '',
  );
  renderChart();
}

async function plotChart() {
  if (chartState().chartPreset === 'advanced') return plotAdvancedChart();
  return plotPresetChart();
}

async function replotChart() {
  if (!chartState().chartData) return;
  renderChart();
}

async function chartRefreshAllMeta() {
  await chartLoadPresetMeta();
  if (chartState().chartPreset === 'advanced') {
    await chartLoadAdvancedMeta();
  }
  chartRefreshPresetControls();
}

function setChartPreset(preset) {
  chartState().chartPreset = preset || 'advanced';
  chartSyncModeUi();
  chartRefreshPresetControls();
  plotChart();
}

window.loadChartsPage = async function loadChartsPage() {
  chartEnsureDefaultDates();
  chartSyncModeUi();
  await chartRefreshAllMeta();
  await plotChart();
};

document.getElementById('cPlot').onclick = plotChart;
document.getElementById('cApplyPreset').onclick = plotChart;
document.getElementById('cKind').addEventListener('change', async () => {
  if (chartState().chartPreset !== 'advanced') return;
  await chartLoadAdvancedMeta();
});
document.getElementById('cBank').addEventListener('change', async () => {
  if (chartState().chartPreset !== 'advanced') return;
  await chartLoadAdvancedMeta();
});
document.getElementById('cTag').addEventListener('change', async () => {
  if (chartState().chartPreset !== 'advanced') return;
  await chartLoadAdvancedMeta();
});
['cDateFrom', 'cDateTo'].forEach(id => {
  document.getElementById(id)?.addEventListener('change', async () => {
    await chartRefreshAllMeta();
  });
});
document.getElementById('cSeparatorMode')?.addEventListener('change', async event => {
  chartState().chartSeparatorMode = event.target.value || 'daily';
  chartRefreshPresetControls();
  if (chartState().chartPreset === 'separator_test') {
    await plotChart();
  }
});
document.querySelectorAll('.charts-preset-chip').forEach(button => {
  button.addEventListener('click', () => setChartPreset(button.dataset.preset));
});
window.replotChart = replotChart;
