'use strict';

function aiEscape(value) {
  return String(value ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
}

// ── Catálogo de modelos por provider ──────────────────────────────────────────
const AI_MODELS = {
  '': [
    { value: 'gemini-2.5-flash', label: 'Gemini 2.5 Flash  ·  atual' },
  ],
  gemini: [
    { value: 'gemini-2.5-flash', label: 'Gemini 2.5 Flash  ·  atual' },
    { value: 'gemini-2.5-pro', label: 'Gemini 2.5 Pro  ·  avançado' },
    { value: 'gemini-2.5-flash-lite', label: 'Gemini 2.5 Flash Lite  ·  rápido' },
  ],
  kimi: [
    { value: 'moonshot-v1-8k', label: 'Kimi K3  ·  8k' },
    { value: 'moonshot-v1-32k', label: 'Kimi K3  ·  32k' },
    { value: 'moonshot-v1-128k', label: 'Kimi K3  ·  128k' },
  ],
};

// ── State ─────────────────────────────────────────────────────────────────────
const aiState = {
  messages: [],
  loading: false,
  providerStatus: {},
  keysConfig: {},
  initialized: false,
  conversationId: null,
  lastAssistantMessageId: null,
  lastAssistantContent: '',
  lastQuestion: '',
};

// ── Init ──────────────────────────────────────────────────────────────────────
async function loadAiPage() {
  await _refreshAiStatus();
  if (!aiState.initialized) {
    aiState.initialized = true;
    bindAiEvents();
    updateModelDropdown('');
  }
  loadAiActions().catch(() => {});
  loadAiNotes().catch(() => {});
  renderAiMessages();
}

async function _refreshAiStatus() {
  try {
    const [status, keys] = await Promise.all([
      j(`${API}/ai/status`).catch(() => ({})),
      j(`${API}/ai/keys`).catch(() => ({})),
    ]);
    aiState.providerStatus = status.providers || {};
    aiState.keysConfig = keys;
    renderProviderStatus(status);
  } catch (_) {}
}

// ── Model dropdown ────────────────────────────────────────────────────────────
function updateModelDropdown(provider) {
  const sel = document.getElementById('aiModelSel');
  if (!sel) return;
  const models = AI_MODELS[provider] || AI_MODELS[''];
  sel.innerHTML = models.map(m =>
    `<option value="${aiEscape(m.value)}">${aiEscape(m.label)}</option>`
  ).join('');
}

// ── Provider status render ────────────────────────────────────────────────────
function renderProviderStatus(d) {
  _renderStatusBlock('aiProviderStatus', d);
}

function _renderStatusBlock(elId, d) {
  const container = document.getElementById(elId);
  if (!container) return;
  const providers = d.providers || {};
  const anyReady = d.any_ready;
  const rows = Object.entries(providers).map(([p, ok]) =>
    `<div class="ai-status-row"><span class="ai-status-dot ${ok ? 'ok' : 'off'}"></span><span>${aiEscape(p)}</span><span class="muted">${ok ? 'configurado' : 'sem chave'}</span></div>`
  ).join('');
  container.innerHTML = `
    <div class="ai-status-label">${anyReady ? '✓ Pronto para usar' : '⚠ Nenhum provider configurado'}</div>
    ${rows}
    ${!anyReady ? `<div class="ai-status-hint muted fs11 mt6">Configure uma chave na aba <strong>⚙ Config.</strong></div>` : ''}
  `;
}

// ── Events ─────────────────────────────────────────────────────────────────────
let _aiEventsBound = false;
function bindAiEvents() {
  if (_aiEventsBound) return;
  _aiEventsBound = true;

  document.getElementById('btnAiSend')?.addEventListener('click', handleAiSend);
  document.getElementById('btnAnalyzeReport')?.addEventListener('click', handleAnalyzeReport);
  document.getElementById('btnSaveAiNote')?.addEventListener('click', saveLastAiNote);
  document.getElementById('btnSaveAiAction')?.addEventListener('click', saveLastAiAction);
  document.getElementById('btnRefreshAiActions')?.addEventListener('click', () => { loadAiNotes(); loadAiActions(); });
  document.querySelectorAll('[data-ai-quick-action]').forEach(btn => {
    btn.addEventListener('click', () => saveQuickAiAction(btn.dataset.aiQuickAction));
  });

  const inputEl = document.getElementById('aiInput');
  if (inputEl) {
    inputEl.addEventListener('keydown', e => {
      if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) { e.preventDefault(); handleAiSend(); }
    });
    inputEl.addEventListener('input', () => {
      inputEl.style.height = 'auto';
      inputEl.style.height = Math.min(inputEl.scrollHeight, 160) + 'px';
    });
  }

  document.getElementById('aiProviderSel')?.addEventListener('change', e => {
    updateModelDropdown(e.target.value);
  });

  // chips click
  document.getElementById('aiMessages')?.addEventListener('click', e => {
    const chip = e.target.closest('.ai-chip');
    if (chip) {
      const inp = document.getElementById('aiInput');
      if (inp) { inp.value = chip.dataset.prompt; inp.focus(); }
    }
  });

  // Settings panel — bind once when first opened
  _bindSettingsAi();
}

// ── Send ──────────────────────────────────────────────────────────────────────
async function handleAiSend() {
  const inputEl = document.getElementById('aiInput');
  const question = (inputEl?.value || '').trim();
  if (!question || aiState.loading) return;
  inputEl.value = '';
  inputEl.style.height = 'auto';
  aiState.lastQuestion = question;
  _pushMsg({ role: 'user', content: question });
  renderAiMessages();
  await _callAsk(question);
}

async function _callAsk(question) {
  aiState.loading = true;
  _setSendLoading(true);
  _pushThinking();

  const provider  = document.getElementById('aiProviderSel')?.value || undefined;
  const modelSel  = document.getElementById('aiModelSel')?.value || undefined;
  const maxTokens = parseInt(document.getElementById('aiMaxTokens')?.value || '1024', 10);
  const temperature = parseFloat(document.getElementById('aiTemp')?.value || '0.3');

  // Histórico: todos os turnos user/assistant anteriores (exclui thinking e error)
  const history = aiState.messages
    .filter(m => !m._thinking && (m.role === 'user' || m.role === 'assistant'))
    .slice(0, -1)  // última user msg já está em `question`
    .map(m => ({ role: m.role, content: m.content }));

  const body = {
    question,
    max_tokens: maxTokens,
    temperature,
    history,
    include_app_context: true,
    app_context: collectAiAppContext(),
    conversation_id: aiState.conversationId,
  };
  if (provider) body.provider = provider;
  if (modelSel)  body.model   = modelSel;

  try {
    const resp = await j(`${API}/ai/ask`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    _removeThinking();
    aiState.conversationId = resp.conversation_id || aiState.conversationId;
    aiState.lastAssistantMessageId = resp.message_id || null;
    aiState.lastAssistantContent = resp.content || '';
    _pushMsg({ role: 'assistant', content: resp.content, provider: resp.provider, model: resp.model, tokens: resp.output_tokens, message_id: resp.message_id });
    _setFooterNote(`${resp.provider} · ${resp.model} · ${(resp.input_tokens || 0) + (resp.output_tokens || 0)} tokens`);
  } catch (err) {
    _removeThinking();
    const detail = err?.detail || err?.message || String(err);
    _pushMsg({ role: 'error', content: `Erro: ${detail}` });
  } finally {
    aiState.loading = false;
    _setSendLoading(false);
    renderAiMessages();
    _scrollBottom();
  }
}

function collectAiAppContext() {
  const activePageId = document.querySelector('.page.active')?.id || '';
  const currentPage = activePageId.replace(/^page-/, '') || '';
  const selectedMonth = document.getElementById('globalMonth')?.value || '';
  const filters = {};
  const page = activePageId ? document.getElementById(activePageId) : null;
  if (page) {
    page.querySelectorAll('input, select, textarea').forEach(el => {
      const key = el.id || el.name;
      if (!key) return;
      if (el.type === 'password' || key.toLowerCase().includes('key')) return;
      let value = el.type === 'checkbox' ? el.checked : el.value;
      if (value === undefined || value === null || value === '') return;
      if (typeof value === 'string' && value.length > 120) value = value.slice(0, 120) + '...';
      filters[key] = value;
    });
  }
  return {
    current_page: currentPage,
    selected_month: selectedMonth,
    filters,
    data_changed_at: (typeof state !== 'undefined' && state?.lastDataChangedAt) ? state.lastDataChangedAt : '',
  };
}

// ── Analyze report ────────────────────────────────────────────────────────────
async function handleAnalyzeReport() {
  const text = document.getElementById('aiReportText')?.value?.trim();
  const files = Array.from(document.getElementById('aiReportFiles')?.files || []);
  if (!text && files.length === 0) { _toast('Cole texto ou carregue ao menos um arquivo.', 'warn'); return; }
  if (aiState.loading) return;

  aiState.loading = true;
  const btn = document.getElementById('btnAnalyzeReport');
  if (btn) { btn.disabled = true; btn.textContent = 'Analisando...'; }

  const provider = document.getElementById('aiProviderSel')?.value || undefined;

  try {
    const attachments = await _readAiReportAttachments(files);
    const body = { report_text: text || '', attachments, conversation_id: aiState.conversationId };
    if (provider) body.provider = provider;
    const resp = await j(`${API}/ai/analyze/report`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    aiState.conversationId = resp.conversation_id || aiState.conversationId;
    aiState.lastAssistantMessageId = resp.message_id || null;
    aiState.lastAssistantContent = resp.content || '';
    const fileLabel = attachments.length ? ` · ${attachments.length} anexo(s)` : '';
    _pushMsg({ role: 'user', content: `[Análise de relatório — ${(text || '').length} chars${fileLabel}]` });
    _pushMsg({ role: 'assistant', content: resp.content, provider: resp.provider, model: resp.model, tokens: resp.output_tokens, message_id: resp.message_id });
    renderAiMessages();
    _scrollBottom();
    _setFooterNote(`${resp.provider} · ${resp.model} · ${(resp.input_tokens || 0) + (resp.output_tokens || 0)} tokens`);
  } catch (err) {
    _toast(`Erro na análise: ${err?.detail || err?.message || err}`, 'error');
  } finally {
    aiState.loading = false;
    if (btn) { btn.disabled = false; btn.textContent = 'Analisar relatório'; }
  }
}

async function _readAiReportAttachments(files) {
  const limited = files.slice(0, 8);
  const maxBytes = 12 * 1024 * 1024;
  const out = [];
  for (const file of limited) {
    if (file.size > maxBytes) {
      _toast(`Arquivo ignorado por tamanho: ${file.name}`, 'warn');
      continue;
    }
    const dataBase64 = await _fileToBase64(file);
    out.push({ name: file.name, mime_type: file.type || 'application/octet-stream', data_base64: dataBase64 });
  }
  return out;
}

function _fileToBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || '').split(',')[1] || '');
    reader.onerror = () => reject(reader.error || new Error('Falha ao ler arquivo'));
    reader.readAsDataURL(file);
  });
}

async function loadAiActions() {
  const container = document.getElementById('aiActionList');
  if (!container) return;
  const data = await j(`${API}/ai/actions?status=all&limit=12`).catch(() => ({ items: [] }));
  renderAiActions(data.items || []);
}

async function loadAiNotes() {
  const container = document.getElementById('aiNoteList');
  if (!container) return;
  const data = await j(`${API}/ai/notes?limit=5`).catch(() => ({ items: [] }));
  renderAiNotes(data.items || []);
}

function renderAiNotes(items) {
  const container = document.getElementById('aiNoteList');
  if (!container) return;
  if (!items.length) {
    container.innerHTML = '<div class="muted fs11">Nenhuma nota IA salva ainda.</div>';
    return;
  }
  container.innerHTML = items.map(item => `
    <div class="ai-action-item ai-note-item">
      <div class="ai-action-top"><strong>${_escHtml(item.decision_summary || 'Nota IA')}</strong><span class="ai-action-status ai-action-status--note">nota</span></div>
      <div class="muted fs11">${_escHtml(item.created_at || '')}</div>
      ${item.impact_notes ? `<div class="ai-action-summary">${_escHtml(item.impact_notes).slice(0, 180)}</div>` : ''}
    </div>`).join('');
}

function renderAiActions(items) {
  const container = document.getElementById('aiActionList');
  if (!container) return;
  if (!items.length) {
    container.innerHTML = '<div class="muted fs11">Nenhuma proposta IA registrada ainda.</div>';
    return;
  }
  container.innerHTML = items.map(item => {
    const statusLabel = item.status === 'approved' ? 'aprovado' : item.status === 'archived' ? 'arquivado' : 'pendente';
    const canApprove = item.status === 'pending';
    const actionLabel = _aiActionTypeLabel(item.action_type);
    const result = _aiParseJson(item.result_json);
    const flowItem = result?.methodology_flow_item || null;
    return `
      <div class="ai-action-item">
        <div class="ai-action-top"><strong>${_escHtml(item.title || 'Registro IA')}</strong><span class="ai-action-status ai-action-status--${_escHtml(item.status)}">${_escHtml(statusLabel)}</span></div>
        <div class="muted fs11">${_escHtml(actionLabel)} · ${_escHtml(item.target_area || 'nota')} · ${_escHtml(item.created_at || '')}</div>
        ${item.summary ? `<div class="ai-action-summary">${_escHtml(item.summary).slice(0, 220)}</div>` : ''}
        ${flowItem?.flow_item_id ? `<div class="ai-action-summary ai-action-summary--trace">Registrado na trilha metrológica: #${_escHtml(flowItem.flow_item_id)} · run #${_escHtml(flowItem.run_id || '-')} · ${_escHtml(flowItem.item_type || 'registro')}</div>` : ''}
        ${canApprove ? `<div class="ai-action-actions"><button class="btn sm secondary" data-ai-approve="${item.id}">Aprovar</button><button class="btn sm secondary" data-ai-archive="${item.id}">Arquivar</button></div>` : ''}
      </div>`;
  }).join('');
  container.querySelectorAll('[data-ai-approve]').forEach(btn => btn.addEventListener('click', () => approveAiAction(btn.dataset.aiApprove)));
  container.querySelectorAll('[data-ai-archive]').forEach(btn => btn.addEventListener('click', () => archiveAiAction(btn.dataset.aiArchive)));
}

async function saveLastAiNote() {
  if (!aiState.lastAssistantContent) { _toast('Ainda não há resposta da IA para salvar.', 'warn'); return; }
  const titleEl = document.getElementById('aiActionTitle');
  const title = (titleEl?.value || '').trim() || 'Nota técnica IA';
  const summary = document.getElementById('aiActionSummary')?.value?.trim() || '';
  try {
    await j(`${API}/ai/notes`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        conversation_id: aiState.conversationId,
        message_id: aiState.lastAssistantMessageId,
        title,
        summary,
        source_content: aiState.lastAssistantContent,
      }),
    });
    if (titleEl) titleEl.value = '';
    const summaryEl = document.getElementById('aiActionSummary');
    if (summaryEl) summaryEl.value = '';
    _toast('Nota técnica salva.', 'info');
    await loadAiNotes();
  } catch (err) {
    _toast(`Erro ao salvar nota: ${err?.detail || err?.message || err}`, 'error');
  }
}

async function saveLastAiAction() {
  if (!aiState.lastAssistantContent) { _toast('Ainda não há resposta da IA para salvar.', 'warn'); return; }
  const titleEl = document.getElementById('aiActionTitle');
  const target = document.getElementById('aiActionTarget')?.value || 'nota';
  const title = (titleEl?.value || '').trim() || `Registro IA - ${target}`;
  const summary = document.getElementById('aiActionSummary')?.value?.trim() || '';
  try {
    await j(`${API}/ai/actions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        conversation_id: aiState.conversationId,
        message_id: aiState.lastAssistantMessageId,
        action_type: 'record_from_ai',
        target_area: target,
        title,
        summary,
        source_content: aiState.lastAssistantContent,
        payload: buildAiActionPayload('record_from_ai'),
      }),
    });
    if (titleEl) titleEl.value = '';
    const summaryEl = document.getElementById('aiActionSummary');
    if (summaryEl) summaryEl.value = '';
    _toast('Proposta IA salva como pendente.', 'info');
    await loadAiActions();
  } catch (err) {
    _toast(`Erro ao salvar proposta: ${err?.detail || err?.message || err}`, 'error');
  }
}

function _aiParseJson(value) {
  if (!value) return null;
  if (typeof value === 'object') return value;
  try { return JSON.parse(value); } catch (_) { return null; }
}

async function saveQuickAiAction(actionType) {
  if (!aiState.lastAssistantContent) {
    _toast('Peça uma análise à IA antes de acionar uma tarefa rastreável.', 'warn');
    return;
  }
  const config = {
    gerar_proposta: {
      target: 'proposta',
      title: 'Proposta técnica gerada pelo Assistente IA',
      summary: 'Converter a recomendação da IA em proposta rastreável para análise e aprovação humana.',
      toast: 'Proposta técnica criada como pendente.',
    },
    abrir_pendencia: {
      target: 'pendencia',
      title: 'Pendência operacional aberta pelo Assistente IA',
      summary: 'Registrar acompanhamento para lacuna, desvio, fonte ausente ou ação requerida identificada pela IA.',
      toast: 'Pendência criada como tarefa pendente.',
    },
    revisar_limite_cv: {
      target: 'limites_cv',
      title: 'Revisão de limite/PAM ou configuração CV',
      summary: 'Avaliar limite, PAM, faixa calibrada ou mudança de configuração CV citada no contexto da IA.',
      toast: 'Revisão de limite/CV criada como pendente.',
    },
    nota_fechamento: {
      target: 'fechamento',
      title: 'Nota técnica do fechamento diário',
      summary: 'Registrar leitura técnica do fechamento diário com base na resposta da IA.',
      toast: 'Nota técnica de fechamento salva.',
      note: true,
    },
  }[actionType] || null;
  if (!config) return;

  const titleEl = document.getElementById('aiActionTitle');
  const summaryEl = document.getElementById('aiActionSummary');
  const title = (titleEl?.value || '').trim() || config.title;
  const summary = (summaryEl?.value || '').trim() || config.summary;

  try {
    if (config.note) {
      await j(`${API}/ai/notes`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          conversation_id: aiState.conversationId,
          message_id: aiState.lastAssistantMessageId,
          title,
          summary,
          source_content: aiState.lastAssistantContent,
        }),
      });
      await loadAiNotes();
    } else {
      await j(`${API}/ai/actions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          conversation_id: aiState.conversationId,
          message_id: aiState.lastAssistantMessageId,
          action_type: actionType,
          target_area: config.target,
          title,
          summary,
          source_content: aiState.lastAssistantContent,
          payload: buildAiActionPayload(actionType),
        }),
      });
      await loadAiActions();
    }
    if (titleEl) titleEl.value = '';
    if (summaryEl) summaryEl.value = '';
    _toast(config.toast, 'info');
  } catch (err) {
    _toast(`Erro ao criar ação IA: ${err?.detail || err?.message || err}`, 'error');
  }
}

function buildAiActionPayload(actionType) {
  const flowContext = typeof window.getMethodologyFlowActionContext === 'function'
    ? window.getMethodologyFlowActionContext()
    : null;
  return {
    source: 'assistant_response',
    action_type: actionType,
    last_question: aiState.lastQuestion || '',
    app_context: collectAiAppContext(),
    methodology_flow_context: flowContext,
    assistant_message_id: aiState.lastAssistantMessageId,
    conversation_id: aiState.conversationId,
    created_from_ui: 'assistente_ia',
  };
}

function _aiActionTypeLabel(value) {
  return ({
    gerar_proposta: 'gerar proposta',
    abrir_pendencia: 'abrir pendência',
    revisar_limite_cv: 'revisar limite/CV',
    nota_fechamento: 'nota de fechamento',
    record_from_ai: 'registro IA',
  })[value] || 'registro IA';
}

async function approveAiAction(id) {
  try {
    await j(`${API}/ai/actions/${id}/approve`, { method: 'POST' });
    _toast('Proposta aprovada e registrada.', 'info');
    await loadAiActions();
  } catch (err) {
    _toast(`Erro ao aprovar: ${err?.detail || err?.message || err}`, 'error');
  }
}

async function archiveAiAction(id) {
  try {
    await j(`${API}/ai/actions/${id}/archive`, { method: 'POST' });
    _toast('Proposta arquivada.', 'info');
    await loadAiActions();
  } catch (err) {
    _toast(`Erro ao arquivar: ${err?.detail || err?.message || err}`, 'error');
  }
}

// ── Render messages ───────────────────────────────────────────────────────────
function renderAiMessages() {
  const container = document.getElementById('aiMessages');
  if (!container) return;

  if (aiState.messages.length === 0) {
    container.innerHTML = `
      <div class="ai-welcome">
        <div class="ai-welcome-icon">⚡</div>
        <div class="ai-welcome-title">Assistente MPFM</div>
        <div class="ai-welcome-sub">Especialista em medição multifásica, Painel do Operador, checklist diário e fechamento operacional.</div>
        <div class="ai-chips">
          <button class="ai-chip" data-prompt="Resuma o fechamento diário mais recente do Painel Operador, destacando Fiscal/Radar, Export ANP, MPFM e pendências.">Fechamento diário</button>
          <button class="ai-chip" data-prompt="Analise o Checklist Diário importado: Tank, Off Spec Tank, Balanço de Gás e MPFM Subsea x Fiscal-Óleo.">Checklist diário</button>
          <button class="ai-chip" data-prompt="Quais limites/PAM e mudanças de configuração CV merecem atenção agora?">Limites & CV</button>
          <button class="ai-chip" data-prompt="Explique o balanço de gás e os principais deltas, informando unidades e comentários operacionais.">Balanço de gás</button>
          <button class="ai-chip" data-prompt="O que pode causar elevação súbita na fração de água medida pelo MPFM?">Elevação de BSW</button>
        </div>
      </div>`;
    return;
  }

  container.innerHTML = aiState.messages.map((m, index) => {
    if (m._thinking) return `
      <div class="ai-msg ai-msg--thinking">
        <span class="ai-thinking-dot"></span>
        <span class="ai-thinking-dot"></span>
        <span class="ai-thinking-dot"></span>
      </div>`;
    const cls = m.role === 'user' ? 'ai-msg--user'
              : m.role === 'error' ? 'ai-msg--error'
              : 'ai-msg--assistant';
    const meta = (m.provider && m.model)
      ? `<div class="ai-msg-meta">${_escHtml(m.provider)} · ${_escHtml(m.model)}${m.tokens ? ` · ${m.tokens} tokens` : ''}</div>`
      : '';
    const html = m.role === 'assistant'
      ? _renderAiMarkdown(m.content, index)
      : _renderPlainMessage(m.content);
    return `<div class="ai-msg ${cls}"><div class="ai-msg-content">${html}</div>${meta}</div>`;
  }).join('');
  _scrollBottom();
}

function _renderPlainMessage(content) {
  return _escHtml(content).replace(/\n/g, '<br>');
}

function _renderAiMarkdown(content, messageIndex) {
  const source = String(content || '').replace(/\r\n/g, '\n').trim();
  if (!source) return '';

  const lines = source.split('\n');
  const htmlParts = [];
  const headings = [];
  const headingCounters = [0, 0, 0, 0, 0, 0, 0];
  let lineIndex = 0;

  while (lineIndex < lines.length) {
    const line = lines[lineIndex];
    const trimmed = line.trim();

    if (!trimmed) {
      lineIndex += 1;
      continue;
    }

    if (trimmed.startsWith('```')) {
      const language = trimmed.slice(3).trim();
      const codeLines = [];
      lineIndex += 1;
      while (lineIndex < lines.length && !lines[lineIndex].trim().startsWith('```')) {
        codeLines.push(lines[lineIndex]);
        lineIndex += 1;
      }
      if (lineIndex < lines.length) lineIndex += 1;
      htmlParts.push(`<pre class="ai-md-code"><code data-lang="${_escHtml(language)}">${_escHtml(codeLines.join('\n'))}</code></pre>`);
      continue;
    }

    const headingMatch = trimmed.match(/^(#{2,4})\s+(.+)$/);
    if (headingMatch) {
      const level = headingMatch[1].length;
      const cleanTitle = _stripHeadingNumber(headingMatch[2]);
      headingCounters[level] += 1;
      for (let counterIndex = level + 1; counterIndex < headingCounters.length; counterIndex += 1) headingCounters[counterIndex] = 0;
      const number = headingCounters.slice(2, level + 1).filter(Boolean).join('.');
      const id = `ai-msg-${messageIndex}-h-${headings.length + 1}`;
      headings.push({ id, level, title: cleanTitle, number });
      htmlParts.push(`<h${level} id="${id}" class="ai-md-heading ai-md-heading--${level}"><span class="ai-md-heading-number">${number}</span>${_renderInlineMarkdown(cleanTitle)}</h${level}>`);
      lineIndex += 1;
      continue;
    }

    if (_isMarkdownTableStart(lines, lineIndex)) {
      const tableBlock = _collectMarkdownTable(lines, lineIndex);
      htmlParts.push(_renderMarkdownTable(tableBlock.rows));
      lineIndex = tableBlock.nextIndex;
      continue;
    }

    if (/^\s*[-*]\s+/.test(line)) {
      const listItems = [];
      while (lineIndex < lines.length && /^\s*[-*]\s+/.test(lines[lineIndex])) {
        listItems.push(lines[lineIndex].replace(/^\s*[-*]\s+/, '').trim());
        lineIndex += 1;
      }
      htmlParts.push(`<ul>${listItems.map(item => `<li>${_renderInlineMarkdown(item)}</li>`).join('')}</ul>`);
      continue;
    }

    if (/^\s*\d+[.)]\s+/.test(line)) {
      const listItems = [];
      while (lineIndex < lines.length && /^\s*\d+[.)]\s+/.test(lines[lineIndex])) {
        listItems.push(lines[lineIndex].replace(/^\s*\d+[.)]\s+/, '').trim());
        lineIndex += 1;
      }
      htmlParts.push(`<ol>${listItems.map(item => `<li>${_renderInlineMarkdown(item)}</li>`).join('')}</ol>`);
      continue;
    }

    const paragraphLines = [];
    while (lineIndex < lines.length) {
      const paragraphLine = lines[lineIndex];
      const paragraphTrimmed = paragraphLine.trim();
      if (!paragraphTrimmed) break;
      if (paragraphTrimmed.startsWith('```')) break;
      if (/^(#{2,4})\s+/.test(paragraphTrimmed)) break;
      if (_isMarkdownTableStart(lines, lineIndex)) break;
      if (/^\s*[-*]\s+/.test(paragraphLine) || /^\s*\d+[.)]\s+/.test(paragraphLine)) break;
      paragraphLines.push(paragraphTrimmed);
      lineIndex += 1;
    }
    htmlParts.push(`<p>${_renderInlineMarkdown(paragraphLines.join(' '))}</p>`);
  }

  const body = htmlParts.join('');
  if (headings.length < 2) return body;

  const toc = `
    <nav class="ai-md-toc" aria-label="Índice da resposta">
      <div class="ai-md-toc-title">Índice</div>
      ${headings.map(item => `<a class="ai-md-toc-link ai-md-toc-link--${item.level}" href="#${item.id}">${_escHtml(item.number)} ${_escHtml(item.title)}</a>`).join('')}
    </nav>`;
  return toc + body;
}

function _stripHeadingNumber(value) {
  return String(value || '').replace(/^\s*\d+(?:\.\d+)*[.)]?\s+/, '').trim();
}

function _renderInlineMarkdown(value) {
  let html = _escHtml(value);
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
  html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/__([^_]+)__/g, '<strong>$1</strong>');
  html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>');
  return html;
}

function _isMarkdownTableStart(lines, lineIndex) {
  if (lineIndex + 1 >= lines.length) return false;
  const header = lines[lineIndex].trim();
  const separator = lines[lineIndex + 1].trim();
  return header.includes('|') && /^\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?$/.test(separator);
}

function _collectMarkdownTable(lines, startIndex) {
  const rows = [];
  let lineIndex = startIndex;
  while (lineIndex < lines.length && lines[lineIndex].trim().includes('|')) {
    rows.push(lines[lineIndex].trim());
    lineIndex += 1;
  }
  return { rows, nextIndex: lineIndex };
}

function _splitTableRow(row) {
  return row.replace(/^\|/, '').replace(/\|$/, '').split('|').map(cell => cell.trim());
}

function _renderMarkdownTable(rows) {
  if (rows.length < 2) return '';
  const headers = _splitTableRow(rows[0]);
  const bodyRows = rows.slice(2).map(_splitTableRow);
  return `
    <div class="ai-md-table-wrap">
      <table class="ai-md-table">
        <thead><tr>${headers.map(cell => `<th>${_renderInlineMarkdown(cell)}</th>`).join('')}</tr></thead>
        <tbody>${bodyRows.map(row => `<tr>${headers.map((_, cellIndex) => `<td>${_renderInlineMarkdown(row[cellIndex] || '')}</td>`).join('')}</tr>`).join('')}</tbody>
      </table>
    </div>`;
}

// ── Settings panel (inside existing modal) ───────────────────────────────────
let _settingsBound = false;
function _bindSettingsAi() {
  if (_settingsBound) return;

  // Load current config when settings modal opens
  const openBtn = document.getElementById('btnSettings');
  if (openBtn) {
    const _orig = openBtn.onclick;
    openBtn.onclick = async (e) => {
      if (_orig) _orig.call(openBtn, e);
      await _loadAiSettingsPanel();
    };
  }

  document.getElementById('btnSaveAiKeys')?.addEventListener('click', _saveAiKeys);
  _settingsBound = true;
}

async function _loadAiSettingsPanel() {
  try {
    const keys = await j(`${API}/ai/keys`).catch(() => ({}));
    aiState.keysConfig = keys;

    // Default provider
    const defSel = document.getElementById('cfgAiDefaultProvider');
    if (defSel && keys.default_provider) defSel.value = keys.default_provider;

    // Models (never show actual key values, just pre-select model)
    const _setModel = (selId, model) => {
      const sel = document.getElementById(selId);
      if (sel && model) sel.value = model;
    };
    _setModel('cfgGeminiModel',    keys.gemini?.model);
    const masterPrompt = document.getElementById('cfgAiMasterPrompt');
    if (masterPrompt) masterPrompt.value = keys.master_prompt || '';

    // Show status
    const status = await j(`${API}/ai/status`).catch(() => ({}));
    _renderSettingsStatus(status, keys);
  } catch (_) {}
}

function _renderSettingsStatus(status, keys) {
  const container = document.getElementById('aiProviderStatusCfg');
  if (!container) return;

  const providers = {
    gemini:    { ok: status?.providers?.gemini,    key: keys?.gemini?.key },
  };

  container.innerHTML = Object.entries(providers).map(([p, d]) => {
    const dot = d.ok ? 'ok' : 'off';
    const label = d.ok ? 'chave ativa' : (d.key ? 'chave inválida ou sem acesso' : 'sem chave');
    return `<div class="ai-status-row"><span class="ai-status-dot ${dot}"></span><span>${aiEscape(p)}</span><span class="muted">${label}</span></div>`;
  }).join('');
}

async function _saveAiKeys() {
  const btn = document.getElementById('btnSaveAiKeys');
  const status = document.getElementById('aiKeysSaveStatus');
  if (btn) btn.disabled = true;
  if (status) status.textContent = 'Salvando...';

  const payload = {
    default_provider: 'gemini',
    gemini_model:      document.getElementById('cfgGeminiModel')?.value || undefined,
    master_prompt:     document.getElementById('cfgAiMasterPrompt')?.value || '',
  };

  // Only include keys if user typed something in the field (non-empty)
  const geminiKey    = document.getElementById('cfgGeminiKey')?.value?.trim();
  if (geminiKey)    payload.gemini_key    = geminiKey;

  // Remove undefined fields
  Object.keys(payload).forEach(k => payload[k] === undefined && delete payload[k]);

  try {
    await j(`${API}/ai/keys`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    // Clear key fields after save (security)
    ['cfgGeminiKey'].forEach(id => {
      const el = document.getElementById(id);
      if (el) el.value = '';
    });

    if (status) status.textContent = '✓ Salvo com sucesso';
    setTimeout(() => { if (status) status.textContent = ''; }, 3000);

    // Refresh status block
    const [st, keys] = await Promise.all([
      j(`${API}/ai/status`).catch(() => ({})),
      j(`${API}/ai/keys`).catch(() => ({})),
    ]);
    aiState.providerStatus = st.providers || {};
    aiState.keysConfig = keys;
    _renderSettingsStatus(st, keys);
    renderProviderStatus(st);

  } catch (err) {
    if (status) status.textContent = `Erro: ${err?.detail || err?.message || err}`;
  } finally {
    if (btn) btn.disabled = false;
  }
}

// ── Helpers ───────────────────────────────────────────────────────────────────
function _pushMsg(msg)  { aiState.messages.push(msg); }
function _pushThinking()  { aiState.messages.push({ _thinking: true }); renderAiMessages(); _scrollBottom(); }
function _removeThinking() { const i = aiState.messages.findIndex(m => m._thinking); if (i >= 0) aiState.messages.splice(i, 1); }

function _setSendLoading(on) {
  const btn = document.getElementById('btnAiSend');
  if (!btn) return;
  btn.disabled = on;
  btn.textContent = on ? '...' : 'Enviar';
}

function _setFooterNote(text) {
  const el = document.getElementById('aiFooterNote');
  if (el) el.textContent = text;
}

function _scrollBottom() {
  const c = document.getElementById('aiMessages');
  if (c) requestAnimationFrame(() => { c.scrollTop = c.scrollHeight; });
}

function _escHtml(s) {
  return String(s)
    .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
    .replace(/"/g,'&quot;').replace(/'/g,'&#39;');
}

function _toast(msg, type = 'info') {
  const t = document.createElement('div');
  t.className = `ai-toast ai-toast--${type}`;
  t.textContent = msg;
  document.body.appendChild(t);
  setTimeout(() => t.remove(), 4000);
}
