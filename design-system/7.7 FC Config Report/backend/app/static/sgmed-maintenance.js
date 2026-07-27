(() => {
  const api = async (path, options = {}) => {
    const response = await fetch(`/api${path}`, options);
    const payload = await response.json().catch(() => null);
    if (!response.ok) throw new Error(payload?.detail || 'Falha na requisicao.');
    return payload;
  };

  const escapeHtml = (value) => String(value ?? '').replace(/[&<>'"]/g, (char) => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    "'": '&#39;',
    '"': '&quot;'
  }[char]));

  const setStatus = (message) => {
    const status = document.getElementById('sgmedMaintenanceStatus');
    if (status) status.textContent = message;
  };

  const loadBatches = async () => {
    const select = document.getElementById('sgmedMaintenanceBatch');
    if (!select) return;
    select.innerHTML = '<option value="">Carregando...</option>';
    const batches = await api('/ingestion/batches');
    select.innerHTML = '<option value="">Selecione uma importacao</option>' + batches
      .map((batch) => `<option value="${batch.id}" title="${escapeHtml(batch.source_path || batch.source_name)}">#${batch.id} - ${escapeHtml(batch.source_name)}</option>`)
      .join('');
    setStatus(batches.length ? `${batches.length} importacao(oes) disponiveis para manutencao.` : 'Nao ha importacoes carregadas.');
  };

  const openModal = async () => {
    const modal = document.getElementById('sgmedMaintenanceModal');
    if (!modal) return;
    modal.hidden = false;
    try {
      await loadBatches();
    } catch (error) {
      setStatus(error instanceof Error ? error.message : 'Falha ao carregar importacoes.');
    }
  };

  const closeModal = () => {
    const modal = document.getElementById('sgmedMaintenanceModal');
    if (modal) modal.hidden = true;
  };

  const deleteSelected = async () => {
    const select = document.getElementById('sgmedMaintenanceBatch');
    const batchId = select?.value;
    if (!batchId) {
      setStatus('Selecione uma importacao para excluir.');
      return;
    }
    const selectedLabel = select.options[select.selectedIndex]?.textContent || `#${batchId}`;
    if (!confirm(`Excluir a importacao ${selectedLabel}?\n\nEsta acao remove arquivos salvos, eventos, snapshots, indicadores e relatorios vinculados.`)) return;
    setStatus('Excluindo importacao...');
    await api(`/ingestion/batches/${batchId}`, { method: 'DELETE' });
    await loadBatches();
    setStatus(`Importacao ${selectedLabel} excluida.`);
  };

  const deleteAll = async () => {
    const confirmation = prompt('Para apagar todas as importacoes carregadas, digite exatamente: APAGAR_TODAS_IMPORTACOES');
    if (confirmation !== 'APAGAR_TODAS_IMPORTACOES') {
      setStatus('Limpeza geral cancelada.');
      return;
    }
    setStatus('Excluindo todas as importacoes carregadas...');
    const result = await api(`/ingestion/batches?confirm=${encodeURIComponent(confirmation)}`, { method: 'DELETE' });
    await loadBatches();
    setStatus(`${result.batches_deleted || 0} importacao(oes) excluida(s). Cadastros, regras e referencias foram preservados.`);
  };

  const mount = () => {
    if (document.getElementById('sgmedTools')) return;

    const tools = document.createElement('nav');
    tools.id = 'sgmedTools';
    tools.className = 'sgmed-tools';
    tools.setAttribute('aria-label', 'Ferramentas SGMed');
    tools.innerHTML = `
      <a href="/carga-pasta" class="secondary">Carga por pasta</a>
      <a href="/xml-monitor" class="secondary">Monitor XML</a>
      <button id="sgmedMaintenanceButton" type="button">Manutencao da base</button>`;

    const modal = document.createElement('div');
    modal.id = 'sgmedMaintenanceModal';
    modal.className = 'sgmed-maintenance-modal';
    modal.hidden = true;
    modal.innerHTML = `
      <div class="sgmed-maintenance-panel" role="dialog" aria-modal="true" aria-labelledby="sgmedMaintenanceTitle">
        <h2 id="sgmedMaintenanceTitle">Manutencao da base</h2>
        <p>Remova importacoes carregadas. A limpeza geral apaga dados importados, mas preserva cadastros, regras, referencias e selecoes.</p>
        <label class="sgmed-maintenance-select">
          <span>Importacao para excluir</span>
          <select id="sgmedMaintenanceBatch"><option value="">Carregando...</option></select>
        </label>
        <div class="sgmed-maintenance-actions">
          <button type="button" id="sgmedMaintenanceDeleteOne" class="ghost-button">Excluir selecionada</button>
          <button type="button" id="sgmedMaintenanceDeleteAll" class="danger">Excluir todas</button>
          <button type="button" id="sgmedMaintenanceRefresh" class="ghost-button">Atualizar</button>
          <button type="button" id="sgmedMaintenanceClose" class="ghost-button">Fechar</button>
        </div>
        <div id="sgmedMaintenanceStatus" class="sgmed-maintenance-status">Carregando importacoes...</div>
      </div>`;

    document.body.append(tools, modal);
    document.getElementById('sgmedMaintenanceButton')?.addEventListener('click', openModal);
    document.getElementById('sgmedMaintenanceDeleteOne')?.addEventListener('click', () => deleteSelected().catch((error) => setStatus(error.message)));
    document.getElementById('sgmedMaintenanceDeleteAll')?.addEventListener('click', () => deleteAll().catch((error) => setStatus(error.message)));
    document.getElementById('sgmedMaintenanceRefresh')?.addEventListener('click', () => loadBatches().catch((error) => setStatus(error.message)));
    document.getElementById('sgmedMaintenanceClose')?.addEventListener('click', closeModal);
    modal.addEventListener('click', (event) => {
      if (event.target === modal) closeModal();
    });
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', mount);
  } else {
    mount();
  }
})();