// Recover from missed reload notifications and routes left over from another dataset.

import { api } from './api.js';
import { parseRoute } from './router.js';
import { parseRelFilter, tableHref } from './values.js';

export function sameGraphVersion(left, right) {
  return Boolean(left && right && left.load_id === right.load_id
    && left.kb_digest === right.kb_digest && left.loaded_at === right.loaded_at);
}

/** SSE is immediate; this independent check also sees loads whose publish failed. */
export function watchGraphVersion(current, changed, interval = 30_000) {
  let timer = null;
  let checking = false;
  let stopped = false;
  let controller = null;
  async function check() {
    if (checking || stopped) return;
    clearTimeout(timer);
    checking = true;
    controller = new AbortController();
    const timeout = setTimeout(() => controller?.abort(), 10_000);
    try {
      // Do not mutate shared meta until graphLoaded has invalidated its other caches.
      const response = await fetch('/api/meta', {
        headers: { Accept: 'application/json' }, cache: 'no-store', signal: controller.signal,
      });
      if (!response.ok) return;
      const meta = await response.json();
      if (!stopped && !sameGraphVersion(meta, current())) await changed();
    } catch {
      // A temporary connection failure never disables later reconciliation.
    } finally {
      clearTimeout(timeout);
      controller = null;
      checking = false;
      if (!stopped) timer = setTimeout(check, interval);
    }
  }
  timer = setTimeout(check, interval);
  return {
    check,
    stop() { stopped = true; clearTimeout(timer); controller?.abort(); },
  };
}

const RELOAD_SCALAR_TYPES = new Set(['string', 'integer', 'number', 'boolean']);

/** Preserve valid parameters on a rebuild; a changed selection starts a fresh table. */
export async function tableRouteAfterReload(hash, kinds, datasetChanged) {
  const route = parseRoute(hash);
  if (route.name !== 'table') return hash;
  if (!kinds.has(route.kind)) return '#/';
  if (datasetChanged) return tableHref(route.kind);
  const schema = await api.schema(route.kind);
  const fields = new Map(schema.fields.map((field) => [field.name, field]));
  const computed = new Set(schema.computed);
  const relationships = new Set(schema.relationships.map((rel) => rel.name));
  const columns = new Set([...fields.keys(), ...computed, ...relationships]);
  const params = new URLSearchParams(route.params);
  let repaired = false;
  const remove = (key) => { params.delete(key); repaired = true; };
  if (params.has('cols')) {
    const previous = params.get('cols').split(',');
    const valid = previous.filter((name) => columns.has(name));
    if (valid.length !== previous.length) {
      if (valid.length) params.set('cols', valid.join(','));
      else params.delete('cols');
      repaired = true;
    }
  }
  const scalar = (name) => {
    const field = fields.get(name);
    return field && RELOAD_SCALAR_TYPES.has(field.type) && !field.ref_kinds && !field.def;
  };
  for (const [key] of [...params]) {
    if (key.startsWith('f.') && !computed.has(key.slice(2)) && !scalar(key.slice(2))) remove(key);
  }
  const sort = params.get('sort');
  if (sort && !['id', 'display_name'].includes(sort) && !computed.has(sort)
    && !(scalar(sort) && !fields.get(sort).list)) {
    remove('sort');
    params.delete('order');
  }
  if (params.has('rel')) {
    const rel = parseRelFilter(params.get('rel'));
    if (!rel || !relationships.has(`${rel.direction}:${rel.type}`)) remove('rel');
  }
  if (!repaired) return hash;
  params.delete('offset');
  return tableHref(route.kind, Object.fromEntries(params));
}
