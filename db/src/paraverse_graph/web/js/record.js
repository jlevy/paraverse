// The one record view every kind shares. Fields render in schema order from the full
// payload (`doc`), nested `$defs` shapes recursively; references become entity chips
// through the entity's `refs` map; relationships, sources and raw JSON follow.

import { api, state } from './api.js';
import { copyable, copyButton, fieldTitle, fmtNumber, h, humanize, imageUrl, safeUrl } from './dom.js';
import {
  chip, cluster, disambiguate, extLink, kindDot, kindTitle, plural, prose, relTitle, relatedHref, scalar,
  tableHref, tag, TYPED_ID,
} from './values.js';

const IMAGE_FIELDS = ['photo_url', 'logo_url', 'image_url', 'avatar_url'];
const IMAGE_NAME = /(^|_)(photo|logo|image|avatar|thumbnail|banner)(_url)?$/;
const SKIP = new Set(['id', 'sources']); // shown in the header and the Sources section
const MAX_DEPTH = 6;
// Long lists show their first few entries and a "Show N more" toggle.
const PREVIEW_ROWS = 10;
const PREVIEW_STACK = 5;
const PREVIEW_CHIPS = 24;
const PREVIEW_RELATED = 12; // chips per relationship type

const dropImage = (event) => event.target.remove(); // a dead image URL shows nothing
const isObject = (v) => v !== null && typeof v === 'object' && !Array.isArray(v);
const isEmpty = (v) => v == null || v === '' || (Array.isArray(v) && v.length === 0)
  || (isObject(v) && Object.keys(v).length === 0);

function section(title, body, hint) {
  return h('section', { class: 'section' },
    h('h2', { class: 'section-heading' }, title, hint ? h('span', { class: 'hint num' }, hint) : null), body);
}

/**
 * Append the first `limit` rendered items to `parent`; return a toggle that shows
 * and hides the rest (rendered on first use), or null when everything fits. A list
 * only a little over the limit is shown whole.
 */
function limited(parent, items, render, limit) {
  const shown = items.length > limit + 2 ? limit : items.length;
  parent.append(...items.slice(0, shown).map(render));
  if (shown === items.length) return null;
  const label = `Show ${fmtNumber(items.length - shown)} more`;
  const button = h('button', { type: 'button', class: 'show-more', 'aria-expanded': 'false' }, label);
  let rest = null;
  button.addEventListener('click', () => {
    const open = button.getAttribute('aria-expanded') !== 'true';
    rest ??= items.slice(shown).map(render);
    if (open) parent.append(...rest);
    else for (const node of rest) node.remove();
    button.setAttribute('aria-expanded', String(open));
    button.textContent = open ? 'Show fewer' : label;
    if (!open) button.scrollIntoView({ block: 'nearest' });
  });
  return button;
}

/** The fields to show for some objects: def fields in order, then any extra keys. */
function fieldsFor(objects, defFields = []) {
  const present = (name) => objects.some((o) => !isEmpty(o[name]));
  const known = new Set(defFields.map((f) => f.name));
  const extra = [...new Set(objects.flatMap((o) => Object.keys(o)))].filter((k) => !known.has(k));
  return [...defFields.filter((f) => present(f.name)), ...extra.filter(present).map((name) => ({ name, title: humanize(name) }))];
}

/** A scalar with its field's help: references, images, URLs, enums, long text. */
function scalarValue(value, f, ctx, top) {
  if (typeof value === 'string') {
    const ref = ctx.refs[value];
    if (ref || (f.ref_kinds && TYPED_ID.test(value))) return chip(value, ref?.name, ref?.kind);
    const href = safeUrl(value);
    if (href && IMAGE_NAME.test(f.name) && imageUrl(href)) {
      return h('span', null, h('img', { class: 'thumb', src: href, alt: '', loading: 'lazy', referrerpolicy: 'no-referrer', onerror: dropImage }), extLink(href));
    }
    if (f.enum) return top ? filterTag(ctx.kind, f, value, value) : tag(value);
    if (!href && (value.length > 100 || value.includes('\n'))) return prose(value);
  }
  if (typeof value === 'boolean' && top) return filterTag(ctx.kind, f, value, value ? 'yes' : 'no');
  return scalar(value, f.name);
}

// Top-level enums and flags link to the table of every record sharing the value.
function filterTag(kind, f, value, label) {
  const href = tableHref(kind, { [`f.${f.name}`]: String(value) });
  return h('a', { class: 'tag on', href, 'data-tooltip': `All ${kindTitle(kind)} records with ${fieldTitle(f)} = ${value}` }, label);
}

/** Render any payload value, using its schema field (and `$def`) when there is one. */
function value(v, f, ctx, depth = 0, top = false) {
  if (depth > MAX_DEPTH) return h('code', null, JSON.stringify(v));
  const defFields = (f.def && ctx.defs[f.def]) || [];
  if (Array.isArray(v)) {
    const items = v.filter((x) => !isEmpty(x));
    if (items.length && items.every(isObject)) return objectList(items, defFields, ctx, depth);
    if (items.some((x) => typeof x === 'string' && x.length > 80 && !ctx.refs[x])) {
      return h('div', { class: 'stack' }, items.map((x) => h('div', { class: 'stack-item' }, value(x, f, ctx, depth + 1))));
    }
    return cluster(items.map((x) => listItem(x, f, ctx, top)), PREVIEW_CHIPS);
  }
  if (isObject(v)) return definitionList(fieldsFor([v], defFields), v, ctx, depth + 1);
  return scalarValue(v, f, ctx, top);
}

function listItem(x, f, ctx, top) {
  if (isObject(x) || Array.isArray(x)) return h('code', null, JSON.stringify(x));
  const node = scalarValue(x, f, ctx, top);
  return typeof node === 'string' ? tag(node) : node;
}

function definitionList(fields, obj, ctx, depth, top = false) {
  const items = fields.filter((f) => !isEmpty(obj[f.name])).flatMap((f) => [
    h('dt', { 'data-tooltip': f.description || null }, fieldTitle(f)),
    h('dd', null, value(obj[f.name], f, ctx, depth, top)),
  ]);
  return items.length ? h('dl', { class: 'fields' }, items) : null;
}

// A list of objects is a compact sub-table when every value fits a cell (scalars,
// short lists, objects of scalars); otherwise each object is its own definition list.
function fitsCell(v, budget = 2) {
  if (v == null || typeof v !== 'object') return typeof v !== 'string' || v.length <= 140;
  if (budget === 0) return false;
  const values = Array.isArray(v) ? v : Object.values(v);
  return values.length <= 12 && values.every((x) => fitsCell(x, budget - 1));
}

function objectList(items, defFields, ctx, depth) {
  const fields = fieldsFor(items, defFields);
  if (fields.length <= 8 && items.every((it) => fields.every((f) => fitsCell(it[f.name])))) {
    return subTable(items, fields, ctx);
  }
  const stack = h('div', { class: 'stack' });
  const more = limited(stack, items, (it) => h('div', { class: 'stack-item' }, definitionList(fields, it, ctx, depth + 1)), PREVIEW_STACK);
  return [stack, more];
}

function subTable(items, fields, ctx) {
  const body = h('tbody');
  const more = limited(body, items, (it) => h('tr', null,
    fields.map((f) => h('td', null, isEmpty(it[f.name]) ? null : compact(it[f.name], f, ctx)))), PREVIEW_ROWS);
  return [h('div', { class: 'sub-wrap' }, h('table', { class: 'sub' },
    h('thead', null, h('tr', null, fields.map((f) => h('th', { 'data-tooltip': f.description || null }, fieldTitle(f))))),
    body)), more];
}

/** A value inside a sub-table cell: nested objects become one muted-key line each. */
function compact(v, f, ctx) {
  if (Array.isArray(v)) {
    if (v.every(isObject)) return v.map((o) => h('div', { class: 'line' }, inlineObject(o, f, ctx)));
    return cluster(v.map((x) => listItem(x, f, ctx, false)), 12);
  }
  if (isObject(v)) return inlineObject(v, f, ctx);
  return scalarValue(v, f, ctx, false);
}

function inlineObject(o, f, ctx) {
  const defs = new Map(((f.def && ctx.defs[f.def]) || []).map((d) => [d.name, d]));
  const parts = [];
  for (const [key, val] of Object.entries(o)) {
    if (isEmpty(val)) continue;
    const sub = defs.get(key) || { name: key };
    if (parts.length) parts.push(h('span', { class: 'muted' }, ' · '));
    parts.push(h('span', { class: 'muted' }, `${fieldTitle(sub).toLowerCase()} `), compact(val, sub, ctx));
  }
  return parts;
}

function header(data) {
  const doc = data.doc || {};
  const image = IMAGE_FIELDS.map((name) => imageUrl(doc[name])).find(Boolean);
  const primary = state.kinds.get(data.kind)?.label;
  const labels = (data.labels || []).filter((l) => l !== 'Entity' && l !== primary);
  return h('header', { class: 'record-head' },
    image ? h('img', { class: 'avatar', src: image, alt: '', loading: 'lazy', referrerpolicy: 'no-referrer', onerror: dropImage }) : null,
    h('div', null,
      h('div', { class: 'eyebrow' },
        h('a', { class: 'tag on', href: tableHref(data.kind), 'data-tooltip': `Open the ${kindTitle(data.kind)} table` }, kindDot(data.kind), ' ', kindTitle(data.kind)),
        labels.map((l) => tag(l, { tooltip: 'Graph label' }))),
      h('h1', { tabindex: '-1' }, data.name || data.id),
      h('div', { class: 'meta-line' },
        h('span', null, 'ID ', copyable(data.id, 'ID')),
        data.kb_path ? h('span', null, 'KB path ', copyable(data.kb_path, 'KB path')) : null)));
}

function fieldsSection(data, schema, ctx) {
  const doc = data.doc || {};
  const fields = schema ? schema.fields : [];
  const shown = fieldsFor([doc], fields).filter((f) => !SKIP.has(f.name));
  return section('Fields', definitionList(shown, doc, ctx, 0, true) || h('p', { class: 'muted' }, 'No fields.'));
}

// One relationship type. Items arrive one per link, so an entity linked several times
// (an affiliation from several sources) is merged into one entry that keeps each
// distinct link's properties.
function entities(group) {
  const byId = new Map();
  for (const it of group.items) {
    const edge = it.edge || {};
    const key = JSON.stringify(edge);
    const seen = byId.get(it.id);
    if (!seen) byId.set(it.id, { ...it, edges: [edge], keys: new Set([key]) });
    else if (!seen.keys.has(key)) {
      seen.edges.push(edge);
      seen.keys.add(key);
    }
  }
  return disambiguate([...byId.values()]);
}

/** The kinds a group's "table" links cover; a truncated group also asks the schema. */
function groupKinds(group, unique, schema) {
  const kinds = new Set(unique.map((it) => it.kind).filter(Boolean));
  if (group.distinct > unique.length) {
    const column = schema?.relationships?.find((r) => r.direction === group.direction && r.type === group.type);
    for (const kind of column?.kinds || []) kinds.add(kind);
  }
  return [...kinds];
}

// One line per link, aligned across the columns, so each line reads as one link.
function edgeCell(it, key, ctx) {
  const one = (edge) => (isEmpty(edge[key]) ? null : compact(edge[key], { name: key }, ctx));
  if (it.edges.length === 1) return one(it.edges[0]);
  return it.edges.map((edge) => h('div', { class: 'line' }, one(edge)));
}

function relationGroup(group, id, ctx, schema) {
  const unique = group.unique;
  const kinds = groupKinds(group, unique, schema);
  const truncated = group.distinct > unique.length;
  const edgeKeys = [...new Set(group.items.flatMap((it) => Object.keys(it.edge || {})))].filter((k) => unique.some((it) => it.edges.some((e) => !isEmpty(e[k]))));
  // A property every link shares ("basis session_facets") is said once, not per row.
  const allEdges = unique.flatMap((it) => it.edges);
  const constant = truncated ? [] : edgeKeys.filter((k) => !isEmpty(allEdges[0][k])
    && allEdges.every((e) => JSON.stringify(e[k]) === JSON.stringify(allEdges[0][k])));
  const varying = edgeKeys.filter((k) => !constant.includes(k));
  const note = constant.length
    ? h('span', { class: 'edge-note' }, inlineObject(Object.fromEntries(constant.map((k) => [k, allEdges[0][k]])), { name: '' }, ctx))
    : null;
  const links = group.distinct > 1 ? kinds.map((k) => h('a', { class: 'table-link', href: relatedHref(k, group.direction, group.type, id) },
    kinds.length > 1 ? `${kindTitle(k)} table →` : truncated ? `All ${fmtNumber(group.distinct)} in table →` : 'Open as table →')) : [];
  const tableLinks = links.length ? h('span', { class: 'table-links' }, links) : null;
  const arrow = group.direction === 'out' ? '→' : '←';
  const tip = `${arrow} ${group.type}\n${plural(group.distinct, 'entity', 'entities')}`
    + (group.count !== group.distinct ? ` through ${plural(group.count, 'link')}` : '');
  // A group with more entities than arrived shows a preview and its table link; a
  // complete one can reveal the rest in place.
  let body;
  if (!varying.length && kinds.length <= 1) {
    const chips = unique.map((it) => chip(it.id, it.name, it.kind));
    body = [truncated ? cluster(chips.slice(0, PREVIEW_RELATED)) : cluster(chips, PREVIEW_RELATED), note, tableLinks];
  } else {
    const rows = h('tbody');
    const more = limited(rows, truncated ? unique.slice(0, PREVIEW_ROWS) : unique, (it) => h('tr', null,
      h('td', null, chip(it.id, it.name, it.kind)),
      kinds.length > 1 ? h('td', { class: 'muted' }, kindTitle(it.kind)) : null,
      varying.map((k) => h('td', null, edgeCell(it, k, ctx)))), PREVIEW_ROWS);
    body = [note ? h('div', null, note) : null, h('div', { class: 'sub-wrap' }, h('table', { class: 'sub' },
      h('thead', null, h('tr', null, h('th', null, 'Entity'), kinds.length > 1 ? h('th', null, 'Kind') : null,
        varying.map((k) => h('th', { 'data-tooltip': 'Relationship property' }, humanize(k))))),
      rows)), more, tableLinks];
  }
  return [
    h('dt', { 'data-tooltip': tip }, relTitle(group.direction, group.type),
      h('span', { class: 'rel-count num' }, fmtNumber(group.distinct))),
    h('dd', { class: 'rel-body' }, body),
  ];
}

function relationsSection(data, ctx, schema) {
  const rels = data.relationships || { out: [], in: [] };
  const groups = [...rels.out.map((g) => ({ ...g, direction: 'out' })), ...rels.in.map((g) => ({ ...g, direction: 'in' }))];
  if (!groups.length) return section('Relationships', h('p', { class: 'muted' }, 'No relationships.'));
  for (const g of groups) {
    g.unique = entities(g);
    g.distinct ??= g.count > g.items.length ? g.count : g.unique.length; // an older API sends links only
  }
  // A type whose every entity the Fields section already shows is folded away.
  const inFields = (g) => g.distinct === g.unique.length && g.unique.every((it) => it.id in ctx.refs);
  const shown = groups.filter((g) => !inFields(g));
  const folded = groups.filter(inFields);
  const list = (gs) => h('dl', { class: 'fields rels' }, gs.flatMap((g) => relationGroup(g, data.id, ctx, schema)));
  const links = groups.reduce((n, g) => n + g.count, 0);
  return section('Relationships', [
    shown.length ? list(shown) : null,
    folded.length ? h('details', { class: 'folded' },
      h('summary', null, shown.length ? 'Also shown in Fields: ' : 'All shown in Fields: ',
        h('span', { class: 'muted' }, folded.map((g) => relTitle(g.direction, g.type)).join(', '))),
      list(folded)) : null,
  ], `${plural(links, 'link')} in ${plural(groups.length, 'type')}`);
}

function sourcesSection(data, ctx) {
  const sources = (data.doc?.sources || []).filter(isObject);
  if (!sources.length) return null;
  return section('Sources', subTable(sources, fieldsFor(sources, ctx.defs.Source), ctx), String(sources.length));
}

function rawBlock(label, object) {
  const json = JSON.stringify(object, null, 2);
  return h('details', { class: 'raw' }, h('summary', null, label),
    h('pre', { class: 'copy-surface' }, h('code', { 'data-copy-value': json }, json), copyButton(label)));
}

export async function mountRecord(route) {
  const data = await api.entity(route.id);
  const schema = data.kind ? await api.schema(data.kind).catch(() => null) : null;
  const ctx = { refs: data.refs || {}, defs: schema?.defs || {}, kind: data.kind };
  const el = h('article', { class: 'record' },
    header(data),
    fieldsSection(data, schema, ctx),
    relationsSection(data, ctx, schema),
    sourcesSection(data, ctx),
    section('Raw', [rawBlock('Document JSON', data.doc), rawBlock('Graph properties', data.properties)]));
  return { key: route.key, el, title: data.name || data.id, kind: data.kind, id: data.id };
}
