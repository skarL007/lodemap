# Third-party notices

Lodemap itself is MIT-licensed (see [LICENSE](LICENSE)). The explorer page embeds unmodified copies of the libraries
below so it opens from `file://` and over http with no external request. Their license texts sit next to the files in
`templates/structurizr/explorador/vendor/`; versions and download sources are listed in that folder's `LEIAME.md`.

| Library | Version | License | Copyright |
|---|---|---|---|
| Cytoscape.js | 3.30.2 | MIT | The Cytoscape Consortium, 2016-2024 |
| cytoscape-dagre | 2.5.0 | MIT | see `LICENSE-cytoscape-dagre.txt` |
| dagre | 0.8.5 | MIT | Chris Pettitt, 2012-2014 |

## Code bundled inside `dagre.min.js`

The published `dagre.min.js` is a browserified bundle. It carries these dependencies inside it, both under the MIT license:

- **graphlib** (version 2.1.8 appears in the bundle) — Copyright (c) 2014, Chris Pettitt.
- **lodash** (declared by dagre 0.8.5 as `^4.17.15`; the exact version is not printed in the bundle) —
  Copyright OpenJS Foundation and other contributors <https://openjsf.org/>. Parts of lodash derive from
  Underscore.js (Copyright Jeremy Ashkenas, DocumentCloud and Investigative Reporters & Editors).

The MIT License for each of these requires that the copyright notice and the permission notice be kept with copies of
the software. This file and the license texts in the `vendor/` folder are that notice.

## Docs reader: Mermaid

The docs reader (`templates/structurizr/leitor/`) embeds an unmodified copy of the `tiny` build of Mermaid, loaded only
on pages that have a diagram. License texts and the download source sit in
`templates/structurizr/leitor/vendor/` (`LEIAME.md`).

| Library | Version | License | Copyright |
|---|---|---|---|
| Mermaid (`@mermaid-js/tiny`) | 12.3.0 | MIT | Knut Sveidqvist, 2014-2022 |

The bundle carries Mermaid's own dependencies, all permissive: MIT (dayjs, marked, stylis, roughjs, dagre-d3-es,
lodash and others), ISC (d3), BSD-3-Clause (d3-sankey) and Apache-2.0 (chevrotain). DOMPurify is offered under
"MPL-2.0 OR Apache-2.0" and is used here under the Apache-2.0; its text is `LICENSE-apache-2.0.txt`. The copyright
notices the bundle prints for those parts stay inside the file. The `tiny` build leaves out ELK (EPL-2.0 OR
GPL-3.0-or-later), Cytoscape, KaTeX and the mindmap and architecture diagrams.
