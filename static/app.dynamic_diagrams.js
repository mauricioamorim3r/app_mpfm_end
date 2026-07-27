'use strict';

(() => {
  const ASSET_BASE = '/static/dynamic-diagrams/';
  const STORAGE_PREFIX = 'mpfm.dynamicDiagram.v1.';
  let wired = false;
  let ctx = null;
  let editMode = false;
  let selectedGroup = '';
  let selectedTemplate = '';

  const CATALOG = [
    { id:'bubble-point-mpfm-subsea', group:'Bolha e escoamento', mode:'bubble', title:'Ponto de bolha e gás livre no MPFM subsea', file:'bubble-point-mpfm-subsea.png', note:'Sequência acima/perto/abaixo do ponto de bolha para avaliar P, Pb, GVF e WLR.' },
    { id:'gif-3-4-bubble-point-pvt', group:'Bolha e escoamento', mode:'bubble', title:'Above vs below bubble point + PVT/FCS320', file:'gif-3-4-bubble-point-pvt.png', note:'Quadro bilíngue para treinamento e diagnóstico da transição de condição de linha.' },
    { id:'gif-8-9-escoamento-boas-praticas', group:'Bolha e escoamento', mode:'bubble', title:'Regimes de escoamento e boas práticas', file:'gif-8-9-escoamento-boas-praticas.png', note:'Regimes, impacto na medição e práticas para confiabilidade operacional.' },

    { id:'pvt-fcs320-base-comparavel', group:'PVT e base comparável', mode:'pvt', title:'Conversão PVT/FCS320 para base comparável', file:'pvt-fcs320-base-comparavel.png', note:'Transforma condição de linha em condição de referência antes da comparação.' },
    { id:'gif-4-5-pvt-comparacao', group:'PVT e base comparável', mode:'pvt', title:'GIF 4/5: PVT e comparação por base equivalente', file:'gif-4-5-pvt-comparacao.png', note:'Fluxo didático para conversão PVT e comparação entre subsea, topside e separador.' },
    { id:'calculation-metrology-chain', group:'PVT e base comparável', mode:'pvt', title:'Calculation & metrology chain', file:'calculation-metrology-chain.png', note:'Cadeia conceitual da grandeza medida até resultados reportáveis em condição padrão.' },

    { id:'frame-1-desvio-detectado', group:'K-factor e reconciliação', mode:'kfactor', title:'Frame 1/5: desvio detectado', file:'frame-1-desvio-detectado.png', note:'Identifica desvio sistemático entre MPFM e referência.' },
    { id:'frame-3-calculo-k-factor', group:'K-factor e reconciliação', mode:'kfactor', title:'Frame 3/5: cálculo do K-factor', file:'frame-3-calculo-k-factor.png', note:'Calcula fator a partir de janela estável e rastreável.' },
    { id:'frame-4-aplicacao-k-factor', group:'K-factor e reconciliação', mode:'kfactor', title:'Frame 4/5: aplicação do K-factor', file:'frame-4-aplicacao-k-factor.png', note:'Aplica fator ao MPFM e verifica aproximação à referência.' },
    { id:'frame-5-reconciliacao-rastreabilidade', group:'K-factor e reconciliação', mode:'kfactor', title:'Frame 5/5: reconciliação e rastreabilidade', file:'frame-5-reconciliacao-rastreabilidade.png', note:'Fecha verificação, registro e monitoramento posterior.' },
    { id:'gif-6-7-kfactor-incerteza', group:'K-factor e reconciliação', mode:'kfactor', title:'GIF 6/7: K-factor, reconciliação e incerteza', file:'gif-6-7-kfactor-incerteza.png', note:'Ajuste, reconciliação e fontes de incerteza do MPFM subsea.' },
    { id:'calibracao-balanco-massa-mpfm', group:'K-factor e reconciliação', mode:'kfactor', title:'Calibração + balanço de massa MPFM subsea', file:'calibracao-balanco-massa-mpfm.png', note:'Processo em cinco etapas para fator K e fechamento de balanço.' },

    { id:'frame-1-subsea-topside-separador', group:'Comparação e sinóptico', mode:'compare', title:'Frame 1/5: Subsea x topside x separador', file:'frame-1-subsea-topside-separador.png', note:'Três fontes de medição entram na cadeia de comparação.' },
    { id:'frame-4-comparacao-por-fase', group:'Comparação e sinóptico', mode:'compare', title:'Frame 4/5: comparação por fase', file:'frame-4-comparacao-por-fase.png', note:'Óleo, gás e água avaliados separadamente.' },
    { id:'frame-3-mesma-base-comparavel', group:'Comparação e sinóptico', mode:'compare', title:'Frame 3/5: mesma base comparável', file:'frame-3-mesma-base-comparavel.png', note:'Somente dados em mesma base devem ser comparados.' },
    { id:'sistema-multifasico-com-paineis', group:'Comparação e sinóptico', mode:'system', title:'Sistema de medição multifásica com painéis', file:'sistema-multifasico-com-paineis.png', note:'Sinóptico com campos separados para subsea, riser, topside e sistema.' },
    { id:'sistema-multifasico-sinoptico', group:'Comparação e sinóptico', mode:'system', title:'Sistema de medição multifásica: sinóptico', file:'sistema-multifasico-sinoptico.png', note:'Versão limpa para operação e preenchimento de dados.' },
    { id:'sinoptico-dinamico-riser-p4', group:'Comparação e sinóptico', mode:'system', title:'Sinóptico dinâmico: calibração MPFM subsea/Riser P4', file:'sinoptico-dinamico-riser-p4.png', note:'Quadro com campos verdes e comparação MPFM x separador de teste.' },
    { id:'twin-metrologico-mpfm-separador', group:'Comparação e sinóptico', mode:'system', title:'Twin metrológico multifásico MPFM subsea x separador', file:'twin-metrologico-mpfm-separador.png', note:'Painel consolidado para calibração, reconciliação e monitoramento contínuo.' },

    { id:'gif-10-dado-medido', group:'Balanço de massa', mode:'mass', title:'GIF 10: do escoamento ao dado medido', file:'gif-10-dado-medido.png', note:'Do sensor ao dado pronto para alimentar o balanço.' },
    { id:'gif-10-11-dado-medido-oleo', group:'Balanço de massa', mode:'mass', title:'GIF 10/11: dado medido e balanço do óleo', file:'gif-10-11-dado-medido-oleo.png', note:'Entradas do MPFM e cálculo de volume/massa de óleo.' },
    { id:'gif-11-balanco-oleo', group:'Balanço de massa', mode:'mass', title:'GIF 11: balanço de massa do óleo', file:'gif-11-balanco-oleo.png', note:'NSV, volume estimado e massa de óleo.' },
    { id:'gif-12-balanco-gas', group:'Balanço de massa', mode:'mass', title:'GIF 12: balanço de massa do gás', file:'gif-12-balanco-gas.png', note:'Gás dissolvido, gás separado e massa total de gás.' },
    { id:'gif-13-balanco-agua', group:'Balanço de massa', mode:'mass', title:'GIF 13: balanço de massa da água', file:'gif-13-balanco-agua.png', note:'Água no óleo, água separada e massa total de água.' },
    { id:'gif-12-13-balanco-gas-agua', group:'Balanço de massa', mode:'mass', title:'GIF 12/13: balanço de gás e água', file:'gif-12-13-balanco-gas-agua.png', note:'Quadro combinado para gás e água.' },
    { id:'gif-14-balanco-consolidado-a', group:'Balanço de massa', mode:'mass', title:'GIF 14: balanço consolidado e reconciliação A', file:'gif-14-balanco-consolidado-a.png', note:'Consolidação de óleo, gás, água e hidrocarboneto.' },
    { id:'gif-14-balanco-consolidado-b', group:'Balanço de massa', mode:'mass', title:'GIF 14: balanço consolidado e reconciliação B', file:'gif-14-balanco-consolidado-b.png', note:'Variante de consolidação com rota de comparação e decisão.' },
    { id:'gif-14-balanco-consolidado-c', group:'Balanço de massa', mode:'mass', title:'GIF 14: balanço consolidado e reconciliação C', file:'gif-14-balanco-consolidado-c.png', note:'Variante final para relatório e rastreabilidade.' },
  ];

  const FIELD_SETS = {
    bubble: [
      f('p_linha', 'P linha', 'mpfmPressure', 80, 18, 'warn'),
      f('pb', 'Pb', 'bubblePoint', 86, 23, 'warn'),
      f('temp', 'T linha', 'mpfmTemp', 80, 28, 'gas'),
      f('gvf', 'GVF', 'gvf', 86, 35, 'gas'),
      f('wlr', 'WLR', 'wlr', 80, 40, 'water'),
      f('status', 'Condição', 'status', 78, 50, 'ok'),
    ],
    pvt: [
      f('lineBase', 'Base linha', 'lineBase', 22, 25, 'gas'),
      f('p_linha', 'P linha', 'mpfmPressure', 29, 35, 'warn'),
      f('temp', 'T linha', 'mpfmTemp', 29, 43, 'gas'),
      f('q_oil', 'Q óleo conv.', 'oilMpfm', 54, 64, 'oil'),
      f('q_gas', 'Q gás conv.', 'gasMpfm', 54, 72, 'gas'),
      f('q_water', 'Q água conv.', 'waterMpfm', 54, 80, 'water'),
      f('status', 'Base', 'status', 80, 70, 'ok'),
    ],
    kfactor: [
      f('refMean', 'Média referência', 'hcRef', 79, 20, 'gas'),
      f('mpfmMean', 'Média MPFM', 'hcMpfm', 79, 27, 'oil'),
      f('devHC', 'Desvio HC', 'devHc', 79, 35, 'warn'),
      f('kProposto', 'K proposto', 'kProposed', 79, 44, 'ok'),
      f('kAplicado', 'K aplicado', 'kApplied', 79, 53, 'ok'),
      f('status', 'Status', 'status', 79, 63, 'ok'),
    ],
    compare: [
      f('oilMpfm', 'Óleo MPFM', 'oilMpfm', 18, 66, 'oil'),
      f('oilRef', 'Óleo ref.', 'oilRef', 33, 66, 'oil'),
      f('gasMpfm', 'Gás MPFM', 'gasMpfm', 48, 66, 'gas'),
      f('gasRef', 'Gás ref.', 'gasRef', 63, 66, 'gas'),
      f('waterMpfm', 'Água MPFM', 'waterMpfm', 78, 66, 'water'),
      f('waterRef', 'Água ref.', 'waterRef', 90, 66, 'water'),
      f('devHC', 'Desvio HC', 'devHc', 73, 82, 'warn'),
      f('status', 'Status', 'status', 87, 82, 'ok'),
    ],
    system: [
      f('run', 'Run', 'run', 9, 88, 'gas'),
      f('bankTag', 'Banco / TAG', 'bankTag', 20, 88, 'gas'),
      f('pMpfm', 'P MPFM', 'mpfmPressure', 32, 88, 'warn'),
      f('tMpfm', 'T MPFM', 'mpfmTemp', 44, 88, 'warn'),
      f('pSep', 'P Separador', 'sepPressure', 56, 88, 'gas'),
      f('tSep', 'T Separador', 'sepTemp', 68, 88, 'gas'),
      f('hcMpfm', 'HC MPFM', 'hcMpfm', 80, 88, 'oil'),
      f('hcRef', 'HC ref.', 'hcRef', 91, 88, 'ok'),
    ],
    mass: [
      f('nsv', 'NSV / óleo', 'oilMpfm', 18, 73, 'oil'),
      f('gasTotal', 'Gás total', 'gasMpfm', 35, 73, 'gas'),
      f('waterTotal', 'Água total', 'waterMpfm', 52, 73, 'water'),
      f('mOil', 'M óleo', 'oilMass', 70, 73, 'oil'),
      f('mGas', 'M gás', 'gasMass', 70, 82, 'gas'),
      f('mWater', 'M água', 'waterMass', 52, 82, 'water'),
      f('hcTotal', 'HC consolidado', 'hcMpfm', 84, 82, 'ok'),
      f('status', 'Reconciliação', 'status', 84, 91, 'ok'),
    ],
  };

  function f(id, label, source, x, y, kind) {
    return { id, label, source, x, y, kind };
  }

  const $ = (id) => document.getElementById(id);
  const esc = (value) => String(value ?? '').replace(/[&<>"']/g, ch => ({
    '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'
  }[ch]));
  const groups = () => Array.from(new Set(CATALOG.map(item => item.group)));
  const currentTemplate = () => CATALOG.find(item => item.id === selectedTemplate) || CATALOG[0];
  const storageKey = (templateId) => `${STORAGE_PREFIX}${templateId}`;
  const readSaved = (templateId) => {
    try { return JSON.parse(localStorage.getItem(storageKey(templateId)) || '{}') || {}; }
    catch { return {}; }
  };
  const writeSaved = (templateId, value) => localStorage.setItem(storageKey(templateId), JSON.stringify(value || {}));

  function fmt(value, digits = 2, unit = '') {
    const n = Number(value);
    if (!Number.isFinite(n)) return '—';
    return `${n.toLocaleString('pt-BR', { minimumFractionDigits: digits, maximumFractionDigits: digits })}${unit ? ` ${unit}` : ''}`;
  }

  function dateBr(value) {
    const m = String(value || '').match(/^(\d{4})-(\d{2})-(\d{2})/);
    return m ? `${m[3]}/${m[2]}/${m[1]}` : (value || '—');
  }

  function hourRow(rows) {
    const hour = Number(ctx?.selected_hour ?? 0);
    return (rows || []).find(row => Number(row.hora) === hour) || (rows || [])[0] || {};
  }

  function metric(key) {
    const item = ctx?.daily_metrics?.[key];
    return item?.value;
  }

  function sourceValue(source) {
    const run = ctx?.run || {};
    const resumo = ctx?.resumo || {};
    const pvt = ctx?.pvt || ctx?.pvt_snapshot || {};
    const campaign = ctx?.campaign || ctx?.synoptic?.campaign || {};
    const mpfm = hourRow(ctx?.mpfm_horas);
    const sep = hourRow(ctx?.sep_horas);
    const calc = hourRow(ctx?.calc_horas);
    const hcMpfm = resumo.massa_hc_mpfm_t ?? metric('MPFM corr HC (t)');
    const hcRef = resumo.massa_hc_ref_t ?? metric('Ref HC (t)');
    const oilMpfm = mpfm.oleo_corr_t ?? metric('MPFM corr Óleo (t)') ?? metric('MPFM corr Oleo (t)');
    const gasMpfm = mpfm.gas_corr_t ?? metric('MPFM corr Gás (t)') ?? metric('MPFM corr Gas (t)');
    const waterMpfm = mpfm.agua_corr_t ?? metric('MPFM corr Água (t)') ?? metric('MPFM corr Agua (t)');
    const oilRef = calc.massa_oleo_ref_t ?? metric('Ref Óleo (t)') ?? metric('Ref Oleo (t)');
    const gasRef = calc.massa_gas_ref_t ?? metric('Ref Gás (t)') ?? metric('Ref Gas (t)');
    const waterRef = calc.massa_agua_ref_t ?? metric('Ref Água (t)') ?? metric('Ref Agua (t)');

    const values = {
      run: run.id ? `#${run.id}` : '—',
      bankTag: `${run.bank || '—'} / ${run.tag || '—'}`,
      lineBase: campaign.reference || 'condição de referência',
      mpfmPressure: fmt(mpfm.pressao_barg ?? run.p_mpfm_barg, 2, 'barg'),
      mpfmTemp: fmt(mpfm.temperatura_c ?? run.t_mpfm_c, 2, '°C'),
      sepPressure: fmt(sep.pressao_barg ?? run.p_sep_barg, 2, 'barg'),
      sepTemp: fmt(sep.temperatura_c ?? run.t_sep_c, 2, '°C'),
      bubblePoint: fmt(pvt.pb_bara ?? pvt.bubble_point_bara ?? pvt.ponto_bolha_bara, 2, 'bara'),
      gvf: fmt(mpfm.gvf_pct ?? run.gvf_pct, 2, '%'),
      wlr: fmt(mpfm.wlr_pct ?? sep.wlr_pct ?? run.wlr_pct, 2, '%'),
      oilMpfm: fmt(oilMpfm, 3, 't/h'),
      gasMpfm: fmt(gasMpfm, 3, 't/h'),
      waterMpfm: fmt(waterMpfm, 3, 't/h'),
      oilRef: fmt(oilRef, 3, 't/h'),
      gasRef: fmt(gasRef, 3, 't/h'),
      waterRef: fmt(waterRef, 3, 't/h'),
      oilMass: fmt(resumo.massa_oleo_mpfm_t ?? oilMpfm, 2, 't'),
      gasMass: fmt(resumo.massa_gas_mpfm_t ?? gasMpfm, 2, 't'),
      waterMass: fmt(resumo.massa_agua_mpfm_t ?? waterMpfm, 2, 't'),
      hcMpfm: fmt(hcMpfm, 2, 't'),
      hcRef: fmt(hcRef, 2, 't'),
      devHc: fmt(resumo.desvio_hc_pct, 3, '%'),
      kProposed: fmt(campaign.proposed_k_factor_hc ?? run.proposed_k_factor_hc, 6),
      kApplied: fmt(campaign.applied_k_factor ?? run.applied_k_factor, 6),
      status: resumo.status_final || resumo.status_linha || run.status || '—',
    };
    return values[source] || '—';
  }

  function buildTwinUrl() {
    const params = new URLSearchParams();
    const runId = $('twinRunSelect')?.value || '';
    const bank = $('twinBank')?.value?.trim() || '';
    const tag = $('twinTag')?.value?.trim() || '';
    const day = $('twinDay')?.value || '';
    if (runId) params.set('run_id', runId);
    if (bank) params.set('bank', bank);
    if (tag) params.set('tag', tag);
    if (day) params.set('day_ref', day);
    const suffix = params.toString();
    return `${API}/twin/synoptic${suffix ? `?${suffix}` : ''}`;
  }

  async function loadDynamicDiagrams(silent = false) {
    wire();
    const root = $('dynamicDiagramRoot');
    if (!root) return;
    if (!silent) setStatus('Carregando dados do run para os campos dinâmicos...');
    try {
      const data = typeof j === 'function'
        ? await j(buildTwinUrl())
        : await fetch(buildTwinUrl()).then(r => r.json());
      if (data?.ok) ctx = data;
      if (!selectedGroup) selectedGroup = groups()[0];
      if (!selectedTemplate) selectedTemplate = CATALOG.find(item => item.group === selectedGroup)?.id || CATALOG[0].id;
      populateSelects();
      render();
      const run = ctx?.run || {};
      setStatus(`Run ${run.id ? `#${run.id}` : 'atual'} · ${run.bank || '—'} / ${run.tag || '—'} · ${dateBr(run.day_ref)}.`);
    } catch (err) {
      if (!selectedGroup) selectedGroup = groups()[0];
      if (!selectedTemplate) selectedTemplate = CATALOG.find(item => item.group === selectedGroup)?.id || CATALOG[0].id;
      populateSelects();
      render();
      setStatus(`Sem dados do Twin no momento; campos continuam editáveis. ${err.message || err}`);
    }
  }

  function wire() {
    if (wired) return;
    wired = true;
    $('diagramGroupSelect')?.addEventListener('change', (ev) => {
      selectedGroup = ev.target.value;
      selectedTemplate = CATALOG.find(item => item.group === selectedGroup)?.id || CATALOG[0].id;
      populateSelects();
      render();
    });
    $('diagramTemplateSelect')?.addEventListener('change', (ev) => {
      selectedTemplate = ev.target.value;
      render();
    });
    $('diagramShowFields')?.addEventListener('change', render);
    $('diagramApplyRunData')?.addEventListener('click', () => {
      const tpl = currentTemplate();
      const saved = readSaved(tpl.id);
      saved.values = {};
      writeSaved(tpl.id, saved);
      render();
      setStatus('Campos atualizados com os dados do run atual.');
    });
    $('diagramEditMode')?.addEventListener('click', () => {
      editMode = !editMode;
      const btn = $('diagramEditMode');
      if (btn) {
        btn.setAttribute('aria-pressed', String(editMode));
        btn.textContent = editMode ? 'Concluir edição' : 'Editar campos';
      }
      render();
    });
    $('diagramResetLayout')?.addEventListener('click', () => {
      const tpl = currentTemplate();
      localStorage.removeItem(storageKey(tpl.id));
      render();
      setStatus('Layout e valores manuais deste template foram resetados.');
    });
  }

  function populateSelects() {
    const groupSelect = $('diagramGroupSelect');
    const templateSelect = $('diagramTemplateSelect');
    if (groupSelect) {
      groupSelect.innerHTML = groups().map(group => `<option value="${esc(group)}"${group === selectedGroup ? ' selected' : ''}>${esc(group)}</option>`).join('');
    }
    if (templateSelect) {
      templateSelect.innerHTML = CATALOG
        .filter(item => item.group === selectedGroup)
        .map(item => `<option value="${esc(item.id)}"${item.id === selectedTemplate ? ' selected' : ''}>${esc(item.title)}</option>`)
        .join('');
    }
  }

  function render() {
    const root = $('dynamicDiagramRoot');
    if (!root) return;
    const tpl = currentTemplate();
    const saved = readSaved(tpl.id);
    const showFields = $('diagramShowFields')?.checked !== false;
    const fields = FIELD_SETS[tpl.mode] || FIELD_SETS.system;
    const run = ctx?.run || {};
    root.innerHTML = `
      <div class="dynamic-diagram-frame">
        <div class="dynamic-diagram-canvas${editMode ? ' dynamic-diagram-editing' : ''}" data-template="${esc(tpl.id)}">
          <img src="${ASSET_BASE}${esc(tpl.file)}" alt="${esc(tpl.title)}">
          ${fields.map(field => renderField(field, saved, showFields)).join('')}
        </div>
        <aside class="dynamic-diagram-side">
          <h3>${esc(tpl.title)}</h3>
          <p>${esc(tpl.note)}</p>
          <dl>
            <div><dt>Grupo</dt><dd>${esc(tpl.group)}</dd></div>
            <div><dt>Arquivo-base</dt><dd>${esc(tpl.file)}</dd></div>
            <div><dt>Run vinculado</dt><dd>${run.id ? `#${esc(run.id)}` : 'Último disponível'} · ${esc(run.bank || '—')} / ${esc(run.tag || '—')}</dd></div>
            <div><dt>Como editar</dt><dd>Ative “Editar campos”, arraste pelo ponto do canto e altere valores nos campos.</dd></div>
          </dl>
        </aside>
      </div>
    `;
    bindFieldEvents(tpl, saved);
  }

  function renderField(field, saved, showFields) {
    const pos = saved.positions?.[field.id] || { x: field.x, y: field.y };
    const value = saved.values?.[field.id] ?? sourceValue(field.source);
    return `
      <div class="dynamic-diagram-field kind-${esc(field.kind || 'info')}" data-field="${esc(field.id)}" style="--x:${Number(pos.x)}%;--y:${Number(pos.y)}%;"${showFields ? '' : ' hidden'}>
        <button class="dynamic-diagram-field__handle" type="button" aria-label="Mover campo">↕</button>
        <label>
          <span>${esc(field.label)}</span>
          <input value="${esc(value)}" ${editMode ? '' : 'readonly'} data-field-input="${esc(field.id)}">
        </label>
      </div>
    `;
  }

  function bindFieldEvents(tpl, savedInitial) {
    const canvas = document.querySelector('.dynamic-diagram-canvas');
    if (!canvas) return;
    canvas.querySelectorAll('[data-field-input]').forEach(input => {
      input.addEventListener('change', () => {
        const saved = readSaved(tpl.id);
        saved.values = saved.values || {};
        saved.values[input.dataset.fieldInput] = input.value;
        writeSaved(tpl.id, saved);
      });
    });
    canvas.querySelectorAll('.dynamic-diagram-field__handle').forEach(handle => {
      handle.addEventListener('pointerdown', (ev) => {
        if (!editMode) return;
        ev.preventDefault();
        const fieldNode = ev.target.closest('[data-field]');
        const fieldId = fieldNode?.dataset.field;
        if (!fieldId) return;
        handle.setPointerCapture?.(ev.pointerId);
        const move = (moveEv) => {
          const rect = canvas.getBoundingClientRect();
          const x = Math.max(2, Math.min(98, ((moveEv.clientX - rect.left) / rect.width) * 100));
          const y = Math.max(2, Math.min(98, ((moveEv.clientY - rect.top) / rect.height) * 100));
          fieldNode.style.setProperty('--x', `${x}%`);
          fieldNode.style.setProperty('--y', `${y}%`);
          const saved = readSaved(tpl.id);
          saved.positions = saved.positions || savedInitial.positions || {};
          saved.positions[fieldId] = { x: Number(x.toFixed(2)), y: Number(y.toFixed(2)) };
          writeSaved(tpl.id, saved);
        };
        const up = () => {
          window.removeEventListener('pointermove', move);
          window.removeEventListener('pointerup', up);
        };
        window.addEventListener('pointermove', move);
        window.addEventListener('pointerup', up, { once:true });
      });
    });
  }

  function setStatus(message) {
    const el = $('diagramDataStatus');
    if (el) el.textContent = message || '';
  }

  window.loadDynamicDiagrams = loadDynamicDiagrams;
})();
