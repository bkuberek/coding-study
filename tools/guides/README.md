# Guide tools

Author-time tools of the [concept guides](../../docs/specs/guides.md) in `guides/`. Readers never run them: `cstudy` ships what they write.

| Path | Holds |
|------|-------|
| `package.json`, `pnpm-lock.yaml` | The development dependencies, pinned with their integrity hashes: [beautiful-mermaid](https://github.com/lukilabs/beautiful-mermaid) 1.1.3 (MIT) for the text drawings, [Mermaid](https://github.com/mermaid-js/mermaid) 11.17.2 (MIT) for the SVG drawings, and [playwright-core](https://github.com/microsoft/playwright) 1.64.1 (Apache-2.0), which drives the headless Chromium that Mermaid draws in |
| `render-text.ts` | Draws every ```` ```mermaid ```` block of every `guides/*/guide.md` as text, in a ```` ```text ```` block after a marker that holds the SHA-256 of the diagram's source ([text drawings](../../docs/specs/guides.md#text-drawings)), then runs `render-svg.ts` |
| `render-svg.ts` | Draws the same blocks as `guides/<slug>/diagrams/<n>-light.svg` and `<n>-dark.svg`, the n-th block of the guide from 1, each starting with `<!-- svg-of-mermaid sha256:<hex> -->`, for the web UI's Guides view ([SVG drawings](../../docs/specs/guides.md#svg-drawings)) |

## Draw the diagrams

You need Node 24 or later, pnpm 9.15.9 (`corepack enable` runs the version `package.json` pins), and Playwright's Chromium 1248, which `uv run --group browser playwright install chromium` in `cli/` installs for the browser tests too: playwright-core 1.64.1 is the version of the Python Playwright there, so both use the same browser.

```bash
cd tools/guides
pnpm install --frozen-lockfile
pnpm render      # draws each diagram whose marker is missing or stale; leaves the rest as it is
pnpm render:all  # draws every diagram again, after a change to the renderer, its palettes or its options
pnpm check       # writes nothing; exits 1 when a drawing is missing, stale or too wide, or an SVG belongs to no diagram
```

Then `cstudy verify --static` agrees: it fails a diagram whose text drawing (G8) or SVG drawings (G10) no longer match its source, and an SVG that belongs to no diagram.

The text renderer leaves out the `accTitle` and `accDescr` lines, which a text drawing has no place for. It draws flowcharts, state, sequence, class and ER diagrams; keep guides to those types. beautiful-mermaid brings elkjs (EPL-2.0 or GPL-3.0-or-later) with it; both stay in `node_modules/`, which is never committed or shipped.

The SVG renderer draws with Mermaid's `base` theme set to the web UI's palettes (`tools/web-ui/src/page/app.css`): a node is the accent's soft tint with the accent as its border, text is the ink, and lines are the soft ink, in light and in dark. Text is SVG text in Helvetica, Arial or a sans-serif, which share their metrics, so a label measured here fits where it is shown. Then each SVG is made self-contained and small: every style Mermaid's stylesheet gives an element becomes a presentation attribute, set only where it differs from what the element inherits, and the stylesheet, the classes, the `style` attributes, ids that nothing refers to, unused markers, the accessibility title and description, which the page's alt text and caption carry, and decimals past the second go. An SVG loads no font and holds no script. A diagram with HTML labels fails, since an image could not style them.
