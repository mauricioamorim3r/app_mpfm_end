'use strict';

const API = `${window.location.origin}/api`;
const DEFAULT_APP_TITLE = 'PulseFlow Ops Studio';
const DEFAULT_THEME_MODE = 'dark';
const BUILTIN_ICONS = {
  summary: '/static/icons/summary.png',
  upload: '/static/icons/upload.png',
  mpfm: '/static/icons/mpfm.png',
  separator: '/static/icons/separator.png',
  cards: '/static/icons/cards.png',
  charts: '/static/icons/charts.png',
  alerts: '/static/icons/alerts.png',
  deadlines: '/static/icons/deadlines.png',
  cadastro: '/static/icons/cadastro.png',
  recon: '/static/icons/recon.png',
  export: '/static/icons/export.png',
  oil: '/static/icons/oil.png',
  gas: '/static/icons/gas.png',
  water: '/static/icons/water.png',
  hc: '/static/icons/hc.png',
  barrel: '/static/icons/barrel.png',
  boe: '/static/icons/boe.png',
  sep_gas: '/static/icons/sep_gas.png',
  sep_hc: '/static/icons/sep_hc.png',
  pipeline: '/static/icons/pipeline.png',
};

function normalizeThemeMode(value) {
  return String(value || '').toLowerCase() === 'light' ? 'light' : DEFAULT_THEME_MODE;
}

function themeToggleLabel(mode) {
  return mode === 'light' ? '◑ Escuro' : '◐ Claro';
}

function syncThemeControls(mode) {
  const normalized = normalizeThemeMode(mode);
  const body = document.body;
  if (body) body.dataset.theme = normalized;
  const toggle = document.getElementById('btnThemeMode');
  if (toggle) {
    toggle.textContent = themeToggleLabel(normalized);
    toggle.setAttribute('aria-pressed', String(normalized === 'light'));
    toggle.setAttribute('title', normalized === 'light' ? 'Alternar para modo escuro' : 'Alternar para modo claro');
  }
  const select = document.getElementById('cfgThemeMode');
  if (select) select.value = normalized;
}

function applyThemePreference(mode) {
  const normalized = normalizeThemeMode(mode);
  if (typeof state !== 'undefined') {
    state.prefs = state.prefs || {};
    state.prefs.theme_mode = normalized;
  }
  syncThemeControls(normalized);
  return normalized;
}

async function persistThemePreference(mode) {
  const normalized = applyThemePreference(mode);
  const prefs = typeof state !== 'undefined' ? (state.prefs || {}) : {};
  const payload = {...prefs, theme_mode: normalized};
  await j(`${API}/user-prefs`, {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify(payload),
  });
  if (typeof state !== 'undefined') state.prefs = payload;
  return normalized;
}

const _apiCache = new Map();
const _apiCacheTtlMs = 10000; // 10 segundos

function _apiCacheKey(url, opts) {
  const method = (opts && opts.method) || 'GET';
  if (method.toUpperCase() !== 'GET') return null;
  return url;
}

function invalidateApiCache() {
  _apiCache.clear();
}

async function j(url, opts) {
  const key = _apiCacheKey(url, opts);
  if (key) {
    const cached = _apiCache.get(key);
    if (cached && Date.now() - cached.at < _apiCacheTtlMs) {
      return cached.data;
    }
  }
  const response = await fetch(url, opts);
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `HTTP ${response.status}`);
  }
  const data = await response.json();
  if (key) _apiCache.set(key, { data, at: Date.now() });
  return data;
}

async function loadPrefs() {
  const fallback = { prefs: { selected_metrics: [] }, all_metrics: [] };
  const d = await j(`${API}/user-prefs`).catch(() => fallback);
  if (typeof state !== 'undefined') {
    state.prefs = d.prefs || {};
    state.allMetrics = d.all_metrics || [];
    state.selectedCols = state.prefs.selected_metrics || [];
    if (typeof applyThemePreference === 'function') applyThemePreference(state.prefs.theme_mode);
  }
  if (typeof buildColCheckGrid === 'function') buildColCheckGrid();
  return d;
}

const fmt = v => v == null ? '—' : new Intl.NumberFormat('pt-BR', {maximumFractionDigits:3}).format(v);

const fmtDate = d => {
  if (!d) return '—';
  const m = String(d).match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (m) return `${m[3]}/${m[2]}/${m[1]}`;
  if (/^\d{2}\/\d{2}\/\d{4}/.test(d)) return d;
  return d;
};

function parseBrDateToIso(value) {
  const raw = String(value || '').trim();
  if (!raw) return '';
  const iso = raw.match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (iso) return `${iso[1]}-${iso[2]}-${iso[3]}`;
  const br = raw.match(/^(\d{2})\/(\d{2})\/(\d{4})$/);
  if (!br) return '';
  const dd = Number(br[1]);
  const mm = Number(br[2]);
  const yy = Number(br[3]);
  if (!yy || mm < 1 || mm > 12 || dd < 1 || dd > 31) return '';
  const dt = new Date(yy, mm - 1, dd);
  if (dt.getFullYear() !== yy || dt.getMonth() !== mm - 1 || dt.getDate() !== dd) return '';
  return `${yy}-${String(mm).padStart(2, '0')}-${String(dd).padStart(2, '0')}`;
}

function refreshDateInputDisplay(root = document) {
  root.querySelectorAll('input[data-br-date="1"]').forEach((input) => {
    const iso = parseBrDateToIso(input.dataset.isoValue || input.value || '');
    input.dataset.isoValue = iso;
    if (document.activeElement === input) return;
    if (input.type !== 'text') input.type = 'text';
    input.inputMode = 'numeric';
    input.placeholder = 'dd/mm/aaaa';
    input.value = iso ? fmtDate(iso) : '';
  });
}

function enhanceBrazilianDateInputs(root = document) {
  root.querySelectorAll('input[type="date"]').forEach((input) => {
    if (input.dataset.brDate === '1') return;
    input.dataset.brDate = '1';
    input.dataset.isoValue = parseBrDateToIso(input.value || '');
    input.autocomplete = 'off';
    input.addEventListener('focus', () => {
      const iso = parseBrDateToIso(input.dataset.isoValue || input.value || '');
      input.type = 'date';
      input.value = iso;
      input.dataset.isoValue = iso;
    });
    input.addEventListener('change', () => {
      input.dataset.isoValue = parseBrDateToIso(input.value || '');
    });
    input.addEventListener('blur', () => {
      const iso = parseBrDateToIso(input.value || input.dataset.isoValue || '');
      input.dataset.isoValue = iso;
      input.type = 'text';
      input.inputMode = 'numeric';
      input.placeholder = 'dd/mm/aaaa';
      input.value = iso ? fmtDate(iso) : '';
    });
  });
  refreshDateInputDisplay(root);
}

function tagChip(s) {
  return `<span class="tag-chip">${escapeHtml(s)}</span>`;
}

function badge(s) {
  const mapping = {
    ok:['OK','ok'],
    attention:['Atenção','warn'],
    missing:['Faltando','err'],
    error:['Crítico','err'],
    warn:['Atenção','warn'],
    info:['Info','ok'],
    partial:['Parcial','warn'],
    empty:['Sem dado','warn'],
  };
  const [text, css] = mapping[s] || [s, 'warn'];
  return `<span class="badge ${css}">${escapeHtml(text)}</span>`;
}

function hc(p) {
  return p == null ? 'health-warn' : p <= 5 ? 'health-ok' : p <= 10 ? 'health-warn' : 'health-err';
}

function getMonthRange(month) {
  if (!month) return {from:'', to:''};
  const [yr, mo] = month.split('-').map(Number);
  const last = new Date(yr, mo, 0).getDate();
  return {from:`${month}-01`, to:`${month}-${String(last).padStart(2,'0')}`};
}

function resolveIconSource(value) {
  const raw = String(value || '').trim();
  if (!raw) return '';
  if (BUILTIN_ICONS[raw]) return BUILTIN_ICONS[raw];
  if (/^https?:\/\//i.test(raw) || raw.startsWith('/static/')) return raw;
  if (raw.toLowerCase().endsWith('.png')) return `/static/icons/${raw}`;
  return '';
}

function renderIconMarkup(value, fallback = '📊', cls = 'ui-icon') {
  const src = resolveIconSource(value);
  if (src) return `<img class="${cls}" src="${src}" alt="">`;
  const content = String(value || fallback || '').trim() || fallback;
  return `<span class="${cls} ${cls}--emoji">${content}</span>`;
}

function renderBranding() {
  const prefs = state.prefs || {};
  const title = prefs.app_title || DEFAULT_APP_TITLE;
  const sub = prefs.app_subtitle || 'Local · editável';
  const titleEl = document.getElementById('appBrandName');
  const subEl = document.getElementById('appBrandSub');
  if (titleEl) titleEl.textContent = title;
  if (subEl) subEl.textContent = sub;
}

window.editAppBranding = async () => {
  const currentTitle = (state.prefs && state.prefs.app_title) || DEFAULT_APP_TITLE;
  const currentSub = (state.prefs && state.prefs.app_subtitle) || 'Local · editável';
  const title = prompt('Nome da aplicação:', currentTitle);
  if (title === null) return;
  const subtitle = prompt('Subtítulo da aplicação:', currentSub);
  if (subtitle === null) return;
  state.prefs = state.prefs || {};
  state.prefs.app_title = title.trim() || DEFAULT_APP_TITLE;
  state.prefs.app_subtitle = subtitle.trim() || 'Local · editável';
  await j(`${API}/user-prefs`, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(state.prefs)}).catch(()=>null);
  renderBranding();
};

window.renderIconMarkup = renderIconMarkup;
window.renderBranding = renderBranding;
window.normalizeThemeMode = normalizeThemeMode;
window.applyThemePreference = applyThemePreference;
window.persistThemePreference = persistThemePreference;
window.syncThemeControls = syncThemeControls;
window.enhanceBrazilianDateInputs = enhanceBrazilianDateInputs;
window.refreshDateInputDisplay = refreshDateInputDisplay;

// ── Accessible modal shell ───────────────────────────────────────────────────
const MODAL_FOCUS_SELECTOR = [
  'a[href]',
  'button:not([disabled])',
  'input:not([disabled]):not([type="hidden"])',
  'select:not([disabled])',
  'textarea:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
].join(',');

let activeAppModal = null;
let modalReturnFocus = null;

function getModalFocusables(modal) {
  return Array.from(modal.querySelectorAll(MODAL_FOCUS_SELECTOR))
    .filter(el => !el.hasAttribute('disabled') && el.getAttribute('aria-hidden') !== 'true' && el.offsetParent !== null);
}

function ensureAppModalA11y(modal) {
  if (!modal || modal.dataset.modalA11yReady === '1') return;
  modal.dataset.modalA11yReady = '1';
  modal.setAttribute('role', modal.getAttribute('role') || 'dialog');
  modal.setAttribute('aria-modal', 'true');
  modal.setAttribute('aria-hidden', modal.classList.contains('show') ? 'false' : 'true');
  const box = modal.querySelector('.modalbox') || modal.firstElementChild;
  if (box && !box.hasAttribute('tabindex')) box.setAttribute('tabindex', '-1');
  if (!modal.hasAttribute('aria-labelledby')) {
    const title = modal.querySelector('h1,h2,h3,h4,h5,h6');
    if (title) {
      title.id = title.id || `${modal.id || 'modal'}-title`;
      modal.setAttribute('aria-labelledby', title.id);
    }
  }
}

function handleAppModalOpen(modal) {
  ensureAppModalA11y(modal);
  if (activeAppModal === modal) return;
  modalReturnFocus = document.activeElement instanceof HTMLElement ? document.activeElement : modalReturnFocus;
  activeAppModal = modal;
  modal.setAttribute('aria-hidden', 'false');
  const focusTarget = modal.querySelector('[autofocus]') || getModalFocusables(modal)[0] || modal.querySelector('.modalbox') || modal;
  requestAnimationFrame(() => focusTarget?.focus({preventScroll: true}));
}

function handleAppModalClose(modal) {
  ensureAppModalA11y(modal);
  modal.setAttribute('aria-hidden', 'true');
  if (activeAppModal === modal) {
    activeAppModal = Array.from(document.querySelectorAll('.modal.show')).pop() || null;
    if (activeAppModal) {
      handleAppModalOpen(activeAppModal);
      return;
    }
    const target = modalReturnFocus;
    modalReturnFocus = null;
    if (target && document.contains(target)) requestAnimationFrame(() => target.focus({preventScroll: true}));
  }
  if (modal.dataset.removeOnClose === 'true' && document.contains(modal)) {
    requestAnimationFrame(() => modal.remove());
  }
}

function openAppModal(modalOrId) {
  const modal = typeof modalOrId === 'string' ? document.getElementById(modalOrId) : modalOrId;
  if (!modal) return;
  ensureAppModalA11y(modal);
  modal.classList.add('show');
  handleAppModalOpen(modal);
}

function closeAppModal(modalOrId) {
  const modal = typeof modalOrId === 'string' ? document.getElementById(modalOrId) : modalOrId;
  if (!modal) return;
  modal.classList.remove('show');
  handleAppModalClose(modal);
}

function bindAccessibleModals(root = document) {
  root.querySelectorAll('.modal').forEach((modal) => {
    ensureAppModalA11y(modal);
    if (modal.dataset.modalObserverReady === '1') return;
    modal.dataset.modalObserverReady = '1';
    const observer = new MutationObserver(() => {
      if (modal.classList.contains('show')) handleAppModalOpen(modal);
      else handleAppModalClose(modal);
    });
    observer.observe(modal, {attributes: true, attributeFilter: ['class']});
  });
}

document.addEventListener('keydown', (event) => {
  if (!activeAppModal || !activeAppModal.classList.contains('show')) return;
  if (event.key === 'Escape') {
    event.preventDefault();
    closeAppModal(activeAppModal);
    return;
  }
  if (event.key !== 'Tab') return;
  const focusables = getModalFocusables(activeAppModal);
  if (!focusables.length) {
    event.preventDefault();
    (activeAppModal.querySelector('.modalbox') || activeAppModal).focus();
    return;
  }
  const first = focusables[0];
  const last = focusables[focusables.length - 1];
  if (event.shiftKey && document.activeElement === first) {
    event.preventDefault();
    last.focus();
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault();
    first.focus();
  }
}, true);

document.addEventListener('focusin', (event) => {
  if (!activeAppModal || !activeAppModal.classList.contains('show')) return;
  if (activeAppModal.contains(event.target)) return;
  const focusTarget = getModalFocusables(activeAppModal)[0] || activeAppModal.querySelector('.modalbox') || activeAppModal;
  focusTarget.focus({preventScroll: true});
});

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => bindAccessibleModals(document), {once: true});
} else {
  bindAccessibleModals(document);
}

window.openAppModal = openAppModal;
window.closeAppModal = closeAppModal;
window.bindAccessibleModals = bindAccessibleModals;

function prefersReducedMotion() {
  return window.matchMedia?.('(prefers-reduced-motion: reduce)').matches || false;
}
window.prefersReducedMotion = prefersReducedMotion;

// ── HTML escaping ─────────────────────────────────────────────────────────────
function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, (c) =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c])
  );
}
window.escapeHtml = escapeHtml;

// Safe escape for JS string literals embedded inside HTML attributes (handles backtick bypass)
function jsStr(s) {
  return String(s ?? '')
    .replace(/\\/g, '\\\\')
    .replace(/'/g, "\\'")
    .replace(/`/g, '\\`')
    .replace(/"/g, '\\"')
    .replace(/\n/g, '\\n')
    .replace(/\r/g, '\\r')
    .replace(/</g, '\\x3C')
    .replace(/>/g, '\\x3E');
}
window.jsStr = jsStr;

// ── Loading state ─────────────────────────────────────────────────────────────
function setLoading(elOrId, on) {
  const el = typeof elOrId === 'string' ? document.getElementById(elOrId) : elOrId;
  if (!el) return;
  el.setAttribute('aria-busy', String(on));
  el.classList.toggle('is-loading', !!on);
}
window.setLoading = setLoading;
