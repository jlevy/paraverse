// A compact welcome page. Metadata paints immediately; slower summaries and
// quality checks fill their own sections without blocking navigation.

import { api, loadIdentity, state } from './api.js';
import { copyable, fmtNumber, h, humanize, relativeAge } from './dom.js';
import { entityHref, kindDot, kindTitle, tableHref } from './values.js';

const SEVERITIES = ['blocker', 'high', 'medium', 'low', 'info'];
const PROVIDERS = { github: 'GitHub', github_api: 'GitHub API', linkedin: 'LinkedIn',
  linkedin_api: 'LinkedIn API', pretalx: 'pretalx', luma: 'Luma', sessionize: 'Sessionize',
  brightdata: 'Bright Data', rainfocus: 'RainFocus', npm: 'npm', pypi: 'PyPI',
  'githubuniverse.com': 'GitHub Universe website', githubuniverse_com: 'GitHub Universe website' };
const number = (value) => value == null ? 'Unknown' : fmtNumber(value);
const note = (text) => h('p', { class: 'muted small overview-note' }, text);
const providerTitle = (source) => PROVIDERS[source] || humanize(String(source).replace(/[.-]/g, ' '));

function timestamp(value) {
  if (!value) return h('span', { class: 'muted' }, 'Not recorded');
  const age = relativeAge(value);
  const parsed = new Date(value);
  const display = Number.isFinite(parsed.getTime()) ? `${parsed.toISOString().slice(0, 16).replace('T', ' ')} UTC` : value;
  return h('time', { datetime: value, title: value, 'data-tooltip': value, tabindex: '0', class: 'mono overview-time' }, display,
    age ? h('span', { class: 'muted' }, ` · ${age}`) : null);
}

function editionDates(start, end) {
  if (!start && !end) return h('span', { class: 'muted' }, 'Not recorded');
  const calendarDate = (value) => String(value).match(/^\d{4}-\d{2}-\d{2}/)?.[0] || value;
  const first = start ? calendarDate(start) : null;
  const last = end ? calendarDate(end) : null;
  const exact = [start, end].filter(Boolean).join(' – ');
  return h('span', { class: 'mono', title: exact, 'data-tooltip': exact, tabindex: '0', 'aria-label': exact },
    first && last && first !== last ? `${first} – ${last}` : first || last);
}

function table(label, columns, rows) {
  return h('div', { class: 'overview-table-wrap', tabindex: '0', role: 'region', 'aria-label': label },
    h('table', { class: 'grid overview-table' },
      h('caption', { class: 'visually-hidden' }, label),
      h('thead', null, h('tr', null, columns.map((column) => h('th', {
        scope: 'col', class: column.numeric ? 'right' : null,
      }, column.title)))),
      h('tbody', null, rows.map((cells) => h('tr', null, cells.map((cell, index) => h('td', {
        class: columns[index].numeric ? 'right num' : null,
      }, cell)))))));
}

function entityTable(entities) {
  if (!entities.length) return note('No entities are loaded.');
  return table('Entities by kind', [{ title: 'Entity kind' }, { title: 'Group' }, { title: 'Count', numeric: true }],
    entities.map((entity) => [h('a', { class: 'overview-kind', href: tableHref(entity.kind) },
      kindDot(entity.kind), kindTitle(entity.kind)), entity.group, number(entity.count)]));
}

function relationshipTable(relationships) {
  if (!relationships.length) return note('No relationships are loaded.');
  const rows = (items) => items.map((rel) => [h('span', { class: 'mono' }, rel.type),
    rel.from?.length || rel.to?.length
      ? h('span', { class: 'muted small' }, (rel.from || []).map(kindTitle).join(', '), ' → ', (rel.to || []).map(kindTitle).join(', '))
      : h('span', { class: 'muted small' }, 'Kinds loading…'), number(rel.count)]);
  const columns = [{ title: 'Type' }, { title: 'Connected kinds' }, { title: 'Count', numeric: true }];
  const first = 8;
  return h('div', null,
    table('Relationship types', columns, rows(relationships.slice(0, first))),
    relationships.length > first ? h('details', { class: 'overview-more' },
      h('summary', null, `Show ${fmtNumber(relationships.length - first)} more relationship types`),
      table('More relationship types', columns, rows(relationships.slice(first)))) : null);
}

function sourcesView(sources) {
  return h('div', null,
    h('dl', { class: 'overview-facts' },
      h('dt', null, 'Entities with direct citations'), h('dd', { class: 'num' }, number(sources.entities_with_sources)),
      h('dt', null, 'Without direct citations'), h('dd', { class: 'num' }, number(sources.entities_without_sources)),
      h('dt', null, 'Source references'), h('dd', { class: 'num' }, number(sources.source_references)),
      h('dt', null, 'Distinct source URLs'), h('dd', { class: 'num' }, number(sources.unique_urls)),
      h('dt', null, 'Latest retrieval'), h('dd', null, timestamp(sources.latest_retrieved_at))),
    note('A reference is one citation entry on an entity. The same URL can be cited more than once. Providers can overlap on an entity. Citations document provenance; independent verification remains separate.'),
    sources.providers.length ? table('Source providers', [
      { title: 'Provider' }, { title: 'Entities', numeric: true }, { title: 'References', numeric: true }, { title: 'Latest retrieval' },
    ], sources.providers.map((provider) => [providerTitle(provider.source), number(provider.entities),
      number(provider.references), timestamp(provider.latest_retrieved_at)])) : note('No source providers are recorded.'),
    note('These are direct entity citations. Derived records, such as days and terms, may trace to sources through their parent records. Retrieval time records collection, not when every fact was last confirmed.'));
}

function editionsView(editions) {
  if (!editions.length) return note('No event editions are loaded.');
  return h('div', null, table('Event editions', [{ title: 'Event' }, { title: 'Edition' }, { title: 'Dates' }, { title: 'Sessions', numeric: true }],
    editions.map((edition) => [h('a', { href: entityHref(edition.id) }, edition.name || edition.id),
      edition.edition ?? 'Not recorded', editionDates(edition.start, edition.end),
      number(edition.sessions)])),
    note('Dates retain the source calendar day. Focus a date for its exact timestamp.'));
}

function coverageView(coverage) {
  if (!coverage.length) return note('No coverage measures are available for this dataset.');
  return h('div', null,
    table('Field coverage', [{ title: 'Measure' }, { title: 'Present / total', numeric: true },
      { title: 'Missing', numeric: true }, { title: 'Flags' }], coverage.map((row) => {
      const flags = [['stale', 'stale'], ['not_fetched', 'not fetched'], ['unknown', 'unknown']]
        .filter(([key]) => row[key] != null).map(([key, label]) => `${number(row[key])} ${label}`);
      return [h('div', null, row.kind && row.kind !== 'all'
        ? h('a', { href: tableHref(row.kind) }, row.title) : row.title,
      row.note ? h('p', { class: 'muted small overview-row-note' }, row.note) : null),
      `${number(row.present)} / ${number(row.total)}`, number(row.missing), flags.length ? flags.join(' · ') : 'Not measured'];
    })),
    note('Present measures availability. Stale and unknown flags can overlap with present or missing records; they are not additional entities. Exact counts keep small gaps visible.'));
}

function participationView(participation) {
  if (!participation.length) return note('No participation basis is recorded for this dataset.');
  return h('div', null,
    table('People inclusion basis', [{ title: 'Basis' }, { title: 'People', numeric: true }],
      participation.map((row) => [humanize(row.basis || 'unknown'), number(row.count)])),
    note('Event-published means an event source named the person. Self-reported means the person described their own participation. The basis explains why a person is included; it does not confirm attendance at every edition.'));
}

function qualityView(review) {
  const checks = review.checks;
  if (!checks.length) return note('No quality checks are available for this dataset.');
  const open = checks.filter((check) => check.count > 0);
  const severity = [...SEVERITIES, ...new Set(checks.map((check) => check.severity).filter((value) => !SEVERITIES.includes(value)))];
  const totals = severity.map((value) => {
    const group = checks.filter((check) => check.severity === value);
    const count = group.reduce((sum, check) => sum + check.count, 0);
    return h('span', { class: 'overview-severity num' },
      h('span', { class: `tag sev-${value}` }, value), `${number(count)}${group.some((check) => check.truncated) ? '+' : ''}`);
  });
  const rank = (check) => severity.indexOf(check.severity);
  open.sort((a, b) => rank(a) - rank(b) || b.count - a.count);
  return h('div', null,
    h('div', { class: 'overview-severities', 'aria-label': 'Findings by severity' }, totals),
    note(`${fmtNumber(checks.length)} checks · ${fmtNumber(checks.length - open.length)} with no findings. Findings can overlap on the same entity. A + marks a capped result, so its count is a lower bound.`),
    open.length ? table('Checks with findings', [{ title: 'Severity' }, { title: 'Check' }, { title: 'Findings', numeric: true }],
      open.map((check) => [h('span', { class: `tag sev-${check.severity}` }, check.severity),
        h('a', { href: `#/review/${encodeURIComponent(check.name)}` }, check.title),
        `${number(check.count)}${check.truncated ? '+' : ''}`]))
      : note('No findings were returned by these checks. Field coverage and source provenance are reported separately.'),
    h('p', { class: 'small overview-note' }, h('a', { href: '#/review' }, 'Explore all quality checks →')));
}

/** The active Overview navigation item also returns to its welcome summary. */
export function returnToOverview(view, main) {
  if (view?.key !== 'overview' || view.disposed) return false;
  main.scrollTop = 0;
  view.el.querySelector('h1')?.focus({ preventScroll: true });
  return true;
}

export async function mountOverview(route) {
  const meta = state.meta;
  const mountedIdentity = loadIdentity(meta);
  let active = true;
  let mismatched = false;
  let overviewSeq = 0;
  let reviewSeq = 0;
  const current = () => active && !mismatched && loadIdentity(state.meta) === mountedIdentity;
  const sections = new Map();

  function section(id, title, initial) {
    const heading = h('h2', { class: 'section-heading', id: `overview-${id}`, tabindex: '-1' }, title);
    const body = h('div', { class: 'overview-section-body' }, initial || note('Loading…'));
    const el = h('section', { class: 'section overview-section', 'aria-labelledby': heading.id }, heading, body);
    sections.set(id, { el, heading, body });
    return el;
  }

  const entities = meta.groups.flatMap((group) => group.kinds.map((kind) => ({ ...kind, group: group.title })));
  const relationships = Object.entries(meta.relationships).map(([type, count]) => ({ type, count }));
  const summaryStatus = h('p', { class: 'muted small overview-note', role: 'status' }, 'Loading detailed summary…');
  const metrics = h('dl', { class: 'overview-metrics' });
  function renderMetrics(totals) {
    metrics.replaceChildren(...[
      ['Entities', totals.entities], ['Relationships', totals.relationships],
      ['Entity kinds', totals.entity_kinds], ['Relationship types', totals.relationship_types],
    ].map(([label, count]) => h('div', null, h('dt', null, label), h('dd', { class: 'num' }, number(count)))));
  }
  renderMetrics({ entities: meta.node_total, relationships: meta.edge_total,
    entity_kinds: entities.length, relationship_types: relationships.length });

  const summary = h('section', { class: 'overview-summary', 'aria-label': 'Knowledge base summary' },
    h('div', { class: 'view-head' }, h('h1', { tabindex: '-1' }, 'Overview'),
      h('span', { class: 'tag' }, meta.dataset || meta.graph)),
    h('p', { class: 'overview-intro' }, 'Explore the loaded knowledge base: what it contains, where it came from, and which gaps need review.'),
    metrics,
    h('dl', { class: 'overview-identity' },
      h('div', null, h('dt', null, 'Dataset'), h('dd', { class: 'mono' }, meta.dataset || 'Not recorded')),
      h('div', null, h('dt', null, 'Graph'), h('dd', { class: 'mono' }, meta.graph)),
      h('div', null, h('dt', null, 'Loaded'), h('dd', null, timestamp(meta.loaded_at)))),
    h('details', { class: 'overview-more' }, h('summary', null, 'Export identity'),
      h('dl', { class: 'overview-facts' },
        h('dt', null, 'KB digest'), h('dd', null, meta.kb_digest ? copyable(meta.kb_digest, 'KB digest') : 'Not recorded'),
        h('dt', null, 'Load ID'), h('dd', { class: 'mono' }, meta.load_id || 'Not recorded')),
      note('The export digest identifies exported records; payload and schema content are outside its scope.')),
    note('Loaded is the graph import time. Source retrieval times appear in Sources.'), summaryStatus);

  const content = h('div', { class: 'overview-columns' },
    section('entities', 'Entities', h('div', null, entityTable(entities), note('Counts from load metadata · loading details…'))),
    section('relationships', 'Relationships', h('div', null, relationshipTable(relationships), note('Counts from load metadata · loading details…'))));
  const evidence = h('div', { class: 'overview-columns' }, section('sources', 'Sources'), section('quality', 'Quality'));
  const coverage = section('coverage', 'Coverage');
  const context = h('div', { class: 'overview-columns' }, section('editions', 'Event editions'), section('inclusion', 'Inclusion basis'));
  const jumps = h('nav', { class: 'overview-jumps', 'aria-label': 'Overview sections' },
    h('span', { class: 'muted small' }, 'On this page'),
    ['entities', 'relationships', 'sources', 'quality', 'coverage', 'editions', 'inclusion'].map((id) => h('button', {
      type: 'button', class: 'overview-jump', onclick: () => {
        const heading = sections.get(id).heading;
        heading.focus({ preventScroll: true });
        heading.scrollIntoView({ block: 'start' });
      },
    }, sections.get(id).heading.textContent)));
  const el = h('div', { class: 'overview' }, summary, jumps, content, evidence, coverage, context);
  const overviewIds = ['entities', 'relationships', 'sources', 'coverage', 'editions', 'inclusion'];

  function status(id, message, retry, error = false) {
    const { body } = sections.get(id);
    body.setAttribute('aria-busy', String(!error));
    body.replaceChildren(h('div', { class: `overview-status${error ? ' overview-status-error' : ''}`, role: error ? 'alert' : 'status' },
      h('p', null, message), retry ? h('button', { type: 'button', class: 'btn', onclick: retry }, 'Retry') : null));
  }

  async function loadOverview(retry = false) {
    const mine = ++overviewSeq;
    if (retry) for (const id of overviewIds) status(id, 'Loading…');
    else for (const id of ['sources', 'coverage', 'editions', 'inclusion']) status(id, 'Loading…');
    try {
      const data = await api.overview();
      if (!current() || mine !== overviewSeq) return;
      if (loadIdentity(data.load) !== mountedIdentity) {
        mismatched = true;
        reviewSeq += 1;
        const refresh = () => location.reload();
        summaryStatus.textContent = 'The graph changed while this summary was loading. Reload to show one consistent load.';
        for (const id of [...overviewIds, 'quality']) status(id, 'The graph changed. Retry to reload the summary.', refresh, true);
        return;
      }
      renderMetrics(data.totals);
      const views = { entities: entityTable(data.entities), relationships: relationshipTable(data.relationships),
        sources: sourcesView(data.sources), coverage: coverageView(data.coverage),
        editions: editionsView(data.editions), inclusion: participationView(data.participation) };
      for (const id of overviewIds) {
        sections.get(id).body.replaceChildren(views[id]);
        sections.get(id).body.setAttribute('aria-busy', 'false');
      }
      summaryStatus.textContent = 'Summary matches the loaded graph.';
    } catch (error) {
      if (!current() || mine !== overviewSeq) return;
      summaryStatus.textContent = 'Detailed summary unavailable. Counts above come from the loaded graph metadata.';
      for (const id of overviewIds) status(id, `Could not load this section. ${error.message || error}`, () => loadOverview(true), true);
    }
  }

  async function loadQuality() {
    const mine = ++reviewSeq;
    status('quality', 'Running quality checks…');
    try {
      const review = await api.review();
      if (!current() || mine !== reviewSeq) return;
      if (loadIdentity(review.load) !== mountedIdentity) {
        status('quality', 'The graph changed while checks were running. Retry to reload the summary.', () => location.reload(), true);
        return;
      }
      sections.get('quality').body.replaceChildren(qualityView(review));
      sections.get('quality').body.setAttribute('aria-busy', 'false');
    } catch (error) {
      if (!current() || mine !== reviewSeq) return;
      status('quality', `Could not load quality checks. ${error.message || error}`, loadQuality, true);
    }
  }

  void loadOverview();
  void loadQuality();
  return { key: route.key, el, title: 'Overview', destroy: () => { active = false; } };
}
