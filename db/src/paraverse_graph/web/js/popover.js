// Entity hover cards. Any element with `data-card-id` (every entity chip) shows a
// card from /api/card/<id> after a short hover or keyboard focus. The card itself is
// hoverable: a grace timer lets the pointer travel from the chip into it.

import { api } from './api.js';
import { fill, h, humanize, imageUrl } from './dom.js';
import { cluster, entityHref, kindDot, kindTitle, scalar, tag } from './values.js';

const SHOW_DELAY = 300;
const WARM_DELAY = 80; // moving between chips while a card is open
const HIDE_GRACE = 220;

const card = h('div', { class: 'card', id: 'entity-card', role: 'dialog', 'aria-label': 'Entity preview', hidden: true });
let anchor = null; // the chip the card is for, or is about to be for
let showTimer = 0;
let hideTimer = 0;

const anchorOf = (node) => (node instanceof Element ? node.closest('[data-card-id]') : null);

// Values render as they do in tables and records: enum codes as tags, URLs as
// links, timestamps as wall time with the exact value in a tooltip.
const ENUM = /^[a-z0-9]+(_[a-z0-9]+)*$/;
function cardValue(value) {
  if (Array.isArray(value)) return cluster(value.map((v) => (typeof v === 'string' && ENUM.test(v) ? tag(v) : scalar(v))), 6);
  if (typeof value === 'string' && ENUM.test(value) && !/^\d+$/.test(value)) return tag(value);
  return scalar(value);
}

function render(data) {
  const image = imageUrl(data.image);
  // A field that only repeats the card's name adds nothing.
  const fields = (data.fields || []).filter((f) => f.value !== data.name);
  fill(card,
    h('div', { class: 'card-head' },
      image && h('img', { src: image, alt: '', referrerpolicy: 'no-referrer', onerror: (e) => e.target.remove() }),
      h('div', null,
        h('div', { class: 'card-name' }, data.name || data.id),
        h('div', { class: 'card-kind' }, kindDot(data.kind), kindTitle(data.kind)))),
    fields.length
      ? h('dl', { class: 'fields' }, fields.flatMap((f) => [h('dt', null, humanize(f.name)), h('dd', null, cardValue(f.value))]))
      : null,
    h('div', { class: 'card-foot' },
      h('span', { class: 'mono' }, data.id),
      h('a', { href: entityHref(data.id) }, 'Open →')));
}

function place(target) {
  const gap = 6;
  const a = target.getBoundingClientRect();
  const c = card.getBoundingClientRect();
  let x = Math.min(a.left, innerWidth - c.width - 8);
  let y = a.bottom + gap;
  if (y + c.height > innerHeight - 8 && a.top - c.height - gap > 8) y = a.top - c.height - gap;
  card.style.left = `${Math.max(8, x)}px`;
  card.style.top = `${Math.max(8, y)}px`;
}

async function show(target) {
  const id = target.dataset.cardId;
  anchor = target;
  let data;
  try {
    data = await api.card(id);
  } catch {
    return; // no card (a dangling reference); the chip still links
  }
  if (anchor !== target || !target.isConnected) return;
  render(data);
  card.hidden = false;
  target.setAttribute('aria-describedby', card.id);
  place(target);
}

export function hideCard() {
  clearTimeout(showTimer);
  clearTimeout(hideTimer);
  anchor?.removeAttribute('aria-describedby');
  anchor = null;
  card.hidden = true;
}

function schedule(target) {
  clearTimeout(hideTimer);
  clearTimeout(showTimer);
  if (anchor === target && !card.hidden) return;
  anchor = target;
  showTimer = setTimeout(() => show(target), card.hidden ? SHOW_DELAY : WARM_DELAY);
}

function scheduleHide() {
  clearTimeout(showTimer);
  clearTimeout(hideTimer);
  hideTimer = setTimeout(hideCard, HIDE_GRACE);
}

export function installPopovers() {
  document.body.append(card);
  document.addEventListener('pointerover', (event) => {
    const target = anchorOf(event.target);
    if (target) schedule(target);
    else if (card.contains(event.target)) clearTimeout(hideTimer);
  });
  document.addEventListener('pointerout', (event) => {
    const from = anchorOf(event.target) || (card.contains(event.target) ? card : null);
    const to = event.relatedTarget;
    if (from && !(to instanceof Node && (from.contains(to) || card.contains(to)))) scheduleHide();
  });
  document.addEventListener('focusin', (event) => {
    const target = anchorOf(event.target);
    if (target) schedule(target);
    else if (!card.contains(event.target)) scheduleHide();
  });
  document.addEventListener('keydown', (event) => event.key === 'Escape' && !card.hidden && hideCard());
  document.addEventListener('scroll', (event) => !card.contains(event.target) && hideCard(), true);
  card.addEventListener('click', (event) => event.target.closest?.('a') && hideCard());
}
