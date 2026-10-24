// Run with `node tests/overview_frontend.mjs` from db/. A minimal DOM keeps the
// async view lifecycle checks portable without adding a browser dependency.
import assert from 'node:assert/strict';

class TestNode {
  constructor(tag = '', text = '') {
    this.tagName = tag.toUpperCase();
    this.value = text;
    this.children = [];
    this.attributes = new Map();
    this.listeners = new Map();
    this.style = { setProperty() {} };
  }
  append(...nodes) {
    this.children.push(...nodes.map((node) => node instanceof TestNode ? node : new TestNode('', String(node))));
  }
  replaceChildren(...nodes) { this.children = []; this.append(...nodes); }
  setAttribute(key, value) { this.attributes.set(key, String(value)); }
  getAttribute(key) { return this.attributes.get(key) ?? null; }
  querySelector(selector) { return this.children.flatMap(all).find((node) => node.tagName === selector.toUpperCase()) ?? null; }
  addEventListener(name, handler) { this.listeners.set(name, handler); }
  click() { this.listeners.get('click')?.({ target: this }); }
  focus() { document.activeElement = this; }
  scrollIntoView() { this.scrolled = true; }
  get id() { return this.getAttribute('id'); }
  get textContent() { return this.value + this.children.map((child) => child.textContent).join(''); }
  set textContent(value) { this.value = String(value); this.children = []; }
}

globalThis.Node = TestNode;
globalThis.document = { createElement: (tag) => new TestNode(tag), activeElement: null };
let reloads = 0;
globalThis.location = { reload() { reloads += 1; } };

const { api, state } = await import('../src/paraverse_graph/web/js/api.js');
const { mountOverview, returnToOverview } = await import('../src/paraverse_graph/web/js/overview.js');
const { parseRoute } = await import('../src/paraverse_graph/web/js/router.js');
const originalReview = api.review;
const originalOverview = api.overview;
const route = parseRoute('#/overview');
assert.equal(route.name, 'overview');
assert.equal(parseRoute('#/').key, route.key);

function deferred() {
  let resolve, reject;
  const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}
const flush = async () => { await new Promise((resolve) => setImmediate(resolve)); };
const all = (node) => [node, ...node.children.flatMap(all)];
const section = (view, id) => all(view.el).find((node) => node.getAttribute('aria-labelledby') === `overview-${id}`);
const buttons = (node) => all(node).filter((child) => child.tagName === 'BUTTON');

function metadata(loadId = 'load-1') {
  return { dataset: 'sample', graph: 'sample_graph', kb_digest: 'digest', loaded_at: '2026-10-24T12:00:00Z', load_id: loadId,
    node_total: 10001, edge_total: 20, groups: [{ title: 'People', kinds: [{ kind: 'person', title: 'Person', count: 10001 }] }],
    relationships: { KNOWS: 20 } };
}
function overview(meta = state.meta) {
  return { load: { ...meta }, totals: { entities: 10001, relationships: 20, entity_kinds: 1, relationship_types: 1 },
    entities: [{ kind: 'person', group: 'People', count: 10001 }],
    relationships: [{ type: 'KNOWS', count: 20, from: ['person'], to: ['person'] }],
    sources: { entities_with_sources: 10000, entities_without_sources: 1, source_references: 10002, unique_urls: 2,
      providers: [{ source: 'github', entities: 10000, references: 10002, latest_retrieved_at: null }], latest_retrieved_at: null },
    coverage: [{ key: 'source_citations', title: 'Direct citations', kind: 'all', total: 10001, present: 10000, missing: 1,
      unknown: 1, note: 'Unknown metadata may overlap with present records.' }],
    editions: [{ id: 'event:one', name: '<img src=x>', edition: '2026', start: '2026-10-24', end: null, sessions: 2 }],
    participation: [{ basis: 'event_published', count: 2 }, { basis: 'self_reported', count: 1 }] };
}
const quality = (checks = [], meta = state.meta) => ({ load: { ...meta }, checks });
function reset() {
  state.meta = metadata();
  state.kinds = new Map([['person', { title: 'Person' }]]);
  const detail = deferred();
  const review = deferred();
  api.overview = () => detail.promise;
  api.review = () => review.promise;
  return { detail, review };
}

// Initial metadata stays useful while independent requests are pending.
let pending = reset();
let view = await mountOverview(route);
assert.match(view.el.textContent, /10,001/);
assert.match(section(view, 'entities').textContent, /Person/);
assert.match(section(view, 'sources').textContent, /Loading/);
assert.match(section(view, 'quality').textContent, /Running quality checks/);
buttons(view.el).find((button) => button.textContent === 'Sources').click();
assert.equal(document.activeElement.id, 'overview-sources');
assert.equal(document.activeElement.scrolled, true);
const main = { scrollTop: 900 };
assert.equal(returnToOverview(view, main), true);
assert.equal(main.scrollTop, 0);
assert.equal(document.activeElement.tagName, 'H1');
main.scrollTop = 900;
assert.equal(returnToOverview({ key: 't/person' }, main), false);
assert.equal(main.scrollTop, 900);
pending.detail.resolve(overview());
pending.review.resolve(quality([
  { name: 'missing', title: 'Missing source', severity: 'high', count: 5, truncated: true },
  { name: 'clear', title: 'Clear check', severity: 'low', count: 0, truncated: false },
]));
await flush();
assert.match(section(view, 'sources').textContent, /GitHub/);
assert.match(section(view, 'sources').textContent, /Not recorded/);
assert.match(section(view, 'coverage').textContent, /10,000 \/ 10,001/);
assert.doesNotMatch(section(view, 'coverage').textContent, /100%/);
assert.match(section(view, 'coverage').textContent, /1 unknown/);
assert.match(section(view, 'quality').textContent, /5\+/);
assert.match(section(view, 'quality').textContent, /lower bound/);
assert.ok(all(view.el).some((node) => node.getAttribute('href') === '#/review/missing'));
assert.ok(all(view.el).some((node) => node.getAttribute('href') === '#/t/person'));
assert.match(section(view, 'editions').textContent, /<img src=x>/);
assert.ok(all(view.el).every((node) => node.tagName !== 'IMG'));

// A failed section remains visible and retries to a successful result.
pending = reset();
view = await mountOverview(route);
pending.detail.reject(new Error('Summary offline'));
pending.review.reject(new Error('Checks offline'));
await flush();
assert.match(section(view, 'sources').textContent, /Summary offline/);
assert.match(section(view, 'quality').textContent, /Checks offline/);
api.overview = async () => overview();
api.review = async () => quality();
buttons(section(view, 'sources'))[0].click();
buttons(section(view, 'quality'))[0].click();
await flush();
assert.match(section(view, 'sources').textContent, /GitHub/);
assert.doesNotMatch(section(view, 'quality').textContent, /Checks offline/);

// A mismatched load cannot mix its counts into the mounted metadata.
pending = reset();
view = await mountOverview(route);
pending.detail.resolve(overview(metadata('load-2')));
await flush();
assert.match(section(view, 'sources').textContent, /graph changed/);
pending.review.resolve(quality());
await flush();
assert.match(section(view, 'quality').textContent, /graph changed/);
buttons(section(view, 'sources'))[0].click();
assert.equal(reloads, 1);

// Quality has its own identity even after the detailed overview was accepted.
pending = reset();
view = await mountOverview(route);
pending.detail.resolve(overview());
await flush();
const acceptedSources = section(view, 'sources').textContent;
pending.review.resolve(quality([{ name: 'new-load', title: 'New load result', severity: 'high', count: 7 }], metadata('load-2')));
await flush();
assert.match(section(view, 'quality').textContent, /graph changed while checks were running/);
assert.doesNotMatch(section(view, 'quality').textContent, /New load result/);
assert.equal(section(view, 'sources').textContent, acceptedSources);
buttons(section(view, 'quality'))[0].click();
assert.equal(reloads, 2);

// Failed metadata refresh leaves the mounted snapshot's retry actions usable.
pending = reset();
view = await mountOverview(route);
pending.detail.reject(new Error('Summary offline'));
pending.review.reject(new Error('Checks offline'));
await flush();
api.clearCaches();
globalThis.fetch = async () => ({ ok: false, status: 503, json: async () => ({ error: 'Refresh offline' }) });
await assert.rejects(api.meta(), /Refresh offline/);
assert.equal(state.meta.load_id, 'load-1');
api.overview = async () => overview();
api.review = async () => quality();
buttons(section(view, 'sources'))[0].click();
buttons(section(view, 'quality'))[0].click();
await flush();
assert.match(section(view, 'sources').textContent, /GitHub/);
assert.match(section(view, 'quality').textContent, /No quality checks are available/);

// Navigation disposal and a new metadata load both suppress late responses.
for (const change of ['dispose', 'reload']) {
  pending = reset();
  view = await mountOverview(route);
  const before = view.el.textContent;
  if (change === 'dispose') view.dispose();
  else state.meta = metadata('load-2');
  pending.detail.resolve(overview(metadata()));
  pending.review.resolve(quality());
  await flush();
  assert.equal(view.el.textContent, before);
}

// Clearing API caches prevents an older quality request repopulating shared state.
api.review = originalReview;
api.overview = originalOverview;
const requests = [];
globalThis.fetch = () => {
  const request = deferred();
  requests.push(request);
  return request.promise;
};
api.clearCaches();
const oldReview = api.review();
api.clearCaches();
const newReview = api.review();
requests[1].resolve({ ok: true, json: async () => quality([{ name: 'new' }]) });
await newReview;
requests[0].resolve({ ok: true, json: async () => quality([{ name: 'old' }]) });
await oldReview;
assert.equal(state.review.checks[0].name, 'new');
assert.equal(api.review(), newReview);

// A response for a different load is neither published nor retained in the cache.
api.clearCaches();
const mismatchedReview = api.review();
requests[2].resolve({ ok: true, json: async () => quality([{ name: 'wrong-load' }], metadata('load-3')) });
await mismatchedReview;
assert.equal(state.review, null);
const recoveredReview = api.review();
assert.notEqual(recoveredReview, mismatchedReview);
requests[3].resolve({ ok: true, json: async () => quality([{ name: 'recovered' }]) });
await recoveredReview;
assert.equal(state.review.checks[0].name, 'recovered');
console.log('Overview frontend lifecycle checks passed.');
