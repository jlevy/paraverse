// Home, review and error views.

import { api, state } from './api.js';
import { fmtNumber, h, relativeAge } from './dom.js';
import { wireRows } from './table.js';
import { chip, chipLabel, description, kindDot, kindOfId, kindTitle, tableHref, tag, TYPED_ID_IN_TEXT } from './values.js';

// Severity, most severe first; `blocker` outranks `high`.
const SEVERITY_ORDER = { blocker: 0, high: 1, medium: 2, low: 3, info: 4 };

export function severityTag(severity) {
  return h('span', { class: `tag sev-${severity}` }, severity);
}

const areaTitle = (area) => (area ? area.charAt(0).toUpperCase() + area.slice(1) : 'Other');

const findings = (check) => (check.truncated ? `${fmtNumber(check.count)}+` : fmtNumber(check.count));

function checksTable(checks) {
  const rank = (c) => SEVERITY_ORDER[c.severity] ?? 9;
  const sorted = [...checks].sort((a, b) => rank(a) - rank(b) || String(a.area).localeCompare(String(b.area)));
  return wireRows(h('table', { class: 'grid' },
    h('thead', null, h('tr', null, h('th', null, 'Severity'), h('th', null, 'Area'), h('th', null, 'Check'),
      h('th', null, 'Description'), h('th', { class: 'right' }, 'Findings'))),
    h('tbody', null, sorted.map((check, index) => {
      const href = `#/review/${encodeURIComponent(check.name)}`;
      return h('tr', { 'data-href': href, tabindex: index ? '-1' : '0' },
        h('td', null, severityTag(check.severity)),
        h('td', null, tag(areaTitle(check.area))),
        h('td', null, h('a', { href }, check.title)),
        h('td', { class: 'muted' }, check.description),
        h('td', { class: 'right num' }, check.count ? findings(check) : h('span', { class: 'muted' }, '0')));
    }))));
}

export async function mountHome(route) {
  const meta = state.meta;
  // The review checks are the slowest query; the section fills in when they arrive.
  const review = h('section', { class: 'section' },
    h('h2', { class: 'section-heading' }, 'Review', h('span', { class: 'hint' }, h('a', { href: '#/review' }, 'All checks →'))),
    h('p', { class: 'muted' }, 'Running checks…'));
  api.review().then((data) => {
    const open = data.checks.filter((c) => c.count > 0);
    review.lastChild.replaceWith(open.length ? checksTable(open) : h('p', { class: 'muted' }, 'Every check passes.'));
  }, () => review.remove());
  const el = h('div', null,
    h('div', { class: 'view-head' },
      h('h1', { tabindex: '-1' }, 'Knowledge base'),
      h('span', { class: 'count' },
        `${fmtNumber(meta.node_total)} entities · ${fmtNumber(meta.edge_total)} relationships in `
        + `${Object.keys(meta.relationships).length} types · loaded ${relativeAge(meta.loaded_at) || meta.loaded_at}`)),
    meta.groups.filter((g) => g.kinds.length).map((group) => h('section', { class: 'section' },
      h('h2', { class: 'section-heading' }, group.title),
      h('div', { class: 'kind-grid' }, group.kinds.map((k) => h('a', { class: 'kind-card', href: tableHref(k.kind) },
        h('div', { class: 'kind-card-title' }, kindDot(k.kind), kindTitle(k.kind), h('span', { class: 'count' }, fmtNumber(k.count))),
        description(String(k.description || '').split(/\n\s*\n/)[0])))))),
    review);
  return { key: route.key, el, title: 'Home' };
}

const total = (checks) => checks.reduce((n, c) => n + c.count, 0);

/** Every check, filterable by area (`#/review?area=people`). */
export async function mountReview(route) {
  const review = await api.review();
  const area = route.params.get('area') || '';
  const areas = [...new Set(review.checks.map((c) => c.area || ''))].sort();
  const shown = review.checks.filter((c) => !area || (c.area || '') === area);
  const tab = (value, label, checks) => h('a', {
    class: 'tag', href: value ? `#/review?area=${encodeURIComponent(value)}` : '#/review',
    'aria-current': value === area ? 'true' : null,
  }, `${label} · ${fmtNumber(total(checks))}`);
  const el = h('div', null,
    h('div', { class: 'view-head' }, h('h1', { tabindex: '-1' }, 'Review'),
      h('span', { class: 'count' }, `${shown.length} checks · ${fmtNumber(total(shown))} findings`)),
    h('p', { class: 'desc' }, 'Read-only data-quality checks over the graph. Each finding links to the entity it is about.'),
    h('div', { class: 'toolbar cluster', role: 'navigation', 'aria-label': 'Areas' },
      tab('', 'All areas', review.checks),
      areas.map((a) => tab(a, areaTitle(a), review.checks.filter((c) => (c.area || '') === a)))),
    checksTable(shown));
  return { key: route.key, el, title: 'Review' };
}

/** Detail text with any typed IDs in it turned into entity chips. */
function detail(text) {
  const s = String(text ?? '');
  const out = [];
  let last = 0;
  for (const m of s.matchAll(TYPED_ID_IN_TEXT)) {
    const id = m[0].replace(/\.+$/, ''); // a sentence's full stop is not part of the ID
    out.push(s.slice(last, m.index), idChip(id));
    last = m.index + id.length;
  }
  out.push(s.slice(last));
  return out;
}

/** A chip for an ID known only as text: it takes the entity's name, or shows as missing. */
function idChip(id) {
  const el = chip(id, id, kindOfId(id));
  api.card(id).then((card) => {
    if (card.name) el.querySelector('.chip-label')?.replaceWith(chipLabel(card.name));
  }, (err) => {
    if (err?.status === 404) el.replaceWith(chip(id, id, null));
  });
  return el;
}

export async function mountReviewCheck(route) {
  const check = await api.reviewCheck(route.check);
  const rows = check.rows || [];
  const el = h('div', null,
    h('p', { class: 'small' }, h('a', { href: '#/review' }, '← Review')),
    h('div', { class: 'view-head' }, h('h1', { tabindex: '-1' }, check.title), severityTag(check.severity),
      check.area ? tag(areaTitle(check.area)) : null,
      h('span', { class: 'count' }, `${findings(check)} findings`)),
    h('p', { class: 'desc' }, check.description),
    h('div', { class: 'section' }, rows.length
      ? wireRows(h('table', { class: 'grid' },
        h('thead', null, h('tr', null, h('th', null, 'Entity'), h('th', null, 'Kind'), h('th', null, 'Detail'))),
        h('tbody', null, rows.map((row, index) => h('tr', { 'data-id': row.id, tabindex: index ? '-1' : '0' },
          h('td', null, chip(row.id, row.name, kindOfId(row.id))),
          h('td', null, tag(kindTitle(kindOfId(row.id)))),
          h('td', null, detail(row.detail)))))))
      : h('p', { class: 'empty' }, 'No findings: this check passes.')),
    check.truncated ? h('p', { class: 'muted small' }, `Showing the first ${rows.length} findings.`) : null);
  return { key: route.key, el, title: check.title };
}

export function errorView(err) {
  const notFound = err?.status === 404;
  const el = h('div', { class: 'error-box', role: 'alert' },
    h('h1', null, notFound ? 'Not found' : 'Could not load this view'),
    h('p', null, err?.message || String(err)),
    h('p', null, h('a', { href: '#/' }, 'Go to the home page')));
  return { key: 'error', el, title: notFound ? 'Not found' : 'Error' };
}
