# Web UI front end

The sources of the front end that `cstudy serve` serves: the page's own code and the CodeMirror 6 editor module ([web-ui](../../docs/specs/web-ui.md#front-end-assets)). The build writes into `cli/src/coding_study/entrypoints/web/static/`, and that output is committed, as the IntelliJ launcher jar is ([ADR 0010](../../docs/decisions/0010-ide-integration.md)). Installing `cstudy` with pip, uv or Homebrew never runs this build and never needs Node.

| Path | Holds |
|------|-------|
| `package.json`, `pnpm-lock.yaml` | Exact versions and integrity hashes of every package |
| `src/app.ts`, `src/page/` | The page: its entry point, views, stylesheets and the pure parts its tests cover. `app.ts` imports the stylesheets of what the page draws at start (`page/app.css`; `page/flows.css` for the attempt flows and the mock banner; `page/files.css` for saving and the file tree; `page/runs.css` for the run controls and the results panel), which make `app.css`. A module fetched on first use imports its own, named after it (`page/dialogs.css`, `page/results-draw.css`, `page/views/health.css`, …), which it links as it loads |
| `src/page/stylesheets.ts` | Links a chunk's stylesheet with the page's CSP nonce; the chunk resolves once the stylesheet applies, so nothing it draws shows unstyled |
| `src/page/notifications.ts` | The tab's notification stream (`/api/v1/events`), closed while the tab is hidden; the views follow what changed elsewhere through it |
| `src/editor.ts` | The editor module, a chunk the page fetches the first time a file opens |
| `src/grammars/*.ts`, `src/vim.ts` | One chunk per language and one for Vim keybindings, each fetched on first use |
| `test/*.test.ts` | Unit tests of the pure parts of the page and the editor module, run with `node --test`; `test/stylesheets.ts` makes an imported stylesheet an empty module for them |
| `scripts/build.ts` | The esbuild run, each chunk's stylesheet, the license notice and the digest manifest. It refuses a stylesheet imported by a module the page loads at start, which `app.ts` must import instead |
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
| `chunks/<name>-<hash>.js` | Content-hashed chunks: the shared CodeMirror core, a chunk per language, Vim, and the views, dialogs and controls fetched on first use |
| `chunks/<name>-<hash>.css` | The stylesheet of a module fetched on first use, linked by its chunk; esbuild alone would also put it into `app.css` |
| `THIRD_PARTY_LICENSES.txt` | Name, version, license and license text of every package the chunks contain |
| `manifest.json` | `entry`, and `files`: each other file's path with its SHA-256 |

Sizes as of the current lockfile, gzip at level 9; a row fetched on first use counts the chunks it fetches and the stylesheets they link:

| Load | Raw KB | Gzip KB |
|------|-------:|--------:|
| The page, before any file opens: `app.js`, the chunks it imports, and `app.css` | 82.7 | 29.2 |
| Every JavaScript and CSS file but Vim | 948.5 | 341.6 |
| The editor before any language: the page, the editor and the core | 486.2 | 163.2 |
| A Python file | 556.6 | 190.1 |
| A TypeScript or JavaScript file, the largest grammar | 595.1 | 203.7 |
| Vim keybindings, added on top | 119.7 | 38.1 |
| The Mock and Progress views together, each fetched when it first opens (Progress with the Start dialog) | 19.8 | 9.1 |
| The Health and Settings views together, each fetched when it first opens (with the chunks they share) | 10.9 | 5.3 |
| The run session, fetched when a run first starts or shows: streaming and drawing it, Cancel, diagnostics | 21.6 | 8.0 |
| The Run options form, fetched when it first opens | 4.1 | 1.8 |
| The code of a past attempt, fetched when the History row of an attempt that is over first opens (the dialog module comes with it, and the editor once a file shows) | 3.9 | 2.0 |
| The job panel for Bench, fetched when Bench first starts (Health fetches it with its view) | 3.9 | 1.8 |
| The file tree's menu and actions, fetched when a menu first opens or an action first runs (with the dialog module) | 9.6 | 4.5 |
| The dialog module (sheets, confirmations, questions that ask for names) and the Start, Done and Solution dialogs, each fetched when first used | 15.8 | 7.8 |

The budget (NFR-12) is 1 MB raw and 350 KB gzip for the whole bundle without Vim, the page's code included, and 600 KB raw loaded before a file of one language is editable. What a view or a control needs only when it is used is a chunk of its own (the rows above), so the page, the largest grammar and the editor stay under the 600 KB; `cli/tests/entrypoints/web/test_bundle_budget.py` holds the committed files to both limits. Markdown uses `markdownLanguage` instead of `markdown()`, which would add the HTML, CSS and JavaScript grammars for embedded HTML and take a Markdown file to 619 KB.

## Editor module

The page imports `createEditor` from `editor.ts` when the first file opens. Every call is on the returned `Editor`.

| Call | Does |
|------|------|
| `createEditor({parent, path, text, nonce, theme, readOnly, vim})` | Shows the file at once; resolves once its language and any Vim keybindings apply |
| `setDocument(path, text)` | Shows another file with fresh undo history and no diagnostics |
| `replaceText(text)` | Shows a file's new version on disk in place: only what differs changes (`text-change.ts`), so the cursor, the selection and the scroll stay, and undo takes it back |
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
