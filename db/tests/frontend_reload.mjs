import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';

const web = process.argv[2];
const source = (file) => fs.readFileSync(path.join(web, file), 'utf8')
  .replace(/^import[\s\S]*?;\n/gm, '').replace(/^export /gm, '');
let nextTimer = 0;
const timers = new Map();
const navigations = [];
const fields = [];
class Element {
  constructor(tag, props = {}) {
    Object.assign(this, props);
    this.tag = tag;
    this.value ??= '';
    this.listeners = new Map();
  }
  addEventListener(name, fn) { this.listeners.set(name, fn); }
  removeEventListener(name, fn) { if (this.listeners.get(name) === fn) this.listeners.delete(name); }
  replaceChildren() {}
  querySelector() { return null; }
  contains() { return false; }
}
const main = { scrollTop: 37 };
const display = new Element('div');
const document = {
  activeElement: null,
  body: { classList: { add() {}, remove() {} } },
  getElementById: (id) => id === 'main' ? main : display,
  querySelectorAll: () => [],
};
const common = {
  console, URLSearchParams, document,
  setTimeout(fn) { const id = ++nextTimer; timers.set(id, fn); return id; },
  clearTimeout(id) { timers.delete(id); },
  h(tag, props) { const el = new Element(tag, props); if (tag === 'input' && props?.['data-filter']) fields.push(el); return el; },
  go: (href) => navigations.push(href),
  qs: (values) => `?${new URLSearchParams(values)}`,
  store: { get() { return null; } }, wireMenu() {},
  kindTitle: (kind) => kind, kindDot() {}, icon() {}, description() {},
  plural: (n) => `${n}`, tableHref: (kind, values = {}) => `#/t/${kind}?${new URLSearchParams(values)}`,
  api: {
    schema: async () => ({ fields: [], computed: [], relationships: [] }),
    rows: async () => ({ columns: [], rows: [], total: 0, offset: 0 }),
  },
  state: { kinds: new Map() },
  ResizeObserver: class { observe() {} },
};
const debounceText = source('js/dom.js').split('function debounce(fn, ms) {')[1].split('\n/**')[0];
const debounceContext = vm.createContext({ ...common });
vm.runInContext(`function debounce(fn, ms) {${debounceText}`, debounceContext);
common.debounce = vm.runInContext('debounce', debounceContext);

for (const [name, file, exportName] of [['table', 'js/table.js', 'mountTable'], ['search', 'js/search.js', 'mountSearch']]) {
  timers.clear(); fields.length = 0; navigations.length = 0;
  const route = { name, kind: 'person', key: name === 'table' ? 't/person' : 'search', params: new URLSearchParams() };
  const module = vm.createContext({ ...common });
  vm.runInContext(source(file), module);
  const mount = vm.runInContext(exportName, module);
  const first = await mount(route);
  const field = fields.at(-1);
  field.value = 'unfinished';
  field.listeners.get('input')();
  assert.equal(timers.size, 1);
  const app = vm.createContext({
    ...common, window: {}, history: { state: { kbEntry: 1 } }, location: { hash: '#/' },
    parseRoute: () => route, mountTable: mount, mountSearch: mount,
    mountRecord() {}, mountReview() {}, mountReviewCheck() {}, mountHome() {},
    hideCard() {}, hideTooltip() {}, closeMenus() {},
  });
  app.window.parent = app.window;
  vm.runInContext(source('app.js').replace(/\nboot\(\);\s*$/, ''), app);
  app.first = first;
  await vm.runInContext('current = first; render({live:true})', app);
  const replacement = fields.at(-1);
  assert.equal(replacement.value, 'unfinished', `${name} draft survives live reload`);
  assert.equal(timers.size, 1, `${name} old callback was cancelled`);
  assert.equal(field.listeners.has('input'), false, `${name} removed input cannot reschedule`);
  assert.equal(main.scrollTop, 37);
  for (const fn of timers.values()) fn();
  assert.equal(navigations.length, 1);
  assert.ok(navigations[0].includes('q=unfinished'));
  timers.clear();
  const paged = await mount({...route, params: new URLSearchParams('offset=50')});
  paged.restoreDraft('');
  assert.equal(timers.size, 0, `${name} unchanged filter does not navigate or reset pagination`);
}
console.log('PASS: real table/search mounts preserve draft filters and cancel removed-view timers on live reload.');

// A route change during an awaited live mount must never reuse a disposed view.
let releaseMount;
let mounted = 0;
let disposedUpdates = 0;
const raceRoute = { name: 'table', kind: 'person', key: 't/person', params: new URLSearchParams() };
const fresh = () => ({ key: raceRoute.key, el: new Element('div'), title: 'People' });
const race = vm.createContext({
  ...common, window: {}, history: { state: { kbEntry: 1 } }, location: { hash: '#/' },
  parseRoute: () => raceRoute,
  mountTable: async () => {
    if (++mounted === 1) await new Promise((resolve) => { releaseMount = resolve; });
    return fresh();
  },
  mountSearch() {}, mountRecord() {}, mountReview() {}, mountReviewCheck() {}, mountHome() {},
  hideCard() {}, hideTooltip() {}, closeMenus() {},
  disposedUpdate: () => ++disposedUpdates,
});
race.window.parent = race.window;
vm.runInContext(source('app.js').replace(/\nboot\(\);\s*$/, ''), race);
const pending = vm.runInContext('current = {key: "t/person", update: async () => disposedUpdate()}; render({live:true})', race);
await vm.runInContext('render({replaced:true})', race);
releaseMount();
await pending;
assert.equal(disposedUpdates, 0);
assert.equal(mounted, 2);
assert.equal(vm.runInContext('current.disposed', race), undefined);
console.log('PASS: navigation during live remount replaces the disposed view.');
