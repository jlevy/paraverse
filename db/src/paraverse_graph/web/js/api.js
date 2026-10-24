// The JSON API client and the small caches the views share. Every call is a
// same-origin GET; errors carry the server's `{error}` message and status.

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

async function get(path, params) {
  const search = params ? new URLSearchParams(Object.entries(params).filter(([, v]) => v != null && v !== '')) : null;
  const url = search && [...search].length ? `${path}?${search}` : path;
  let response;
  try {
    response = await fetch(url, { headers: { Accept: 'application/json' } });
  } catch {
    throw new ApiError('The server is not reachable.', 0);
  }
  let body = null;
  try {
    body = await response.json();
  } catch {
    // A non-JSON error page; the status line below still explains it.
  }
  if (!response.ok) throw new ApiError(body?.error || `${response.status} ${response.statusText}`, response.status);
  return body;
}

const enc = encodeURIComponent;
const schemas = new Map();
const cards = new Map();
let reviewPending = null;
let cacheGeneration = 0;

/** Shared state: the current meta and a kind index built from it. */
export const state = { meta: null, kinds: new Map(), review: null };

/** Full snapshot identity shared by metadata, overview and quality responses. */
export const loadIdentity = (load) => JSON.stringify(
  ['dataset', 'graph', 'kb_digest', 'loaded_at', 'load_id'].map((key) => load?.[key] ?? null),
);

export const api = {
  async meta() {
    const meta = await get('/api/meta');
    state.meta = meta;
    state.kinds = new Map(meta.groups.flatMap((g) => g.kinds.map((k) => [k.kind, { ...k, group: g.title }])));
    return meta;
  },
  schema(kind) {
    if (!schemas.has(kind)) {
      const pending = get(`/api/schema/${enc(kind)}`);
      pending.catch(() => schemas.delete(kind));
      schemas.set(kind, pending);
    }
    return schemas.get(kind);
  },
  rows: (kind, params) => get(`/api/rows/${enc(kind)}`, params),
  entity: (id) => get(`/api/entity/${enc(id)}`),
  card(id) {
    if (!cards.has(id)) {
      const pending = get(`/api/card/${enc(id)}`);
      pending.catch(() => cards.delete(id));
      cards.set(id, pending);
    }
    return cards.get(id);
  },
  search: (q, params) => get('/api/search', { q, ...params }),
  overview: () => get('/api/overview'),
  /** Check counts, shared by the top bar, overview and review views until a reload. */
  review() {
    if (!reviewPending) {
      const generation = cacheGeneration;
      const pending = get('/api/review').then((review) => {
        if (generation === cacheGeneration && loadIdentity(review.load) === loadIdentity(state.meta)) state.review = review;
        else if (reviewPending === pending) reviewPending = null;
        return review;
      });
      pending.catch(() => { if (reviewPending === pending) reviewPending = null; });
      reviewPending = pending;
    }
    return reviewPending;
  },
  reviewCheck: (name) => get(`/api/review/${enc(name)}`),
  /** After a graph reload every cached schema and card may be stale. */
  clearCaches() {
    cacheGeneration += 1;
    schemas.clear();
    cards.clear();
    reviewPending = null;
    state.review = null;
  },
};
