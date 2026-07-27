(() => {
  const api = async (path, options = {}) => {
    const response = await fetch(`/api${path}`, options);
    const payload = await response.json().catch(() => null);
    if (!response.ok) throw new Error(payload?.detail || 'Falha na requisição.');
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
    select.innerHTML = '<option value="">Selecione uma importação</option>' + batches
      .map((batch) => `<option value="${batch.id}" title="${escapeHtml(batch.source_path || batch.source_name)}">#${batch.id} - ${escapeHtml(batch.source_name)}</option>`)
      .join('');
    setStatus(batches.length ? `${batches.length} importação(ões) disponíveis para manutenção.` : 'Não há importações carregadas.');
  };

  const openModal = async () => {
    const modal = document.getElementById('sgmedMaintenanceModal');
    modal.hidden = false;
    try {
      await loadBatches();
    } catch (error) {
      setStatus(error instanceof Error ? error.message : 'Falha ao carregar importações.');
    }
  };

  const closeModal = () => {
    const modal = document.getElementById('sgmedMaintenanceModal');
    modal.hidden = true;
  };

  const deleteSelected = async () => {
    const select = document.getElementById('sgmedMaintenanceBatch');
    const batchId = select?.value;
    if (!batchId) {
      setStatus('Selecione uma importação para excluir.');
      return;
    }
    const selectedLabel = select.options[select.selectedIndex]?.textContent || `#${batchId}`;
    if (!confirm(`Excluir a importação ${selectedLabel}?\n\nEsta ação remove os arquivos salvos, eventos, snapshots, indicadores e relatórios vinculados a esta importação.`)) return;
    setStatus('Excluindo importação...');
    await api(`/ingestion/batches/${batchId}`, { method: 'DELETE' });
    await loadBatches();
    setStatus(`Importação ${selectedLabel} excluída.`);
  };

  const deleteAll = async () => {
    const confirmation = prompt('Para apagar todas as importações carregadas, digite exatamente: APAGAR_TODAS_IMPORTACOES');
    if (confirmation !== 'APAGAR_TODAS_IMPORTACOES') {
      setStatus('Limpeza geral cancelada.');
      return;
    }
    setStatus('Excluindo todas as importações carregadas...');
    const result = await api(`/ingestion/batches?confirm=${encodeURIComponent(confirmation)}`, { method: 'DELETE' });
    await loadBatches();
    setStatus(`${result.batches_deleted || 0} importação(ões) excluída(s). Cadastros, regras e referências foram preservados.`);
  };

  const mount = () => {
    if (document.getElementById('sgmedMaintenanceButton')) return;

    const button = document.createElement('button');
    button.id = 'sgmedMaintenanceButton';
    button.className = 'sgmed-maintenance-button';
    button.type = 'button';
    button.textContent = 'Manutenção da base';
    button.addEventListener('click', openModal);

    const modal = document.createElement('div');
    modal.id = 'sgmedMaintenanceModal';
    modal.className = 'sgmed-maintenance-modal';
    modal.hidden = true;
    modal.innerHTML = `
      <div class="sgmed-maintenance-panel" role="dialog" aria-modal="true" aria-labelledby="sgmedMaintenanceTitle">
        <h2 id="sgmedMaintenanceTitle">Manutenção da base</h2>
        <p>Use esta área para remover importações carregadas. A limpeza geral apaga os dados importados, mas preserva cadastros, regras, referências e seleções.</p>
        <label class="field sgmed-maintenance-select">
          <span>Importação para excluir</span>
          <select id="sgmedMaintenanceBatch"><option value="">Carregando...</option></select>
        </label>
        <div class="sgmed-maintenance-actions">
          <button type="button" id="sgmedMaintenanceDeleteOne" class="ghost-button">Excluir importação selecionada</button>
          <button type="button" id="sgmedMaintenanceDeleteAll" class="danger">Excluir todas as importações</button>
          <button type="button" id="sgmedMaintenanceRefresh" class="ghost-button">Atualizar lista</button>
          <button type="button" id="sgmedMaintenanceClose" class="ghost-button">Fechar</button>
        </div>
        <div id="sgmedMaintenanceStatus" class="sgmed-maintenance-status">Carregando importações...</div>
      </div>`;

    document.body.append(button, modal);
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
