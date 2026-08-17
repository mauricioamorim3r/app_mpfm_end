'use strict';

function uploadEscape(value) {
  return String(value ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
}

// ── UPLOAD ────────────────────────────────────────────────────────────────────
const drop = document.getElementById('dropZone'), inp = document.getElementById('fileInput');
let uploadQueueSeq = 0;
drop.onclick = () => inp.click();
inp.onchange = e => addFiles([...e.target.files]);
['dragover','dragenter'].forEach(ev => drop.addEventListener(ev, e => { e.preventDefault(); drop.style.borderColor='var(--accent)'; }));
['dragleave','drop'].forEach(ev => drop.addEventListener(ev, e => { e.preventDefault(); drop.style.borderColor=''; }));
drop.addEventListener('drop', e => addFiles([...e.dataTransfer.files]));
function ensureQueueId(file) {
  if (!file._queueId) {
    uploadQueueSeq += 1;
    file._queueId = `upload-${Date.now()}-${uploadQueueSeq}-${file.name}-${file.size}-${file.lastModified}`;
  }
  return file._queueId;
}
async function sha1File(file) {
  const buffer = await file.arrayBuffer();
  const digest = await crypto.subtle.digest('SHA-1', buffer);
  return Array.from(new Uint8Array(digest)).map(b => b.toString(16).padStart(2,'0')).join('');
}
async function ensureFileHash(file) {
  if (file._sha1) return file._sha1;
  if (!file._sha1Promise) file._sha1Promise = sha1File(file);
  file._sha1 = await file._sha1Promise;
  return file._sha1;
}
async function buildQueueManifest(progressCallback) {
  const files = state.queue || [];
  const result = [];
  const batchSize = 3; // Processa 3 arquivos por vez para evitar travar a UI
  
  for (let i = 0; i < files.length; i += batchSize) {
    const batch = files.slice(i, i + batchSize);
    if (progressCallback) {
      progressCallback(i, files.length);
    }
    const batchResults = await Promise.all(batch.map(async (file) => ({
      file_id: ensureQueueId(file),
      filename: file.name,
      file_hash: await ensureFileHash(file),
      size: file.size || 0,
      last_modified: file.lastModified || 0,
    })));
    result.push(...batchResults);
    // Yield para a UI entre batches
    await new Promise(resolve => setTimeout(resolve, 10));
  }
  
  return result;
}
function addFiles(files) {
  files.filter(f => /\.(pdf|txt)$/i.test(f.name)).forEach(f => {
    ensureQueueId(f);
    state.queue.push(f);
  });
  renderQueue();
  renderUploadContext();
}
function renderQueue() {
  document.getElementById('queue').innerHTML = state.queue.map((f,i) =>
    `<div class="file-item"><div><div>${uploadEscape(f.name)}</div><div class="muted" style="font-size:11px">${Math.max(1, Math.round((f.size || 0)/1024))} KB</div></div><button class="btn secondary sm" onclick="removeQ(${i})">✕</button></div>`
  ).join('') || '<div class="muted" style="font-size:12px;margin-top:8px">Fila vazia.</div>';
  setMainProcessingBusy(false);
}
function renderUploadContext(historyRuns) {
  const host = document.getElementById('uploadContext');
  if (!host) return;
  const queue = state.queue || [];
  const queuePdf = queue.filter(f => /\.pdf$/i.test(f.name)).length;
  const queueTxt = queue.filter(f => /\.txt$/i.test(f.name)).length;
  const runs = historyRuns || state.processHistoryRuns || [];
  const last = runs[0] || null;
  const lastMonths = (last?.months_updated || []).join(', ') || '—';
  host.innerHTML = `
    <div class="upload-context-card"><div class="k">Fila pronta</div><div class="v">${queue.length}</div><div class="m">${queuePdf} PDF · ${queueTxt} TXT aguardando processamento</div></div>
    <div class="upload-context-card"><div class="k">Último processamento</div><div class="v">${last ? uploadEscape((last.started_at || '').replace('T',' ').slice(0,16)) : '—'}</div><div class="m">${last ? `${last.files_count || 0} arquivo(s) · ${uploadEscape(last.status || 'sem status')}` : 'Nenhum processamento ainda'}</div></div>
    <div class="upload-context-card"><div class="k">Meses afetados</div><div class="v">${uploadEscape(lastMonths)}</div><div class="m">Última execução registrada no histórico</div></div>
  `;
}

function appendImportCheckFeedback(res) {
  const host = document.getElementById('processLog');
  if (!host) return;
  const check = res?.import_check || {};
  const problemCount = Array.isArray(check.problem_files) ? check.problem_files.length : 0;
  const failedCount = Array.isArray(check.failed_files) ? check.failed_files.length : 0;
  const checkedCount = Number(check.checked_files || 0);
  const validatedCount = Number(check.validated_files || 0);
  if (!checkedCount && !problemCount && !failedCount) return;
  const summary = [
    '',
    '🧪 Validação automática da importação:',
    `Arquivos checados: ${checkedCount}`,
    `Arquivos validados com persistência: ${validatedCount}`,
    `Arquivos com dados esperados ausentes: ${problemCount}`,
    `Arquivos com falha de processamento/regra: ${failedCount}`,
    problemCount || failedCount
      ? 'Revise o log acima e tente corrigir ou reenviar os arquivos afetados.'
      : 'Todas as regras de PDF/TXT e a persistência mínima foram validadas nesta carga.'
  ].join('\n');
  host.textContent = `${host.textContent || ''}${summary}`;
  if (problemCount || failedCount) {
    alert(`Pós-checagem da importação: ${problemCount} arquivo(s) sem dados completos e ${failedCount} com falha. Revise o log de processamento.`);
  }
}
window.removeQ = i => { state.queue.splice(i,1); renderQueue(); renderUploadContext(); };
document.getElementById('clearQueue').onclick = () => { state.queue=[]; renderQueue(); renderUploadContext(); };

function setMainProcessingBusy(isBusy) {
  const processBtn = document.getElementById('processBtn');
  const processFolderBtn = document.getElementById('processFolderBtn');
  const processLatestDayBtn = document.getElementById('btnProcessLatestDay');
  const processLatest3DaysBtn = document.getElementById('btnProcessLatest3Days');
  const processSelectedWindowBtn = document.getElementById('btnProcessSelectedWindow');
  const clearQueueBtn = document.getElementById('clearQueue');
  const folderInput = document.getElementById('folderPath');
  const fileInput = document.getElementById('fileInput');
  const busy = !!isBusy || !!state.mainProcessingBusy || !!state.mainCheckBusy || !!state.dupConfirmBusy || !!state.dupModalOpen;
  const hasQueue = !!((state.queue || []).length);
  const hasFolder = !!(folderInput?.value || '').trim();
  if (processBtn) processBtn.disabled = busy || !hasQueue;
  if (processFolderBtn) processFolderBtn.disabled = busy || !hasFolder;
  if (processLatestDayBtn) processLatestDayBtn.disabled = busy;
  if (processLatest3DaysBtn) processLatest3DaysBtn.disabled = busy;
  if (processSelectedWindowBtn) processSelectedWindowBtn.disabled = busy;
  if (clearQueueBtn) clearQueueBtn.disabled = busy || !hasQueue;
  if (folderInput) folderInput.disabled = busy;
  if (fileInput) fileInput.disabled = busy;
}

function setProcessLogStatus(message) {
  const host = document.getElementById('processLog');
  if (host) host.textContent = message;
}

function setDuplicateModalBusy(isBusy, statusText) {
  const cancelBtn = document.getElementById('dupCancelBtn');
  const overwriteAllBtn = document.getElementById('dupOverwriteAllBtn');
  const skipAllBtn = document.getElementById('dupSkipAllBtn');
  const confirmBtn = document.getElementById('dupConfirmBtn');
  const statusEl = document.getElementById('dupStatus');
  [cancelBtn, overwriteAllBtn, skipAllBtn, confirmBtn].forEach(btn => {
    if (btn) btn.disabled = !!isBusy;
  });
  document.querySelectorAll('#dupList button[id^="ow_"]').forEach(btn => {
    btn.disabled = !!isBusy;
  });
  if (statusEl && typeof statusText === 'string') {
    statusEl.textContent = statusText;
  }
}

function closeDuplicateModal(force = false) {
  if (state.dupConfirmBusy && !force) return;
  state.dupModalOpen = false;
  state.dupConfirmHandler = null;
  document.getElementById('dupModal')?.classList.remove('show');
  setDuplicateModalBusy(false, '');
  setMainProcessingBusy(false);
}

document.getElementById('folderPath')?.addEventListener('input', () => setMainProcessingBusy(false));

// ── Processing history ────────────────────────────────────────────────────────
async function loadProcessHistory() {
  const el = document.getElementById('processHistory');
  if (!el) return;
  const previousRuns = state.processHistoryRuns || [];
  el.innerHTML = '<div class="muted" style="font-size:12px;padding:8px 0">Carregando histórico…</div>';
  try {
    const d = await j(`${API}/ops/processing-history?limit=20`);
    const runs = d.runs || [];
    state.processHistoryRuns = runs;
    renderUploadContext(runs);
    if (!runs.length) {
      el.innerHTML = '<div class="muted" style="font-size:12px;padding:8px 0">Nenhum processamento registrado ainda.</div>';
    } else {
      el.innerHTML = runs.map(r => {
        const dt = r.started_at ? uploadEscape(r.started_at.replace('T',' ').slice(0,16)) : '—';
        const months = uploadEscape((r.months_updated||[]).join(', ') || '—');
        const srcIcon = r.source_type === 'upload' ? '↑' : '📁';
        const ok = r.files?.filter(f => f.processed_ok).length || 0;
        const nok = (r.files?.length||0) - ok;
        const fileTypes = {};
        (r.files||[]).forEach(f => { fileTypes[f.file_type] = (fileTypes[f.file_type]||0)+1; });
        const typeSummary = uploadEscape(Object.entries(fileTypes).map(([k,n]) => `${n}×${k}`).join(', '));
        return `<div style="border:1px solid var(--line);border-radius:8px;padding:10px 12px;margin-bottom:8px">
          <div class="row" style="justify-content:space-between;margin-bottom:4px">
            <div style="font-size:12px;font-weight:600">${srcIcon} ${dt}
              <span class="muted" style="font-weight:400;margin-left:8px">${uploadEscape(r.source_ref||'')}</span>
            </div>
            <div>${badge(r.status||'ok')}</div>
          </div>
          <div style="font-size:11px;color:var(--muted)">
            ${r.files_count||0} arquivo(s) · ${ok} OK${nok>0?` · <span style="color:var(--red)">${nok} erro(s)</span>`:''}
            · Meses: <strong style="color:var(--accent)">${months}</strong>
          </div>
          ${typeSummary ? `<div style="font-size:11px;color:var(--muted);margin-top:3px">${typeSummary}</div>` : ''}
        </div>`;
      }).join('');
    }
  } catch (error) {
    console.error('Falha ao carregar histórico de processamento', error);
    renderUploadContext(previousRuns);
    el.innerHTML = '<div class="muted" style="font-size:12px;padding:8px 0">Não foi possível carregar o histórico agora. Tente atualizar a página ou repetir a operação.</div>';
  }
  if (typeof loadAutoFolderMonitorStatus === 'function') {
    try {
      await loadAutoFolderMonitorStatus();
    } catch (error) {
      console.error('Falha ao atualizar o status do monitor automático', error);
    }
  }
}

// ── Duplicate-aware processing ──────────────────────────────────────────────
async function startProcessing(overwriteMap) {
  if (state.mainProcessingBusy) return;
  state.mainProcessingBusy = true;
  setMainProcessingBusy(true);
  setProcessLogStatus('Preparando upload…');
  try {
    const fd = new FormData();
    setProcessLogStatus('Calculando hash dos arquivos…');
    const manifest = await buildQueueManifest((processed, total) => {
      setProcessLogStatus(`Calculando hash dos arquivos… ${processed}/${total}`);
    });
    setProcessLogStatus('Enviando arquivos…');
    fd.append('file_manifest', JSON.stringify(manifest));
    state.queue.forEach(f => fd.append('files', f));
    if (overwriteMap) fd.append('overwrite_map', JSON.stringify(overwriteMap));
    const res = await j(`${API}/process-files`, {method:'POST', body:fd});
    setProcessLogStatus((res.log||[]).join('\n'));
    appendImportCheckFeedback(res);
    state.queue = []; state.dupDecisions = {}; renderQueue();
    await notifyDataChanged(['upload','mpfm','separador','cards','alertas','exportar','monitoramento','xml042']);
    syncGlobal();
    await loadSummary();
    await loadProcessHistory();
    if (typeof loadAutoFolderMonitorStatus === 'function') {
      await loadAutoFolderMonitorStatus();
    }
    // ✅ Navegar de volta para a página de resumo após upload completo
    setPage('resumo');
  } catch (error) {
    console.error('Falha ao processar arquivos da fila', error);
    setProcessLogStatus(error?.message || 'Falha ao processar os arquivos da fila.');
  } finally {
    state.mainProcessingBusy = false;
    setMainProcessingBusy(false);
  }
}

async function startFolderProcessing(folder, overwriteMap) {
  if (state.mainProcessingBusy) return;
  state.mainProcessingBusy = true;
  setMainProcessingBusy(true);
  setProcessLogStatus(`Processando pasta:\n${folder}\n\nAguarde…`);
  try {
    const res = await j(`${API}/process-folder`, {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({folder, overwrite_map: overwriteMap || null}),
    });
    setProcessLogStatus((res.log||[]).join('\n'));
    appendImportCheckFeedback(res);
    if (res.last_date) {
      const newMonth = res.last_date.slice(0,7);
      const moSel = document.getElementById('globalMonth');
      if (moSel) moSel.value = newMonth;
    }
    await notifyDataChanged(['upload','mpfm','separador','cards','alertas','exportar','monitoramento','xml042']);
    syncGlobal();
    await loadSummary();
    await loadProcessHistory();
    if (typeof loadAutoFolderMonitorStatus === 'function') {
      await loadAutoFolderMonitorStatus();
    }
    setPage('resumo');
  } catch (error) {
    console.error('Falha ao processar pasta local', error);
    setProcessLogStatus(error?.message || 'Falha ao processar a pasta selecionada.');
  } finally {
    state.mainProcessingBusy = false;
    setMainProcessingBusy(false);
  }
}

function getSelectedIngestionWindow() {
  const targetDay = (document.getElementById('latestTargetDay')?.value || '').trim();
  const rawWindow = parseInt(document.getElementById('latestWindowDays')?.value || '1', 10);
  const daysCount = Math.max(1, Math.min(31, Number.isFinite(rawWindow) ? rawWindow : 1));
  return {targetDay, daysCount};
}

function buildLatestDayPayload(daysCount = 1, overwriteMap = null, targetDay = '') {
  return {
    days_count: daysCount,
    target_day: targetDay || '',
    sep_root: (document.getElementById('sepFolderRoot')?.value || '').trim(),
    sep_folder_names: (document.getElementById('sepFolderNames')?.value || 'FC13, FC14, FC17')
      .split(/[,;]/)
      .map(item => item.trim())
      .filter(Boolean),
    overwrite_map: overwriteMap || null,
    force_overwrite: !!overwriteMap && Object.values(overwriteMap).some(value => value === 'overwrite'),
  };
}

function formatLatestDayPreview(preview) {
  const folders = preview?.folders || [];
  const targetDays = preview?.target_days || (preview?.target_day ? [preview.target_day] : []);
  const requestedDay = preview?.requested_day || '';
  const daysLabel = targetDays.length > 1 ? targetDays.slice().sort().join(' a ') : (targetDays[0] || 'não identificado');
  const folderLines = folders.map(folder => {
    const expectedHourly = 24 * Math.max(1, targetDays.length || preview?.days_count || 1);
    const status = folder.exists ? `${folder.daily_found || 0} daily · ${folder.hourly_found || 0}/${expectedHourly} hourly` : 'pasta não encontrada';
    const missing = (folder.missing || []).length ? ` · faltando: ${(folder.missing || []).join(', ')}` : '';
    return `• ${folder.label || folder.path}: ${status}${missing}`;
  });
  const sep = preview?.sep || {};
  const sepLine = sep.enabled
    ? `SEP TXT: ${preview.sep_count || 0} arquivo(s) selecionado(s) · ${sep.complete ? 'trio completo' : 'trio incompleto/ausente'}`
    : `SEP TXT: ${sep.message || 'pasta SEP não informada'}`;
  return [
    `${requestedDay ? (targetDays.length > 1 ? 'Janela solicitada' : 'Dia solicitado') : (targetDays.length > 1 ? 'Últimos dias vigentes' : 'Último dia vigente')}: ${daysLabel}`,
    `${preview?.message || ''}`,
    `MPFM PDF: ${preview?.mpfm_count || 0} arquivo(s)` ,
    sepLine,
    `Duplicados detectados: ${preview?.duplicates_count || 0}`,
    '',
    ...folderLines,
  ].join('\n');
}

async function startLatestDayProcessing(daysCount = 1, overwriteMap = null, targetDay = '') {
  if (state.mainProcessingBusy) return;
  state.mainProcessingBusy = true;
  setMainProcessingBusy(true);
  setProcessLogStatus(targetDay
    ? `Processando janela de ${daysCount} dia(s) até ${targetDay}…`
    : (daysCount > 1 ? `Processando ${daysCount} últimos dias vigentes…` : 'Processando último dia vigente…'));
  try {
    const res = await j(`${API}/latest-day-ingestion/process`, {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify(buildLatestDayPayload(daysCount, overwriteMap, targetDay)),
    });
    setProcessLogStatus((res.log || []).join('\n') || formatLatestDayPreview(res));
    appendImportCheckFeedback(res);
    if (res.last_date) {
      const moSel = document.getElementById('globalMonth');
      if (moSel) moSel.value = res.last_date.slice(0, 7);
    }
    await notifyDataChanged(['upload','mpfm','separador','cards','alertas','exportar','monitoramento','xml042']);
    syncGlobal();
    await loadSummary();
    await loadProcessHistory();
    if (typeof loadAutoFolderMonitorStatus === 'function') {
      await loadAutoFolderMonitorStatus();
    }
  } catch (error) {
    console.error('Falha ao processar último dia vigente', error);
    setProcessLogStatus(error?.message || 'Falha ao processar o último dia vigente.');
  } finally {
    state.mainProcessingBusy = false;
    setMainProcessingBusy(false);
  }
}

async function previewAndMaybeProcessLatestDays(daysCount = 1, targetDay = '') {
  if (state.mainProcessingBusy || state.mainCheckBusy) return;
  state.mainCheckBusy = true;
  setMainProcessingBusy(true);
  const label = targetDay
    ? `janela de ${daysCount} dia(s) até ${targetDay}`
    : (daysCount > 1 ? `${daysCount} últimos dias vigentes` : 'último dia vigente');
  setProcessLogStatus(`Verificando arquivos elegíveis da ${label} nas pastas MPFM configuradas…`);
  try {
    const preview = await j(`${API}/latest-day-ingestion/preview`, {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify(buildLatestDayPayload(daysCount, null, targetDay)),
    });
    const summary = formatLatestDayPreview(preview);
    setProcessLogStatus(summary);
    if (!preview.has_eligible) {
      alert('Não foram encontrados arquivos elegíveis para processar.');
      return;
    }
    const proceed = confirm(`${summary}\n\nDeseja processar agora?`);
    if (!proceed) return;
    const dups = preview.duplicates || [];
    if (dups.length) {
      openDuplicateModal(dups, async () => startLatestDayProcessing(daysCount, state.dupDecisions, targetDay));
      return;
    }
    await startLatestDayProcessing(daysCount, null, targetDay);
  } catch (error) {
    console.error(`Falha ao verificar ${label}`, error);
    setProcessLogStatus(error?.message || `Falha ao verificar ${label}.`);
  } finally {
    state.mainCheckBusy = false;
    if (!state.mainProcessingBusy) {
      setMainProcessingBusy(false);
    }
  }
}

function openDuplicateModal(dups, confirmHandler) {
  state.dupDecisions = {};
  dups.forEach(d => state.dupDecisions[d.file_id] = 'overwrite');
  state.dupConfirmHandler = confirmHandler;
  state.dupModalOpen = true;
  state.dupStatusBase = `${dups.length} arquivo(s) duplicado(s)`;
  document.getElementById('dupList').innerHTML = dups.map(d => `
    <div style="display:flex;align-items:center;justify-content:space-between;padding:10px 14px;border-bottom:1px solid var(--line)" id="duprow_${CSS.escape(d.file_id)}">
      <div>
        <div style="font-size:12px;color:var(--text);font-family:'IBM Plex Mono',monospace;max-width:380px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${d.filename}">${d.filename}</div>
        <div style="font-size:11px;color:var(--muted);margin-top:2px">${d.duplicate_mode === 'same_content' ? 'Mesmo conteúdo já importado' : 'Mesmo nome já importado'} · ${d.last_imported||'data desconhecida'} · ${d.content_date||''} · ${d.file_type||''}${d.meter_id ? ` · ${d.meter_id}` : ''}</div>
      </div>
      <div class="row" style="gap:6px;flex-shrink:0">
        <button class="btn sm" id="ow_${CSS.escape(d.file_id)}" onclick="dupToggle(${JSON.stringify(d.file_id)})" style="min-width:120px">🔄 Sobrescrever</button>
      </div>
    </div>`).join('');
  setDuplicateModalBusy(false, state.dupStatusBase);
  document.getElementById('dupModal').classList.add('show');
  setMainProcessingBusy(false);
}

document.getElementById('processBtn').onclick = async () => {
  if (!state.queue.length || state.mainProcessingBusy || state.mainCheckBusy) return;
  state.mainCheckBusy = true;
  setMainProcessingBusy(true);
  setProcessLogStatus('Calculando hash dos arquivos…');
  try {
    const items = await buildQueueManifest((processed, total) => {
      setProcessLogStatus(`Calculando hash dos arquivos… ${processed}/${total}`);
    });
    setProcessLogStatus('Verificando duplicidades na fila…');
    const chk = await j(`${API}/check-duplicates`, {method:'POST',
      headers:{'Content-Type':'application/json'}, body:JSON.stringify({items})});
    const dups = chk.duplicates || [];
    if (!dups.length) {
      await startProcessing(null);
      return;
    }
    openDuplicateModal(dups, async () => startProcessing(state.dupDecisions));
  } catch (error) {
    console.error('Falha ao verificar duplicidades da fila', error);
    setProcessLogStatus(error?.message || 'Falha ao verificar duplicidades da fila.');
  } finally {
    state.mainCheckBusy = false;
    if (!state.mainProcessingBusy) {
      setMainProcessingBusy(false);
    }
  }
};

window.dupToggle = (fileId) => {
  if (state.dupConfirmBusy) return;
  const cur = state.dupDecisions[fileId] || 'overwrite';
  const next = cur === 'overwrite' ? 'skip' : 'overwrite';
  state.dupDecisions[fileId] = next;
  const btn = document.getElementById('ow_' + CSS.escape(fileId));
  if (btn) {
    btn.textContent = next === 'overwrite' ? '🔄 Sobrescrever' : '⏭ Ignorar';
    btn.style.background = next === 'skip' ? 'var(--panel2)' : '';
    btn.style.color = next === 'skip' ? 'var(--muted)' : '';
  }
};

window.dupSetAll = (mode) => {
  if (state.dupConfirmBusy) return;
  Object.keys(state.dupDecisions).forEach(fileId => {
    state.dupDecisions[fileId] = mode;
    const btn = document.getElementById('ow_' + CSS.escape(fileId));
    if (btn) {
      btn.textContent = mode === 'overwrite' ? '🔄 Sobrescrever' : '⏭ Ignorar';
      btn.style.background = mode === 'skip' ? 'var(--panel2)' : '';
      btn.style.color = mode === 'skip' ? 'var(--muted)' : '';
    }
  });
};

window.dupCancel = () => {
  closeDuplicateModal();
};

window.dupConfirm = async () => {
  if (state.dupConfirmBusy) return;
  const handler = state.dupConfirmHandler;
  if (!handler) {
    closeDuplicateModal(true);
    return;
  }
  state.dupConfirmBusy = true;
  setDuplicateModalBusy(true, 'Aplicando decisões e iniciando processamento…');
  setMainProcessingBusy(false);
  try {
    await handler();
    state.dupConfirmBusy = false;
    closeDuplicateModal(true);
  } catch (error) {
    console.error('Falha ao confirmar duplicidades', error);
    setDuplicateModalBusy(false, error?.message || 'Falha ao iniciar o processamento após a conferência de duplicidades.');
  } finally {
    state.dupConfirmBusy = false;
    if (state.dupModalOpen) {
      setDuplicateModalBusy(false, state.dupStatusBase || '');
    }
    setMainProcessingBusy(false);
  }
};

document.getElementById('processFolderBtn').onclick = async () => {
  const folder = document.getElementById('folderPath').value.trim();
  if (!folder || state.mainProcessingBusy || state.mainCheckBusy) return;
  state.mainCheckBusy = true;
  setMainProcessingBusy(true);
  setProcessLogStatus(`Verificando duplicidades na pasta:\n${folder}`);
  try {
    const chk = await j(`${API}/check-folder-duplicates`, {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({folder}),
    });
    const dups = chk.duplicates || [];
    if (!dups.length) {
      await startFolderProcessing(folder, null);
      return;
    }
    openDuplicateModal(dups, async () => startFolderProcessing(folder, state.dupDecisions));
  } catch (error) {
    console.error('Falha ao verificar duplicidades da pasta', error);
    setProcessLogStatus(error?.message || 'Falha ao verificar duplicidades da pasta.');
  } finally {
    state.mainCheckBusy = false;
    if (!state.mainProcessingBusy) {
      setMainProcessingBusy(false);
    }
  }
};

document.getElementById('btnProcessLatestDay')?.addEventListener('click', () => previewAndMaybeProcessLatestDays(1));
document.getElementById('btnProcessLatest3Days')?.addEventListener('click', () => previewAndMaybeProcessLatestDays(3));
document.getElementById('btnProcessSelectedWindow')?.addEventListener('click', () => {
  const {targetDay, daysCount} = getSelectedIngestionWindow();
  if (!targetDay) {
    alert('Informe a data de produção para pesquisar a janela.');
    document.getElementById('latestTargetDay')?.focus();
    return;
  }
  previewAndMaybeProcessLatestDays(daysCount, targetDay);
});

function buildSepFolderPayload() {
  return {
    folder: (document.getElementById('sepFolderRoot')?.value || '').trim(),
    folder_names: (document.getElementById('sepFolderNames')?.value || 'FC13, FC14, FC17')
      .split(/[,;]/)
      .map(item => item.trim())
      .filter(Boolean),
    date_from: (document.getElementById('sepDateFrom')?.value || '').trim(),
    date_to: (document.getElementById('sepDateTo')?.value || '').trim(),
    include_incomplete_days: !!document.getElementById('sepIncludeIncomplete')?.checked,
    force_overwrite: !!document.getElementById('sepForceOverwrite')?.checked,
  };
}

function renderSepPreviewStatCard(label, value, meta = '', tone = '') {
  const toneClass = tone ? ` sep-preview-card--${tone}` : '';
  return `
    <div class="sep-preview-card${toneClass}">
      <div class="sep-preview-card__label">${escapeHtml(label)}</div>
      <div class="sep-preview-card__value">${escapeHtml(String(value ?? '0'))}</div>
      <div class="sep-preview-card__meta">${escapeHtml(meta || ' ')}</div>
    </div>
  `;
}

function renderSepPreviewItems(items, emptyLabel) {
  if (!items.length) {
    return `<div class="sep-preview-empty">${escapeHtml(emptyLabel)}</div>`;
  }
  return items.map(item => `<div class="sep-preview-list__item">${escapeHtml(item)}</div>`).join('');
}

function renderSepPreviewSamples(items) {
  if (!items.length) {
    return '<div class="sep-preview-empty">Nenhum TXT elegível encontrado com a regra atual.</div>';
  }
  return items.slice(0, 12).map(item => `
    <div class="sep-preview-sample">
      <div class="sep-preview-sample__top">
        <strong>${escapeHtml(item.content_date || '—')}</strong>
        <span>${escapeHtml(item.folder_name || '—')}</span>
        <span>${escapeHtml(item.fluid_label || item.fluid_kind || '—')}</span>
      </div>
      <div class="sep-preview-sample__name">${escapeHtml(item.name || '—')}</div>
      <div class="sep-preview-sample__meta">Meter ID ${escapeHtml(item.meter_id || '—')} · ${escapeHtml(item.location || 'Local não informado')}</div>
    </div>
  `).join('');
}

function renderSepFolderPreview(preview) {
  const host = document.getElementById('sepPreviewResult');
  const importBtn = document.getElementById('sepImportBtn');
  if (!host || !importBtn) return;
  if (!preview) {
    host.innerHTML = '<div class="sep-preview-empty">Nenhuma pré-visualização carregada.</div>';
    importBtn.disabled = true;
    return;
  }
  const stats = preview.stats || {};
  const days = preview.days || [];
  const skipped = preview.skipped || [];
  const samples = preview.samples || [];
  const warnings = preview.warnings || [];
  const selectedCount = Number(stats.selected_count || 0);
  const candidateCount = Number(stats.candidate_count || 0);
  const completeDays = days.filter(item => item.is_complete).length;
  const incompleteDays = Math.max(0, days.length - completeDays);
  const cards = [
    ['Selecionados para importar', selectedCount, `${stats.day_count || days.length || 0} dia(s) com dados`, selectedCount ? 'ok' : 'warn'],
    ['Candidatos elegíveis', candidateCount, `${stats.search_root_count || 0} pasta(s) FC encontradas`, candidateCount ? '' : 'warn'],
    ['TXTs vistos', stats.txt_seen || 0, `${stats.txt_ignored_by_name || 0} ignorados pelo nome`, 'muted'],
    ['Filtro por conteúdo', stats.txt_ignored_by_meter || 0, 'TXT(s) sem meter id alvo', 'muted'],
    ['Filtro por data', stats.txt_ignored_by_date || 0, 'TXT(s) fora da janela', 'muted'],
    ['Cobertura diária', completeDays, incompleteDays ? `${incompleteDays} dia(s) incompleto(s)` : 'Todos os dias completos', incompleteDays ? 'warn' : 'ok'],
  ];

  host.innerHTML = `
    <div class="sep-preview">
      <div class="sep-preview-meta">
        <div class="sep-preview-meta__item"><strong>Pasta raiz</strong><span>${escapeHtml(preview.source_root || '—')}</span></div>
        <div class="sep-preview-meta__item"><strong>FCs analisados</strong><span>${escapeHtml((preview.folder_names || []).join(', ') || '—')}</span></div>
        <div class="sep-preview-meta__item"><strong>Janela</strong><span>${escapeHtml(preview.date_from || 'início livre')} até ${escapeHtml(preview.date_to || 'fim livre')}</span></div>
      </div>
      <div class="sep-preview-grid">${cards.map(([label, value, meta, tone]) => renderSepPreviewStatCard(label, value, meta, tone)).join('')}</div>
      ${warnings.length ? `
        <div class="sep-preview-panel sep-preview-panel--warn">
          <div class="sep-preview-panel__title">Avisos da varredura</div>
          <div class="sep-preview-list">${renderSepPreviewItems(warnings.slice(0, 6), 'Sem avisos.')}</div>
        </div>
      ` : ''}
      ${skipped.length ? `
        <div class="sep-preview-panel">
          <div class="sep-preview-panel__title">Dias ignorados</div>
          <div class="sep-preview-list">${renderSepPreviewItems(skipped.slice(0, 10), 'Nenhum dia ignorado.')}</div>
        </div>
      ` : ''}
      <div class="sep-preview-panel">
        <div class="sep-preview-panel__title">Amostra dos arquivos selecionados</div>
        <div class="sep-preview-samples">${renderSepPreviewSamples(samples)}</div>
      </div>
    </div>
  `;
  importBtn.disabled = selectedCount <= 0;
}

function renderSepFolderStatus(message, tone = '') {
  const host = document.getElementById('sepPreviewResult');
  if (!host) return;
  const toneClass = tone ? ` sep-preview-empty--${tone}` : '';
  host.innerHTML = `<div class="sep-preview-empty${toneClass}">${escapeHtml(message)}</div>`;
}

function setSepFolderBusy(isBusy) {
  const previewBtn = document.getElementById('sepPreviewBtn');
  const importBtn = document.getElementById('sepImportBtn');
  if (previewBtn) previewBtn.disabled = !!isBusy;
  if (importBtn) {
    if (isBusy) {
      importBtn.dataset.wasDisabled = importBtn.disabled ? '1' : '0';
      importBtn.disabled = true;
    } else if (importBtn.dataset.wasDisabled === '0') {
      importBtn.disabled = false;
    }
    delete importBtn.dataset.wasDisabled;
  }
}

document.getElementById('sepPreviewBtn')?.addEventListener('click', async () => {
  const payload = buildSepFolderPayload();
  if (!payload.folder) {
    alert('Informe a pasta raiz dos Daily Reports.');
    return;
  }
  if (state.sepFolderPreviewBusy) return;
  state.sepFolderPreviewBusy = true;
  setSepFolderBusy(true);
  renderSepFolderStatus('Analisando pasta e classificando TXTs por conteúdo...');
  try {
    const res = await j(`${API}/sep-folder/preview`, {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify(payload),
    });
    state.sepFolderPreview = res.preview || null;
    renderSepFolderPreview(state.sepFolderPreview);
  } catch (error) {
    console.error('Falha ao pré-visualizar SEP por pasta', error);
    renderSepFolderStatus(error?.message || 'Falha ao pré-visualizar SEP.', 'error');
  } finally {
    state.sepFolderPreviewBusy = false;
    setSepFolderBusy(false);
    const importBtn = document.getElementById('sepImportBtn');
    if (importBtn && !state.sepFolderPreview) {
      importBtn.disabled = true;
    }
  }
});

document.getElementById('sepImportBtn')?.addEventListener('click', async () => {
  const payload = buildSepFolderPayload();
  if (!payload.folder) {
    alert('Informe a pasta raiz dos Daily Reports.');
    return;
  }
  if (state.sepFolderImportBusy) return;
  state.sepFolderImportBusy = true;
  setSepFolderBusy(true);
  document.getElementById('processLog').textContent = 'Importando TXTs elegíveis do SEP...';
  try {
    const res = await j(`${API}/sep-folder/import`, {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify(payload),
    });
    document.getElementById('processLog').textContent = (res.log || []).join('\n') || 'Importação SEP concluída.';
    state.sepFolderPreview = res.preview || null;
    renderSepFolderPreview(state.sepFolderPreview);
    appendImportCheckFeedback(res);
    if (res.last_date) {
      const newMonth = res.last_date.slice(0,7);
      const moSel = document.getElementById('globalMonth');
      if (moSel) moSel.value = newMonth;
    }
    await notifyDataChanged(['upload','mpfm','separador','cards','alertas','exportar','monitoramento','xml042']);
    syncGlobal();
    await loadSummary();
    await loadProcessHistory();
  } catch (error) {
    console.error('Falha ao importar SEP por pasta', error);
    document.getElementById('processLog').textContent = error?.message || 'Falha ao importar os arquivos SEP.';
    renderSepFolderStatus(error?.message || 'Falha ao importar os arquivos SEP.', 'error');
  } finally {
    state.sepFolderImportBusy = false;
    setSepFolderBusy(false);
    const importBtn = document.getElementById('sepImportBtn');
    if (importBtn && !state.sepFolderPreview) {
      importBtn.disabled = true;
    }
  }
});

