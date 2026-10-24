// Dataset choices live on the server so every view uses the same combined data.

import { api, state } from './api.js';
import { fill, h, wireMenu } from './dom.js';
import { parseRoute } from './router.js';
import { tableHref } from './values.js';

const $ = (id) => document.getElementById(id);
let catalog = null;
let choices = new Set();
let applying = false;
let error = '';
let catalogRequest = 0;

/** The final page reload owns rendering while a dataset selection is in flight. */
export function datasetSelectionPending() {
  return applying;
}

/** Install the checkbox popup once; the catalog can refresh after a graph reload. */
export function installDatasetSelector() {
  const button = $('dataset-button');
  const menu = $('dataset-menu');
  wireMenu(button, menu, () => {
    renderChoices();
    queueMicrotask(() => menu.querySelector('input:not(:disabled), button:not(:disabled)')?.focus());
  });
}

/** Keep the selected labels current when another reader changes the shared view. */
export async function refreshDatasetSelector() {
  if (applying) return;
  const mine = ++catalogRequest;
  try {
    const data = await api.datasets();
    if (applying || mine !== catalogRequest) return;
    catalog = data;
    choices = new Set(data.selected);
    error = '';
    $('dataset-selector').hidden = !data.selection_enabled;
    $('graph-name').hidden = Boolean(data.selection_enabled);
    const names = data.datasets.filter((item) => choices.has(item.id)).map((item) => item.name);
    $('dataset-label').textContent = names.join(' + ') || 'Choose datasets';
    $('dataset-button').title = names.join(' + ');
    $('dataset-button').setAttribute('aria-label', `Datasets: ${names.join(' + ') || 'choose datasets'}`);
    if (!$('dataset-menu').hidden) renderChoices();
  } catch (err) {
    if (applying || mine !== catalogRequest) return;
    // A legacy server has no dataset selector; its existing browser still works.
    if (err.status === 404) return;
    error = `Couldn’t load the dataset list. ${err.message} Try again.`;
    $('dataset-selector').hidden = false;
    $('dataset-label').textContent = 'Unavailable';
    renderChoices();
  }
}

function hasChanges() {
  return choices.size !== catalog.selected.length || catalog.selected.some((id) => !choices.has(id));
}

function updateApplyState() {
  $('dataset-apply').disabled = applying || !choices.size || !hasChanges();
  $('dataset-minimum').hidden = Boolean(choices.size);
}

function renderChoices() {
  const menu = $('dataset-menu');
  menu.setAttribute('aria-busy', String(applying));
  const heading = h('h2', { id: 'dataset-heading' }, 'Datasets');
  const status = h('p', { class: 'dataset-error', role: 'alert', hidden: !error }, error);
  if (!catalog) {
    fill(menu, heading, status, h('button', { type: 'button', class: 'btn', onclick: refreshDatasetSelector }, 'Try again'));
    return;
  }
  const options = catalog.datasets.map((item) => {
    const checkbox = h('input', { type: 'checkbox', value: item.id, checked: choices.has(item.id), disabled: applying || (!item.available && !choices.has(item.id)) });
    checkbox.addEventListener('change', () => {
      if (checkbox.checked) choices.add(item.id);
      else choices.delete(item.id);
      checkbox.disabled = !item.available && !checkbox.checked;
      updateApplyState();
    });
    return h('label', { class: 'menu-item dataset-option' }, checkbox, h('span', null, item.name),
      !item.available ? h('span', { class: 'muted' }, 'Unavailable') : null);
  });
  fill(menu, heading,
    h('p', { class: 'muted dataset-hint', id: 'dataset-hint' }, 'Select one or more to browse together.'),
    h('div', { role: 'group', 'aria-labelledby': 'dataset-heading', 'aria-describedby': 'dataset-hint' }, options),
    h('p', { class: 'dataset-minimum', id: 'dataset-minimum', role: 'status' }, 'Select at least one dataset.'),
    status,
    h('div', { class: 'dataset-actions' },
      h('span', { class: 'muted dataset-progress', role: 'status' }, applying ? (choices.size > 1 ? 'Combining datasets…' : 'Loading dataset…') : 'Shared by everyone using this address.'),
      h('button', { type: 'button', class: 'btn', id: 'dataset-apply', onclick: applySelection }, applying ? 'Loading…' : 'Apply')));
  updateApplyState();
}

async function applySelection() {
  if (applying || !choices.size || !hasChanges()) return;
  applying = true;
  ++catalogRequest; // invalidate any catalog read started before this selection
  error = '';
  $('dataset-button').disabled = true;
  renderChoices();
  let selected = false;
  try {
    await api.selectDatasets([...choices]);
    selected = true;
    api.clearCaches();
    await api.meta();
    const route = parseRoute(location.hash);
    // Column and filter parameters from the previous dataset may no longer apply.
    const next = route.name === 'table' && state.kinds.has(route.kind) ? tableHref(route.kind) : '#/';
    history.replaceState(null, '', next);
    location.reload();
  } catch (err) {
    applying = false;
    $('dataset-button').disabled = false;
    if (selected) {
      // The selection succeeded, but metadata could not be fetched for routing.
      history.replaceState(null, '', '#/');
      location.reload();
      return;
    }
    error = `Couldn’t update datasets. ${err.message} Your choices are kept; try Apply again.`;
    renderChoices();
    $('dataset-apply').focus();
  }
}
