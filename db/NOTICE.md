# Notices

Paraverse is licensed under the MIT License; see [LICENSE](../LICENSE).
The browser in this component adapts small, selected parts of the projects below.

## metabrowser

[metabrowser](https://github.com/jlevy/metabrowser) is by Joshua Levy and is
distributed under the GNU Affero General Public License v3.0.
Its author licenses the portions adapted here under the MIT License, as part of
Paraverse.
Only these portions are relicensed; the rest of metabrowser remains under AGPL-3.0.

- `src/paraverse_graph/browser.py`: Host-header validation, compact JSON responses,
  bounded query parameters, and the server-sent-events fan-out bus with its heartbeat.
- `src/paraverse_graph/web/app.js`: live-update reconnection and backoff.
- `src/paraverse_graph/web/js/icons.js`: the icon registry format.
- `src/paraverse_graph/web/js/search.js` and the `.palette` and `.kbd` rules in
  `src/paraverse_graph/web/style.css`: the search palette and keyboard-key style.

## tbd

[tbd](https://github.com/jlevy/tbd) is Copyright (c) 2026 Joshua Levy and is
distributed under the MIT License, the same terms as Paraverse.
Adapted portions:

- `src/paraverse_graph/web/index.html`: theme resolution before first paint.
- `src/paraverse_graph/web/js/dom.js`: relative-age labels, the tooltip and the copy
  button.
- `src/paraverse_graph/web/style.css`: design tokens, scrollbars, tags, sticky table
  headers, the copy button, the tooltip and reduced-motion rules.

## Lucide

`src/paraverse_graph/web/js/icons.js` embeds icons from [Lucide](https://lucide.dev),
distributed under the ISC License:

```
ISC License

Copyright (c) 2026 Lucide Icons and Contributors

Permission to use, copy, modify, and/or distribute this software for any
purpose with or without fee is hereby granted, provided that the above
copyright notice and this permission notice appear in all copies.

THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
```

Some Lucide icons derive from the [Feather](https://feathericons.com) project and are
also covered by its license:

```
The MIT License (MIT)

Copyright (c) 2013-present Cole Bemis

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
