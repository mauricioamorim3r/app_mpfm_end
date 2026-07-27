'use strict';

(() => {
  let twinCtx = null;
  let twinSelected = 'topside';
  let twinHour = 0;
  let twinWired = false;

  const ASSET = '/twin/assets/a02/';
  const EQUIPMENT = [
    { id:'well', label:'POÇO / PRODUÇÃO', asset:'subsea_well_phase_lines.png', slot:'slot-1' },
    { id:'gaslift', label:'GAS LIFT', asset:'gas_lift_valve_phase_lines.png', slot:'slot-2' },
    { id:'subsea', label:'MPFM SUBSEA', asset:'mpfm_subsea_gold_front.png', slot:'slot-3' },
    { id:'riser', label:'FLOWLINE / RISER', asset:'riser_flowline_elbow.png', slot:'slot-4' },
    { id:'topside', label:'MPFM TOPSIDE', asset:'mpfm_topside_silver_front.png', slot:'slot-5' },
    { id:'separator', label:'SEPARADOR', asset:'test_separator_horizontal.png', slot:'slot-6' },
    { id:'fcs', label:'FCS320 / ALOCAÇÃO', asset:'fcs320_monitor_labeled.png', slot:'slot-7' },
  ];

  const $ = (id) => document.getElementById(id);
  const esc = (value) => String(value ?? '').replace(/[&<>"']/g, ch => ({
    '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'
  }[ch]));
  const num = (value, digits = 2) => {
    const n = Number(value);
    if (!Number.isFinite(n)) return '—';
    return n.toLocaleString('pt-BR', { minimumFractionDigits: digits, maximumFractionDigits: digits });
  };
  const dateBr = (value) => {
    if (!value) return '—';
    const m = String(value).match(/^(\d{4})-(\d{2})-(\d{2})/);
    return m ? `${m[3]}/${m[2]}/${m[1]}` : String(value);
  };
  const metricValue = (metrics, key, digits = 2) => {
    const item = metrics?.[key];
    if (!item || item.value == null) return '—';
    return `${num(item.value, digits)} ${item.unit || ''}`.trim();
  };
  const findHour = (rows, hour) => (rows || []).find(row => Number(row.hora) === Number(hour)) || null;
  const statusKind = (value) => {
    const s = String(value || '').toUpperCase();
    if (s.includes('OK') || s.includes('NORMAL') || s.includes('APROV')) return 'ok';
    if (s.includes('VERIFICAR') || s.includes('ATEN') || s.includes('ALERTA') || s.includes('INSUFFICIENT')) return 'warn';
    if (s.includes('FALHA') || s.includes('REPROV') || s.includes('BLOQUE')) return 'err';
    return 'info';
  };
  const devKind = (value, limit) => {
    const n = Math.abs(Number(value));
    if (!Number.isFinite(n)) return 'info';
    return n <= limit ? 'ok' : 'warn';
  };

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

  async function loadTwinMPFM(silent = false) {
    wireTwin();
    const root = $('twinRoot');
    const status = $('twinStatus');
    if (!root) return;
    if (!silent) {
      status.textContent = 'Carregando twin com dados reais...';
      root.innerHTML = '<div class="twin-empty">Carregando sinóptico operacional...</div>';
    }
    try {
      const data = typeof j === 'function'
        ? await j(buildTwinUrl())
        : await fetch(buildTwinUrl()).then(r => r.json());
      if (!data?.ok) throw new Error(data?.detail || 'Payload inválido');
      twinCtx = data;
      populateRuns(data);
      const validHours = getValidHours(data);
      if (!validHours.includes(Number(twinHour))) twinHour = validHours[0] ?? 0;
      renderTwin();
      const run = data.run || {};
      const contract = data.synoptic?.source?.dataContract || 'contexto real';
      status.textContent = `Twin carregado com Run #${run.id || '—'} · ${run.bank || '—'} / ${run.tag || '—'} · ${dateBr(run.day_ref)} · ${contract}.`;
    } catch (err) {
      status.textContent = `Falha ao carregar twin: ${err.message || err}`;
      root.innerHTML = '<div class="twin-empty">Não foi possível carregar os dados reais do twin.</div>';
    }
  }

  function wireTwin() {
    if (twinWired) return;
    twinWired = true;
    $('twinLoadBtn')?.addEventListener('click', () => loadTwinMPFM());
    $('twinRunSelect')?.addEventListener('change', () => loadTwinMPFM());
    $('twinClearFilters')?.addEventListener('click', () => {
      ['twinBank','twinTag','twinDay'].forEach(id => { const el = $(id); if (el) el.value = ''; });
      const sel = $('twinRunSelect');
      if (sel) sel.value = '';
      loadTwinMPFM();
    });
    $('twinRoot')?.addEventListener('click', (ev) => {
      const node = ev.target.closest?.('[data-twin-node]');
      const hour = ev.target.closest?.('[data-twin-hour]');
      if (node) {
        twinSelected = node.dataset.twinNode;
        renderTwin();
      }
      if (hour) {
        twinHour = Number(hour.dataset.twinHour);
        renderTwin();
      }
    });
  }

  function populateRuns(data) {
    const sel = $('twinRunSelect');
    if (!sel) return;
    const run = data.run || {};
    const current = String(run.id || '');
    const options = ['<option value="">Último run disponível</option>'].concat((data.runs || []).map(item => {
      const selected = String(item.id) === current ? ' selected' : '';
      const label = `#${item.id} · ${item.day_ref || '—'} · ${item.bank || '—'} / ${item.tag || '—'} · ${item.status || item.proposal_status || 'run'}`;
      return `<option value="${esc(item.id)}"${selected}>${esc(label)}</option>`;
    }));
    sel.innerHTML = options.join('');
    if (current) sel.value = current;
  }

  function buildNodes(ctx) {
    const syn = ctx.synoptic || {};
    const synStatus = syn.status || {};
    const run = ctx.run || {};
    const resumo = ctx.resumo || {};
    const pvt = ctx.pvt || ctx.pvt_snapshot || {};
    const metrics = ctx.daily_metrics || {};
    const campaign = ctx.campaign || {};
    const calcHour = findHour(ctx.calc_horas, twinHour) || {};
    const mpfmHour = findHour(ctx.mpfm_horas, twinHour) || {};
    const sepHour = findHour(ctx.sep_horas, twinHour) || {};
    const statusFinal = resumo.status_final || resumo.status_linha || run.proposal_status || '—';
    const hcLimit = Number(pvt.limite_hc_pct ?? run.pvt_snapshot?.limite_hc_pct ?? 10);
    const totalLimit = Number(pvt.limite_total_pct ?? run.pvt_snapshot?.limite_total_pct ?? 7);

    return {
      well: {
        status:synStatus.well?.status || 'ATIVO',
        kind:synStatus.well?.kind || 'ok',
        summary:synStatus.well?.message || `${run.bank || '—'} / ${run.tag || '—'} em ${dateBr(run.day_ref)}.`,
        metrics:[
          ['Banco', run.bank], ['TAG/Riser', run.tag], ['Campanha', campaign.id ? `#${campaign.id}` : '—'], ['Fase', run.campaign_phase || '—']
        ],
        evidence:['Run de reconciliação selecionado', `Data de produção: ${dateBr(run.day_ref)}`]
      },
      gaslift: {
        status:synStatus.gasLift?.status || 'NÃO INFORMADO',
        kind:synStatus.gasLift?.kind || 'info',
        summary:synStatus.gasLift?.message || 'O run atual não trouxe massa de gas lift dedicada; manter como premissa operacional a confirmar quando aplicável.',
        metrics:[['Massa GL', '—'], ['Tratamento', 'Não aplicado'], ['Impacto HC', 'Sem desconto no payload atual']],
        evidence:['Campo de gas lift não identificado no contexto real carregado']
      },
      subsea: {
        status:synStatus.ss?.status || 'SEM FONTE',
        kind:synStatus.ss?.kind || 'warn',
        summary:synStatus.ss?.message || 'O material Twin prevê MPFM subsea, mas este run real está reconciliado como MPFM topside × separador.',
        metrics:[['Óleo subsea', '—'], ['Gás subsea', '—'], ['Água subsea', '—'], ['Par', run.analytical_snapshot?.flow_mode || 'topside_sep']],
        evidence:['Sem série subsea dedicada no payload deste run', 'Manter nó para continuidade visual da cadeia']
      },
      riser: {
        status:synStatus.flowline?.status || (run.tag ? 'RASTREADO' : '—'),
        kind:synStatus.flowline?.kind || (run.tag ? 'ok' : 'info'),
        summary:synStatus.flowline?.message || 'Trecho lógico usado para conectar a medição MPFM à referência de separador e à decisão de alocação.',
        metrics:[['Riser/TAG', run.tag], ['Banco', run.bank], ['Janela', `${resumo.horas_validas || '—'} / ${resumo.horas_janela || 24} h`]],
        evidence:[`Cobertura: ${num(resumo.cobertura_pct, 1)}%`, resumo.qa_flags_consolidados || 'Sem flags consolidadas']
      },
      topside: {
        status:synStatus.ts?.status || (mpfmHour.hc_corr_t != null ? 'NORMAL' : 'SEM DADOS'),
        kind:synStatus.ts?.kind || (mpfmHour.hc_corr_t != null ? 'ok' : 'warn'),
        summary:synStatus.ts?.message || 'Medição MPFM horária e acumulada carregada da base curada.',
        metrics:[
          ['Óleo hora', `${num(mpfmHour.oleo_corr_t, 3)} t/h`],
          ['Gás hora', `${num(mpfmHour.gas_corr_t, 3)} t/h`],
          ['Água hora', `${num(mpfmHour.agua_corr_t, 3)} t/h`],
          ['P/T', `${num(mpfmHour.pressao_barg, 1)} barg / ${num(mpfmHour.temperatura_c, 1)} °C`],
          ['HC dia', metricValue(metrics, 'MPFM corr HC (t)', 2)],
          ['Total dia', metricValue(metrics, 'MPFM corr Total (t)', 2)]
        ],
        evidence:[metrics['MPFM corr HC (t)']?.source_file ? `Fonte MPFM: ${metrics['MPFM corr HC (t)'].source_file}` : 'Fonte MPFM não informada']
      },
      separator: {
        status:synStatus.sep?.status || (calcHour.hora_valida ? 'REFERÊNCIA OK' : 'VERIFICAR'),
        kind:synStatus.sep?.kind || (calcHour.hora_valida ? 'ok' : 'warn'),
        summary:synStatus.sep?.message || 'Referência do separador convertida por NSV, FE/SF, gás dissolvido e densidades standard.',
        metrics:[
          ['GSV óleo hora', `${num(sepHour.gsv_sep_sm3, 3)} Sm³/h`],
          ['Gás livre hora', `${num(sepHour.gas_vol_sm3, 1)} Sm³/h`],
          ['BSW', `${num(sepHour.bsw_user_pct, 2)}%`],
          ['Massa HC ref hora', `${num(calcHour.massa_hc_ref_t, 3)} t`],
          ['Massa HC ref dia', `${num(resumo.massa_hc_ref_t, 2)} t`],
          ['Total ref dia', `${num(resumo.massa_total_ref_t, 2)} t`]
        ],
        evidence:(ctx.sep_sources || []).map(src => `${src.fluid_kind}: ${src.source_file}`).slice(0, 4)
      },
      fcs: {
        status:synStatus.fcs?.status || statusFinal,
        kind:synStatus.fcs?.kind || statusKind(statusFinal),
        summary:synStatus.fcs?.message || 'Decisão final baseada nos desvios HC/total, cobertura, QA flags e limites vigentes do PVT.',
        metrics:[
          ['Desvio HC', `${num(resumo.desvio_hc_pct, 3)}%`],
          ['Limite HC', `±${num(hcLimit, 1)}%`],
          ['Desvio Total', `${num(resumo.desvio_total_pct, 3)}%`],
          ['Limite Total', `±${num(totalLimit, 1)}%`],
          ['K proposto HC', num(campaign.proposed_k_factor_hc, 6)],
          ['K aplicado', campaign.applied_k_factor ? num(campaign.applied_k_factor, 6) : '—']
        ],
        evidence:[`Status HC: ${resumo.status_hc || '—'}`, `Status total: ${resumo.status_total || '—'}`, `Status água: ${resumo.status_agua || '—'}`]
      },
      meta: { hcLimit, totalLimit, calcHour, mpfmHour, sepHour }
    };
  }

  function renderTwin() {
    if (!twinCtx) return;
    const root = $('twinRoot');
    if (!root) return;
    const nodes = buildNodes(twinCtx);
    const run = twinCtx.run || {};
    const resumo = twinCtx.resumo || {};
    const pvt = twinCtx.pvt || twinCtx.pvt_snapshot || {};
    const syn = twinCtx.synoptic || {};
    const campaign = syn.campaign || {};
    const monitoring = syn.monitoring || {};
    const selected = nodes[twinSelected] || nodes.topside;
    const validHours = new Set(getValidHours(twinCtx));
    const statusKindFinal = statusKind(resumo.status_final || resumo.status_linha);
    const execSteps = syn.executionSteps || twinCtx.steps || [];
    const activeEquipment = getActiveEquipment(twinCtx, nodes);
    const flowMode = run.analytical_snapshot?.flow_mode || campaign.mode || 'topside_sep';

    root.innerHTML = `
      <div class="twin-kpis">
        ${kpi('Run', `#${run.id || '—'}`, `${run.bank || '—'} / ${run.tag || '—'}`)}
        ${kpi('Data', dateBr(run.day_ref), `${campaign.phase || run.campaign_phase || 'fase'} · ${campaign.id || `campanha ${run.campaign_id || '—'}`}`)}
        ${kpi('Cobertura', `${num(resumo.cobertura_pct, 1)}%`, `${resumo.horas_validas || '—'} de ${resumo.horas_janela || 24} horas`)}
        ${kpi('Status', resumo.status_final || resumo.status_linha || '—', 'reconciliação real', statusKindFinal)}
      </div>

      ${renderTwinGuide(syn, run, resumo)}

      <div class="twin-layout">
        <section class="card twin-stage-card">
          <div class="twin-stage-head">
            <div>
              <h3>Gêmeo operacional adaptativo</h3>
              <p>${esc(campaign.comparison || 'TS x SEP')} · referência ${esc(campaign.reference || 'Separador de Testes')} · arquitetura ${esc(flowMode)} · hora ativa ${String(twinHour).padStart(2, '0')}:00.</p>
            </div>
            <div class="twin-status-pill ${statusKindFinal}">${esc(resumo.status_final || resumo.status_linha || '—')}</div>
          </div>
          <div class="twin-contract">
            <span>Contrato: ${esc(syn.source?.dataContract || 'contexto legado')}</span>
            <span>Modo: ${esc(campaign.mode || 'daily')}</span>
            <span>Alertas: ${esc(String(monitoring.alarmCount ?? (twinCtx.alarms || []).length ?? 0))}</span>
          </div>
          <div class="twin-stage" data-flow-mode="${esc(flowMode)}">
            ${renderTwinBackdrop(twinCtx, nodes)}
            ${renderPhaseMeters(nodes)}
            <div class="twin-flow-line oil"></div>
            <div class="twin-flow-line gas"></div>
            <div class="twin-flow-line water"></div>
            <div class="twin-flow-line total"></div>
            <div class="twin-flow-spine"></div>
            ${activeEquipment.map((eq, index) => renderEquipment(eq, nodes[eq.id], index, activeEquipment.length)).join('')}
          </div>
          <div class="twin-hour-strip">
            ${Array.from({ length:24 }, (_, index) => {
              const h = index;
              const active = h === Number(twinHour) ? ' active' : '';
              const valid = validHours.has(h) ? ' valid' : ' missing';
              return `<button type="button" class="twin-hour${active}${valid}" data-twin-hour="${h}">${String(h).padStart(2, '0')}</button>`;
            }).join('')}
          </div>
        </section>

        <aside class="card twin-detail">
          <div class="twin-detail-head">
            <span class="twin-node-dot ${selected.kind}"></span>
            <div>
              <h3>${esc((EQUIPMENT.find(e => e.id === twinSelected) || {}).label || 'Detalhe')}</h3>
              <p>${esc(selected.summary)}</p>
            </div>
          </div>
          <div class="twin-detail-status ${selected.kind}">${esc(selected.status)}</div>
          <div class="twin-detail-grid">
            ${(selected.metrics || []).map(([label, value]) => `
              <div class="twin-detail-metric"><span>${esc(label)}</span><strong>${esc(value ?? '—')}</strong></div>
            `).join('')}
          </div>
          <div class="twin-evidence">
            <div class="twin-section-label">Evidências</div>
            ${(selected.evidence && selected.evidence.length ? selected.evidence : ['Sem evidência adicional no payload atual']).map(item => `
              <div class="twin-evidence-row">${esc(item)}</div>
            `).join('')}
          </div>
        </aside>
      </div>

      <section class="card twin-execution">
        <div class="twin-execution-head">
          <h3>Execução end-to-end</h3>
          <p>Atividades suportadas pelo memorial e pelo contexto real da reconciliação.</p>
        </div>
        <div class="twin-execution-grid">
          ${execSteps.slice(0, 8).map(renderExecutionStep).join('')}
        </div>
      </section>

      <div class="twin-lower">
        <section class="card twin-panel">
          <h3>Resultado metrológico</h3>
          <div class="twin-result-grid">
            ${resultCard('HC MPFM', `${num(resumo.massa_hc_mpfm_t, 2)} t`, `Ref. ${num(resumo.massa_hc_ref_t, 2)} t`, devKind(resumo.desvio_hc_pct, nodes.meta.hcLimit))}
            ${resultCard('Desvio HC', `${num(resumo.desvio_hc_pct, 3)}%`, `limite ±${num(nodes.meta.hcLimit, 1)}%`, devKind(resumo.desvio_hc_pct, nodes.meta.hcLimit))}
            ${resultCard('Total MPFM', `${num(resumo.massa_total_mpfm_t, 2)} t`, `Ref. ${num(resumo.massa_total_ref_t, 2)} t`, devKind(resumo.desvio_total_pct, nodes.meta.totalLimit))}
            ${resultCard('Desvio Total', `${num(resumo.desvio_total_pct, 3)}%`, `limite ±${num(nodes.meta.totalLimit, 1)}%`, devKind(resumo.desvio_total_pct, nodes.meta.totalLimit))}
          </div>
        </section>

        <section class="card twin-panel">
          <h3>PVT e memorial</h3>
          <div class="twin-formulas">
            <code>NSV = GSV × (1 - BSW / 100)</code>
            <code>V_STO = NSV × FE/SF (${num(pvt.fe, 6)})</code>
            <code>V_gas_total = V_gas_sep + V_STO × ΔRs (${num(pvt.rs, 4)})</code>
            <code>δ = 100 × (MPFM - REF) / REF</code>
          </div>
          <p>Fonte PVT: ${esc(pvt.source || run.pvt_snapshot?.source || 'pvt_params / snapshot do run')}.</p>
        </section>
      </div>
    `;
  }

  function renderEquipment(eq, node, index = 0, total = EQUIPMENT.length) {
    const active = twinSelected === eq.id ? ' active' : '';
    const muted = node?.kind === 'info' && /NÃO INFORMADO|SEM FONTE|—/i.test(String(node?.status || '')) ? ' context' : '';
    const position = total > 1 ? `${(index / (total - 1)) * 100}` : '50';
    return `
      <button type="button" class="twin-eq ${eq.slot}${active}${muted} ${node?.kind || 'info'}" data-twin-node="${eq.id}" style="--node-progress:${position}%">
        <img src="${ASSET}${eq.asset}" alt="">
        <span>${esc(eq.label)}</span>
        <b>${esc(node?.status || '—')}</b>
      </button>
    `;
  }

  function getActiveEquipment(ctx, nodes) {
    const flowMode = String(ctx.run?.analytical_snapshot?.flow_mode || '').toLowerCase();
    const equipment = EQUIPMENT.filter(eq => {
      if (eq.id === 'gaslift') return flowMode.includes('gas') || nodes.gaslift?.kind !== 'info' || !/NÃO INFORMADO/i.test(String(nodes.gaslift?.status || ''));
      if (eq.id === 'subsea') return flowMode.includes('subsea') || nodes.subsea?.kind !== 'info';
      return true;
    });
    return equipment.length >= 5 ? equipment : EQUIPMENT;
  }

  function renderTwinBackdrop(ctx, nodes) {
    const run = ctx.run || {};
    const resumo = ctx.resumo || {};
    const flowMode = run.analytical_snapshot?.flow_mode || 'topside_sep';
    return `
      <div class="twin-zone twin-zone--reservoir">
        <span>Reservatório / poço</span>
        <strong>${esc(run.bank || '—')} · ${esc(run.tag || '—')}</strong>
      </div>
      <div class="twin-zone twin-zone--subsea">
        <span>Subsea e escoamento</span>
        <strong>${esc(flowMode)}</strong>
      </div>
      <div class="twin-zone twin-zone--topside">
        <span>Topside / referência</span>
        <strong>${esc(resumo.status_final || resumo.status_linha || 'em análise')}</strong>
      </div>
      <div class="twin-seabed"></div>
      <div class="twin-platform"></div>
    `;
  }

  function renderPhaseMeters(nodes) {
    const ts = nodes.topside || {};
    const sep = nodes.separator || {};
    const phaseRows = [
      ['Óleo', 'oil', metricFromNode(ts, 'Óleo hora') || metricFromNode(sep, 'GSV óleo hora')],
      ['Gás', 'gas', metricFromNode(ts, 'Gás hora') || metricFromNode(sep, 'Gás livre hora')],
      ['Água', 'water', metricFromNode(ts, 'Água hora') || metricFromNode(sep, 'BSW')],
    ];
    return `
      <div class="twin-phase-board">
        ${phaseRows.map(([label, kind, value]) => `
          <div class="twin-phase-row ${kind}">
            <span>${esc(label)}</span>
            <strong>${esc(value || 'sem leitura')}</strong>
          </div>
        `).join('')}
      </div>
    `;
  }

  function metricFromNode(node, label) {
    const found = (node.metrics || []).find(([itemLabel]) => itemLabel === label);
    return found ? found[1] : '';
  }

  function kpi(label, value, sub, kind = '') {
    return `<div class="card twin-kpi ${kind}"><span>${esc(label)}</span><strong>${esc(value)}</strong><em>${esc(sub)}</em></div>`;
  }

  function resultCard(label, value, sub, kind) {
    return `<div class="twin-result ${kind}"><span>${esc(label)}</span><strong>${esc(value)}</strong><em>${esc(sub)}</em></div>`;
  }

  function renderTwinGuide(syn, run, resumo) {
    const contract = syn.source?.dataContract || 'contexto real';
    return `
      <section class="card twin-guide">
        <div class="twin-guide-head">
          <div>
            <h3>Guia rápido do Twin</h3>
            <p>Esta tela é um sinóptico navegável do run real. Ela não recalcula no navegador; mostra o que o backend já reconciliou.</p>
          </div>
          <span>${esc(contract)}</span>
        </div>
        <div class="twin-guide-grid">
          ${guideCard('1', 'Escolha o run', `Use banco, TAG, data ou a lista. Agora: #${run.id || '—'} · ${run.bank || '—'} / ${run.tag || '—'}.`)}
          ${guideCard('2', 'Clique nos equipamentos', 'Cada nó abre métricas e evidências do ponto da cadeia: MPFM, separador, FCS320, riser e premissas.')}
          ${guideCard('3', 'Mude a hora', `A linha 00-23 altera os valores horários. Horas apagadas indicam ausência ou invalidez no cálculo.`)}
          ${guideCard('4', 'Leia a decisão', `Status ${resumo.status_final || resumo.status_linha || '—'} com cobertura ${num(resumo.cobertura_pct, 1)}%. Desvios e limites ficam no bloco de resultado.`)}
        </div>
        <div class="twin-guide-legend">
          <span><b class="ok"></b>Normal ou conforme</span>
          <span><b class="warn"></b>Atenção, fonte ausente ou verificar</span>
          <span><b class="info"></b>Informação contextual</span>
        </div>
      </section>
    `;
  }

  function guideCard(numLabel, title, copy) {
    return `
      <div class="twin-guide-card">
        <b>${esc(numLabel)}</b>
        <strong>${esc(title)}</strong>
        <span>${esc(copy)}</span>
      </div>
    `;
  }

  function renderExecutionStep(step) {
    const metrics = (step.metrics || []).slice(0, 3).map(item => `
      <div class="twin-step-metric"><span>${esc(item.label)}</span><strong>${esc(item.value)}</strong></div>
    `).join('');
    return `
      <div class="twin-step ${step.kind || 'info'}" data-twin-step="${esc(step.id || '')}">
        <b>${esc(step.num || '')}</b>
        <span>${esc(step.title || 'Atividade')}</span>
        <em>${esc(step.summary || '')}</em>
        <div>${metrics}</div>
      </div>
    `;
  }

  function getValidHours(data) {
    const synHours = (data.synoptic?.hourly || []).filter(h => h.valid).map(h => Number(h.hour));
    if (synHours.length) return synHours;
    return (data.calc_horas || []).filter(h => h.hora_valida).map(h => Number(h.hora));
  }

  window.loadTwinMPFM = loadTwinMPFM;
})();
