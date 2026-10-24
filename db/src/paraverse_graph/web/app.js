// Knowledge base browser: the shell (sidebar, top bar, theme), the hash router,
// keyboard shortcuts, live updates over server-sent events, and embed messaging.
// Views live in ./js/; this file only wires them together.

import { api, state } from './js/api.js';
import { datasetSelectionPending, installDatasetSelector, refreshDatasetSelector } from './js/datasets.js';
import { closeMenus, fill, fmtNumber, h, hideTooltip, installCopy, installTooltips, relativeAge, wireMenu } from './js/dom.js';
import { icon } from './js/icons.js';
import { hideCard, installPopovers } from './js/popover.js';
import { mountRecord } from './js/record.js';
import { sameGraphVersion, tableRouteAfterReload, watchGraphVersion } from './js/reconcile.js';
import { go, parseRoute, setRenderer } from './js/router.js';
import { closePalette, mountSearch, openPalette, paletteOpen } from './js/search.js';
import { mountTable, moveRowFocus } from './js/table.js';
import { kindDot, kindTitle, tableHref } from './js/values.js';
import { errorView, mountHome, mountReview, mountReviewCheck } from './js/views.js';

const $ = (id) => document.getElementById(id);
const THEME_KEY = 'paraverse-kb.themeMode';
let current = null; // the mounted view: {key, el, update?, fit?, title, kind?, id?}
let renderSeq = 0;
let displayedMeta = null; // last load whose route and view were reconciled successfully

// Where the reader was in each view, keyed by hash, so Back returns to the same
// scroll position and row. A history entry this page has shown carries `kbEntry`
// in its state; arriving at one is a Back or Forward, anything else is new.
const places = new Map();
let shownHash = null;
let entrySeq = 0;
let lastRow = null; // the row last clicked, when the click landed on a link inside it
const ROW_SELECTOR = '#view .grid tbody tr[data-id], #view .grid tbody tr[data-href]';
const rowKey = (tr) => tr?.dataset.id || tr?.dataset.href || null;

function remember() {
  if (shownHash == null) return;
  const active = document.activeElement?.closest?.(ROW_SELECTOR);
  const row = active || (lastRow?.isConnected ? lastRow : null);
  places.delete(shownHash); // re-inserted last, so the oldest entries go first
  places.set(shownHash, { scroll: $('main').scrollTop, row: rowKey(row) });
  if (places.size > 200) places.delete(places.keys().next().value);
}

/** What has keyboard focus, described well enough to find its twin after a re-mount. */
function focusKey() {
  const el = document.activeElement;
  if (!el || el === document.body || !$('view').contains(el)) return null;
  const row = el.closest(ROW_SELECTOR);
  if (row) return { row: rowKey(row) };
  if (el.matches('[data-filter]')) return { filter: true, start: el.selectionStart, end: el.selectionEnd };
  if (el.getAttribute('href')) return { href: el.getAttribute('href') };
  return null;
}

function focusRow(key) {
  const rows = [...document.querySelectorAll(ROW_SELECTOR)];
  const row = rows.find((tr) => rowKey(tr) === key);
  if (!row) return false;
  for (const tr of rows) tr.tabIndex = tr === row ? 0 : -1;
  row.focus({ preventScroll: true });
  return true;
}

function restoreFocus(key) {
  if (!key || (document.activeElement && document.activeElement !== document.body && document.activeElement.isConnected)) return;
  if (key.row) focusRow(key.row);
  else if (key.filter) {
    const input = $('view').querySelector('[data-filter]');
    input?.focus({ preventScroll: true });
    try { input?.setSelectionRange(key.start, key.end); } catch { /* not a text input */ }
  } else if (key.href) {
    [...$('view').querySelectorAll('[href]')].find((a) => a.getAttribute('href') === key.href)?.focus({ preventScroll: true });
  }
}

// ── Router ────────────────────────────────────────────────────────────────

const MOUNTS = { table: mountTable, entity: mountRecord, review: mountReview, check: mountReviewCheck, search: mountSearch, home: mountHome };

/**
 * Show the view for the current hash. A view with `update` (table, search) keeps
 * its controls and only refreshes data when just its parameters change. `live`
 * re-renders in place after a graph reload, keeping the scroll position and focus;
 * `replaced` is a history entry rewritten in place (typing in a filter).
 */
async function render({ live = false, replaced = false, preserveDraft = true } = {}) {
  const route = parseRoute(location.hash);
  const mine = ++renderSeq;
  // Back or Forward to a view shown before; only then is the old place restored.
  const returning = !live && !replaced && Boolean(history.state?.kbEntry);
  hideCard();
  hideTooltip();
  if (!live && !current?.disposed && current?.update && current.key === route.key) {
    // Same view, new parameters: refresh the data in place, so the
    // filter keeps focus and open menus stay open, e.g. the column picker.
    if (!live && !replaced) remember();
    const focus = focusKey();
    await current.update(route);
    if (mine !== renderSeq) return;
    const place = returning ? places.get(location.hash) : null;
    if (place) {
      $('main').scrollTop = place.scroll;
      if (place.row) focusRow(place.row);
    } else {
      restoreFocus(focus);
    }
    settle(route, current);
    return;
  }
  if (!live) remember();
  const focus = live ? focusKey() : null;
  const previous = current;
  const retainDraft = preserveDraft && live && previous?.key === route.key && previous?.draftFilter;
  previous?.destroy?.();
  if (previous) previous.disposed = true;
  closeMenus();
  document.body.classList.add('busy');
  let view;
  try {
    view = await MOUNTS[route.name](route);
  } catch (err) {
    view = errorView(err);
  }
  if (mine !== renderSeq) { view.destroy?.(); return; } // a newer navigation won
  document.body.classList.remove('busy');
  const main = $('main');
  const scroll = main.scrollTop;
  const draft = retainDraft ? previous.draftFilter() : null;
  $('view').replaceChildren(view.el);
  current = view;
  if (draft !== null) view.restoreDraft?.(draft);
  view.fit?.(); // a table hides columns to fit before any scroll position is applied
  const place = returning ? places.get(location.hash) : null;
  main.scrollTop = live ? scroll : place ? place.scroll : 0;
  document.title = `${view.title || 'Knowledge Base'} · Knowledge Base`;
  markNav(route, view);
  if (live) restoreFocus(focus);
  else if (!(place?.row && focusRow(place.row))) view.el.querySelector('h1')?.focus({ preventScroll: true });
  settle(route, view);
}

/** After a view shows: mark this history entry as seen and tell an embedding host. */
function settle(route, view) {
  if (!history.state?.kbEntry) {
    try { history.replaceState({ ...history.state, kbEntry: ++entrySeq }, ''); } catch { /* state is optional */ }
  }
  shownHash = location.hash;
  lastRow = null;
  announce(route, view);
}

/** Tell an embedding host (an iframe parent or a WebKit web view) where we are. */
function announce(route, view) {
  const message = { type: 'paraverse-kb:navigate', route: location.hash.replace(/^#/, '') || '/' };
  if (route.name === 'entity') message.id = view?.id || route.id;
  // A host that cannot receive messages is fine; neither channel is required.
  try { if (window.parent !== window) window.parent.postMessage(message, '*'); } catch { /* ignored */ }
  try { window.webkit?.messageHandlers?.paraverseKb?.postMessage(message); } catch { /* ignored */ }
}

// ── Shell ─────────────────────────────────────────────────────────────────

function renderShell() {
  const meta = state.meta;
  $('graph-name').textContent = meta.dataset || meta.graph;
  const groups = meta.groups.filter((g) => g.kinds.length);
  fill($('sidebar'),
    h('a', { class: 'nav-link', href: '#/', 'data-nav': 'home' }, icon('home'), 'Home'),
    groups.map((g) => [
      h('div', { class: 'nav-heading' }, g.title),
      g.kinds.map((k) => h('a', { class: 'nav-link', href: tableHref(k.kind), 'data-nav': `kind:${k.kind}` },
        kindDot(k.kind), kindTitle(k.kind), h('span', { class: 'count' }, fmtNumber(k.count)))),
    ]),
    h('div', { class: 'nav-heading' }, 'Quality'),
    h('a', { class: 'nav-link', href: '#/review', 'data-nav': 'review' }, icon('alert'), 'Review',
      h('span', { class: 'count', id: 'nav-review-count' })));
  fill($('kind-select'),
    h('option', { value: '' }, 'Tables…'),
    groups.map((g) => h('optgroup', { label: g.title },
      g.kinds.map((k) => h('option', { value: k.kind }, `${kindTitle(k.kind)} (${fmtNumber(k.count)})`)))));
  renderDigest();
  renderReviewCount();
}

function renderDigest() {
  const meta = state.meta;
  if (!meta) return;
  const badge = $('digest');
  badge.replaceChildren('KB ', h('span', { class: 'mono' }, String(meta.kb_digest || '').slice(0, 8)), ` · ${relativeAge(meta.loaded_at) || ''}`);
  badge.dataset.tooltip = `Dataset ${meta.dataset || 'unknown'}\nGraph ${meta.graph}\nKB digest ${meta.kb_digest}\nLoaded ${meta.loaded_at}`;
}

function renderReviewCount() {
  const checks = state.review?.checks;
  const total = checks ? checks.reduce((n, c) => n + c.count, 0) : null;
  const pill = $('review-count');
  pill.textContent = total == null ? '…' : fmtNumber(total);
  pill.classList.toggle('warn', Boolean(checks?.some((c) => c.count > 0 && (c.severity === 'blocker' || c.severity === 'high'))));
  const nav = $('nav-review-count');
  if (nav) nav.textContent = total == null ? '' : fmtNumber(total);
}

function markNav(route, view) {
  const key = route.name === 'table' || route.name === 'entity' ? `kind:${view.kind}` : route.name === 'check' ? 'review' : route.name;
  for (const link of document.querySelectorAll('#sidebar [data-nav]')) {
    if (link.dataset.nav === key) link.setAttribute('aria-current', 'page');
    else link.removeAttribute('aria-current');
  }
}

// ── Theme: three states, after tbd (MIT) ──────────────────────────────────

const THEME_ICONS = { system: 'monitor', light: 'sun', dark: 'moon' };

function applyTheme(mode, persist) {
  const root = document.documentElement;
  root.dataset.themeMode = mode;
  if (mode === 'system') delete root.dataset.theme;
  else root.dataset.theme = mode;
  for (const button of document.querySelectorAll('[data-theme-choice]')) {
    button.setAttribute('aria-checked', String(button.dataset.themeChoice === mode));
  }
  $('theme-button').replaceChildren(icon(THEME_ICONS[mode]));
  // Stored raw (not JSON) because index.html reads it before first paint.
  try { if (persist) localStorage.setItem(THEME_KEY, mode); } catch { /* optional storage */ }
}

function wireShell() {
  $('search-icon').replaceWith(icon('search'));
  $('search-trigger').addEventListener('click', openPalette);
  $('kind-select').addEventListener('change', (event) => {
    const kind = event.target.value;
    event.target.value = '';
    if (kind) go(tableHref(kind));
  });
  wireMenu($('theme-button'), $('theme-menu'));
  for (const button of document.querySelectorAll('[data-theme-choice]')) {
    button.addEventListener('click', () => {
      applyTheme(button.dataset.themeChoice, true);
      closeMenus();
    });
  }
  $('help-button').addEventListener('click', () => {
    closeMenus();
    openHelp();
  });
  matchMedia('(prefers-color-scheme: dark)').addEventListener?.('change', () => {
    if (document.documentElement.dataset.themeMode === 'system') applyTheme('system', false);
  });
  const mode = document.documentElement.dataset.themeMode;
  applyTheme(mode === 'light' || mode === 'dark' ? mode : 'system', false);
  setInterval(renderDigest, 60_000);
}

// ── Keyboard ──────────────────────────────────────────────────────────────

let help = null;
const SHORTCUTS = [
  [['/'], 'Search'], [['⌘', 'K'], 'Search (Ctrl K elsewhere)'], [['j'], 'Next row'], [['k'], 'Previous row'],
  [['Enter'], 'Open the focused row or result'], [['Esc'], 'Close a card, menu or dialog'], [['?'], 'This help'],
];

function openHelp() {
  if (!help) {
    help = h('dialog', { class: 'help', 'aria-label': 'Keyboard shortcuts' },
      h('div', { class: 'help-body' }, h('h2', null, 'Keyboard shortcuts'),
        h('dl', { class: 'fields' }, SHORTCUTS.flatMap(([keys, label]) => [
          h('dt', null, keys.map((k) => h('span', { class: 'kbd' }, k))), h('dd', null, label)]))));
    help.addEventListener('click', (event) => event.target === help && help.close());
    document.body.append(help);
  }
  if (!help.open) help.showModal();
}

function onKeydown(event) {
  if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
    event.preventDefault();
    if (paletteOpen()) closePalette();
    else openPalette();
    return;
  }
  const typing = event.target.closest?.('input, textarea, select, [contenteditable="true"]');
  if (typing || event.metaKey || event.ctrlKey || event.altKey || paletteOpen() || help?.open) return;
  const onRow = event.target.matches?.('.grid tbody tr');
  if (event.key === '/') {
    event.preventDefault();
    openPalette();
  } else if (event.key === '?') {
    event.preventDefault();
    openHelp();
  } else if (event.key === 'j' || (onRow && event.key === 'ArrowDown')) {
    if (moveRowFocus(1)) event.preventDefault();
  } else if (event.key === 'k' || (onRow && event.key === 'ArrowUp')) {
    if (moveRowFocus(-1)) event.preventDefault();
  }
}

// ── Live updates: reconnect and backoff adapted from metabrowser ──────────

function connectEvents() {
  const reconciliation = watchGraphVersion(() => displayedMeta || state.meta, () => graphLoaded());
  document.addEventListener('visibilitychange', () => {
    if (!document.hidden) reconciliation.check();
  });
  if (typeof EventSource === 'undefined') return;
  let source = null;
  let backoff = 2000;
  let errors = 0;
  let retryTimer = null;
  let stableTimer = null;

  function reconnect(delay = backoff) {
    clearTimeout(stableTimer);
    source?.close();
    source = null;
    if (retryTimer) return;
    backoff = Math.min(backoff * 2, 60_000);
    retryTimer = setTimeout(() => {
      retryTimer = null;
      errors = 0;
      open();
    }, delay);
  }

  function open() {
    source = new EventSource('/api/events');
    source.addEventListener('hello', (event) => {
      let hello = null;
      try { hello = JSON.parse(event.data); } catch { /* a malformed hello is ignored */ }
      // A reload that happened while we were disconnected.
      if (hello && state.meta && !sameGraphVersion(hello, displayedMeta || state.meta)) graphLoaded();
    });
    source.addEventListener('graph.loaded', () => graphLoaded());
    source.addEventListener('resync', () => reconnect(500));
    source.onopen = () => {
      // Only a connection that stays up resets the backoff.
      clearTimeout(stableTimer);
      stableTimer = setTimeout(() => {
        backoff = 2000;
        errors = 0;
      }, 10_000);
    };
    source.onerror = () => {
      clearTimeout(stableTimer);
      errors += 1;
      if (source.readyState === EventSource.CLOSED || errors >= 5) reconnect();
    };
  }
  open();
}

let toastTimer = 0;
function toast(text) {
  const el = $('toast');
  el.textContent = text;
  el.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { el.hidden = true; }, 4000);
}

let reloadPending = null;
let reloadAgain = false;

function graphLoaded() {
  if (datasetSelectionPending()) return Promise.resolve();
  reloadAgain = true;
  if (!reloadPending) {
    reloadPending = (async () => {
      do {
        reloadAgain = false;
        await refreshGraph();
      } while (reloadAgain && !datasetSelectionPending());
    })().finally(() => { reloadPending = null; });
  }
  return reloadPending;
}

async function refreshGraph() {
  const previous = displayedMeta || state.meta;
  displayedMeta ??= previous;
  api.clearCaches();
  try {
    await api.meta();
  } catch {
    return; // the next event or reconnect tries again
  }
  const datasetChanged = Boolean(previous && previous.dataset !== state.meta.dataset);
  const hash = location.hash;
  let repaired = false;
  try {
    const next = await tableRouteAfterReload(hash, state.kinds, datasetChanged);
    // A navigation during the schema request takes precedence over this reload.
    if (location.hash === hash && next !== hash) {
      history.replaceState(history.state, '', next);
      repaired = true;
    }
  } catch {
    return; // keep the previous load stamp so reconciliation retries a failed schema request
  }
  renderShell();
  refreshDatasetSelector();
  await render({ live: true, preserveDraft: !datasetChanged && !repaired });
  displayedMeta = state.meta;
  api.review().then(renderReviewCount, () => {});
  const badge = $('digest');
  badge.classList.remove('flash');
  void badge.offsetWidth;
  badge.classList.add('flash');
  toast(`Updated: ${state.meta.dataset || state.meta.graph} was reloaded (KB ${String(state.meta.kb_digest).slice(0, 8)}).`);
}

// ── Boot ──────────────────────────────────────────────────────────────────

async function boot() {
  installTooltips();
  installCopy();
  installPopovers();
  wireShell();
  installDatasetSelector();
  refreshDatasetSelector();
  setRenderer(() => render({ replaced: true }));
  document.addEventListener('keydown', onKeydown);
  // A click on a link inside a row (a chip, the name) leaves focus where it was.
  document.addEventListener('click', (event) => {
    lastRow = event.target instanceof Element ? event.target.closest(ROW_SELECTOR) : null;
  }, { capture: true });
  window.addEventListener('hashchange', () => render());
  connectEvents();
  try {
    await api.meta();
  } catch (err) {
    $('view').replaceChildren(errorView(err).el);
    return; // a graph.loaded event retries through graphLoaded()
  }
  renderShell();
  await render(); // first, so the slower review checks never delay the first view
  displayedMeta = state.meta;
  api.review().then(renderReviewCount, () => {});
}

boot();
