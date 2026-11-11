# Guide tools

Author-time tools of the [concept guides](../../docs/specs/guides.md) in `guides/`. Readers never run them: `cstudy` ships what they write.

| Path | Holds |
|------|-------|
| `package.json`, `pnpm-lock.yaml` | The one development dependency, [beautiful-mermaid](https://github.com/lukilabs/beautiful-mermaid) 1.1.3 (MIT), pinned with its integrity hash |
| `render-text.ts` | Draws every ```` ```mermaid ```` block of every `guides/*/guide.md` as text, in a ```` ```text ```` block after a marker that holds the SHA-256 of the diagram's source ([text drawings](../../docs/specs/guides.md#text-drawings)) |

## Draw the diagrams

You need Node 24 or later and pnpm 9.15.9 (`corepack enable` runs the version `package.json` pins).

```bash
cd tools/guides
pnpm install --frozen-lockfile
pnpm render      # draws each diagram whose marker is missing or stale; leaves the rest as it is
pnpm check       # writes nothing; exits 1 when a drawing is missing, stale or wider than 100 columns
```

Then `cstudy verify --static` (check G8) agrees: it fails a diagram whose marker no longer matches its source.

The renderer leaves out the `accTitle` and `accDescr` lines, which a text drawing has no place for. It draws flowcharts, state, sequence, class and ER diagrams; keep guides to those types. beautiful-mermaid brings elkjs (EPL-2.0 or GPL-3.0-or-later) with it; both stay in `node_modules/`, which is never committed or shipped.
