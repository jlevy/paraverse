// Global search: a modal palette (an ARIA combobox over a grouped listbox, markup
// after metabrowser's search palette) and a full results view at #/search?q=.

import { api } from './api.js';
import { debounce, fill, fmtNumber, h, qs } from './dom.js';
import { go } from './router.js';
import { chip, disambiguate, entityHref, kindDot, kindTitle, plain } from './values.js';

let dialog = null;
let input = null;
let list = null;
let status = null;
let hits = [];
let active = -1;
let seq = 0;

/** Hits grouped by kind, groups in order of their best hit; repeated names get a hint. */
function groupByKind(items) {
  const groups = new Map();
  for (const hit of items) {
    if (!groups.has(hit.kind)) groups.set(hit.kind, []);
    groups.get(hit.kind).push(hit);
  }
  return [...groups].map(([kind, group]) => [kind, disambiguate(group)]);
}

const kbd = (key) => h('span', { class: 'kbd' }, key);

function build() {
  input = h('input', {
    class: 'palette-input', type: 'text', role: 'combobox', 'aria-expanded': 'false',
    'aria-controls': 'palette-list', 'aria-autocomplete': 'list', autocomplete: 'off',
    spellcheck: 'false', placeholder: 'Search people, sessions, organizations, repositories…',
    'aria-label': 'Search the knowledge base',
  });
  list = h('div', { class: 'palette-results', id: 'palette-list', role: 'listbox', 'aria-label': 'Search results' });
  status = h('div', { class: 'palette-status', role: 'status', 'aria-live': 'polite' });
  const all = h('a', { href: '#/search' }, 'All results →');
  dialog = h('dialog', { class: 'palette', 'aria-label': 'Search' }, input, list, status,
    h('div', { class: 'palette-hint' },
      h('span', null, kbd('↑'), ' ', kbd('↓'), ' move'), h('span', null, kbd('Enter'), ' open'),
      h('span', null, kbd('Esc'), ' close'), all));
  document.body.append(dialog);

  input.addEventListener('input', debounce(run, 150));
  input.addEventListener('keydown', onKey);
  list.addEventListener('mousedown', (event) => event.preventDefault()); // keep focus in the input
  list.addEventListener('click', (event) => {
    const option = event.target.closest('[role="option"]');
    if (option) choose(Number(option.dataset.index));
  });
  all.addEventListener('click', (event) => {
    event.preventDefault();
    const q = input.value.trim();
    closePalette();
    go(`#/search${qs({ q })}`);
  });
  // A click on the backdrop lands on the dialog element itself, outside its box.
  dialog.addEventListener('click', (event) => {
    const r = dialog.getBoundingClientRect();
    const outside = event.clientX < r.left || event.clientX > r.right || event.clientY < r.top || event.clientY > r.bottom;
    if (event.target === dialog && event.detail > 0 && outside) closePalette();
  });
}

export function openPalette() {
  if (!dialog) build();
  if (!dialog.open) dialog.showModal();
  input.focus();
  input.select();
}

export function closePalette() {
  if (dialog?.open) dialog.close();
}

export const paletteOpen = () => Boolean(dialog?.open);

async function run() {
  const q = input.value.trim();
  const mine = ++seq;
  if (!q) {
    render([]);
    status.textContent = '';
    return;
  }
  status.textContent = 'Searching…';
  try {
    const data = await api.search(q, { limit: 40 });
    if (mine !== seq) return;
    render(data.hits);
    status.textContent = data.hits.length ? `${data.hits.length} results` : 'No matches.';
  } catch (err) {
    if (mine === seq) status.textContent = err.message;
  }
}

function render(items) {
  hits = [];
  list.replaceChildren(...groupByKind(items).map(([kind, group], g) => h('div', { role: 'group', 'aria-labelledby': `palette-g${g}` },
    h('div', { class: 'palette-group', id: `palette-g${g}` }, kindTitle(kind)),
    group.map((hit) => {
      const index = hits.push(hit) - 1;
      return h('div', { class: 'palette-option', role: 'option', id: `palette-o${index}`, 'data-index': index, 'aria-selected': 'false' },
        kindDot(hit.kind), h('span', { class: 'name' }, hit.name || hit.id),
        hit.snippet ? h('span', { class: 'snippet' }, plain(hit.snippet)) : null);
    }))));
  input.setAttribute('aria-expanded', String(hits.length > 0));
  setActive(hits.length ? 0 : -1);
}

function setActive(index) {
  active = index;
  for (const option of list.querySelectorAll('[role="option"]')) {
    option.setAttribute('aria-selected', String(Number(option.dataset.index) === index));
  }
  const current = index >= 0 ? list.querySelector(`#palette-o${index}`) : null;
  if (current) {
    input.setAttribute('aria-activedescendant', current.id);
    current.scrollIntoView({ block: 'nearest' });
  } else {
    input.removeAttribute('aria-activedescendant');
  }
}

function onKey(event) {
  if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
    event.preventDefault();
    if (hits.length) setActive((active + (event.key === 'ArrowDown' ? 1 : hits.length - 1)) % hits.length);
  } else if (event.key === 'Enter') {
    event.preventDefault();
    if (active >= 0) choose(active);
    else if (input.value.trim()) {
      closePalette();
      go(`#/search${qs({ q: input.value.trim() })}`);
    }
  }
}

function choose(index) {
  const hit = hits[index];
  if (!hit) return;
  closePalette();
  go(entityHref(hit.id));
}

const LIMIT = 200; // the API's maximum

/** The full results view: every hit grouped by kind, with a per-kind filter. */
export async function mountSearch(route) {
  const field = h('input', { class: 'input', type: 'search', placeholder: 'Search…', 'aria-label': 'Search', 'data-filter': true });
  const results = h('div');
  let current = route;
  let mine = 0;
  const navigate = (changes) => go(`#/search${qs({ ...Object.fromEntries(current.params), ...changes })}`, { replace: true });
  const onFilter = debounce(() => navigate({ q: field.value.trim() }), 250);
  field.addEventListener('input', onFilter);

  async function update(next) {
    current = next;
    const q = next.params.get('q') || '';
    const kinds = next.params.get('kinds') || '';
    if (document.activeElement !== field) field.value = q;
    const ticket = ++mine;
    if (!q) return results.replaceChildren(h('p', { class: 'empty' }, 'Type to search every kind by name and text.'));
    let data;
    try {
      data = await api.search(q, { limit: LIMIT, kinds });
    } catch (err) {
      if (ticket === mine) results.replaceChildren(h('div', { class: 'error-box', role: 'alert' }, err.message));
      return;
    }
    if (ticket !== mine) return;
    const groups = groupByKind(data.hits);
    const capped = data.hits.length >= LIMIT;
    fill(results,
      kinds ? h('p', null, h('span', { class: 'filter-chip' }, h('span', { class: 'label' }, 'Only'), kindTitle(kinds),
        h('a', { href: `#/search${qs({ q })}`, 'aria-label': 'Show every kind' }, ' ×'))) : null,
      groups.length ? null : h('p', { class: 'empty' }, 'No matches.'),
      capped ? h('p', { class: 'muted small' }, `Showing the ${fmtNumber(LIMIT)} best matches. Narrow the search, or pick one kind, to see others.`) : null,
      groups.map(([kind, group]) => h('section', { class: 'section' },
        h('h2', { class: 'section-heading' }, kindDot(kind), kindTitle(kind),
          h('span', { class: 'hint num' }, fmtNumber(group.length),
            kinds ? null : [' · ', h('a', { href: `#/search${qs({ q, kinds: kind })}` }, 'only these')])),
        h('ul', { class: 'hits' }, group.map((hit) => h('li', { class: 'hit' },
          chip(hit.id, hit.name, hit.kind), hit.snippet ? h('div', { class: 'snippet' }, plain(hit.snippet)) : null))))));
  }

  const el = h('div', null,
    h('div', { class: 'view-head' }, h('h1', { tabindex: '-1' }, 'Search')),
    h('div', { class: 'toolbar' }, field), results);
  await update(route);
  return {
    key: route.key, el, update, title: 'Search',
    draftFilter: () => field.value,
    restoreDraft(value) {
      field.value = value;
      if (value.trim() !== (current.params.get('q') || '')) onFilter();
    },
    destroy() { field.removeEventListener('input', onFilter); onFilter.cancel(); ++mine; },
  };
}
