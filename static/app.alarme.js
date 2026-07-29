'use strict';

(function () {
  const workspace = state.alarmWorkspace || (state.alarmWorkspace = { rows: [], selectedId: null, detail: null, summary: null, preview: null, catalog: {}, currentSourceRef: '', alarmOffset: 0, alarmLimit: 50, alarmHasMore: true });

  function severityLabel(code) {
    const mapping = {
      critical: ['Crítica', 'alarm-chip--critical'],
      warning: ['Atenção', 'alarm-chip--warning'],
      info: ['Info', 'alarm-chip--info'],
    };
    return mapping[String(code || '').toLowerCase()] || [code || '—', 'alarm-chip--info'];
  }

  function statusLabel(code) {
    const mapping = {
      open: 'Aberta',
      in_progress: 'Em andamento',
      monitoring: 'Monitoramento',
      closed: 'Encerrada',
      cancelled: 'Cancelada',
    };
    return mapping[String(code || '').toLowerCase()] || (code || '—');
  }

  function typeLabel(code) {
    return String(code || '').toLowerCase() === 'incident' ? 'Incidente' : 'Evento';
  }

  function renderChip(label, cls) {
    return `<span class="alarm-chip ${cls}">${escapeHtml(label)}</span>`;
  }

  function formatNumber(value) {
    return Number(value || 0).toLocaleString('pt-BR');
  }

  function formatPercent(part, total) {
    if (!total) return '0%';
    return `${Math.round((Number(part || 0) / Number(total || 0)) * 100)}%`;
  }

  function formatDateTime(value) {
    const raw = String(value || '').trim();
    if (!raw) return '—';
    const m = raw.match(/^(\d{4})-(\d{2})-(\d{2})(?:[ T](\d{2}):(\d{2})(?::(\d{2}))?)?/);
    if (!m) return raw;
    const date = `${m[3]}/${m[2]}/${m[1]}`;
    if (!m[4]) return date;
    return `${date} ${m[4]}:${m[5]}`;
  }

  function qsValue(id) {
    return document.getElementById(id)?.value?.trim?.() || '';
  }

  function setAlarmStatusLine(message, kind = '') {
    const host = document.getElementById('alarmUploadStatus');
    if (!host) return;
    host.textContent = message;
    host.classList.remove('is-error', 'is-success');
    if (kind) host.classList.add(kind === 'error' ? 'is-error' : 'is-success');
  }

  function mergeUnique(values) {
    return Array.from(new Set((values || []).filter(Boolean).map(value => String(value).trim()).filter(Boolean))).sort((a, b) => a.localeCompare(b, 'pt-BR'));
  }

  function populateSelect(selectId, items, currentValue, allLabel) {
    const el = document.getElementById(selectId);
    if (!el) return;
    const previous = currentValue != null ? currentValue : el.value;
    const options = [`<option value="">${escapeHtml(allLabel || 'Todos')}</option>`]
      .concat((items || []).map(item => {
        const value = typeof item === 'string' ? item : item.code;
        const label = typeof item === 'string' ? item : (item.label || item.code);
        return `<option value="${escapeHtml(value)}">${escapeHtml(label)}</option>`;
      }));
    el.innerHTML = options.join('');
    if (previous && Array.from(el.options).some(opt => opt.value === previous)) {
      el.value = previous;
    }
  }

  function populateRowDerivedFilters(rows) {
    populateSelect('alarmMeasurementPoint', mergeUnique((rows || []).map(row => row.measurement_point || row.tag)), null, 'Todos');
    populateSelect('alarmSourceSheet', mergeUnique((rows || []).map(row => row.source_sheet)), null, 'Todas');
  }

  function renderAlarmSummary(summary) {
    workspace.summary = summary || {};
    const host = document.getElementById('alarmSummaryCards');
    if (!host) return;
    const cards = [
      ['Registros ativos', summary.total_active || 0, `${summary.events || 0} eventos · ${summary.incidents || 0} incidentes`],
      ['Ocorrências abertas', summary.open || 0, 'Fila que exige avaliação operacional'],
      ['Críticos', summary.critical || 0, 'Casos com maior potencial de impacto'],
      ['Em andamento', summary.in_progress || 0, 'Casos com investigação ou contenção em curso'],
      ['Monitoramento', summary.monitoring || 0, 'Ocorrências acompanhadas após ação'],
      ['Ações abertas', summary.actions_open || 0, `${summary.overdue || 0} ação(ões) vencida(s)`],
    ];
    host.innerHTML = cards.map(([label, value, meta]) => `
      <div class="alarm-summary-card">
        <div class="alarm-summary-card__label">${escapeHtml(label)}</div>
        <div class="alarm-summary-card__value">${escapeHtml(String(value))}</div>
        <div class="alarm-summary-card__meta">${escapeHtml(meta)}</div>
      </div>
    `).join('');
  }

  function renderAlarmPreview(preview) {
    workspace.preview = preview || null;
    const grid = document.getElementById('alarmPreviewGrid');
    const refs = document.getElementById('alarmPreviewRefs');
    const chip = document.getElementById('alarmWorkbookModel');
    if (!grid || !refs || !chip) return;
    if (!preview) {
      chip.textContent = 'Sem análise';
      grid.innerHTML = '<div class="alarm-preview-empty">Faça um upload para ver o recorte do workbook analisado.</div>';
      refs.innerHTML = '';
      renderAlarmDerivation(null);
      return;
    }
    const modelLabel = preview.model_type === 'enriched'
      ? 'Modelo enriquecido'
      : preview.model_type === 'raw-derived'
        ? 'Bruto com derivação interna'
        : preview.model_type === 'raw'
          ? 'Modelo bruto'
          : 'Modelo não identificado';
    chip.textContent = modelLabel;
    const cards = [
      ['Eventos', preview.events?.rows || 0, `${(preview.events?.meters || []).join(', ') || 'Sem medidores identificados'}`],
      ['Incidentes', preview.incidents?.rows || 0, preview.incident_rows ? 'Agrupamentos operacionais detectados' : 'Sem incidentes na leitura'],
      ['Fonte dos eventos', preview.event_source_sheet || '—', `Abas encontradas: ${Object.entries(preview.sheets_found || {}).filter(([, ok]) => ok).map(([name]) => name).join(', ') || 'nenhuma'}`],
    ];
    grid.innerHTML = cards.map(([label, value, meta]) => `
      <div class="alarm-preview-card">
        <div class="alarm-preview-card__label">${escapeHtml(label)}</div>
        <div class="alarm-preview-card__value">${escapeHtml(String(value))}</div>
        <div class="alarm-preview-card__meta">${escapeHtml(meta)}</div>
      </div>
    `).join('');
    const chips = [];
    (preview.references_detected?.families || []).forEach(item => chips.push(tagChip(`Família: ${item}`)));
    (preview.references_detected?.categories || []).forEach(item => chips.push(tagChip(`Categoria: ${item}`)));
    (preview.references_detected?.measurement_states || []).forEach(item => chips.push(tagChip(`Estado: ${item}`)));
    refs.innerHTML = chips.join('');
    renderAlarmDerivation(preview);
    renderAlarmMonitoring(preview.monitoring || {});
  }

  function renderAlarmDerivation(preview) {
    const meta = document.getElementById('alarmDerivationMeta');
    const chip = document.getElementById('alarmDerivationChip');
    const banner = document.getElementById('alarmDerivationBanner');
    const flow = document.getElementById('alarmDerivationFlow');
    if (!meta || !chip || !banner || !flow) return;
    if (!preview) {
      chip.textContent = 'Pipeline interno';
      meta.textContent = 'Aguardando workbook para montar o funil bruto → eventos → incidentes.';
      banner.innerHTML = '<strong>Sem derivação carregada.</strong><span>Faça upload de um workbook para ver como a aplicação transforma o Excel recebido na fila operacional exibida abaixo.</span>';
      flow.innerHTML = '<div class="alarm-preview-empty">O funil operacional aparecerá aqui após a leitura do workbook.</div>';
      return;
    }

    const isRawDerived = preview.model_type === 'raw-derived';
    const rawRows = Number(preview.raw_event_rows || 0);
    const eventRows = Number(preview.events?.rows || 0);
    const incidentRows = Number(preview.incidents?.rows || 0);
    const dailyRows = Number(preview.monitoring?.daily?.row_count || 0);
    const monthlyRows = Number(preview.monitoring?.monthly?.row_count || 0);

    chip.textContent = isRawDerived ? 'Derivado do Alarmes_Log' : 'Modelo operacional final';
    meta.textContent = isRawDerived
      ? 'O Excel bruto enviado foi consolidado internamente para produzir exatamente os eventos, incidentes e monitoramentos exibidos nesta tela.'
      : 'O workbook já veio estruturado, mas a tela continua exibindo o mesmo modelo operacional final usado pela aplicação.';
    banner.innerHTML = isRawDerived
      ? `<strong>Origem operacional: aba Alarmes_Log.</strong><span>${formatNumber(rawRows)} linhas técnicas foram lidas e convertidas automaticamente em ${formatNumber(eventRows)} eventos consolidados, ${formatNumber(incidentRows)} incidentes e janelas de monitoramento diário/mensal.</span>`
      : `<strong>Origem operacional: workbook estruturado.</strong><span>A aplicação carregou diretamente os eventos, incidentes e monitoramentos do arquivo já consolidado, preservando o mesmo modelo final de operação.</span>`;

    const steps = isRawDerived
      ? [
          ['Linhas brutas', formatNumber(rawRows), 'Bits ativos recebidos diretamente da aba Alarmes_Log.'],
          ['Eventos consolidados', formatNumber(eventRows), `${formatPercent(eventRows, rawRows)} do bruto virou eventos tratáveis após consolidação temporal.`],
          ['Incidentes', formatNumber(incidentRows), `${formatPercent(incidentRows, eventRows)} dos eventos formaram agrupamentos operacionais.`],
          ['Monitoramento', formatNumber(dailyRows + monthlyRows), `${formatNumber(dailyRows)} janelas diárias · ${formatNumber(monthlyRows)} mensais.`],
        ]
      : [
          ['Eventos', formatNumber(eventRows), 'Registros finais já vieram estruturados no workbook.'],
          ['Incidentes', formatNumber(incidentRows), 'Agrupamentos operacionais já estavam presentes na carga.'],
          ['Monit. diário', formatNumber(dailyRows), 'Janelas diárias prontas para leitura operacional.'],
          ['Monit. mensal', formatNumber(monthlyRows), 'Janelas mensais prontas para acompanhamento tático.'],
        ];

    flow.innerHTML = steps.map(([label, value, detail]) => `
      <div class="alarm-derivation-step">
        <div class="alarm-derivation-step__label">${escapeHtml(label)}</div>
        <div class="alarm-derivation-step__value">${escapeHtml(String(value))}</div>
        <div class="alarm-derivation-step__meta">${escapeHtml(detail)}</div>
      </div>
    `).join('<div class="alarm-derivation-arrow" aria-hidden="true">→</div>');
  }

  function renderMonitoringTable(hostId, rows, periodLabel) {
    const host = document.getElementById(hostId);
    if (!host) return;
    if (!(rows || []).length) {
      host.innerHTML = `<tr><td colspan="8" style="text-align:center;color:var(--muted);padding:24px">Sem dados de ${escapeHtml(periodLabel.toLowerCase())} disponíveis no workbook.</td></tr>`;
      return;
    }
    host.innerHTML = rows.map(row => `
      <tr>
        <td>${escapeHtml(formatDateTime(row.period))}</td>
        <td>${escapeHtml(row.measurement_point || '—')}</td>
        <td>${escapeHtml(row.instrument || '—')}</td>
        <td>${escapeHtml(String(row.snapshots || 0))}</td>
        <td>${escapeHtml(String(row.events || 0))}</td>
        <td>${escapeHtml(String(row.incidents_started || 0))}</td>
        <td>${escapeHtml(String(row.critical || 0))}</td>
        <td>${escapeHtml(String(row.open_count || 0))}</td>
      </tr>
    `).join('');
  }

  function renderMonitoringSummaryCards(hostId, cards) {
    const host = document.getElementById(hostId);
    if (!host) return;
    host.innerHTML = cards.map(([label, value, meta]) => `
      <div class="alarm-monitor-summary-card">
        <div class="alarm-monitor-summary-card__label">${escapeHtml(label)}</div>
        <div class="alarm-monitor-summary-card__value">${escapeHtml(String(value))}</div>
        <div class="alarm-monitor-summary-card__meta">${escapeHtml(meta)}</div>
      </div>
    `).join('');
  }

  function renderAlarmMonitoring(monitoring) {
    const daily = monitoring?.daily || null;
    const monthly = monitoring?.monthly || null;
    const dailyMeta = document.getElementById('alarmDailyMonitorMeta');
    const monthlyMeta = document.getElementById('alarmMonthlyMonitorMeta');
    if (dailyMeta) {
      dailyMeta.textContent = daily?.row_count
        ? `Última janela diária: ${formatDateTime(daily.latest_period)} · pico em ${daily.peak_measurement_point || '—'}`
        : 'Sem leitura diária disponível.';
    }
    if (monthlyMeta) {
      monthlyMeta.textContent = monthly?.row_count
        ? `Última janela mensal: ${formatDateTime(monthly.latest_period)} · pico em ${monthly.peak_measurement_point || '—'}`
        : 'Sem leitura mensal disponível.';
    }
    renderMonitoringSummaryCards('alarmDailyMonitorSummary', daily?.row_count ? [
      ['Snapshots', daily.totals.snapshots || 0, `Linhas analisadas: ${daily.row_count}`],
      ['Eventos', daily.totals.events || 0, `Críticos: ${daily.totals.critical || 0}`],
      ['Incidentes iniciados', daily.totals.incidents_started || 0, `Abertos no dia: ${daily.totals.open_count || 0}`],
      ['Bits reservados', daily.totals.reserved_bits || 0, daily.window || 'Janela diária'],
    ] : [['Sem leitura', '—', 'Faça upload de um workbook com a aba Monitoramento_Diario.']]);
    renderMonitoringSummaryCards('alarmMonthlyMonitorSummary', monthly?.row_count ? [
      ['Snapshots', monthly.totals.snapshots || 0, `Linhas analisadas: ${monthly.row_count}`],
      ['Eventos', monthly.totals.events || 0, `Críticos: ${monthly.totals.critical || 0}`],
      ['Incidentes iniciados', monthly.totals.incidents_started || 0, `Abertos no mês: ${monthly.totals.open_count || 0}`],
      ['Bits reservados', monthly.totals.reserved_bits || 0, monthly.window || 'Janela mensal'],
    ] : [['Sem leitura', '—', 'Faça upload de um workbook com a aba Monitoramento_Mensal.']]);
    renderMonitoringTable('alarmDailyMonitorRows', daily?.latest_rows || [], 'monitoramento diário');
    renderMonitoringTable('alarmMonthlyMonitorRows', monthly?.latest_rows || [], 'monitoramento mensal');
  }

  function renderAlarmRows(rows) {
    workspace.rows = rows || [];
    populateRowDerivedFilters(workspace.rows);
    const tbody = document.getElementById('alarmRows');
    const meta = document.getElementById('alarmTableMeta');
    if (!tbody || !meta) return;
    meta.textContent = workspace.rows.length ? `${workspace.rows.length} registro(s) carregado(s) na fila operacional.` : 'Nenhum registro encontrado para os filtros atuais.';
    if (!workspace.rows.length) {
      tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;color:var(--muted);padding:24px">Nenhuma ocorrência disponível para os filtros selecionados.</td></tr>';
      renderAlarmDetail(null);
      return;
    }
    tbody.innerHTML = workspace.rows.map(row => {
      const [sevLabel, sevCls] = severityLabel(row.severity_code);
      return `
        <tr data-alarm-id="${row.id}" class="${workspace.selectedId === row.id ? 'is-selected' : ''}">
          <td>${escapeHtml(formatDateTime(row.event_at || row.detected_at || row.production_date))}</td>
          <td>${renderChip(typeLabel(row.record_type), 'alarm-chip--type')}</td>
          <td>${escapeHtml(row.measurement_point || row.tag || '—')}</td>
          <td>${escapeHtml(row.instrument || '—')}</td>
          <td>
            <div class="alarm-name-stack">
              <strong>${escapeHtml(row.title || '—')}</strong>
              <span>${escapeHtml(row.external_code || row.source_sheet || '')}</span>
            </div>
          </td>
          <td>${escapeHtml([row.family_code, row.category_code].filter(Boolean).join(' / ') || '—')}</td>
          <td>${renderChip(sevLabel, sevCls)}</td>
          <td>${renderChip(statusLabel(row.status_code), `alarm-chip--status-${String(row.status_code || '').toLowerCase()}`)}</td>
        </tr>
      `;
    }).join('');
    tbody.querySelectorAll('tr[data-alarm-id]').forEach(row => {
      row.addEventListener('click', () => selectAlarm(Number(row.dataset.alarmId)));
    });
  }

  function renderAlarmDetail(payload) {
    const empty = document.getElementById('alarmDetailEmpty');
    const body = document.getElementById('alarmDetailBody');
    if (!empty || !body) return;
    if (!payload || !payload.record) {
      workspace.detail = null;
      workspace.selectedId = null;
      empty.style.display = '';
      body.style.display = 'none';
      document.querySelectorAll('#alarmRows tr[data-alarm-id]').forEach(row => row.classList.remove('is-selected'));
      return;
    }
    workspace.detail = payload;
    workspace.selectedId = payload.record.id;
    empty.style.display = 'none';
    body.style.display = 'block';
    document.querySelectorAll('#alarmRows tr[data-alarm-id]').forEach(row => row.classList.toggle('is-selected', Number(row.dataset.alarmId) === payload.record.id));
    const record = payload.record;
    const [sevLabel, sevCls] = severityLabel(record.severity_code);
    document.getElementById('alarmDetailRecordType').textContent = typeLabel(record.record_type);
    document.getElementById('alarmDetailTitle').textContent = record.title || 'Ocorrência sem título';
    document.getElementById('alarmDetailMeta').textContent = `Origem: ${record.source_sheet || '—'} · código ${record.external_code || '—'} · atualizado em ${formatDateTime(record.updated_at || record.created_at)}`;
    document.getElementById('alarmDetailBadges').innerHTML = [
      renderChip(sevLabel, sevCls),
      renderChip(statusLabel(record.status_code), `alarm-chip--status-${String(record.status_code || '').toLowerCase()}`),
      renderChip(typeLabel(record.record_type), 'alarm-chip--type'),
    ].join('');
    document.getElementById('alarmDetailOverview').innerHTML = [
      ['Medidor', record.measurement_point || record.tag || '—'],
      ['Instrumento', record.instrument || '—'],
      ['Família', record.family_code || '—'],
      ['Categoria', record.category_code || '—'],
      ['Estado da medição', record.measurement_state || '—'],
      ['Ocorrências', record.occurrence_count || 0],
      ['Alarmes distintos', record.distinct_alarm_count || 0],
      ['Data do evento', formatDateTime(record.event_at || record.detected_at || record.production_date)],
    ].map(([label, value]) => `
      <div class="alarm-detail-overview-card">
        <div class="alarm-detail-overview-card__label">${escapeHtml(label)}</div>
        <div class="alarm-detail-overview-card__value">${escapeHtml(String(value))}</div>
      </div>
    `).join('');
    document.getElementById('alarmDetailNarrative').innerHTML = [
      ['Mensagem', record.message || 'Sem mensagem consolidada'],
      ['Ação imediata sugerida', record.immediate_action || 'Sem ação sugerida'],
      ['Impacto / estado', record.impact || 'Sem impacto consolidado'],
      ['Referência', record.reference || 'Sem referência adicional'],
    ].map(([label, value]) => `
      <div class="alarm-detail-note">
        <strong>${escapeHtml(label)}</strong>
        <span>${escapeHtml(value)}</span>
      </div>
    `).join('');
    document.getElementById('alarmActionList').innerHTML = (payload.actions || []).length
      ? payload.actions.map(action => `
          <div class="alarm-action-item">
            <strong>${escapeHtml(action.description || 'Ação sem descrição')}</strong>
            <span>${escapeHtml((action.action_type || '—') + ' · ' + (action.owner || 'Sem responsável'))}</span>
            <span>${escapeHtml('Status: ' + statusLabel(action.status_code) + ' · Prazo: ' + (formatDateTime(action.due_date) || '—'))}</span>
          </div>
        `).join('')
      : '<div class="alarm-action-item"><span>Nenhuma ação registrada para esta ocorrência.</span></div>';
    document.getElementById('alarmAuditList').innerHTML = (payload.audit || []).length
      ? payload.audit.map(entry => `
          <div class="alarm-audit-item">
            <strong>${escapeHtml(entry.event_type || 'evento')}</strong>
            <span>${escapeHtml(formatDateTime(entry.created_at))}</span>
            <span>${escapeHtml(entry.notes || [entry.field_name, entry.old_value, entry.new_value].filter(Boolean).join(' → ') || 'Sem observações')}</span>
          </div>
        `).join('')
      : '<div class="alarm-audit-item"><span>Sem trilha de auditoria adicional.</span></div>';
    const sourceRow = record.payload?.source_row || record.payload || {};
    document.getElementById('alarmPayloadDump').textContent = JSON.stringify(sourceRow, null, 2);
  }

  async function loadAlarmCatalog() {
    const data = await j(`${API}/alarmes/reference`).catch(() => ({ catalog: {} }));
    workspace.catalog = data.catalog || {};
    populateSelect('alarmRecordType', workspace.catalog.record_type || [], null, 'Todos');
    populateSelect('alarmStatus', workspace.catalog.status || [], null, 'Todos');
    populateSelect('alarmSeverity', workspace.catalog.severity || [], null, 'Todas');
    populateSelect('alarmFamily', workspace.catalog.family || [], null, 'Todas');
  }

  async function loadAlarmSummary() {
    const params = new URLSearchParams();
    if (workspace.currentSourceRef) params.set('source_ref', workspace.currentSourceRef);
    const data = await j(`${API}/alarmes/summary${params.toString() ? `?${params.toString()}` : ''}`).catch(() => ({ summary: {} }));
    renderAlarmSummary(data.summary || {});
  }

  function buildAlarmQuery() {
    const params = new URLSearchParams();
    const values = {
      q: qsValue('alarmSearch'),
      source_ref: workspace.currentSourceRef,
      record_type: qsValue('alarmRecordType'),
      status: qsValue('alarmStatus'),
      severity: qsValue('alarmSeverity'),
      family: qsValue('alarmFamily'),
      measurement_point: qsValue('alarmMeasurementPoint'),
      source_sheet: qsValue('alarmSourceSheet'),
      date_from: qsValue('alarmDateFrom'),
      date_to: qsValue('alarmDateTo'),
      limit: String(workspace.alarmLimit || 50),
      offset: String(workspace.alarmOffset || 0),
    };
    Object.entries(values).forEach(([key, value]) => {
      if (value || value === '0') params.set(key, value);
    });
    return params.toString();
  }

  async function loadAlarmRows(options = {}) {
    const keepSelection = !!options.keepSelection;
    const reset = !!options.reset;
    if (reset) {
      workspace.alarmOffset = 0;
      workspace.alarmHasMore = true;
    }
    const data = await j(`${API}/alarmes?${buildAlarmQuery()}`).catch(() => ({ items: [] }));
    const items = data.items || [];
    workspace.alarmHasMore = items.length >= workspace.alarmLimit;
    if (reset || workspace.alarmOffset === 0) {
      workspace.rows = items;
    } else {
      workspace.rows = workspace.rows.concat(items);
    }
    workspace.alarmOffset = workspace.rows.length;
    renderAlarmRows(workspace.rows);
    if (!workspace.rows.length) {
      return;
    }
    const preferredId = keepSelection ? workspace.selectedId : null;
    const candidate = preferredId && workspace.rows.find(row => row.id === preferredId)
      ? preferredId
      : workspace.rows[0].id;
    await selectAlarm(candidate);
  }

  function loadMoreAlarmRows() {
    if (!workspace.alarmHasMore) return;
    loadAlarmRows({ keepSelection: true, reset: true });
  }

  async function selectAlarm(id) {
    if (!id) {
      renderAlarmDetail(null);
      return;
    }
    const payload = await j(`${API}/alarmes/${id}`).catch(() => null);
    renderAlarmDetail(payload);
  }

  async function updateAlarmStatus(statusCode) {
    if (!workspace.selectedId) {
      setAlarmStatusLine('Selecione uma ocorrência antes de alterar o status.', 'error');
      return;
    }
    const endpoint = statusCode === 'closed' ? 'close' : 'acknowledge';
    try {
      await j(`${API}/alarmes/${workspace.selectedId}/${endpoint}`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
          status_code: statusCode,
          notes: qsValue('alarmStatusNotes'),
          acknowledged_by: qsValue('alarmStatusOwner'),
        }),
      });
      setAlarmStatusLine(`Ocorrência atualizada para ${statusLabel(statusCode)}.`, 'success');
      await Promise.all([loadAlarmSummary(), loadAlarmRows({ keepSelection: true, reset: true })]);
      document.getElementById('alarmStatusNotes').value = '';
    } catch (err) {
      setAlarmStatusLine(`Falha ao atualizar ocorrência: ${err.message || err}`, 'error');
    }
  }

  async function saveAlarmAction() {
    if (!workspace.selectedId) {
      setAlarmStatusLine('Selecione uma ocorrência antes de registrar uma ação.', 'error');
      return;
    }
    const description = qsValue('alarmActionDescription');
    if (!description) {
      setAlarmStatusLine('Descreva a ação antes de salvar.', 'error');
      return;
    }
    try {
      await j(`${API}/alarmes/${workspace.selectedId}/actions`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
          description,
          action_type: qsValue('alarmActionType') || 'corrective',
          owner: qsValue('alarmActionOwner'),
          due_date: qsValue('alarmActionDueDate'),
        }),
      });
      document.getElementById('alarmActionDescription').value = '';
      document.getElementById('alarmActionOwner').value = '';
      document.getElementById('alarmActionDueDate').value = '';
      setAlarmStatusLine('Ação registrada com sucesso.', 'success');
      await Promise.all([loadAlarmSummary(), selectAlarm(workspace.selectedId)]);
    } catch (err) {
      setAlarmStatusLine(`Falha ao registrar ação: ${err.message || err}`, 'error');
    }
  }

  function describeSelectedPdfs(files) {
    if (!files || files.length === 0) {
      return 'Nenhum arquivo selecionado.';
    }
    if (files.length === 1) {
      const sizeMb = (files[0].size / (1024 * 1024)).toFixed(2);
      return `${files[0].name} · ${sizeMb} MB`;
    }
    const totalMb = (Array.from(files).reduce((acc, f) => acc + f.size, 0) / (1024 * 1024)).toFixed(2);
    return `${files.length} PDFs selecionados · ${totalMb} MB total`;
  }

  async function uploadAlarmPdfs() {
    const input = document.getElementById('alarmPdfInput');
    const button = document.getElementById('btnUploadAlarmPdfs');
    const files = input?.files;
    if (!files || files.length === 0) {
      setAlarmStatusLine('Selecione ao menos um PDF antes de iniciar a análise.', 'error');
      return;
    }
    const form = new FormData();
    for (const file of files) {
      form.append('files', file);
    }
    const original = button?.textContent || 'Analisar PDFs';
    try {
      if (button) {
        button.disabled = true;
        button.textContent = 'Analisando...';
      }
      setAlarmStatusLine('Upload em andamento. Os PDFs estão sendo lidos e importados.', '');
      const response = await fetch(`${API}/alarmes/upload-pdfs`, { method: 'POST', body: form });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(payload.detail || payload.error || `Falha HTTP ${response.status}`);
      }
      workspace.preview = payload.import_result?.preview || null;
      const firstFile = payload.files?.[0];
      workspace.currentSourceRef = workspace.preview?.path || firstFile?.saved_path || '';
      renderAlarmPreview(workspace.preview);
      renderAlarmSummary(payload.summary || {});
      document.getElementById('alarmWorkbookMeta').textContent = `${describeSelectedPdfs(files)} · salvo em ${firstFile?.saved_path || '—'}`;
      setAlarmStatusLine(`PDFs processados. ${payload.import_result?.imported || 0} novo(s), ${payload.import_result?.updated || 0} atualizado(s).`, 'success');
      await loadAlarmCatalog();
      await loadAlarmRows({ reset: true });
    } catch (err) {
      setAlarmStatusLine(`Falha ao analisar PDFs: ${err.message || err}`, 'error');
    } finally {
      if (button) {
        button.disabled = false;
        button.textContent = original;
      }
    }
  }

  async function loadAlarmWorkspace() {
    if (!workspace.preview) {
      const latest = await j(`${API}/alarmes/latest-pdf-preview`).catch(() => null);
      if (latest?.preview) {
        workspace.preview = latest.preview;
        workspace.currentSourceRef = latest.preview?.path || latest.file?.saved_path || '';
        renderAlarmPreview(workspace.preview);
        const label = latest.files?.length > 1
          ? `${latest.files.length} PDFs carregados`
          : (latest.file?.name || 'Último PDF');
        document.getElementById('alarmWorkbookMeta').textContent = `${label} · salvo em ${latest.file?.saved_path || '—'}`;
        setAlarmStatusLine('Último upload de PDFs restaurado na tela.', 'success');
      }
    }
    await loadAlarmCatalog();
    await loadAlarmSummary();
    if (workspace.preview) {
      renderAlarmPreview(workspace.preview);
    }
    await loadAlarmRows({ keepSelection: true, reset: true });
  }

  function resetAlarmFilters() {
    ['alarmDateFrom', 'alarmDateTo', 'alarmRecordType', 'alarmStatus', 'alarmSeverity', 'alarmFamily', 'alarmMeasurementPoint', 'alarmSourceSheet', 'alarmSearch'].forEach(id => {
      const el = document.getElementById(id);
      if (el) el.value = '';
    });
    loadAlarmRows({ reset: true });
  }

  async function analyzeAlarmsWithAI() {
    const btn = document.getElementById('btnAnalyzeAlarmsWithAI');
    if (btn) { btn.disabled = true; btn.textContent = 'Analisando...'; }
    try {
      const body = {
        date_from: document.getElementById('alarmDateFrom')?.value || '',
        date_to: document.getElementById('alarmDateTo')?.value || '',
        bank: document.getElementById('alarmMeasurementPoint')?.value || '',
        status: document.getElementById('alarmStatus')?.value || '',
        severity: document.getElementById('alarmSeverity')?.value || '',
        priority: '',
        limit: 150,
      };
      const resp = await j(`${API}/ai/agent/alarms`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      openModal('aiAnalysisModal');
      document.getElementById('aiAnalysisTitle').textContent = 'Análise de Alarmes FCS320';
      document.getElementById('aiAnalysisBody').innerHTML = _renderAiMarkdown(resp.content, 0);
      document.getElementById('aiAnalysisMeta').textContent = `${resp.provider} · ${resp.model} · ${resp.input_tokens + resp.output_tokens} tokens`;
    } catch (err) {
      _toast(`Erro na análise: ${err?.detail || err?.message || err}`, 'error');
    } finally {
      if (btn) { btn.disabled = false; btn.textContent = 'Analisar com IA'; }
    }
  }

  function bindAlarmWorkspace() {
    document.getElementById('btnPickAlarmPdfs')?.addEventListener('click', () => document.getElementById('alarmPdfInput')?.click());
    document.getElementById('alarmPdfInput')?.addEventListener('change', (event) => {
      const files = event.target?.files || null;
      document.getElementById('alarmWorkbookMeta').textContent = describeSelectedPdfs(files);
    });
    document.getElementById('btnUploadAlarmPdfs')?.addEventListener('click', uploadAlarmPdfs);
    document.getElementById('btnLoadAlarmRows')?.addEventListener('click', () => loadAlarmRows({ reset: true }));
    document.getElementById('btnAnalyzeAlarmsWithAI')?.addEventListener('click', analyzeAlarmsWithAI);
    document.getElementById('btnResetAlarmFilters')?.addEventListener('click', resetAlarmFilters);
    document.getElementById('alarmSearch')?.addEventListener('keydown', (event) => {
      if (event.key === 'Enter') loadAlarmRows({ reset: true });
    });
    document.getElementById('btnAlarmMarkInProgress')?.addEventListener('click', () => updateAlarmStatus('in_progress'));
    document.getElementById('btnAlarmMarkMonitoring')?.addEventListener('click', () => updateAlarmStatus('monitoring'));
    document.getElementById('btnAlarmMarkClosed')?.addEventListener('click', () => updateAlarmStatus('closed'));
    document.getElementById('btnSaveAlarmAction')?.addEventListener('click', saveAlarmAction);

    const dropZone = document.getElementById('alarmDropZone');
    if (dropZone) {
      dropZone.addEventListener('dragover', (event) => {
        event.preventDefault();
        dropZone.classList.add('is-dragover');
      });
      dropZone.addEventListener('dragleave', () => dropZone.classList.remove('is-dragover'));
      dropZone.addEventListener('drop', (event) => {
        event.preventDefault();
        dropZone.classList.remove('is-dragover');
        const droppedFiles = event.dataTransfer?.files;
        if (!droppedFiles || droppedFiles.length === 0) return;
        const input = document.getElementById('alarmPdfInput');
        if (!input) return;
        const dt = new DataTransfer();
        for (const file of droppedFiles) {
          if (file.name.toLowerCase().endsWith('.pdf')) dt.items.add(file);
        }
        if (dt.files.length === 0) {
          setAlarmStatusLine('Arraste somente arquivos PDF.', 'error');
          return;
        }
        input.files = dt.files;
        document.getElementById('alarmWorkbookMeta').textContent = describeSelectedPdfs(dt.files);
      });
    }
  }

  bindAlarmWorkspace();
  window.loadAlarmWorkspace = loadAlarmWorkspace;
  window.loadAlerts = loadAlarmWorkspace;
})();