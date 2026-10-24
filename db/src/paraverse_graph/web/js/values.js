// Value primitives shared by every view: kind dots, entity chips, tags, external
// links, prose, and readable names for relationship columns.

import { state } from './api.js';
import { encodeId, fmtDateTime, fmtNumber, h, humanize, isIsoDateTime, qs, relativeAge, safeUrl, shortUrl, splitTitle } from './dom.js';

// Typed-ID prefixes, for a kind dot when only the ID is known (review rows).
const PREFIX_KINDS = { org: 'organization', gh: 'github_account', acct: 'social_account', site: 'website', repo: 'repository', pkg: 'package' };
const ID_PATTERN = '(?:event|day|session|person|profile|org|room|venue|experience|facet|term|gh|acct|site|repo|pkg|software|page):[a-z0-9][a-z0-9._/@+-]*';
export const TYPED_ID = new RegExp(`^${ID_PATTERN}$`);
/** Typed IDs inside running text (review details); global, so use with matchAll. */
export const TYPED_ID_IN_TEXT = new RegExp(`\\b${ID_PATTERN}`, 'g');

export function kindOfId(id) {
  const prefix = String(id).split(':', 1)[0];
  return PREFIX_KINDS[prefix] || prefix;
}

export const entityHref = (id) => `#/e/${encodeId(id)}`;
export const tableHref = (kind, params = {}) => `#/t/${encodeURIComponent(kind)}${qs(params)}`;

export function kindTitle(kind) {
  const info = state.kinds.get(kind);
  return info ? splitTitle(info.title) : humanize(kind || 'entity');
}

export function kindDot(kind) {
  const dot = h('span', { class: 'kdot', 'aria-hidden': 'true' });
  // Kind names come from the API; only plain identifiers may name a CSS token.
  if (/^[a-z_]+$/.test(kind || '')) dot.style.setProperty('--kc', `var(--kind-${kind})`);
  return dot;
}

/**
 * A chip's label. When the last word is what tells similar names apart (a year or
 * other number, the surname of a short name), a long label keeps it whole and
 * truncates in the middle: "GitHub Universe 2025" narrows to "GitHub Univ… 2025".
 * Other long labels (session titles) truncate at the end. The hover card shows all.
 */
export function chipLabel(text) {
  const s = String(text);
  const cut = s.lastIndexOf(' ');
  const tail = s.slice(cut + 1);
  const telling = (/\d/.test(tail) && tail.replace(/[^\w-]/g, '').length >= 3) || s.split(' ').length <= 3;
  if (s.length <= 16 || cut <= 0 || tail.length > 14 || !telling) return h('span', { class: 'chip-label' }, s);
  return h('span', { class: 'chip-label split' },
    h('span', { class: 'chip-head' }, s.slice(0, cut)), h('span', { class: 'chip-tail' }, s.slice(cut)));
}

/**
 * An entity reference: kind dot and name, linking to the record, with a hover card.
 * A reference whose entity has no node (`kind` null) renders as a muted ID.
 */
export function chip(id, name, kind) {
  if (!kind) {
    return h('span', { class: 'chip missing', 'data-tooltip': `${id}\nNo record in the graph` }, h('span', { class: 'chip-label' }, id));
  }
  return h('a', { class: 'chip', href: entityHref(id), 'data-card-id': id }, kindDot(kind), chipLabel(name || id));
}

export function tag(text, { tooltip, href, on } = {}) {
  if (href) return h('a', { class: 'tag on', href, 'data-tooltip': tooltip }, text);
  return h('span', { class: on ? 'tag on' : 'tag', 'data-tooltip': tooltip }, text);
}

export function boolTag(value) {
  return tag(value ? 'yes' : 'no', { on: value });
}

export function extLink(href) {
  return h('a', { class: 'ext', href, target: '_blank', rel: 'noopener noreferrer', 'data-tooltip': href }, shortUrl(href));
}

/**
 * Items whose names repeat within one list (`{id, name}`) get a hint from their IDs,
 * so the terms `term:topic-2024/ai` and `term:track-2024/ai` read "AI (topic-2024)"
 * and "AI (track-2024)".
 */
export function disambiguate(items) {
  const counts = new Map();
  for (const it of items) counts.set(it.name, (counts.get(it.name) || 0) + 1);
  const local = (id) => String(id).slice(String(id).indexOf(':') + 1);
  const hint = (id) => local(id).split('/')[0];
  return items.map((it) => {
    if (!it.name || counts.get(it.name) < 2) return it;
    const short = hint(it.id);
    const clash = items.some((o) => o !== it && o.name === it.name && hint(o.id) === short);
    return { ...it, name: `${it.name} (${clash ? local(it.id) : short})` };
  });
}

/** Up to `max` nodes, then a "+N" that reveals the rest in place. */
export function cluster(nodes, max = 40, moreHref) {
  const box = h('span', { class: 'cluster' }, nodes.slice(0, max));
  if (nodes.length > max) {
    const rest = nodes.length - max;
    if (moreHref) {
      box.append(h('a', { class: 'more', href: moreHref }, `+${fmtNumber(rest)}`));
    } else {
      const more = h('button', { type: 'button', class: 'more', 'aria-label': `Show ${rest} more` }, `+${fmtNumber(rest)}`);
      more.addEventListener('click', (event) => {
        event.stopPropagation();
        more.replaceWith(...nodes.slice(max));
      });
      box.append(more);
    }
  }
  return box;
}

/** A timestamp: relative age for `*_at` fields, else the wall-clock time. */
export function timeValue(value, name = '') {
  const label = name.endsWith('_at') ? relativeAge(value) || value : fmtDateTime(value);
  return h('time', { class: 'mono', datetime: value, 'data-tooltip': value, 'data-tooltip-literal': true }, label);
}

const DATE = /^\d{4}-\d{2}(-\d{2})?$/;

/** One scalar with no schema help: numbers, booleans, URLs, timestamps, text. */
export function scalar(value, name = '') {
  if (value == null || value === '') return null;
  if (typeof value === 'boolean') return boolTag(value);
  if (typeof value === 'number') return h('span', { class: 'num' }, fmtNumber(value));
  const href = safeUrl(value);
  if (href) return extLink(href);
  if (isIsoDateTime(value)) return timeValue(value, name);
  if (DATE.test(value)) return h('time', { datetime: value }, value); // never broken mid-date
  return String(value);
}

// Inline text: `code`, **bold**, [label](http...) and bare http(s) URLs become
// elements; everything else stays text. No other Markdown is interpreted.
const INLINE = /`([^`\n]+)`|\*\*([^*\n]+)\*\*|\[([^\]\n]+)\]\((https?:\/\/[^\s)]+)\)|(https?:\/\/[^\s<>()"']+[^\s<>()"'.,;:!?])/g;
export function inline(text) {
  const s = String(text);
  const out = [];
  let last = 0;
  for (const m of s.matchAll(INLINE)) {
    out.push(s.slice(last, m.index));
    const href = safeUrl(m[4] || m[5]);
    if (m[1]) out.push(h('code', null, m[1]));
    else if (m[2]) out.push(h('strong', null, m[2]));
    else if (href) out.push(h('a', { href, target: '_blank', rel: 'noopener noreferrer' }, m[3] || shortUrl(href)));
    else out.push(m[0]);
    last = m.index + m[0].length;
  }
  out.push(s.slice(last));
  return out;
}

/** One-line text (search snippets): Markdown bold markers dropped. */
export const plain = (text) => String(text ?? '').replace(/\*\*([^*\n]+)\*\*/g, '$1');

/** Long text, line breaks preserved (CSS pre-line), URLs linked. */
export function prose(text) {
  return h('div', { class: 'prose' }, inline(text));
}

/** A schema description: Markdown paragraphs, hard-wrapped lines joined. */
export function description(text, className = 'desc') {
  if (!text) return null;
  const paragraphs = String(text).split(/\n\s*\n/).map((p) => h('p', null, inline(p.replace(/\s*\n\s*/g, ' '))));
  return h('div', { class: className }, paragraphs);
}

// Relationship column names. `out:TYPE` reads as the verb; `in:TYPE` needs the
// inverse, which a small map supplies for the common types.
const INVERSE = {
  ABOUT_TOPIC: 'Sessions on topic', AFFILIATED_WITH: 'Affiliated people', CATALOG_TERM: 'Catalog term of',
  CONTRIBUTES_TO: 'Contributors', DELIVERED_AS: 'Sessions in format', DESCRIBES: 'Described by',
  DISTRIBUTES: 'Distributed by', EXPERT_IN: 'Experts', FEATURES: 'Featured at',
  FEATURES_PRODUCT: 'Featured in sessions', FOR_AUDIENCE: 'Sessions for audience', FOR_INDUSTRY: 'Sessions for industry',
  HAS_ACCOUNT: 'Account of', HAS_DAY: 'Day of', HAS_LEVEL: 'Sessions at level', HAS_TERM: 'In facet',
  HAS_TYPE: 'Sessions of type', HAS_WEBSITE: 'Website of', HELD_IN: 'Sessions held here', HOSTS: 'Hosted by',
  IN_CURATED_AGENDA: 'Sessions in agenda', IN_TRACK: 'Sessions in track', LINKS_TO: 'Linked from',
  LOCATED_AT: 'Location of', LOCATED_IN: 'Contains', MAINTAINS: 'Maintained by', MAKES: 'Made by',
  MENTIONS: 'Mentioned by', ORGANIZES: 'Organized by', OWNS: 'Owned by', PART_OF: 'Parts',
  PARTICIPATES_IN: 'Participants', PINNED: 'Pinned by', PINS: 'Pinned by', PRESENTS: 'Presented by',
  PUBLISHED_FROM: 'Packages published', PUBLISHES: 'Published by', RELATED_TO: 'Related from',
  SCHEDULED_ON: 'Sessions scheduled', SOURCE_OF: 'Source repositories', SPONSORS: 'Sponsored by',
  TOP_REPOSITORY: 'Top repository of', WORKS_WITH: 'Used by',
};

export function relTitle(direction, type) {
  const name = humanize(String(type || 'linked to').toLowerCase());
  if (direction === 'in') return INVERSE[type] || `← ${name}`;
  return name;
}

/** `out:PRESENTS:person:x` → {direction, type, id}; null when malformed. */
export function parseRelFilter(value) {
  const m = /^(in|out):([A-Z][A-Z0-9_]*):(.+)$/.exec(String(value || ''));
  return m ? { direction: m[1], type: m[2], id: m[3] } : null;
}

/** "1 link", "2 links": English plurals for the counts in headings. */
export function plural(count, one, many = `${one}s`) {
  return `${fmtNumber(count)} ${count === 1 ? one : many}`;
}

/** The table that lists everything entity `id` reaches through one relationship. */
export function relatedHref(kind, direction, type, id) {
  return tableHref(kind, { rel: `${direction === 'out' ? 'in' : 'out'}:${type}:${id}` });
}
