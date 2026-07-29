'use strict';
/* ============================================================
   Painel Operador – Sistema de Ajuda Contextual
   Drawer lateral contextual que muda conforme a aba ativa.
   ============================================================ */

function poHelpEscape(value) {
  return String(value ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
}

// ---------------------------------------------------------------------------
// Conteúdo de ajuda por aba
// ---------------------------------------------------------------------------
const PO_HELP_CONTENT = {

  _actionbar: {
    icon: '⚡',
    title: 'Barra de ações do módulo',
    desc: 'Ações globais disponíveis em qualquer aba. Execute-as na sequência indicada ao iniciar o fechamento diário.',
    buttons: [
      { icon: '↻', label: 'Atualizar painel', text: 'Recarrega todos os resumos, contagens e indicadores sem reprocessar dados.' },
      { icon: '▦', label: 'Reindexar fontes', text: 'Varre todos os caminhos configurados na aba Ingestão e recria o índice de arquivos no banco (staging). Use antes de importar exports ANP.' },
      { icon: '⇄', label: 'Sincronizar contrato', text: 'Lê o contrato técnico (pontos de medição, famílias, tags) e persiste no SQLite. Execute após qualquer alteração no cadastro.' },
      { icon: '⇩', label: 'Importar exports ANP', text: 'Importa os arquivos XML de export do sistema ANP localizados nos caminhos configurados. Ação principal do fechamento.' },
      { icon: '⚙', label: 'Processar Limites/CV', text: 'Recalcula os limites técnicos e os snapshots de CV (Fator de Compressibilidade) com base nos dados indexados.' },
    ],
    steps: [
      'Clique em <strong>Reindexar fontes</strong> para garantir que os arquivos novos estejam visíveis.',
      'Clique em <strong>Importar exports ANP</strong> para carregar os XMLs do período.',
      'Clique em <strong>Sincronizar contrato</strong> se o cadastro foi atualizado.',
      'Use <strong>Processar Limites/CV</strong> quando houver novos snapshots de CV ou limites alterados.',
      'Clique em <strong>Atualizar painel</strong> a qualquer momento para ver os dados mais recentes.',
    ],
    tip: { kind: 'info', icon: 'ℹ️', text: 'O botão <strong>Importar exports ANP</strong> é a ação mais crítica. Execute-o sempre que receber novos XMLs antes de fechar o período.' },
  },

  overview: {
    icon: '🗂️',
    title: 'Visão Geral',
    desc: 'Painel executivo que consolida o estado atual do módulo: inventário de fontes, cobertura ANP por família e a fila rastreável de pendências MPFM.',
    sections: [
      { icon: '📁', label: 'Inventário técnico de fontes', text: 'Lista os arquivos indexados agrupados por categoria. Serve para identificar lacunas (arquivos faltando) ou duplicidades — não é um indicador de produção.' },
      { icon: '📋', label: 'Cobertura ANP por família', text: 'Mostra quantos registros ANP foram importados por família (001=óleo, 002=gás, 003=gás diferencial, 039=falhas, 040=BSW). Leia <em>por família e tag</em>, não pelo total.' },
      { icon: '🔗', label: 'Fila rastreável MPFM', text: 'Resumo das pendências e alertas do fluxo MPFM: pontos sem par, desvios fora do limite, itens aguardando decisão.' },
      { icon: '🗄️', label: 'Contrato técnico sincronizado', text: 'Tabelas do SQLite com pontos, fontes, comparações e propostas carregados pelo contrato. É a base de auditoria do módulo.' },
    ],
    tip: { kind: 'info', icon: 'ℹ️', text: 'Esta tela é o ponto de partida. Se algum card mostrar "sem carga" ou "sem importação", execute as ações da barra antes de prosseguir.' },
  },

  radar: {
    icon: '📡',
    title: 'Dashboard ANP Radar',
    desc: 'Recreação do Radar ANP integrado ao MPFM Manager. Consolida medição, operação, trilha E2E, calendário e propostas em 9 visões.',
    sections: [
      { icon: '📊', label: 'Radar Medição', text: 'Volume fiscal do dia selecionado por ponto. Compara MPFM vs fiscal e destaca desvios críticos.' },
      { icon: '⚙️', label: 'Operação', text: 'Estado operacional de cada ponto: produções em falha, modo de operação, manutenções e intercorrências.' },
      { icon: '🔄', label: 'Trilha E2E', text: 'Rastreabilidade do dado desde o arquivo fonte até o export ANP. Identifica onde o dado foi gerado, transformado ou rejeitado.' },
      { icon: '📅', label: 'Calendário', text: 'Calendário de fechamento com status diário (completo, parcial, atenção, vazio). Clique no dia para ver detalhes.' },
      { icon: '⏰', label: 'Prazos', text: 'Pendências com prazo: itens em aberto, próximos do vencimento e atrasados.' },
      { icon: '✅', label: 'Propostas', text: 'Fila de propostas aguardando autorização, com status e evidências.' },
      { icon: '🔧', label: 'Configuração', text: 'Parâmetros do contrato do ponto: limites, CV, instrumento e família ANP.' },
      { icon: '🤖', label: 'Pergunte ao Radar', text: 'Assistente de IA integrado. Faça perguntas em linguagem natural sobre o ponto selecionado.' },
      { icon: '📁', label: 'Dossiê do ponto', text: 'Consolidação completa do ponto: medições, eventos, evidências e histórico de propostas.' },
    ],
    controls: [
      { icon: '📅', label: 'Dia', text: 'Seleciona a data de referência. Por padrão usa o último dia disponível.' },
      { icon: '🏷️', label: 'Ponto/Tag', text: 'Filtra para exibir apenas o ponto de medição selecionado.' },
      { icon: '🔍', label: 'Busca', text: 'Filtra resultados por tag, alerta, norma, fonte ou proposta.' },
    ],
    tip: { kind: 'warn', icon: '⚠️', text: 'Para o Radar funcionar é necessário ter o contrato sincronizado e os exports ANP importados. Use a barra de ações antes.' },
  },

  ingestion: {
    icon: '📥',
    title: 'Ingestão — Fontes de dados',
    desc: 'Configura os caminhos de onde o módulo busca os arquivos (XMLs ANP, PDFs MPFM, Excel, etc.). Cada fonte pode ter múltiplos caminhos e opção de varrer subpastas.',
    sections: [
      { icon: '📂', label: 'Fonte', text: 'Nome da categoria de fonte (ex: ANP XML, MPFM Daily, Fiscal).' },
      { icon: '🗺️', label: 'Caminhos', text: 'Um ou mais diretórios no sistema de arquivos onde os arquivos dessa fonte ficam armazenados.' },
      { icon: '↘️', label: 'Subpastas', text: 'Quando ativado, a varredura desce em todas as subpastas do caminho configurado.' },
      { icon: '🟢', label: 'Status', text: 'Indica se os caminhos existem e estão acessíveis (ok, not_found, empty).' },
    ],
    buttons: [
      { icon: '✔', label: 'Validar caminhos', text: 'Verifica se os diretórios configurados existem e conta os arquivos disponíveis.' },
      { icon: '↺', label: 'Recarregar', text: 'Recarrega a lista de fontes sem validar os caminhos.' },
    ],
    tip: { kind: 'warn', icon: '⚠️', text: 'Se uma fonte aparecer como <strong>not_found</strong>, verifique se a pasta de rede está mapeada e acessível antes de usar a ação "Reindexar fontes".' },
  },

  files: {
    icon: '📄',
    title: 'Fontes — Índice de arquivos',
    desc: 'Pesquisa e audita todos os arquivos indexados. Permite identificar duplicidades, categorias faltando e estado de cada arquivo.',
    sections: [
      { icon: '🗂️', label: 'Categoria', text: 'Tipo geral do arquivo (ANP, MPFM, Fiscal, Checklist, etc.).' },
      { icon: '📑', label: 'Tipo documental', text: 'Subtipo dentro da categoria (Daily Report, XML, Excel, PDF).' },
      { icon: '👪', label: 'Família ANP', text: 'Código da família ANP associada ao arquivo (001, 002, 003, 039, 040).' },
      { icon: '🏷️', label: 'Tag', text: 'Tag do ponto de medição ao qual o arquivo se refere.' },
      { icon: '🔴', label: 'Duplicata', text: 'Indica se o mesmo arquivo foi indexado mais de uma vez (diferente caminho, mesmo hash).' },
    ],
    tip: { kind: 'info', icon: 'ℹ️', text: 'Use os filtros <strong>Categoria + Família + Tag</strong> para auditar se um período específico está completo antes de importar.' },
  },

  anp: {
    icon: '📋',
    title: 'Exports ANP',
    desc: 'Lista e filtra todos os registros importados dos XMLs de export ANP. Cada linha corresponde a uma medição diária de um ponto de uma família.',
    sections: [
      { icon: '👪', label: 'Família', text: '001=Óleo, 002=Gás Natural, 003=Gás Diferencial, 039=Falhas/Paradas, 040=BSW.' },
      { icon: '📊', label: 'Volume', text: 'Volume bruto (m³) reportado ao ANP para o dia.' },
      { icon: '💧', label: 'BSW%', text: 'Percentual de BS&W (Basic Sediment & Water) reportado. Relevante para família 040.' },
      { icon: '❌', label: 'Código de falha', text: 'Código de evento/falha ANP quando aplicável (família 039).' },
    ],
    buttons: [
      { icon: '🔍', label: 'Consultar', text: 'Aplica os filtros de data, família, tipo e tag para buscar os registros.' },
      { icon: '🧹', label: 'Limpar', text: 'Remove todos os filtros e exibe todos os registros disponíveis.' },
    ],
    tip: { kind: 'warn', icon: '⚠️', text: 'Se não houver registros para uma família/período esperado, verifique se a <strong>importação ANP</strong> foi executada. Use o botão na barra de ações.' },
  },

  xmlValidation: {
    icon: '🔍',
    title: 'Validação XML',
    desc: 'Verifica a integridade dos arquivos XML importados do ANP: malformações estruturais, vínculos quebrados e dados inconsistentes.',
    sections: [
      { icon: '❌', label: 'Crítico', text: 'XML com estrutura inválida ou dados obrigatórios ausentes. Não pode ser processado.' },
      { icon: '⚠️', label: 'Alerta', text: 'Dado presente mas com valor suspeito (ex: volume zero sem código de falha).' },
      { icon: '✅', label: 'OK', text: 'Arquivo válido e consistente.' },
    ],
    buttons: [
      { icon: '🔍', label: 'Consultar', text: 'Filtra os resultados por data, tipo, status, família e tag.' },
    ],
    tip: { kind: 'warn', icon: '⚠️', text: 'Erros <strong>críticos</strong> requerem ação antes do fechamento. Verifique os XMLs originais ou solicite reenvio ao sistema de origem.' },
  },

  measured: {
    icon: '📈',
    title: 'Dados Medidos',
    desc: 'Exibe as medições de produção organizadas em três visões: dias de produção, totais diários agregados e linhas detalhadas de medição.',
    sections: [
      { icon: '📅', label: 'Dias de produção', text: 'Cada linha é um dia-ponto. Mostra horas disponíveis, volumes e se o dado é completo ou parcial.' },
      { icon: '📊', label: 'Totais diários', text: 'Agregações por dia: total de óleo, gás e água. Útil para comparar com o fiscal.' },
      { icon: '🔢', label: 'Linhas detalhadas', text: 'Cada linha de medição individual com valor, unidade, fonte e status.' },
    ],
    buttons: [
      { icon: '📅', label: 'De / Até', text: 'Define o intervalo de datas para consulta.' },
      { icon: '👪', label: 'Família', text: 'Filtra por família ANP.' },
      { icon: '🏷️', label: 'Tag', text: 'Filtra por ponto de medição.' },
    ],
    tip: { kind: 'info', icon: 'ℹ️', text: 'Para um dia aparecer como <strong>completo</strong>, é necessário ter 24 horas registradas e os volumes diários presentes.' },
  },

  checklist: {
    icon: '✅',
    title: 'Checklist Diário',
    desc: 'Importa e analisa os arquivos Excel de fechamento diário (checklist operacional). Organiza os dados em 6 seções: resumo, fechamento de óleo, qualidade, MPFM vs fiscal, balanço de gás e linhas brutas.',
    sections: [
      { icon: '📊', label: 'Resumo', text: 'Visão consolidada do checklist: cobertura por data, alertas e status geral.' },
      { icon: '🛢️', label: 'Fechamento óleo', text: 'Balanço de tanques: estoque inicial, produção, transferências, injeção e saldo final.' },
      { icon: '🔬', label: 'Qualidade', text: 'Amostras de qualidade: API, BSW%, densidade. Destaca amostras fora de especificação.' },
      { icon: '⚖️', label: 'MPFM vs Fiscal', text: 'Comparação entre o volume MPFM e o fiscal de óleo. Calcula o desvio percentual por ponto.' },
      { icon: '⛽', label: 'Balanço gás', text: 'Entradas (produção) vs saídas (fiscal + injeção + queima). Identifica desequilíbrios.' },
      { icon: '📝', label: 'Linhas brutas', text: 'Todas as linhas do Excel original para auditoria completa.' },
    ],
    buttons: [
      { icon: '🔍', label: 'Inspecionar arquivo', text: 'Analisa o arquivo Excel sem importar. Verifica estrutura e disponibilidade das abas.' },
      { icon: '⬇️', label: 'Importar', text: 'Importa o arquivo selecionado para o banco local. Dados ficam disponíveis nas sub-seções.' },
    ],
    tip: { kind: 'warn', icon: '⚠️', text: 'Importe o checklist <em>após</em> importar os exports ANP. Assim a comparação MPFM vs fiscal terá os dados mais completos.' },
  },

  technical: {
    icon: '🔧',
    title: 'Limites & CV',
    desc: 'Gerencia os limites técnicos dos pontos de medição (range calibrado, range PAM) e os snapshots de CV (Fator de Compressibilidade) utilizados nos cálculos de gás.',
    sections: [
      { icon: '📏', label: 'Limites configurados', text: 'Tabela com todos os limites vigentes: tag, família, métrica, unidade, range calibrado, range PAM e período de validade.' },
      { icon: '🧮', label: 'Snapshots de CV', text: 'Valores de fator de compressibilidade por data. Usados para corrigir volumes de gás em condições de referência.' },
      { icon: '📐', label: 'Incerteza', text: 'Parâmetros de incerteza de medição por ponto e família.' },
    ],
    buttons: [
      { icon: '💾', label: 'Salvar limite', text: 'Persiste um novo limite ou atualiza um existente para o ponto/família/métrica selecionados.' },
      { icon: '⚙️', label: 'Processar Limites/CV', text: 'Recalcula snapshots e aplica os novos limites às medições históricas. Pode demorar alguns minutos.' },
    ],
    tip: { kind: 'warn', icon: '⚠️', text: 'Alterar um limite não atualiza automaticamente as comparações. Execute <strong>Processar Limites/CV</strong> após salvar para propagar a mudança.' },
  },

  dossiers: {
    icon: '📁',
    title: 'Dossiês',
    desc: 'Consolidação completa por ponto de medição: medições fiscais, exports ANP, dados MPFM, propostas de correção e evidências arquivadas.',
    sections: [
      { icon: '🗃️', label: 'Cards por ponto', text: 'Cada card resume o estado de um ponto: horas medidas, volumes, status fiscal e alertas ativos.' },
      { icon: '📊', label: 'Tabela detalhada', text: 'Drill-down do ponto selecionado com todas as fontes de dado lado a lado.' },
      { icon: '📎', label: 'Evidências', text: 'Documentos anexados (PDFs, Excel) que suportam as medições ou decisões do período.' },
    ],
    tip: { kind: 'info', icon: 'ℹ️', text: 'O dossiê é o documento de referência para auditorias. Certifique-se de que todas as evidências relevantes estejam anexadas antes de fechar o período.' },
  },

  compare: {
    icon: '⚖️',
    title: 'Comparação ANP vs Staging',
    desc: 'Confronta os valores do export ANP com os dados do staging local. Identifica divergências de valor e registros que existem em apenas uma das bases.',
    sections: [
      { icon: '✅', label: 'matched', text: 'Registro presente nas duas bases com valores coincidentes (dentro da tolerância).' },
      { icon: '🔄', label: 'value_mismatch', text: 'Registro presente nas duas bases mas com valores diferentes. Requer análise.' },
      { icon: '📤', label: 'anp_only', text: 'Registro presente no ANP mas ausente no staging local. Pode indicar dado ANP não processado.' },
      { icon: '📥', label: 'staging_only', text: 'Registro presente no staging mas não enviado ao ANP. Pode indicar dado pendente de envio.' },
      { icon: '➖', label: 'not_comparable', text: 'Registro não pode ser comparado (formatos incompatíveis ou período fora de escopo).' },
    ],
    tip: { kind: 'warn', icon: '⚠️', text: 'Status <strong>value_mismatch</strong> é o mais crítico: o ANP tem um valor diferente do que o sistema local calculou. Investigue antes do fechamento.' },
  },

  calendar: {
    icon: '📅',
    title: 'Calendário',
    desc: 'Calendário de fechamento diário. Cada célula representa um dia e exibe o status de fechamento. Agrupa pendências por decisão requerida.',
    sections: [
      { icon: '🟢', label: 'complete', text: 'Dia fechado com todos os dados necessários presentes e validados.' },
      { icon: '🟡', label: 'partial', text: 'Dia com dados parciais: algumas horas ou volumes faltando.' },
      { icon: '🔴', label: 'attention', text: 'Dia com problemas críticos que precisam de ação antes do fechamento.' },
      { icon: '⚪', label: 'empty', text: 'Dia sem dados importados.' },
    ],
    buttons: [
      { icon: '✔', label: 'Resolver', text: 'Marca uma pendência como resolvida com a decisão registrada.' },
      { icon: '⏩', label: 'Deferir', text: 'Adia a resolução da pendência para uma data posterior.' },
      { icon: '✕', label: 'Ignorar', text: 'Descarta a pendência quando não requer ação (ex: dia sem produção planejada).' },
    ],
    tip: { kind: 'info', icon: 'ℹ️', text: 'Clique em um dia do calendário para ver as pendências específicas daquele dia e registrar decisões.' },
  },

  proposals: {
    icon: '📝',
    title: 'Propostas',
    desc: 'Fila de propostas de correção rastreáveis. Cada proposta registra uma mudança proposta (volume, período, parâmetro) com evidência e decisão auditável.',
    sections: [
      { icon: '⏳', label: 'pending_authorization', text: 'Proposta aguardando aprovação de um responsável.' },
      { icon: '✅', label: 'authorized', text: 'Proposta aprovada e aplicada.' },
      { icon: '❌', label: 'rejected', text: 'Proposta rejeitada com justificativa registrada.' },
      { icon: '⏸️', label: 'deferred', text: 'Proposta adiada para análise posterior.' },
      { icon: '🔒', label: 'closed', text: 'Proposta encerrada (aprovada + executada ou arquivada).' },
    ],
    buttons: [
      { icon: '✔', label: 'Autorizar', text: 'Aprova a proposta. Gera registro auditável com quem autorizou e quando.' },
      { icon: '✕', label: 'Rejeitar', text: 'Rejeita a proposta. Deve incluir justificativa.' },
      { icon: '⏸️', label: 'Deferir', text: 'Adia a decisão. A proposta volta para a fila com status "deferred".' },
      { icon: '🔒', label: 'Fechar', text: 'Encerra a proposta quando aprovada e executada.' },
    ],
    tip: { kind: 'warn', icon: '⚠️', text: 'Propostas <strong>pending_authorization</strong> são o gargalo do fechamento. Não feche o período com propostas críticas pendentes.' },
  },

  staging: {
    icon: '🗄️',
    title: 'Staging — Registros SQLite',
    desc: 'Navegador de baixo nível dos registros persistidos no banco SQLite local. Use para auditoria técnica e verificação de estado interno.',
    sections: [
      { icon: '⚖️', label: 'comparisons', text: 'Comparações entre o valor local e o ANP por ponto/dia.' },
      { icon: '🔔', label: 'alerts', text: 'Alertas gerados automaticamente por regras de validação.' },
      { icon: '📝', label: 'proposals', text: 'Propostas de correção em todos os estados.' },
      { icon: '📎', label: 'evidence', text: 'Evidências anexadas a pontos e propostas.' },
      { icon: '📍', label: 'points', text: 'Pontos de medição cadastrados no contrato.' },
      { icon: '📅', label: 'calendar', text: 'Registros de calendário por dia.' },
      { icon: '⏳', label: 'pendencies', text: 'Pendências abertas por dia e tipo.' },
    ],
    tip: { kind: 'warn', icon: '⚠️', text: 'Esta tela é para <strong>diagnóstico técnico</strong>. Não edite registros aqui diretamente — use as telas específicas (Propostas, Calendário, etc.).' },
  },
};

// ---------------------------------------------------------------------------
// Estado e referências DOM
// ---------------------------------------------------------------------------
let _helpOpen = false;
let _helpCurrentTab = 'overview';

function _helpEl(id) { return document.getElementById(id); }

// ---------------------------------------------------------------------------
// Render de seção de ajuda
// ---------------------------------------------------------------------------
function _renderHelpContent(tabKey) {
  const body = _helpEl('poHelpBody');
  const headerTitle = _helpEl('poHelpHeaderTitle');
  const headerIcon = _helpEl('poHelpHeaderIcon');
  const nav = _helpEl('poHelpNav');
  if (!body) return;

  const data = PO_HELP_CONTENT[tabKey] || PO_HELP_CONTENT['overview'];
  _helpCurrentTab = tabKey;

  // Atualiza cabeçalho
  if (headerIcon) headerIcon.textContent = data.icon || '❓';
  if (headerTitle) headerTitle.textContent = data.title || 'Ajuda';

  // Atualiza nav pills
  if (nav) {
    nav.querySelectorAll('.po-help-nav__btn').forEach((btn) => {
      btn.classList.toggle('po-help-nav__btn--active', btn.dataset.helpTab === tabKey);
    });
  }

  // Monta HTML do corpo
  let html = '';

  // Descrição principal
  html += `<div class="po-help-section">`;
  html += `<div class="po-help-section__badge">📖 Sobre esta tela</div>`;
  html += `<p class="po-help-section__desc">${poHelpEscape(data.desc || '')}</p>`;
  html += `</div>`;

  // Seções/elementos
  if (data.sections && data.sections.length) {
    html += `<div class="po-help-section">`;
    html += `<div class="po-help-section__badge">🗂️ O que cada item significa</div>`;
    html += `<ul class="po-help-list">`;
    for (const s of data.sections) {
      html += `<li class="po-help-list__item">
        <span class="po-help-list__icon">${poHelpEscape(s.icon || '•')}</span>
        <div class="po-help-list__content">
          <div class="po-help-list__label">${poHelpEscape(s.label)}</div>
          <div class="po-help-list__text">${poHelpEscape(s.text)}</div>
        </div>
      </li>`;
    }
    html += `</ul></div>`;
  }

  // Botões
  if (data.buttons && data.buttons.length) {
    html += `<div class="po-help-section">`;
    html += `<div class="po-help-section__badge">🖱️ Botões e controles</div>`;
    html += `<ul class="po-help-list">`;
    for (const b of data.buttons) {
      html += `<li class="po-help-list__item">
        <span class="po-help-list__icon">${poHelpEscape(b.icon || '🔘')}</span>
        <div class="po-help-list__content">
          <div class="po-help-list__label">${poHelpEscape(b.label)}</div>
          <div class="po-help-list__text">${poHelpEscape(b.text)}</div>
        </div>
      </li>`;
    }
    html += `</ul></div>`;
  }

  // Controles (radar)
  if (data.controls && data.controls.length) {
    html += `<div class="po-help-section">`;
    html += `<div class="po-help-section__badge">🎛️ Filtros e controles</div>`;
    html += `<ul class="po-help-list">`;
    for (const c of data.controls) {
      html += `<li class="po-help-list__item">
        <span class="po-help-list__icon">${poHelpEscape(c.icon || '🔘')}</span>
        <div class="po-help-list__content">
          <div class="po-help-list__label">${poHelpEscape(c.label)}</div>
          <div class="po-help-list__text">${poHelpEscape(c.text)}</div>
        </div>
      </li>`;
    }
    html += `</ul></div>`;
  }

  // Passos
  if (data.steps && data.steps.length) {
    html += `<div class="po-help-section">`;
    html += `<div class="po-help-section__badge">📋 Como usar</div>`;
    html += `<ol class="po-help-steps">`;
    for (const step of data.steps) {
      html += `<li class="po-help-steps__item"><span>${poHelpEscape(step)}</span></li>`;
    }
    html += `</ol></div>`;
  }

  // Dica
  if (data.tip) {
    html += `<div class="po-help-tip po-help-tip--${poHelpEscape(data.tip.kind || 'info')}">
      <span class="po-help-tip__icon">${poHelpEscape(data.tip.icon || 'ℹ️')}</span>
      <span>${poHelpEscape(data.tip.text)}</span>
    </div>`;
  }

  body.innerHTML = html;
  body.scrollTop = 0;
}

// ---------------------------------------------------------------------------
// Abrir / fechar drawer
// ---------------------------------------------------------------------------
function poHelpOpen(tabKey) {
  const drawer = _helpEl('poHelpDrawer');
  const overlay = _helpEl('poHelpOverlay');
  const fab = _helpEl('poHelpFab');
  if (!drawer) return;

  const key = tabKey || (typeof painelOperadorState !== 'undefined' ? painelOperadorState.activeTab : 'overview');
  _renderHelpContent(key);

  drawer.classList.add('po-help-drawer--open');
  overlay.classList.add('po-help-overlay--open');
  fab && fab.classList.add('po-help-fab--active');
  drawer.setAttribute('aria-hidden', 'false');
  _helpOpen = true;
  // Foco no botão fechar
  const closeBtn = _helpEl('poHelpClose');
  if (closeBtn) setTimeout(() => closeBtn.focus(), 80);
}

function poHelpClose() {
  const drawer = _helpEl('poHelpDrawer');
  const overlay = _helpEl('poHelpOverlay');
  const fab = _helpEl('poHelpFab');
  if (!drawer) return;
  drawer.classList.remove('po-help-drawer--open');
  overlay.classList.remove('po-help-overlay--open');
  fab && fab.classList.remove('po-help-fab--active');
  drawer.setAttribute('aria-hidden', 'true');
  _helpOpen = false;
  fab && fab.focus();
}

// ---------------------------------------------------------------------------
// Mostrar/esconder FAB conforme página ativa
// ---------------------------------------------------------------------------
function poHelpSyncFabVisibility() {
  const fab = _helpEl('poHelpFab');
  if (!fab) return;
  // setPage() em app.main.js adiciona classe 'active' na .page correspondente
  const pageEl = document.getElementById('page-painel-operador');
  const visible = pageEl && pageEl.classList.contains('active');
  fab.style.display = visible ? 'flex' : 'none';
  // Fecha o drawer se saiu da página
  if (!visible && _helpOpen) poHelpClose();
}

// ---------------------------------------------------------------------------
// Inicialização
// ---------------------------------------------------------------------------
function initPainelOperadorHelp() {
  const fab = _helpEl('poHelpFab');
  const closeBtn = _helpEl('poHelpClose');
  const overlay = _helpEl('poHelpOverlay');
  const drawer = _helpEl('poHelpDrawer');
  const nav = _helpEl('poHelpNav');

  if (!fab || !drawer) return;

  // FAB – abre o drawer
  fab.addEventListener('click', () => {
    if (_helpOpen) poHelpClose();
    else poHelpOpen();
  });

  // Botão fechar dentro do drawer
  closeBtn && closeBtn.addEventListener('click', poHelpClose);

  // Overlay – clique fora fecha
  overlay && overlay.addEventListener('click', poHelpClose);

  // Tecla ESC fecha
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && _helpOpen) poHelpClose();
  });

  // Nav pills – permite escolher qualquer aba manualmente
  nav && nav.addEventListener('click', (e) => {
    const btn = e.target.closest('.po-help-nav__btn');
    if (btn && btn.dataset.helpTab) _renderHelpContent(btn.dataset.helpTab);
  });

  // Quando o tab do Painel muda, atualiza o conteúdo de ajuda automaticamente
  // Intercepta poSetActiveTab se disponível
  if (typeof poSetActiveTab === 'function') {
    const _origSetTab = poSetActiveTab;
    window.poSetActiveTab = function(tab) {
      _origSetTab(tab);
      // Se drawer aberto, atualiza para a aba nova
      if (_helpOpen) _renderHelpContent(tab);
    };
  }

  // Observa mudanças de página via hash (app.main.js usa history.replaceState + hash)
  window.addEventListener('hashchange', poHelpSyncFabVisibility);
  // MutationObserver como fallback (quando hash não muda mas classe muda)
  const pageEls = document.querySelectorAll('.page');
  if ('MutationObserver' in window) {
    const obs = new MutationObserver(poHelpSyncFabVisibility);
    pageEls.forEach((p) => obs.observe(p, { attributes: true, attributeFilter: ['class'] }));
  }

  // Estado inicial
  poHelpSyncFabVisibility();
}

// Aguarda DOM pronto
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initPainelOperadorHelp);
} else {
  initPainelOperadorHelp();
}
