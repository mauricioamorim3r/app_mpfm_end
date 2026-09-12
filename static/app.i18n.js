// ═══════════════════════════════════════════════════════════════════════════
// Sistema de Internacionalização (i18n) - PT/EN
// ═══════════════════════════════════════════════════════════════════════════

const i18n = {
  currentLang: 'pt',

  // Dicionário de traduções
  translations: {
    // ═══ NAVEGAÇÃO ═══
    'nav.review': { pt: 'Revisão', en: 'Review' },
    'nav.ingest': { pt: 'Ingestão', en: 'Ingestion' },
    'nav.automation': { pt: 'Automação', en: 'Automation' },
    'nav.settings': { pt: 'Configurações', en: 'Settings' },

    // ═══ PÁGINAS ═══
    'page.resumo': { pt: 'Resumo do Mês', en: 'Monthly Summary' },
    'page.mpfm': { pt: 'Dados MPFM', en: 'MPFM Data' },
    'page.monitoramento': { pt: 'Monitoramento MPFM', en: 'MPFM Monitoring' },
    'page.poco-riser': { pt: 'Poço / Riser', en: 'Well / Riser' },
    'page.upload': { pt: 'Processar Arquivos', en: 'Process Files' },
    'page.separador': { pt: 'Dados Separador', en: 'Separator Data' },
    'page.xml042': { pt: 'XML 042', en: 'XML 042' },
    'page.automacoes': { pt: 'Automações', en: 'Automations' },

    // ═══ TOPBAR ═══
    'topbar.month': { pt: 'Mês de referência', en: 'Reference month' },
    'topbar.auto': { pt: 'Auto', en: 'Auto' },
    'topbar.theme': { pt: 'Claro', en: 'Light' },
    'topbar.theme.dark': { pt: 'Escuro', en: 'Dark' },
    'topbar.config': { pt: 'Config.', en: 'Config.' },
    'topbar.refresh': { pt: 'Atualizar', en: 'Refresh' },
    'topbar.lang': { pt: 'PT', en: 'EN' },

    // ═══ RESUMO DO MÊS ═══
    'resumo.subtitle': { pt: 'Produção multifásica acumulada do mês, por banco e por TAG', en: 'Monthly multiphase production accumulated by bank and TAG' },
    'resumo.eyebrow': { pt: 'Painel Operacional', en: 'Operational Dashboard' },
    'resumo.title': { pt: 'Leitura mensal para produção, cobertura e desvios', en: 'Monthly overview for production, coverage and deviations' },
    'resumo.text': { pt: 'Use esta visão para acompanhar o mês ativo, identificar lacunas de medição e priorizar os bancos ou TAGs que precisam de investigação.', en: 'Use this view to monitor the active month, identify measurement gaps and prioritize banks or TAGs that need investigation.' },
    'resumo.focus.label': { pt: 'Foco', en: 'Focus' },
    'resumo.focus.value': { pt: 'Resumo + cobertura + recon', en: 'Summary + coverage + recon' },
    'resumo.mode.label': { pt: 'Modo', en: 'Mode' },
    'resumo.mode.value': { pt: 'Operação mensal', en: 'Monthly operation' },
    'resumo.visibility.title': { pt: 'Visibilidade do resumo', en: 'Summary visibility' },
    'resumo.visibility.meta': { pt: 'Mostre ou esconda os cards e os painéis de produção conforme a sua necessidade operacional.', en: 'Show or hide cards and production panels according to your operational needs.' },
    'resumo.btn.collapse': { pt: 'Recolher tudo', en: 'Collapse all' },
    'resumo.btn.hide-cards': { pt: 'Ocultar cards', en: 'Hide cards' },
    'resumo.btn.report': { pt: 'Relatório HTML do Mês', en: 'Monthly HTML Report' },

    // ═══ PROCESSAR ARQUIVOS ═══
    'upload.title': { pt: 'Processar Arquivos', en: 'Process Files' },
    'upload.subtitle': { pt: 'Importar arquivos MPFM e SEP', en: 'Import MPFM and SEP files' },
    'upload.section.send': { pt: 'Enviar arquivos', en: 'Upload files' },
    'upload.section.folder': { pt: 'Processar pasta local', en: 'Process local folder' },
    'upload.section.sep': { pt: 'Importar SEP diário por pasta', en: 'Import daily SEP by folder' },
    'upload.section.gap': { pt: 'Diagnóstico mensal de lacunas', en: 'Monthly gap diagnostics' },
    'upload.section.automation': { pt: 'Automações — Base Única e PETEC', en: 'Automations — Unique Base and PETEC' },
    'upload.section.log': { pt: 'Log de processamento', en: 'Processing log' },
    'upload.drop.text': { pt: 'Arraste arquivos aqui ou clique para selecionar', en: 'Drag files here or click to select' },
    'upload.drop.waiting': { pt: 'Aguardando arquivos…', en: 'Waiting for files…' },
    'upload.btn.send': { pt: 'Enviar', en: 'Send' },
    'upload.btn.cancel': { pt: 'Cancelar', en: 'Cancel' },
    'upload.btn.process': { pt: 'Processar pasta', en: 'Process folder' },
    'upload.btn.scan': { pt: 'Varrer mês', en: 'Scan month' },
    'upload.btn.import-pending': { pt: 'Importar pendências', en: 'Import pending' },
    'upload.btn.base-unica': { pt: 'Gerar Base Única', en: 'Generate Unique Base' },
    'upload.btn.petec': { pt: 'Gerar PETEC', en: 'Generate PETEC' },
    'upload.gap.description': { pt: 'Varre, pasta por pasta e subpasta por subpasta, todos os bancos MPFM configurados para o mês escolhido e explica cada data\\hora com dado ausente: arquivo pendente de importação (existe em disco, ainda não foi processado) ou lacuna de origem (não existe na pasta de origem).', en: 'Scans all configured MPFM banks folder by folder and subfolder by subfolder for the chosen month and explains each missing date\\hour: pending import file (exists on disk, not yet processed) or source gap (does not exist in source folder).' },
    'upload.automation.description': { pt: 'Gera relatório HTML ou Excel PETEC diretamente do banco SQLite, sem necessidade de arquivos externos.', en: 'Generates HTML or PETEC Excel report directly from SQLite database, without external files.' },
    'upload.sep.description': { pt: 'A busca manual varre apenas as subpastas FC13, FC14 e FC17. Dentro delas, só analisa arquivos TXT com <strong>Run_24Hours</strong> no nome e ignora arquivos de alarmes, configuração, hourly, daily e monthly.', en: 'Manual search only scans FC13, FC14 and FC17 subfolders. Inside them, only analyzes TXT files with <strong>Run_24Hours</strong> in the name and ignores alarm, configuration, hourly, daily and monthly files.' },

    // ═══ TABELAS ═══
    'table.date': { pt: 'Data', en: 'Date' },
    'table.well': { pt: 'Poço', en: 'Well' },
    'table.riser': { pt: 'Riser', en: 'Riser' },
    'table.file': { pt: 'Arquivo', en: 'File' },
    'table.oil': { pt: 'Óleo', en: 'Oil' },
    'table.gas': { pt: 'Gás', en: 'Gas' },
    'table.water': { pt: 'Água', en: 'Water' },
    'table.total': { pt: 'Total', en: 'Total' },
    'table.deviation': { pt: 'Desvio', en: 'Deviation' },
    'table.status': { pt: 'Status', en: 'Status' },
    'table.type': { pt: 'Tipo', en: 'Type' },
    'table.meter-id': { pt: 'Meter ID', en: 'Meter ID' },
    'table.location': { pt: 'Location', en: 'Location' },
    'table.usage': { pt: 'Uso', en: 'Usage' },
    'table.application': { pt: 'Aplicação', en: 'Application' },

    // ═══ SEPARADOR ═══
    'sep.trio.title': { pt: 'Completude do trio', en: 'Trio completeness' },
    'sep.files.title': { pt: 'Arquivos recebidos', en: 'Received files' },
    'sep.extract.title': { pt: 'Dados extraídos do Separador', en: 'Extracted Separator data' },
    'sep.btn.csv': { pt: 'CSV', en: 'CSV' },
    'sep.btn.excel': { pt: 'Excel', en: 'Excel' },
    'sep.btn.production': { pt: 'Excel Produção', en: 'Production Excel' },

    // ═══ CONFIGURAÇÕES ═══
    'config.theme.title': { pt: 'Modo de cores', en: 'Color mode' },
    'config.conversions.title': { pt: 'Conversões e equivalências', en: 'Conversions and equivalencies' },
    'config.equations.title': { pt: 'Equações usadas na aplicação', en: 'Equations used in the application' },
    'config.equations.intro': { pt: 'Referência rápida das fórmulas operacionais exibidas em resumo, monitoramento e gráficos. Os percentuais são mostrados em <strong>%</strong>.', en: 'Quick reference for operational formulas shown in summary, monitoring and charts. Percentages are shown in <strong>%</strong>.' },
    'config.recovery.title': { pt: 'Recuperação operacional', en: 'Operational recovery' },
    'config.recovery.intro': { pt: 'Ações seguras para diagnóstico, recompilação do mês ativo e regeneração do workbook sem depender de intervenção manual no banco.', en: 'Safe actions for diagnosis, active month recompilation and workbook regeneration without manual database intervention.' },
    'config.monitor.title': { pt: 'Monitor automático de pastas', en: 'Automatic folder monitor' },
    'config.monitor.intro': { pt: 'Enquanto a aplicação estiver aberta, o monitor verifica as pastas ativas, identifica arquivos novos estáveis e roda o mesmo pipeline de processamento da aba de ingestão.', en: 'While the application is open, the monitor checks active folders, identifies stable new files and runs the same ingestion tab processing pipeline.' },
    'config.ai.title': { pt: 'Assistente IA, Google Gemini', en: 'AI Assistant, Google Gemini' },
    'config.ai.intro': { pt: 'Configure a chave do Gemini. As outras integrações foram ocultadas porque estão bloqueadas na rede da empresa.', en: 'Configure the Gemini key. Other integrations have been hidden because they are blocked on the company network.' },

    // ═══ OUTPUTS ═══
    'outputs.title': { pt: 'Arquivos Excel gerados', en: 'Generated Excel files' },

    // ═══ BADGES ═══
    'badge.ok': { pt: 'Diário OK', en: 'Daily OK' },
    'badge.warn': { pt: 'Sem métrica', en: 'No metric' },
    'badge.error': { pt: 'Erro', en: 'Error' },

    // ═══ POCO-RISER ═══
    'poco-riser.subsea': { pt: 'Subsea / Poço — massa corrigida', en: 'Subsea / Well — corrected mass' },
    'poco-riser.topside': { pt: 'Topside / Riser — massa corrigida', en: 'Topside / Riser — corrected mass' },
    'poco-riser.deviation-hc': { pt: '% Desvio HC', en: '% HC Deviation' },
    'poco-riser.deviation-total': { pt: '% Desvio Total', en: '% Total Deviation' },
    'poco-riser.file-well': { pt: 'Arquivo Poço', en: 'Well File' },
    'poco-riser.file-riser': { pt: 'Arquivo Riser', en: 'Riser File' },
    'poco-riser.btn.query': { pt: 'Consultar', en: 'Query' },
    'poco-riser.btn.excel': { pt: 'Excel', en: 'Excel' },
    'poco-riser.zoom.in': { pt: 'Aumentar zoom', en: 'Zoom in' },
    'poco-riser.zoom.out': { pt: 'Diminuir zoom', en: 'Zoom out' },
    'poco-riser.zoom.reset': { pt: 'Resetar zoom', en: 'Reset zoom' },

    // ═══ MENSAGENS DINÂMICAS ═══
    'msg.processing-folder': { pt: 'Processando pasta:', en: 'Processing folder:' },
    'msg.please-wait': { pt: 'Aguarde…', en: 'Please wait…' },
    'msg.processing-window': { pt: 'Processando janela de {count} dia(s) até {day}…', en: 'Processing window of {count} day(s) until {day}…' },
    'msg.processing-days': { pt: 'Processando {count} últimos dias vigentes…', en: 'Processing last {count} active days…' },
    'msg.processing-last-day': { pt: 'Processando último dia vigente…', en: 'Processing last active day…' },
    'msg.sending-files': { pt: 'Enviando arquivos…', en: 'Sending files…' },
    'msg.processing': { pt: 'Processando', en: 'Processing' },
    'msg.success': { pt: 'Concluído com sucesso', en: 'Successfully completed' },
    'msg.error': { pt: 'Erro', en: 'Error' },
    'msg.waiting': { pt: 'Aguardando arquivos…', en: 'Waiting for files…' },

    // ═══ TOOLTIPS ═══
    'tooltip.month-ref': { pt: 'Mês de referência', en: 'Reference month' },
    'tooltip.toggle-theme': { pt: 'Alternar modo de cores', en: 'Toggle color mode' },
    'tooltip.html-report': { pt: 'Abre o relatório HTML consolidado do mês vigente, considerando apenas os dias com dados disponíveis', en: 'Opens the consolidated HTML report for the current month, considering only days with available data' },
    'tooltip.click-day': { pt: 'Clique em qualquer dia para ver a auditoria completa', en: 'Click any day to see the complete audit' },
    'tooltip.printable-page': { pt: 'Abrir uma página HTML com o gráfico atual e a tabela dos dados plotados', en: 'Open an HTML page with the current chart and plotted data table' },
    'tooltip.query-table': { pt: 'Consultar tabela diária', en: 'Query daily table' },
    'tooltip.export-excel': { pt: 'Exportar tabela para Excel', en: 'Export table to Excel' },

    // ═══ PLACEHOLDERS ═══
    'placeholder.folder-path': { pt: 'Caminho da pasta (ex: C:\\dados\\2026-03)', en: 'Folder path (e.g.: C:\\data\\2026-03)' },
    'placeholder.sep-folder': { pt: 'Caminho da pasta (ex: C:\\Users\\...\\05. Maio)', en: 'Folder path (e.g.: C:\\Users\\...\\05. May)' },
    'placeholder.sep-subfolders': { pt: 'FC13, FC14, FC17', en: 'FC13, FC14, FC17' },

    // ═══ LABELS E TÍTULOS ADICIONAIS ═══
    'label.deadlines': { pt: 'Prazos e contagem regressiva', en: 'Deadlines and countdown' },
    'label.manage': { pt: 'Gerenciar', en: 'Manage' },
    'label.coverage': { pt: 'Cobertura de dados do mês', en: 'Monthly data coverage' },
    'label.mpfm-legend': { pt: 'MPFM (Topside / Subsea)', en: 'MPFM (Topside / Subsea)' },
    'label.sep-legend': { pt: 'Separador (Ó, G, Á)', en: 'Separator (O, G, W)' },
    'label.click-detail': { pt: 'Clique em qualquer dia para detalhar', en: 'Click any day for details' },
    'btn.query': { pt: 'Consultar', en: 'Query' },
    'btn.printable': { pt: 'Abrir página imprimível', en: 'Open printable page' },
  },

  // ═══ FUNÇÕES ═══

  // Obter texto traduzido
  t(key) {
    const translation = this.translations[key];
    if (!translation) {
      console.warn(`[i18n] Translation key not found: ${key}`);
      return key;
    }
    return translation[this.currentLang] || translation.pt || key;
  },

  // Aplicar traduções em elementos com data-i18n
  applyTranslations() {
    document.querySelectorAll('[data-i18n]').forEach(el => {
      const key = el.getAttribute('data-i18n');
      const text = this.t(key);

      // Se o elemento tem data-i18n-html="true", usa innerHTML
      if (el.getAttribute('data-i18n-html') === 'true') {
        el.innerHTML = text;
      } else {
        el.textContent = text;
      }
    });

    // Aplicar em placeholders
    document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
      const key = el.getAttribute('data-i18n-placeholder');
      el.placeholder = this.t(key);
    });

    // Aplicar em titles
    document.querySelectorAll('[data-i18n-title]').forEach(el => {
      const key = el.getAttribute('data-i18n-title');
      el.title = this.t(key);
    });

    // Aplicar em aria-label
    document.querySelectorAll('[data-i18n-aria-label]').forEach(el => {
      const key = el.getAttribute('data-i18n-aria-label');
      el.setAttribute('aria-label', this.t(key));
    });

    // Atualizar botão de idioma
    const langBtn = document.getElementById('btnLanguage');
    if (langBtn) {
      langBtn.textContent = this.currentLang === 'pt' ? '🌐 EN' : '🌐 PT';
      langBtn.setAttribute('aria-label', this.currentLang === 'pt' ? 'Switch to English' : 'Mudar para Português');
    }
  },

  // Alternar idioma
  toggleLanguage() {
    this.currentLang = this.currentLang === 'pt' ? 'en' : 'pt';
    this.savePreference();
    this.applyTranslations();

    // Disparar evento customizado para módulos que precisam reagir
    window.dispatchEvent(new CustomEvent('languageChanged', { detail: { lang: this.currentLang } }));
  },

  // Salvar preferência no localStorage
  savePreference() {
    try {
      localStorage.setItem('app_lang', this.currentLang);
    } catch (e) {
      console.warn('[i18n] Could not save language preference to localStorage:', e);
    }
  },

  // Carregar preferência do localStorage
  loadPreference() {
    try {
      const saved = localStorage.getItem('app_lang');
      if (saved === 'pt' || saved === 'en') {
        this.currentLang = saved;
      }
    } catch (e) {
      console.warn('[i18n] Could not load language preference from localStorage:', e);
    }
  },

  // Inicializar sistema i18n
  init() {
    this.loadPreference();
    this.applyTranslations();

    // Adicionar listener ao botão de idioma
    const langBtn = document.getElementById('btnLanguage');
    if (langBtn) {
      langBtn.addEventListener('click', () => this.toggleLanguage());
    }

    console.log(`[i18n] Initialized with language: ${this.currentLang}`);
  }
};

// Exportar para uso global
window.i18n = i18n;
