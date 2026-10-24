"""Runtime regressions for shared dataset reloads and selector request ordering."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

WEB = Path(__file__).resolve().parents[1] / "src" / "paraverse_graph" / "web"

HARNESS = r"""
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
const web = process.argv[1];
const source = (file) => fs.readFileSync(path.join(web, file), 'utf8')
  .replace(/^import[\s\S]*?;\n/gm, '').replace(/^export /gm, '');
const timers = new Map();
let timerId = 0;
const nodes = new Map();
const element = (id) => {
  if (!nodes.has(id)) nodes.set(id, {
    hidden: id === 'dataset-menu', textContent: '', dataset: {},
    classList: { add() {}, remove() {} },
    setAttribute(name, value) { this[name] = value; },
    replaceChildren() {}, querySelector() { return null; },
  });
  return nodes.get(id);
};
const schema = {
  fields: [{name:'id',type:'string'}, {name:'name',type:'string'}],
  computed: ['participation_roles'],
  relationships: [{name:'out:PARTICIPATES_IN'}],
};
const originalMeta = {
  dataset: 'universe + ptc', load_id: 'old', kb_digest: 'same', loaded_at: 'same', groups: [],
};
let serverMeta = {...originalMeta};
const state = {meta: {...originalMeta}, kinds: new Map([['person', {}], ['session', {}]])};
const calls = {meta: 0, schema: 0, render: [], fetch: 0};
const location = {hash: '#/t/person'};
const base = {
  console, URLSearchParams, Map, Set, AbortController,
  location, state,
  history: {state: null, replaceState(_state, _title, hash) { if(hash) location.hash = hash; }},
  document: {getElementById: element, body: {}, addEventListener() {}},
  window: {},
  setTimeout(fn, ms) { const id = ++timerId; timers.set(id, {fn, ms}); return id; },
  clearTimeout(id) { timers.delete(id); },
  fetch: async () => { calls.fetch++; return {ok: true, json: async () => serverMeta}; },
  EventSource: class {
    static CLOSED = 2;
    constructor() { this.readyState = 1; }
    addEventListener() {}
    close() {}
  },
  api: {
    clearCaches() {},
    async meta() { calls.meta++; state.meta = {...serverMeta}; state.kinds = new Map([['person', {}]]); return state.meta; },
    async schema() { calls.schema++; return schema; },
    review: async () => ({}),
  },
  datasetSelectionPending: () => false,
  refreshDatasetSelector() {},
  mountTable() {}, mountRecord() {}, mountReview() {}, mountReviewCheck() {}, mountSearch() {}, mountHome() {},
};
const context = vm.createContext(base);
vm.runInContext(source('js/router.js'), context);
vm.runInContext(source('js/values.js'), context);
// values/router helpers need only these DOM-independent dependencies here.
context.decodePart = decodeURIComponent;
context.qs = (params) => { const q = new URLSearchParams(params).toString(); return q ? `?${q}` : ''; };
if (fs.existsSync(path.join(web, 'js/reconcile.js'))) vm.runInContext(source('js/reconcile.js'), context);
vm.runInContext(source('app.js').replace(/\nboot\(\);\s*$/, ''), context);
vm.runInContext('renderShell = () => {}; renderReviewCount = () => {};', context);
context.recordRender = (options) => calls.render.push({...options, hash: location.hash});
vm.runInContext('render = async (options) => recordRender(options);', context);
const run = (code) => vm.runInContext(code, context);
"""


def _run_node(script: str) -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node is needed for frontend runtime regressions")
    result = subprocess.run(
        [node, "--input-type=module", "--eval", HARNESS + script, str(WEB)],
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_connected_tab_reconciles_a_load_without_an_sse_notification():
    _run_node(r"""
run('connectEvents()'); // SSE stays connected, but no graph.loaded message arrives.
assert.equal(timers.size, 1, 'connected streams still need bounded reconciliation');
const tick = async () => {
  const [id, timer] = [...timers].find(([,timer]) => timer.ms === 30_000);
  timers.delete(id);
  await timer.fn();
};
serverMeta = {...serverMeta, load_id: 'new'}; // identical digest and timestamp
await tick();
assert.equal(calls.meta, 1);
assert.equal(calls.render.length, 1);
assert.equal(state.meta.load_id, 'new');
await tick();
assert.equal(calls.meta, 1, 'unchanged polls do not remount the view');
const fetch = context.fetch;
context.fetch = (_url, {signal}) => new Promise((_resolve, reject) => {
  signal.addEventListener('abort', () => reject(new Error('timed out')));
});
const hanging = tick();
const [timeoutId, timeout] = [...timers].find(([,timer]) => timer.ms === 10_000);
timers.delete(timeoutId);
timeout.fn();
await hanging;
context.fetch = async () => { throw new Error('temporarily offline'); };
await tick();
context.fetch = fetch;
serverMeta = {...serverMeta, load_id: 'newer'};
await tick();
assert.equal(calls.meta, 2, 'a failed poll does not stop later reconciliation');
const readSchema = context.api.schema;
context.api.schema = async () => { throw new Error('schema temporarily unavailable'); };
serverMeta = {...serverMeta, load_id: 'newest'};
await tick();
assert.equal(calls.meta, 3);
assert.equal(calls.render.length, 2, 'failed schema reconciliation keeps the old view');
context.api.schema = readSchema;
await tick();
assert.equal(calls.meta, 4, 'a schema failure is retried even after metadata was fetched');
assert.equal(calls.render.length, 3);
""")


def test_other_tabs_repair_routes_after_shared_selection_and_schema_changes():
    _run_node(r"""
location.hash = '#/t/session?cols=title&f.track=AI';
serverMeta = {...serverMeta, dataset: 'ptc', load_id: 'switched'};
await run('graphLoaded()');
assert.equal(location.hash, '#/', 'missing table kinds return to the home view');
assert.equal(calls.render.at(-1).preserveDraft, false);

// A surviving table starts with fresh parameters on a shared dataset switch.
state.meta = {...originalMeta};
context.previousMeta = state.meta;
run('displayedMeta = previousMeta');
location.hash = '#/t/person?cols=name,out:PRESENTS&f.conference_role=speaker&q=old';
await run('graphLoaded()');
assert.equal(location.hash, '#/t/person');
assert.equal(calls.render.at(-1).preserveDraft, false);

// A source rebuild with the same selection validates columns, sorts and filters.
location.hash = '#/t/person?cols=name,out:PRESENTS&f.missing=x&sort=old&rel=out:PRESENTS:session:old&q=keep&offset=50';
serverMeta = {...serverMeta, load_id:'rebuilt'};
await run('graphLoaded()');
let query = new URLSearchParams(location.hash.split('?')[1]);
assert.equal(query.get('cols'), 'name');
assert.equal(query.get('q'), 'keep');
for (const key of ['f.missing', 'sort', 'rel', 'offset']) assert.equal(query.has(key), false, key);

// Normal data reloads preserve valid query state and in-progress filter drafts.
location.hash = '#/t/person?cols=name&f.name=Riken&q=keep';
serverMeta = {...serverMeta, load_id:'normal-reload'};
await run('graphLoaded()');
assert.equal(location.hash, '#/t/person?cols=name&f.name=Riken&q=keep');
assert.equal(calls.render.at(-1).preserveDraft, true);
""")


def test_overlapping_reload_signals_do_not_race_metadata_and_route_repairs():
    _run_node(r"""
let release;
let reads = 0;
context.api.meta = async () => {
  if (++reads === 1) await new Promise((resolve) => { release = resolve; });
  state.meta = {...serverMeta};
  state.kinds = new Map([['person', {}]]);
};
serverMeta = {...serverMeta, dataset: 'ptc', load_id:'switched'};
location.hash = '#/t/person?q=previous-dataset';
const first = run('graphLoaded()');
const second = run('graphLoaded()');
assert.equal(reads, 1, 'only one metadata refresh may run at once');
release();
await Promise.all([first, second]);
assert.equal(reads, 2, 'a signal during refresh is reconciled after it');
assert.equal(location.hash, '#/t/person');
assert.equal(calls.render[0].preserveDraft, false);
""")


def test_selector_ignores_out_of_order_success_and_error_responses():
    _run_node(r"""
const requests = [];
const selector = vm.createContext({
  ...base,
  api: {datasets: () => new Promise((resolve, reject) => requests.push({resolve, reject}))},
});
vm.runInContext(source('js/datasets.js'), selector);
const refresh = () => vm.runInContext('refreshDatasetSelector()', selector);
const catalog = (selected) => ({selection_enabled:true, selected:[selected], datasets:[
  {id:'ptc', name:'PTC', available:true},
  {id:'universe', name:'Universe', available:true},
]});
let first = refresh();
let second = refresh();
requests[1].resolve(catalog('ptc'));
await second;
requests[0].resolve(catalog('universe'));
await first;
assert.equal(element('dataset-label').textContent, 'PTC', 'old boot response cannot overwrite the newer resync');
assert.equal(vm.runInContext('[...choices].join()', selector), 'ptc');

first = refresh(); second = refresh();
requests[3].resolve(catalog('universe'));
await second;
requests[2].reject(new Error('stale failure'));
await first;
assert.equal(element('dataset-label').textContent, 'Universe', 'old errors cannot replace current labels');
assert.equal(element('dataset-selector').hidden, false);
""")
