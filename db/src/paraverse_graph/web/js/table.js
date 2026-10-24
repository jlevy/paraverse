// The one table view every kind shares. Columns, titles, sortability and filters all
// come from /api/schema/<kind>; rows come from /api/rows/<kind>, up to PAGE_SIZE at a
// time, so every current kind fits on one page and the pager only appears beyond that.

import { api, state } from './api.js';
import { append, debounce, fieldTitle, fmtNumber, h, humanize, isIsoDateTime, safeUrl, store, wireMenu } from './dom.js';
import { icon } from './icons.js';
import { go } from './router.js';
import {
  boolTag, chip, cluster, description, entityHref, extLink, kindDot, kindTitle, parseRelFilter,
  plural, relTitle, relatedHref, scalar, tableHref, tag,
} from './values.js';

const SCALAR_TYPES = new Set(['string', 'integer', 'number', 'boolean']);
const API_PARAMS = new Set(['sort', 'order', 'q', 'rel', 'offset', 'limit']);
const BOOLEAN_VALUES = new Set(['true', 'false', '1', '0', 'yes', 'no']);
// The server's maximum page size (browser.MAX_LIMIT); `limit` in the URL overrides it.
const PAGE_SIZE = 2000;
const colsKey = (kind) => `paraverse-kb.cols.${kind}`;

/** Every column a kind offers, keyed by name: schema fields, computed, relationships. */
export function columnCatalog(schema) {
  const cols = new Map();
  for (const f of schema.fields) {
    cols.set(f.name, { name: f.name, title: fieldTitle(f), tip: f.description, field: f, group: 'Fields' });
  }
  for (const name of schema.computed) {
    if (!cols.has(name)) cols.set(name, { name, title: humanize(name), tip: 'Derived property', group: 'Computed' });
  }
  for (const rel of schema.relationships) {
    const arrow = rel.direction === 'out' ? '→' : '←';
    cols.set(rel.name, {
      name: rel.name, title: relTitle(rel.direction, rel.type), rel, group: 'Relationships',
      tip: `${arrow} ${rel.type} · ${rel.kinds.map(kindTitle).join(', ')} · ${fmtNumber(rel.count)} links`,
    });
  }
  return cols;
}

function sortable(col) {
  if (col.group === 'Computed') return true;
  const f = col.field;
  return Boolean(f && SCALAR_TYPES.has(f.type) && !f.ref_kinds && !f.list);
}

/** The ID column shows the ID without its kind prefix; the table names the kind. */
const localId = (id) => id.slice(id.indexOf(':') + 1);

export async function mountTable(route) {
  const kind = route.kind;
  const schema = await api.schema(kind);
  const catalog = columnCatalog(schema);
  let current = route;
  let columns = [];
  let loadSeq = 0;

  const count = h('span', { class: 'count' });
  const filter = h('input', {
    class: 'input', type: 'search', placeholder: `Filter ${kindTitle(kind).toLowerCase()}…`,
    'aria-label': 'Filter rows', value: route.params.get('q') || '', 'data-filter': true,
  });
  const chips = h('span', { class: 'cluster' });
  const colButton = h('button', { type: 'button', class: 'btn', 'aria-haspopup': 'true', 'aria-expanded': 'false' }, icon('columns'), 'Columns');
  const colMenu = h('div', { class: 'menu', hidden: true });
  const pagerTop = h('span', { class: 'pager' });
  const pagerFoot = h('div', { class: 'pager-foot' });
  const body = h('div', { class: 'grid-box' });
  const trimNote = h('button', { type: 'button', class: 'trim-note', hidden: true });
  trimNote.addEventListener('click', (event) => {
    event.stopPropagation(); // the document click would close the menu it opens
    colButton.click();
  });
  let nameCol = null; // the column that repeats each row's name, if any

  // Merge changes into the current route; a null value removes the parameter.
  function navigate(changes, replace = false) {
    const next = Object.fromEntries(current.params);
    for (const [key, value] of Object.entries(changes)) {
      if (value == null || value === '') delete next[key];
      else next[key] = value;
    }
    go(tableHref(kind, next), { replace });
  }

  function chosenColumns(params) {
    const raw = params.get('cols') ?? (store.get(colsKey(kind)) || []).join(',');
    const list = raw.split(',').filter((name) => catalog.has(name));
    return list.length ? list : null;
  }

  function setColumns(list) {
    store.set(colsKey(kind), list);
    navigate({ cols: list ? list.join(',') : null }, true);
  }

  function renderColumnMenu() {
    const active = new Set(columns);
    colMenu.replaceChildren();
    for (const group of ['Fields', 'Computed', 'Relationships']) {
      const items = [...catalog.values()].filter((c) => c.group === group && c.name !== 'id');
      if (!items.length) continue;
      colMenu.append(h('div', { class: 'menu-heading' }, group));
      for (const col of items) {
        const box = h('input', { type: 'checkbox', checked: active.has(col.name) });
        box.addEventListener('change', () => {
          const next = columns.filter((name) => name !== col.name);
          if (box.checked) next.push(col.name);
          setColumns(next.length ? next : null);
        });
        colMenu.append(h('label', { class: 'menu-item', 'data-tooltip': col.tip || null }, box, col.title,
          col.rel ? h('span', { class: 'muted' }, col.rel.kinds.map(kindTitle).join(', ')) : null));
      }
    }
    colMenu.append(h('button', { type: 'button', class: 'menu-item', onclick: () => setColumns(null) }, 'Reset to defaults'));
  }
  wireMenu(colButton, colMenu, renderColumnMenu);

  const onFilter = debounce(() => navigate({ q: filter.value.trim() || null, offset: null }, true), 250);
  filter.addEventListener('input', onFilter);

  // A filter-by-value link for enum and boolean cells.
  function filterLink(col, value, label) {
    const href = tableHref(kind, { ...Object.fromEntries(current.params), [`f.${col.name}`]: String(value), offset: null });
    return h('a', { class: 'tag on', href, 'data-tooltip': `Only rows with ${col.title} = ${value}` }, label);
  }

  function listItem(value, col) {
    const f = col?.field;
    if (f?.enum) return filterLink(col, value, value);
    const href = safeUrl(value);
    return href ? extLink(href) : tag(String(value));
  }

  function cell(value, col, row) {
    if (value == null || value === '') return null;
    if (col?.rel) {
      if (!value.count) return null;
      // At most two chips (two lines in a narrow column), then a "+N" to the full list.
      const shown = value.items.slice(0, 2);
      const items = shown.map((it) => chip(it.id, it.name, it.kind));
      const more = value.items[0] && relatedHref(value.items[0].kind, col.rel.direction, col.rel.type, row.id);
      if (value.count > items.length) {
        items.push(h('a', { class: 'more', href: more, 'data-tooltip': `All ${fmtNumber(value.count)}` }, `+${fmtNumber(value.count - items.length)}`));
      }
      return h('span', { class: 'cluster' }, items);
    }
    if (Array.isArray(value)) return value.length ? cluster(value.map((v) => listItem(v, col)), 3) : null;
    if (typeof value === 'object') {
      if (value.refs) return cluster(value.refs.map((r) => chip(r.id, r.name, r.kind)), 2);
      if (value.nested) {
        const label = col?.field?.list ? `${value.count} ${value.count === 1 ? 'item' : 'items'}` : humanize(value.nested.replace(/([a-z])([A-Z])/g, '$1 $2').toLowerCase());
        return h('span', { class: 'muted', 'data-tooltip': value.preview || null }, label);
      }
      return JSON.stringify(value);
    }
    const f = col?.field;
    if (f && (f.enum || f.type === 'boolean')) {
      return filterLink(col, value, typeof value === 'boolean' ? (value ? 'yes' : 'no') : value);
    }
    if (typeof value === 'boolean') return boolTag(value);
    if (col?.name === nameCol && typeof value === 'string') {
      // The name is the row's link, so the record stays one click away when the
      // ID column is hidden to fit.
      return h('a', { class: 'row-link', href: entityHref(row.id), 'data-tooltip': `${value}\n${row.id}` }, value);
    }
    if (typeof value === 'string' && !safeUrl(value) && !isIsoDateTime(value)) {
      return h('span', { 'data-tooltip': value.length > 40 ? value : null }, value);
    }
    return scalar(value, col?.name);
  }

  function header(data, numeric) {
    const th = (name, title, tip, canSort, right) => {
      const active = data.sort === name || (data.sort === 'display_name' && name === nameCol);
      const indicator = active ? h('span', { class: 'sort-indicator', 'aria-hidden': 'true' }, data.order === 'desc' ? '↓' : '↑') : null;
      const cellEl = h('th', { scope: 'col', class: right ? 'right' : null, 'aria-sort': active ? (data.order === 'desc' ? 'descending' : 'ascending') : null });
      if (!canSort) return append(cellEl, [h('span', { 'data-tooltip': tip || null }, title)]);
      const order = active && data.order === 'asc' ? 'desc' : 'asc';
      cellEl.append(h('button', {
        type: 'button', class: 'sort-button', 'data-tooltip': tip || null,
        onclick: () => navigate({ sort: name, order, offset: null }),
      }, title, indicator));
      return cellEl;
    };
    return h('thead', null, h('tr', null,
      th('id', 'ID', 'Typed ID', true, false),
      columns.map((name) => {
        const col = catalog.get(name) || { name, title: humanize(name) };
        return th(name, col.title, col.tip, sortable(col), numeric.has(name));
      })));
  }

  const isNumeric = (data, name) => data.rows.some((r) => typeof r.cells[name] === 'number')
    && data.rows.every((r) => r.cells[name] == null || typeof r.cells[name] === 'number');

  function pager(data) {
    const shown = data.offset + data.rows.length;
    const from = data.total ? data.offset + 1 : 0;
    return [
      h('button', {
        type: 'button', class: 'btn', 'aria-label': 'Previous page', disabled: data.offset <= 0,
        onclick: () => navigate({ offset: Math.max(0, data.offset - data.limit) || null }),
      }, icon('chevronLeft')),
      h('span', null, data.rows.length ? `${fmtNumber(from)}–${fmtNumber(shown)} of ${fmtNumber(data.total)}` : `${fmtNumber(data.total)} rows`),
      h('button', {
        type: 'button', class: 'btn', 'aria-label': 'Next page', disabled: shown >= data.total,
        onclick: () => navigate({ offset: data.offset + data.limit }),
      }, icon('chevronRight')),
    ];
  }

  function renderChips(params) {
    chips.replaceChildren();
    const remove = (key) => h('button', { type: 'button', 'aria-label': 'Remove filter', onclick: () => navigate({ [key]: null, offset: null }) }, icon('x'));
    const rel = params.get('rel');
    const parsed = parseRelFilter(rel);
    if (parsed) {
      const label = h('span', { class: 'value' }, parsed.id);
      api.card(parsed.id).then((card) => { label.textContent = card.name || parsed.id; }, () => {});
      chips.append(h('span', { class: 'filter-chip' },
        h('span', { class: 'label' }, relTitle(parsed.direction, parsed.type)),
        h('a', { href: entityHref(parsed.id), 'data-card-id': parsed.id }, label), remove('rel')));
    } else if (rel) {
      chips.append(h('span', { class: 'filter-chip' }, h('span', { class: 'label' }, 'Linked'), h('span', { class: 'value' }, rel), remove('rel')));
    }
    for (const [key, value] of params) {
      if (!key.startsWith('f.')) continue;
      const col = catalog.get(key.slice(2));
      chips.append(h('span', { class: 'filter-chip' },
        h('span', { class: 'label' }, `${col ? col.title : key.slice(2)} =`), h('span', { class: 'value' }, value), remove(key)));
    }
  }

  /** A client-side check the API is lenient about: boolean filters take yes or no. */
  function invalidFilter(params) {
    for (const [key, value] of params) {
      const f = key.startsWith('f.') ? catalog.get(key.slice(2))?.field : null;
      if (f?.type === 'boolean' && !BOOLEAN_VALUES.has(value.toLowerCase())) {
        return `\`${value}\` is not a yes or no value for ${catalog.get(key.slice(2)).title}.`;
      }
    }
    return null;
  }

  function errorBox(message) {
    return h('div', { class: 'error-box', role: 'alert' }, h('p', null, message), h('a', { href: tableHref(kind) }, 'Reset this table'));
  }

  function renderRows(data) {
    if (!data.rows.length) {
      if (data.offset > 0 && data.total > 0) {
        // An offset past the end (an old link, a hand-edited URL).
        const last = Math.floor((data.total - 1) / data.limit) * data.limit;
        return h('p', { class: 'empty' }, `This page is past the last of ${plural(data.total, 'row')}. `,
          h('a', { href: tableHref(kind, { ...Object.fromEntries(current.params), offset: null }) }, 'Go to the first page'), ' or ',
          h('a', { href: tableHref(kind, { ...Object.fromEntries(current.params), offset: last || null }) }, 'the last page'), '.');
      }
      const filtered = [...current.params.keys()].some((k) => k === 'q' || k === 'rel' || k.startsWith('f.'));
      return h('p', { class: 'empty' }, 'No rows', filtered ? [' match these filters. ', h('a', { href: tableHref(kind) }, 'Clear filters')] : '.');
    }
    nameCol = nameColumn(data);
    const numeric = new Set(columns.filter((name) => isNumeric(data, name)));
    // Columns of long text get a minimum width, so chip columns cannot crush them.
    const wide = new Set(columns.filter((name) => data.rows.some((r) => typeof r.cells[name] === 'string' && r.cells[name].length > 32)));
    // So do columns of entity chips, so a chip keeps room for a readable name.
    const chipCols = new Set(columns.filter((name) => catalog.get(name)?.rel || catalog.get(name)?.field?.ref_kinds));
    const cellClass = (name) => (wide.has(name) ? 'cell wide' : chipCols.has(name) ? 'cell chips' : 'cell');
    const rows = data.rows.map((row, index) => h('tr', { tabindex: index === 0 ? '0' : '-1', 'data-id': row.id },
      h('td', { class: 'id-cell' }, h('a', { href: entityHref(row.id), 'data-tooltip': row.name ? `${row.name}\n${row.id}` : row.id }, localId(row.id))),
      columns.map((name) => h('td', { class: numeric.has(name) ? 'right' : null },
        h('div', { class: cellClass(name) }, cell(row.cells[name], catalog.get(name), row))))));
    const table = wireRows(h('table', { class: 'grid' }, header(data, numeric), h('tbody', null, rows)));
    // Which cells hide first when the table is too wide: the ID column when a name
    // column carries the same identity, then columns from the right, keeping one.
    const nameIndex = nameCol ? columns.indexOf(nameCol) + 1 : -1;
    const fromRight = columns.map((_, i) => i + 1).filter((i) => i > 1 && i !== nameIndex).reverse();
    table.hideOrder = nameCol ? [0, ...fromRight] : fromRight;
    return table;
  }

  /** The column whose value is each row's display name (a name or title), if any. */
  function nameColumn(data) {
    const named = data.rows.filter((r) => r.name);
    if (!named.length) return null;
    return columns.find((c) => named.filter((r) => r.cells[c] === r.name).length >= named.length * 0.8) || null;
  }

  /**
   * Fit the default columns to the view: while the table is wider than its box,
   * hide the next column in its hide order. Columns the reader chose never hide; that
   * table scrolls sideways instead, with its first column pinned.
   */
  let fitWidth = -1;
  // Hiding and pinning are nth-child rules in one small stylesheet per view, so a fit
  // step changes one text node instead of a class on every cell; with a couple of
  // thousand rows, per-cell toggling made each step cost a full table walk.
  const fitStyle = h('style');
  const fitId = `fit-${Math.random().toString(36).slice(2, 8)}`;
  function fit(force = false) {
    const table = body.querySelector('table.grid');
    const width = body.clientWidth;
    if (!table || !width || (!force && width === fitWidth)) return;
    fitWidth = width;
    table.dataset.fit = fitId;
    if (!fitStyle.isConnected) body.before(fitStyle);
    const order = chosenColumns(current.params) ? [] : table.hideOrder || [];
    const heads = [...table.rows[0].cells];
    const scope = `table[data-fit="${fitId}"]`;
    const column = (i) => `${scope} > * > tr > :nth-child(${i + 1})`;
    const apply = (n) => {
      const off = new Set(order.slice(0, n));
      const lead = heads.findIndex((_, i) => !off.has(i)) + 1;
      const pinned = `${scope}.scrolls > * > tr > :nth-child(${lead})`;
      fitStyle.textContent = [
        off.size ? `${[...off].map(column).join(', ')} { display: none; }` : '',
        `${pinned} { position: sticky; left: 0; z-index: 1; background: var(--bg); box-shadow: inset -1px 0 0 var(--border); }`,
        `${scope}.scrolls > thead > tr > :nth-child(${lead}) { z-index: calc(var(--z-sticky) + 1); }`,
        `${scope}.scrolls > tbody > tr:is(:hover, :focus) > :nth-child(${lead}) { background: var(--panel); }`,
      ].join('\n');
    };
    // Header widths, measured once, estimate how many columns must go; the loop then
    // only corrects the estimate, so a fit costs one or two layouts.
    const widths = heads.map((th) => th.offsetWidth);
    let n = 0;
    for (let excess = table.offsetWidth - width; n < order.length && excess > 1; n++) excess -= widths[order[n]];
    apply(n);
    while (n < order.length && table.offsetWidth > width + 1) apply(++n);
    while (n > 0) {
      apply(n - 1);
      if (table.offsetWidth > width + 1) { apply(n); break; }
      n--;
    }
    table.classList.toggle('scrolls', table.offsetWidth > width + 1);
    const hidden = order.slice(0, n).map((i) => heads[i].textContent.trim() || 'ID');
    trimNote.hidden = !n;
    trimNote.textContent = n ? `${plural(n, 'column')} hidden to fit` : '';
    trimNote.dataset.tooltip = n ? `Hidden at this width: ${hidden.join(', ')}.\nWiden the window, or pick columns.` : '';
  }
  new ResizeObserver((_, observer) => {
    if (!body.isConnected && fitWidth >= 0) observer.disconnect(); // the view was replaced
    else fit();
  }).observe(body);

  async function update(route) {
    const previous = current;
    current = route;
    const mine = ++loadSeq;
    const params = {};
    for (const [key, value] of route.params) if (API_PARAMS.has(key) || key.startsWith('f.')) params[key] = value;
    params.limit ??= String(PAGE_SIZE);
    const chosen = chosenColumns(route.params);
    if (chosen) params.cols = chosen.join(',');
    if (document.activeElement !== filter) filter.value = route.params.get('q') || '';
    const fail = (message) => {
      count.textContent = '';
      body.replaceChildren(errorBox(message));
      pagerTop.replaceChildren();
      pagerFoot.replaceChildren();
      trimNote.hidden = true;
    };
    try {
      renderChips(route.params);
      const invalid = invalidFilter(route.params);
      if (invalid) return fail(invalid);
      const data = await api.rows(kind, params);
      if (mine !== loadSeq) return;
      columns = data.columns;
      const all = state.kinds.get(kind)?.count;
      count.textContent = all != null && all !== data.total ? `${fmtNumber(data.total)} of ${fmtNumber(all)}` : plural(data.total, 'row');
      body.replaceChildren(renderRows(data));
      const paged = data.rows.length > 0 && data.total > data.rows.length;
      pagerTop.replaceChildren(...(data.rows.length || !data.offset ? pager(data) : []));
      pagerFoot.replaceChildren(...(paged ? pager(data) : []));
      if (el.isConnected) fit(true);
      if (previous.params.get('offset') !== route.params.get('offset')) {
        document.getElementById('main')?.scrollTo({ top: 0 });
      }
    } catch (err) {
      // An API error (a bad parameter: 400) or a bug: either way a notice, never a crash.
      if (mine === loadSeq) fail(err?.message || String(err));
    }
  }

  const el = h('div', { class: 'table-view' },
    h('div', { class: 'view-head' }, h('h1', { tabindex: '-1' }, kindDot(kind), kindTitle(kind)), count, trimNote),
    description(schema.description),
    h('div', { class: 'toolbar' }, filter, chips, h('span', { class: 'menu-wrap' }, colButton, colMenu), pagerTop),
    body, pagerFoot);
  await update(route);
  return {
    key: route.key, el, update, fit: () => fit(true), title: kindTitle(kind), kind,
    draftFilter: () => filter.value,
    restoreDraft(value) {
      filter.value = value;
      if (value.trim() !== (current.params.get('q') || '')) onFilter();
    },
    destroy() { filter.removeEventListener('input', onFilter); onFilter.cancel(); ++loadSeq; },
  };
}

const ROW = 'tbody tr[data-id], tbody tr[data-href]';

/**
 * Rows that open something: a click (not on a link or control, not ending a text
 * selection) or Enter on a focused row opens the row's record or `data-href`.
 */
export function wireRows(table) {
  const open = (tr) => go(tr.dataset.href || entityHref(tr.dataset.id));
  table.addEventListener('click', (event) => {
    if (event.target.closest('a, button, input, label') || String(getSelection()).length) return;
    const tr = event.target.closest(ROW);
    if (tr) open(tr);
  });
  table.addEventListener('keydown', (event) => {
    if (event.key === 'Enter' && event.target.matches?.(ROW)) open(event.target);
  });
  return table;
}

/** Move keyboard focus to the next or previous row (j/k); true when a row moved. */
export function moveRowFocus(delta) {
  const rows = [...document.querySelectorAll(`#view .grid ${ROW.replace(', ', ', #view .grid ')}`)];
  if (!rows.length) return false;
  const index = rows.indexOf(document.activeElement);
  const next = rows[index < 0 ? 0 : Math.min(rows.length - 1, Math.max(0, index + delta))];
  for (const row of rows) row.tabIndex = row === next ? 0 : -1;
  next.focus({ preventScroll: true });
  next.scrollIntoView({ block: 'nearest' });
  return true;
}
