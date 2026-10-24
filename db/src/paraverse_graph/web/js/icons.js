// Icon registry in metabrowser's format: Lucide v1 glyphs (ISC, https://lucide.dev),
// stored as constant SVG markup with the Lucide id beside each. These strings are the
// only markup the app ever parses; no API value reaches them.

const SA = 'viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"';

const ICONS = {
  search: '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>', // Lucide `search`
  x: '<path d="M18 6 6 18"/><path d="m6 6 12 12"/>', // Lucide `x`
  chevronLeft: '<path d="m15 18-6-6 6-6"/>', // Lucide `chevron-left`
  chevronRight: '<path d="m9 18 6-6-6-6"/>', // Lucide `chevron-right`
  external: '<path d="M15 3h6v6"/><path d="M10 14 21 3"/><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>', // Lucide `external-link`
  columns: '<rect width="18" height="18" x="3" y="3" rx="2"/><path d="M9 3v18"/><path d="M15 3v18"/>', // Lucide `columns-3`
  home: '<path d="M15 21v-8a1 1 0 0 0-1-1h-4a1 1 0 0 0-1 1v8"/><path d="M3 10a2 2 0 0 1 .709-1.528l7-5.999a2 2 0 0 1 2.582 0l7 5.999A2 2 0 0 1 21 10v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>', // Lucide `house`
  alert: '<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3"/><path d="M12 9v4"/><path d="M12 17h.01"/>', // Lucide `triangle-alert`
  monitor: '<rect width="20" height="14" x="2" y="3" rx="2"/><line x1="8" x2="16" y1="21" y2="21"/><line x1="12" x2="12" y1="17" y2="21"/>', // Lucide `monitor`
  sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2"/><path d="M12 20v2"/><path d="m4.93 4.93 1.41 1.41"/><path d="m17.66 17.66 1.41 1.41"/><path d="M2 12h2"/><path d="M20 12h2"/><path d="m6.34 17.66-1.41 1.41"/><path d="m19.07 4.93-1.41 1.41"/>', // Lucide `sun`
  moon: '<path d="M20.985 12.486a9 9 0 1 1-9.473-9.472c.405-.022.617.46.402.803a6 6 0 0 0 8.268 8.268c.344-.215.825-.004.803.401"/>', // Lucide `moon`
};

const template = document.createElement('template');

/** A fresh SVG element for a registered icon name. */
export function icon(name, className = 'icon') {
  template.innerHTML = `<svg class="${className}" ${SA}>${ICONS[name] || ''}</svg>`;
  return template.content.firstElementChild;
}
