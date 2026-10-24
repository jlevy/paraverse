// DOM building, formatting and the two delegated widgets every view shares (tooltip
// and copy button). All text from the API reaches the page through text nodes and
// setAttribute, never through HTML parsing.

/**
 * Build an element. `props` keys become attributes, except `class`, and `on<event>`
 * handlers. Children may be strings (text nodes), nodes, arrays, or null.
 */
export function h(tag, props, ...children) {
  const el = document.createElement(tag);
  for (const [key, value] of Object.entries(props || {})) {
    if (value == null || value === false) continue;
    if (key === 'class') el.className = value;
    else if (key.startsWith('on')) el.addEventListener(key.slice(2), value);
    else if ((key === 'href' || key === 'src') && !/^(#|\/(?!\/)|https?:)/i.test(String(value))) continue;
    else el.setAttribute(key, value === true ? '' : String(value));
  }
  append(el, children);
  return el;
}

/** Replace an element's children; like `append`, flattens arrays and skips nulls. */
export function fill(el, ...children) {
  el.replaceChildren();
  return append(el, children);
}

export function append(el, children) {
  for (const child of [children].flat(Infinity)) {
    if (child == null || child === false || child === '') continue;
    el.append(child instanceof Node ? child : String(child));
  }
  return el;
}

/** The URL to show as an image, or null when remote images are off (`?images=0`). */
export function imageUrl(value) {
  return document.documentElement.hasAttribute('data-no-images') ? null : safeUrl(value);
}

/** The URL if it is http(s), else null: the only URLs that become links or images. */
export function safeUrl(value) {
  if (typeof value !== 'string' || !/^https?:\/\//i.test(value)) return null;
  try { return new URL(value).href; } catch { return null; }
}

export function shortUrl(href) {
  try {
    const url = new URL(href);
    const path = (url.pathname + url.search).replace(/\/$/, '');
    return url.host.replace(/^www\./, '') + path;
  } catch {
    return href;
  }
}

const ACRONYMS = { Url: 'URL', Urls: 'URLs', Id: 'ID', Ids: 'IDs', Github: 'GitHub', Sha256: 'SHA-256', Http: 'HTTP' };

/** A readable label from a snake_case name or a generated schema title. */
export function humanize(name) {
  const words = String(name).replace(/_/g, ' ').trim().split(/\s+/);
  return words
    .map((w, i) => {
      const cap = w.charAt(0).toUpperCase() + w.slice(1);
      if (ACRONYMS[cap]) return ACRONYMS[cap];
      return i === 0 ? cap : w;
    })
    .join(' ');
}

/** Schema titles are generated from names ("Photo Url"); fix the acronyms only. */
export function fieldTitle(field) {
  const title = field.title || humanize(field.name);
  return title.split(' ').map((w) => ACRONYMS[w] || w).join(' ');
}

/** "GitHubAccount" → "GitHub Account"; plain titles pass through. */
export function splitTitle(title) {
  return String(title).replace(/([a-z])([A-Z])/g, '$1 $2').replace('Git Hub', 'GitHub');
}

export function fmtNumber(value) {
  return typeof value === 'number' ? value.toLocaleString('en-US') : String(value);
}

const ISO_DATETIME = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/;
export const isIsoDateTime = (value) => typeof value === 'string' && ISO_DATETIME.test(value);

/** "2025-10-29T15:00:00-07:00" → "2025-10-29 15:00", keeping the local wall time. */
export function fmtDateTime(value) {
  return value.replace('T', ' ').replace(/:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})?$/, '');
}

// Adapted from tbd's formatRelativeAge (MIT, core.ts): compact "ago" labels.
const STEPS = [['y', 31536e6], ['mo', 2592e6], ['w', 6048e5], ['d', 864e5], ['h', 36e5], ['m', 6e4]];
export function relativeAge(timestamp, nowMs = Date.now()) {
  const ms = new Date(timestamp).getTime();
  if (!Number.isFinite(ms)) return null;
  const age = Math.max(0, nowMs - ms);
  for (const [suffix, size] of STEPS) {
    if (age >= size) return `${Math.floor(age / size)}${suffix} ago`;
  }
  return 'just now';
}

/** Typed IDs stay readable in the hash: keep `/`, `:` and `@`, encode the rest. */
export function encodeId(id) {
  return encodeURIComponent(id).replace(/%(2F|3A|40)/gi, (m) => decodeURIComponent(m));
}

export function decodePart(part) {
  try { return decodeURIComponent(part); } catch { return part; }
}

/** A query string for hash routes, readable for typed IDs and column lists. */
export function qs(params) {
  const parts = [];
  for (const [key, value] of Object.entries(params)) {
    if (value == null || value === '') continue;
    const enc = (s) => encodeURIComponent(s).replace(/%(2F|3A|40|2C)/gi, (m) => decodeURIComponent(m));
    parts.push(`${enc(key)}=${enc(String(value))}`);
  }
  return parts.length ? `?${parts.join('&')}` : '';
}

export function debounce(fn, ms) {
  let timer = 0;
  const run = (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), ms);
  };
  run.cancel = () => clearTimeout(timer);
  return run;
}

/** localStorage that never throws (private mode, blocked storage, thumbnails). */
export const store = {
  get(key) {
    try { return JSON.parse(localStorage.getItem(key) ?? 'null'); } catch { return null; }
  },
  set(key, value) {
    try {
      if (value == null) localStorage.removeItem(key);
      else localStorage.setItem(key, JSON.stringify(value));
    } catch {
      // Storage is optional; the choice holds for this page load.
    }
  },
};

/**
 * Wire a button to a popup menu: toggles on click, closes on outside click and
 * Escape. `onOpen` runs before showing, so a menu can render fresh content. One
 * registry and one pair of document listeners serve every menu on the page.
 */
const menus = new Set();
let menuListeners = false;
export function wireMenu(button, menu, onOpen) {
  if (!menuListeners) {
    menuListeners = true;
    document.addEventListener('click', () => closeMenus());
    document.addEventListener('keydown', (event) => event.key === 'Escape' && closeMenus(true));
  }
  menus.add({ button, menu });
  button.addEventListener('click', (event) => {
    event.stopPropagation();
    const opening = menu.hidden;
    closeMenus();
    if (!opening) return;
    onOpen?.();
    menu.hidden = false;
    placeMenu(menu, button);
    button.setAttribute('aria-expanded', 'true');
  });
  menu.addEventListener('click', (event) => event.stopPropagation());
}

/**
 * Keep an open menu inside the viewport. It hangs below its button, aligned to the
 * button's right edge; it shifts sideways when that would cross a window edge, and
 * opens upward when there is more room above than below.
 */
function placeMenu(menu, button) {
  const gap = 8;
  const width = document.documentElement.clientWidth;
  Object.assign(menu.style, { left: '', right: '', top: '', bottom: '', maxWidth: `${width - 2 * gap}px`, maxHeight: '' });
  const b = button.getBoundingClientRect();
  const m = menu.getBoundingClientRect();
  if (m.left < gap) menu.style.right = `${m.left - gap}px`;
  else if (m.right > width - gap) menu.style.right = `${m.right - (width - gap)}px`;
  const below = innerHeight - b.bottom - gap;
  const above = b.top - gap;
  if (m.height > below && above > below) {
    Object.assign(menu.style, { top: 'auto', bottom: 'calc(100% + 4px)', maxHeight: `${Math.max(120, above - 4)}px` });
  } else if (m.height > below) {
    menu.style.maxHeight = `${Math.max(120, below - 4)}px`;
  }
}

/** Close every open menu; `refocus` returns focus to the menu's button (Escape). */
export function closeMenus(refocus = false) {
  for (const entry of menus) {
    if (!entry.menu.isConnected) {
      menus.delete(entry);
    } else if (!entry.menu.hidden) {
      entry.menu.hidden = true;
      entry.button.setAttribute('aria-expanded', 'false');
      if (refocus) entry.button.focus();
    }
  }
}

// ── Tooltip: adapted from tbd (MIT, client.ts) ───────────────────────────────
// One body-level tooltip for every [data-tooltip], delegated, with a CSS reveal
// delay, placement under (or above) its anchor, and Escape or scroll dismissal.
const tooltip = h('div', { class: 'tooltip', id: 'tooltip', role: 'tooltip', 'aria-hidden': 'true' });
let tipTarget = null;

function showTooltip(target) {
  const value = target.dataset.tooltip?.trim();
  if (!value) return;
  if (tipTarget !== target) {
    tooltip.classList.remove('visible');
    void tooltip.offsetWidth; // restart the reveal delay for each new target
    tipTarget = target;
  }
  tooltip.textContent = value;
  tooltip.classList.toggle('literal', target.hasAttribute('data-tooltip-literal'));
  tooltip.setAttribute('aria-hidden', 'false');
  const gap = 8;
  const a = target.getBoundingClientRect();
  const t = tooltip.getBoundingClientRect();
  const y = a.bottom + gap + t.height > innerHeight - gap ? a.top - t.height - gap : a.bottom + gap;
  tooltip.style.left = `${Math.max(gap, Math.min(a.left, innerWidth - t.width - gap))}px`;
  tooltip.style.top = `${Math.max(gap, y)}px`;
  tooltip.classList.add('visible');
}

export function hideTooltip() {
  tipTarget = null;
  tooltip.classList.remove('visible');
  tooltip.setAttribute('aria-hidden', 'true');
}

const tipOf = (node) => (node instanceof Element ? node.closest('[data-tooltip]') : null);

export function installTooltips() {
  document.body.append(tooltip);
  document.addEventListener('pointerover', (event) => {
    const target = tipOf(event.target);
    if (target && target !== tipTarget) showTooltip(target);
  });
  document.addEventListener('pointerout', (event) => {
    if (tipTarget && !(event.relatedTarget instanceof Node && tipTarget.contains(event.relatedTarget))) hideTooltip();
  });
  document.addEventListener('focusin', (event) => {
    const target = tipOf(event.target);
    if (target) showTooltip(target);
  });
  document.addEventListener('focusout', hideTooltip);
  document.addEventListener('scroll', hideTooltip, true);
  document.addEventListener('keydown', (event) => event.key === 'Escape' && hideTooltip());
}

// ── Copy button: adapted from tbd (MIT, client.ts) ───────────────────────────
// One delegated click handler; each literal carries one small accessible button.
export function copyable(value, label, display = value) {
  return h('span', { class: 'copyable' },
    h('span', { class: 'copy-value mono', 'data-copy-value': value }, display),
    copyButton(label));
}

export function copyButton(label) {
  return h('button', { type: 'button', class: 'copy-button', 'aria-label': `Copy ${label}`, 'data-tooltip': `Copy ${label}` });
}

// Some embedded web views refuse the async clipboard; the selection-based copy works there.
function legacyCopy(text) {
  const area = h('textarea', { readonly: true, 'aria-hidden': 'true', class: 'visually-hidden' });
  area.value = text;
  document.body.append(area);
  area.select();
  let ok = false;
  try { ok = document.execCommand('copy'); } catch { /* unsupported: report failure */ }
  area.remove();
  return ok;
}

function finishCopy(button, ok) {
  button.classList.remove('copied', 'copy-failed');
  void button.offsetWidth;
  button.classList.add(ok ? 'copied' : 'copy-failed');
  button.dataset.tooltip = ok ? 'Copied' : 'Copy failed';
}

export function installCopy() {
  document.addEventListener('click', (event) => {
    const button = event.target instanceof Element ? event.target.closest('.copy-button') : null;
    if (!button) return;
    // Capture keeps the owning row or link from seeing the same click.
    event.preventDefault();
    event.stopPropagation();
    const source = button.parentElement?.querySelector('[data-copy-value]');
    const value = source?.getAttribute('data-copy-value') ?? '';
    const fallback = () => finishCopy(button, legacyCopy(value));
    if (!navigator.clipboard) return fallback();
    navigator.clipboard.writeText(value).then(() => finishCopy(button, true), fallback);
  }, { capture: true });
  document.addEventListener('animationend', (event) => {
    const button = event.target;
    if (event.animationName === 'copy-feedback' && button instanceof HTMLElement) {
      button.classList.remove('copied', 'copy-failed');
      button.dataset.tooltip = button.getAttribute('aria-label') || 'Copy';
    }
  });
}
