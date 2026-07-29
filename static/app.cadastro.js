'use strict';

function cadEscape(value) {
  return String(value ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
}

// ── CADASTRO ─────────────────────────────────────────────────────────────────
let cadData = { subsea:[], topside:[] };
const CAD_FIELDS = ['Bank','Loop','Tipo','TAG','Instrumento','Ativo'];

// Cadastro field mapping: cadastro.json keys → display labels
const CAD_FIELD_MAP = {
  bank_code: 'Banco', sistema: 'TAG/Sistema', loop: 'Loop', fluido: 'Fluido',
  tecnologia: 'Tecnologia', tag_associado: 'Instrumento', stream: 'Stream',
  nome_anp: 'Nome ANP', poco_equinor: 'Poço', chega_riser: 'Riser'
};
const CAD_SUBSEA_FIELDS = ['bank_code','sistema','loop','fluido','tecnologia','tag_associado','nome_anp'];
const CAD_TOPSIDE_FIELDS = ['bank_code','sistema','loop','fluido','tecnologia','tag_associado'];

async function loadCadastro() {
  setLoading('page-cadastro', true);
  try {
    const d = await j(`${API}/cadastro`).catch(() => ({}));
    cadData = {
      subsea:  (d.banks_subsea  || d.subsea  || []),
      topside: (d.banks_topside || d.topside || [])
    };
    renderCad('subsea'); renderCad('topside');
    renderSepInstruments(d);
  } finally {
    setLoading('page-cadastro', false);
  }
}

function renderSepInstruments(d) {
  const panel = document.getElementById('cadSepPanel');
  if (!panel) return;
  // Separator instruments = tag_associado fields from all banks (FCS instruments)
  const allBanks = [...(d.banks_subsea||[]), ...(d.banks_topside||[])];
  const fcsTag = d.fcs_tag_geral || '';  // single valve tag
  const loopMap = d.banco_loop || {};
  const nameMap = d.banco_nome_completo || {};
  if (!allBanks.length) {
    panel.innerHTML = '<div class="muted" style="font-size:12px">Nenhum instrumento cadastrado. Verifique o arquivo <code>cadastro.json</code>.</div>';
    return;
  }
  // Show all banks with their associated instruments (tag_associado = flowmeter tag)
  panel.innerHTML = `
    <div style="font-size:11px;color:var(--muted);margin-bottom:8px">
      TAG geral FCS: <code style="color:var(--accent);background:var(--panel2);padding:1px 6px;border-radius:3px">${fcsTag||'—'}</code>
      &nbsp;·&nbsp; Todos os flowmeters cadastrados nos bancos:
    </div>
    <table class="table" style="font-size:12px">
      <thead><tr><th>Banco</th><th>Nome</th><th>Loop</th><th>TAG/Sistema</th><th>Instrumento (TAG)</th><th>Tipo</th><th>Status</th><th>ANP</th></tr></thead>
      <tbody>${allBanks.map(r => {
        const ativo = r.ativo !== false;
        const anp   = r.aprovado_anp === true;
        const statusBadge = ativo
          ? `<span style="font-size:10px;padding:2px 7px;border-radius:10px;background:#c07a00;color:#fff;font-weight:600">EM OPERAÇÃO</span>`
          : `<span style="font-size:10px;padding:2px 7px;border-radius:10px;background:#555;color:#fff;font-weight:600">INATIVO</span>`;
        const anpBadge = anp
          ? `<span style="font-size:10px;padding:2px 7px;border-radius:10px;background:var(--green);color:#fff;font-weight:600">✔ APROVADO</span>`
          : `<span style="font-size:10px;padding:2px 7px;border-radius:10px;background:var(--panel2);color:var(--muted);font-weight:600">—</span>`;
        return `<tr style="${ativo?'':'opacity:0.4'}">
          <td>${tagChip(cadEscape(r.bank_code||r.bank||''))}</td>
          <td style="font-size:11px">${cadEscape(nameMap[r.bank_code||r.bank] || r.bank||'')}</td>
          <td style="font-size:11px;color:var(--muted)">${cadEscape(r.loop||loopMap[r.bank_code]||'')}</td>
          <td class="mono" style="color:var(--accent)">${cadEscape(r.sistema||'')}</td>
          <td class="mono" style="color:var(--green)">${cadEscape(r.tag_associado||'')}</td>
          <td style="font-size:11px;color:var(--muted)">${cadEscape(r.tecnologia||r.fluido||'')}</td>
          <td>${statusBadge}</td>
          <td>${anpBadge}</td>
        </tr>`;
      }).join('')}
      </tbody>
    </table>`;
}

function renderCad(type) {
  const rows = cadData[type] || [];
  const section = type === 'subsea' ? 'banks_subsea' : 'banks_topside';
  document.getElementById(`c${type==='subsea'?'Sub':'Top'}Count`).textContent = `(${rows.length})`;
  const prefix = type === 'subsea' ? 'Sub' : 'Top';
  const fields = type === 'subsea' ? CAD_SUBSEA_FIELDS : CAD_TOPSIDE_FIELDS;
  document.getElementById(`c${prefix}Table`).innerHTML = rows.length ? `
    <table class="table" style="min-width:600px">
      <thead><tr>${fields.map(f=>`<th>${cadEscape(CAD_FIELD_MAP[f]||f)}</th>`).join('')}<th>Status</th><th>ANP</th><th></th></tr></thead>
      <tbody>${rows.map((r,i) => {
        const ativo = r.ativo !== false;
        const anp   = r.aprovado_anp === true;
        const statusBadge = ativo
          ? `<span style="font-size:10px;padding:2px 7px;border-radius:10px;background:#c07a00;color:#fff;font-weight:600">EM OPERAÇÃO</span>`
          : `<span style="font-size:10px;padding:2px 7px;border-radius:10px;background:#555;color:#fff;font-weight:600">INATIVO</span>`;
        const anpBadge = anp
          ? `<span style="font-size:10px;padding:2px 7px;border-radius:10px;background:var(--green);color:#fff;font-weight:600">✔ APROVADO</span>`
          : `<span style="font-size:10px;padding:2px 7px;border-radius:10px;background:var(--panel2);color:var(--muted);font-weight:600">—</span>`;
        const btnAtivo = `<button onclick="toggleCadAtivo('${section}',${i})" style="font-size:10px;padding:2px 8px;border-radius:4px;border:1px solid var(--border);background:transparent;color:var(--text);cursor:pointer">${ativo?'Desativar':'Ativar'}</button>`;
        const btnAnp = ativo
          ? `<button onclick="toggleCadAnp('${section}',${i})" style="font-size:10px;padding:2px 8px;border-radius:4px;border:1px solid var(--border);background:transparent;color:var(--text);cursor:pointer">${anp?'Remover ANP':'Aprovar ANP'}</button>`
          : `<button disabled style="font-size:10px;padding:2px 8px;border-radius:4px;border:1px solid var(--border);background:transparent;color:var(--muted);cursor:not-allowed">Aprovar ANP</button>`;
        const rowStyle = ativo ? '' : 'opacity:0.45;';
        return `<tr style="${rowStyle}">
          ${fields.map(f => `<td style="font-size:12px;min-width:70px">${cadEscape(r[f]||'—')}</td>`).join('')}
          <td>${statusBadge}</td>
          <td>${anpBadge}</td>
          <td style="white-space:nowrap">${btnAtivo}&nbsp;${btnAnp}</td>
        </tr>`;
      }).join('')}</tbody>
    </table>` :
    `<div class="muted" style="font-size:12px;padding:12px 0">Nenhum banco cadastrado.</div>`;
}
window.toggleCadAtivo = async (section, index) => {
  const res = await j(`${API}/cadastro/toggle-ativo`, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({section, index})});
  if (res.ok !== undefined) {
    const type = section === 'banks_subsea' ? 'subsea' : 'topside';
    cadData[type][index].ativo = res.ativo;
    renderCad(type);
  }
};
window.toggleCadAnp = async (section, index) => {
  const res = await j(`${API}/cadastro/toggle-anp`, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({section, index})});
  if (res.ok !== undefined) {
    const type = section === 'banks_subsea' ? 'subsea' : 'topside';
    cadData[type][index].aprovado_anp = res.aprovado_anp;
    renderCad(type);
  }
};
window.editCad = (type, i, field, val) => {
  if (!cadData[type][i]) cadData[type][i] = {};
  cadData[type][i][field] = val;
};
window.addCadRow = type => {
  const empty = Object.fromEntries(CAD_FIELDS.map(f => [f,'']));
  cadData[type].push(empty); renderCad(type);
};
window.delCadRow = (type, i) => { cadData[type].splice(i,1); renderCad(type); };
async function saveCadastro() {
  await j(`${API}/cadastro`, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(cadData)});
  alert('Cadastro salvo com sucesso!');
}


// ── Cadastro coverage check ──────────────────────────────────────────────────
window.checkCadastroVsData = async () => {
  const panel = document.getElementById('cadCoveragePanel');
  panel.innerHTML = '<span style="color:var(--muted)">Carregando dados do banco…</span>';
  // Get all banks/tags from DB
  const d = await j(`${API}/ops/mpfm-data?date_from=2020-01-01&date_to=2030-12-31&row_kind=daily&limit=9999`);
  const dbBankTags = {};
  (d.rows||[]).forEach(r => {
    if (r.bank && r.tag) {
      dbBankTags[r.bank] = dbBankTags[r.bank] || new Set();
      dbBankTags[r.bank].add(r.tag);
    }
  });
  // Get cadastro
  const cad = await j(`${API}/cadastro`);
  const cadTags = {};
  ([...(cad.banks_subsea||[]), ...(cad.banks_topside||[])]).forEach(e => {
    if (e.ativo === false) return;  // ignorar inativos na cobertura
    const bc = e.bank_code; const tag = e.sistema;
    if (bc && tag) { cadTags[bc] = cadTags[bc] || new Set(); cadTags[bc].add(tag); }
  });
  const allBanks = [...new Set([...Object.keys(dbBankTags), ...Object.keys(cadTags)])].sort();
  let html = '<div style="display:grid;grid-template-columns:auto 1fr;gap:10px 20px;margin-top:6px">';
  let totalIssues = 0;
  for (const bank of allBanks) {
    const inDb  = dbBankTags[bank] || new Set();
    const inCad = cadTags[bank]    || new Set();
    const unknown = [...inDb].filter(t => t && !inCad.has(t));
    const missing  = [...inCad].filter(t => t && !inDb.has(t));
    const ok = unknown.length === 0 && missing.length === 0;
    totalIssues += unknown.length + missing.length;
    const unknownEsc = unknown.map(t => cadEscape(t)).join(', ');
    const missingEsc  = missing.map(t => cadEscape(t)).join(', ');
    html += `<strong style="color:var(--accent)">${cadEscape(bank)}</strong>
      <div>
        <span style="color:${ok?'var(--green)':'var(--amber)'}">
          ${ok ? '✅ Todos os TAGs cadastrados foram encontrados' : ''}
          ${unknown.length ? `⚠️ <strong>No PDF mas não no cadastro:</strong> ${unknownEsc}` : ''}
          ${missing.length  ? `  ℹ️ <strong>No cadastro mas não encontrado ainda:</strong> ${missingEsc}` : ''}
        </span>
      </div>`;
  }
  html += '</div>';
  if (allBanks.length === 0) html = '<span style="color:var(--muted)">Nenhum dado no banco ainda. Processe arquivos primeiro.</span>';
  else html = `<div style="margin-bottom:10px;color:${totalIssues?'var(--amber)':'var(--green)'}">
    <strong>${totalIssues === 0 ? '✅ Cadastro consistente com os dados' : `⚠️ ${totalIssues} inconsistência(s) encontrada(s)`}</strong>
  </div>` + html;
  panel.innerHTML = html;
};

