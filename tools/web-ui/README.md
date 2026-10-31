# Web UI front end

The sources of the front end that `cstudy serve` serves: the page's own code and the CodeMirror 6 editor module ([web-ui](../../docs/specs/web-ui.md#front-end-assets)). The build writes into `cli/src/coding_study/entrypoints/web/static/`, and that output is committed, as the IntelliJ launcher jar is ([ADR 0010](../../docs/decisions/0010-ide-integration.md)). Installing `cstudy` with pip, uv or Homebrew never runs this build and never needs Node.

| Path | Holds |
|------|-------|
| `package.json`, `pnpm-lock.yaml` | Exact versions and integrity hashes of every package |
| `src/app.ts`, `src/page/` | The page: its entry point, views, stylesheets (`page/app.css`, and `page/flows.css` for the attempt flows, mocks, solutions and progress) and the pure parts its tests cover |
| `src/editor.ts` | The editor module, a chunk the page fetches the first time a file opens |
| `src/grammars/*.ts`, `src/vim.ts` | One chunk per language and one for Vim keybindings, each fetched on first use |
| `test/*.test.ts` | Unit tests of the pure parts of the page and the editor module, run with `node --test` |
| `scripts/build.ts` | The esbuild run, the license notice and the digest manifest |
| `build.sh` | Install, type-check, test, build |

## Rebuild

You need Node 24 or later and pnpm 9.15.9. Node ships Corepack, which runs the pnpm version `package.json` pins; enable it once with `corepack enable`.

1. Change the sources under `src/`.
2. Run the build from anywhere in the checkout:

   ```bash
   tools/web-ui/build.sh
   ```

   It installs exactly what `pnpm-lock.yaml` pins, with `--ignore-scripts` so no package runs code at install, then type-checks, runs the unit tests and builds. It prints each output file's raw and gzip size.
3. Run the CLI's checks from `cli/`, including the slow rebuild test:

   ```bash
   uv run pytest -q tests/entrypoints/web/test_static_assets.py
   ```

4. Commit the sources and the whole `static/` directory together.

Only the install uses the network, and only for packages missing from the pnpm store; the build itself is offline. The same lockfile and esbuild give the same bytes on every machine, which the slow test checks by rebuilding into a temporary directory and comparing every file's SHA-256 with the committed one.

The build owns `static/`: it deletes every file there and writes a fresh set. It refuses to replace a non-empty directory without a `manifest.json`, so a wrong path argument cannot empty an unrelated directory. `tools/web-ui/build.sh <directory>` builds somewhere else.

## Output

The build writes minified ES modules with no runtime network request: the page loads them from its own origin under `script-src 'self'`.

| File | Content |
|------|---------|
| `app.js`, `app.css` | The page's entry point and stylesheet, with fixed names, which `page.html` loads |
| `chunks/<name>-<hash>.js` | Content-hashed chunks: the shared CodeMirror core, a chunk per language, Vim |
| `THIRD_PARTY_LICENSES.txt` | Name, version, license and license text of every package the chunks contain |
| `manifest.json` | `entry`, and `files`: each other file's path with its SHA-256 |

Sizes as of the current lockfile, gzip at level 9:

| Load | Raw KB | Gzip KB |
|------|-------:|--------:|
| The page, before any file opens: `app.js`, the chunks it imports, and `app.css` | 114.9 | 36.4 |
| Every JavaScript and CSS file but Vim | 929.0 | 326.7 |
| The editor before any language: the page, the editor and the core | 518.0 | 170.2 |
| A Python file | 588.4 | 197.1 |
| A TypeScript or JavaScript file, the largest grammar | 627.0 | 210.7 |
| Vim keybindings, added on top | 119.7 | 38.2 |
| The Mock and Progress views together, each a chunk fetched when it first opens | 9.2 | 4.1 |
| The Start, Done, Solution and file dialogs, each fetched when first used (with the chunks they share) | 12.6 | 6.1 |

The budget (NFR-12) is 1 MB raw and 350 KB gzip for the whole bundle without Vim, the page's code included, and 600 KB raw loaded before a file of one language is editable. Markdown uses `markdownLanguage` instead of `markdown()`, which would add the HTML, CSS and JavaScript grammars for embedded HTML and take a Markdown file to 619 KB.

## Editor module

The page imports `createEditor` from `editor.ts` when the first file opens. Every call is on the returned `Editor`.

| Call | Does |
|------|------|
| `createEditor({parent, path, text, nonce, theme, readOnly, vim})` | Shows the file at once; resolves once its language and any Vim keybindings apply |
| `setDocument(path, text)` | Shows another file with fresh undo history and no diagnostics |
| `text`, `modified`, `markSaved()`, `onChange(listener)` | Read the text, whether it changed since it was set or saved, and each change |
| `setDiagnostics(diagnostics)` | Lint markers from `cstudy`'s `diagnostic` events for this file; F8 moves to the next one |
| `jumpTo(line, column)` | Moves the cursor there and focuses the editor |
| `setReadOnly(readOnly)` | Refuses edits; the text stays focusable and selectable |
| `setTheme("light" \| "dark" \| "system")` | `system` follows `prefers-color-scheme` as it changes |
| `setVim(enabled)` | Fetches the Vim chunk the first time it is turned on |
| `languageForPath(path)` | The language of a file name, or `null` |

| Concern | Behavior |
|---------|----------|
| Languages | Python, TypeScript and JavaScript (with TSX and JSX), Java, Kotlin, Go, Rust, JSON, TOML, YAML and Markdown, by extension; any other file opens as plain text |
| CSP | Pass the page's nonce: CodeMirror adds style elements, which `style-src 'self' 'nonce-…'` blocks otherwise |
| Keyboard | Tab indents. Escape, then Tab, moves focus out; Ctrl-M (Shift-Alt-M on macOS) toggles tab focus mode, and works with Vim on |
| Themes | Text meets WCAG AA (4.5:1) in both. The page may set `--cs-editor-background`, `--cs-editor-foreground`, `--cs-editor-font` and `--cs-editor-font-size` |
| Screen readers | The editor is labelled with the file's path, and a read-only one is marked `aria-readonly` |

## Update dependencies

Every version is exact, so an update is always a deliberate change.

1. List what is out of date:

   ```bash
   cd tools/web-ui
   pnpm outdated
   ```

2. Pin the new version with `pnpm add --save-exact <package>@<version>`, adding `--save-dev` for esbuild, TypeScript or `@types/node`. Keep every `@codemirror/*` package on versions that resolve to one copy of `@codemirror/state` and `@codemirror/view` in `pnpm-lock.yaml`, or the editor breaks at runtime.
3. Run `build.sh` and compare the printed sizes with the table above, then update the table.
4. Review the diff of `THIRD_PARTY_LICENSES.txt` for a new package or a changed license.
5. Run the checks in [Rebuild](#rebuild) and commit `package.json`, `pnpm-lock.yaml` and `static/` together.

To add a language, map its extensions in `src/languages.ts`, add `src/grammars/<name>.ts` exporting `languageSupport`, add its loader in `src/language-loaders.ts`, and add a test to `test/languages.test.ts`.
