// Hash routes, so every view is a deep link and works inside an iframe or a
// WKWebView without server routes:
//   #/, #/overview            overview
//   #/t/<kind>?sort&order&q&cols&rel&f.<field>&offset   a table
//   #/e/<id>                  a record
//   #/review, #/review/<name> review checks
//   #/search?q&kinds          search results

import { decodePart } from './dom.js';

let renderer = () => {};

export function setRenderer(fn) {
  renderer = fn;
}

/** Navigate. `replace` rewrites the current history entry (typing in a filter). */
export function go(hash, { replace = false } = {}) {
  if (replace) {
    history.replaceState(history.state, '', hash);
    renderer();
  } else {
    location.hash = hash;
  }
}

export function parseRoute(hash) {
  const raw = String(hash || '').replace(/^#\/?/, '');
  const cut = raw.indexOf('?');
  const path = cut < 0 ? raw : raw.slice(0, cut);
  const params = new URLSearchParams(cut < 0 ? '' : raw.slice(cut + 1));
  const [head, ...rest] = path.split('/');
  const tail = decodePart(rest.join('/'));
  if (head === 't' && tail) return { name: 'table', kind: tail, params, key: `t/${tail}` };
  if (head === 'e' && tail) return { name: 'entity', id: tail, params, key: `e/${tail}` };
  if (head === 'review') return tail ? { name: 'check', check: tail, params, key: `review/${tail}` } : { name: 'review', params, key: 'review' };
  if (head === 'search') return { name: 'search', params, key: 'search' };
  return { name: 'overview', params, key: 'overview' };
}
