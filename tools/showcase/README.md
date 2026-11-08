# Showcase media for `cstudy serve`

`showcase.py` retakes the screenshots and animations in [`docs/images/`](../../docs/images/) from a **released** wheel, so the pictures show what users get and not what the checkout holds. Run it again for each release that changes the web UI.

It drives one headless Chromium with Playwright against a throwaway workspace, and never touches an installed `cstudy`: the wheel goes into a new virtual environment, and `PATH` for the server hides any other `cstudy`, so the Health view lists one install.

## Run it

You need `uv`, `ffmpeg`, `gh` (to fetch the wheel), the language toolchains that `cstudy doctor` checks, with JDK 25 or 26 selected (`JAVA_HOME`) so that Java's language server runs, and Playwright's Chromium (`uv run playwright install chromium` in `cli/` if the browser tests never ran on this machine). `pngquant` is optional and shrinks the PNGs.

```bash
# 1. The released wheel
mkdir -p /tmp/showcase-wheel
gh release download v0.13.0 -p '*.whl' -D /tmp/showcase-wheel

# 2. Everything, from `cli/`, into an empty working folder
cd cli
uv run python ../tools/showcase/showcase.py \
  --wheel /tmp/showcase-wheel/coding_study-0.13.0-py3-none-any.whl \
  --work /tmp/showcase-work \
  --out ../docs/images

# 3. Clean up
rm -rf /tmp/showcase-work /tmp/showcase-wheel
```

A run takes several minutes and runs one Chromium, `cstudy serve` and the language servers it starts, so close other heavy work first.

`--stages` runs part of it, in this order: `prepare` (virtual environment, `cstudy init --no-ide`, preferences, `cstudy doctor --fix`), `seed` (practice history), `videos`, `shots`, `mock`. A later stage needs the earlier ones, so rerun a single stage only against the same `--work` folder, and without `prepare`, which wants the folder empty. Run `videos` before `shots`, and `mock` last: a mock in progress adds a banner to every view.

`--shots` takes some of the screenshots of the `shots` stage, by name, such as `--shots web-ui-attempt,web-ui-settings`; a shot left out does not open its view, so leaving out `web-ui-health` starts no Gradle. `--variants` takes the screenshots in some themes and widths only, such as `--variants light-phone`: on a machine short of memory, one variant per run starts one Chromium and one Java language server at a time, and frees them in between. `--video-theme dark` records the animations in the dark theme.

When it ends, stop what it may have left: `ps -Ao pid,ppid,etime,command | rg -i "basedpyright|typescript-language-server|jdtls|gopls|rust-analyzer|uvicorn|cstudy serve|ms-playwright|GradleDaemon|KotlinCompileDaemon"`. The script stops the server and the browser, and the Gradle and Kotlin daemons that its own processes started (`cstudy doctor --fix`, the Health view and JDT LS start them): it looks at the processes below it every half second while it runs, notes the daemons it finds there, and stops those by PID at the end. A daemon that was running before, or that other work on this machine starts meanwhile, is never below the script, so it stays.

## What it makes

Desktop images are 1440 by 900, the phone ones 390 wide at 2x. A name is `<name>-<theme>` for desktop and `<name>-<theme>-phone` for the phone, with `<theme>` `light` or `dark`.

| Name | Shows |
|------|-------|
| `code-intelligence-hover` | The documentation tooltip on `sorted` in two-sum (Python) |
| `code-intelligence-error` | An undefined name underlined, with its message |
| `autocomplete-list` | The completion list with its documentation panel |
| `code-intelligence-java-hover` | The Javadoc tooltip on `getOrDefault` in top-k-frequent-elements (Java), from Eclipse JDT LS; the seed stage starts that attempt |
| `code-intelligence-go-hover` | The documentation of `strings.Split` in group-anagrams (Go), from gopls, with its links to `SplitN` and `Cut`; the seed stage starts that attempt |
| `code-intelligence-rust-hover` | The documentation of `Vec` in product-except-self (Rust), from rust-analyzer and the toolchain's standard library; the seed stage starts that attempt |
| `web-ui-problems` | The problem list |
| `web-ui-attempt` | A project attempt with the file tree, the editor, a run's results and the statement |
| `web-ui-project` | The same attempt with several file tabs open |
| `web-ui-results` | A function problem with all tests passing |
| `web-ui-history` | A past attempt's code, open read-only from the Problem view's history |
| `web-ui-health` | The Health view, with the code intelligence rows |
| `web-ui-settings` | Settings, with both toggles and the state of each language |
| `web-ui-mock` | A mock in progress |

Two animations, in the light theme at desktop width unless `--video-theme` says otherwise, each as `<name>.gif`, `<name>.mp4` and `<name>-poster.png` (the first frame):

| Name | Shows |
|------|-------|
| `code-intelligence-demo` | Typing an undefined name, its underline, the fix, hover documentation, a Cmd-click into a read-only library tab, and back |
| `autocomplete-demo` | Typing letters, the list with documentation, accepting an item, and signature help on `(` |

Recording uses Playwright's `record_video_dir` with a small injected pointer, since Playwright does not draw one. ffmpeg makes the GIF in two passes (palette, then `paletteuse`) after a light denoise, because Playwright's video is noisy and noise makes every GIF frame different. It starts at 1100 px and 15 fps and steps down until the file is under 3 MB. The MP4 is H.264, `yuv420p`, `+faststart`, with no audio, and kept under about 2 MB.

## Notes

- The screenshots replace this machine's paths with `~` in the page text before they are taken, so no temporary folder or user name shows. A `XDG_CONFIG_HOME` in the environment shows as `~/.config`, so a run can keep its `config.toml` apart from yours.
- The practice files keep the header `cstudy start` wrote, and the script replaces only the code below it, so the media show the header of the release they come from.
- Statements credit the problem each one rewords, by the name of the site it comes from. The media must not name any assessment vendor, so the script hides those credit lines in the page while it records and photographs. Nothing else in a statement changes.
- The script writes files only into `--work` and `--out`. Nothing it makes is committed for you.
- It needs the language servers, so it runs `cstudy doctor --fix` with the network. After that it works offline.
- A new language server needs a new feature shot, as Java's has, and a scene in `code_intelligence_scene` if the animation should show it. The health shot picks up new rows by itself; the settings shot also waits for each server's line, so a JDK outside 25 and 26 stops it instead of showing Java's `needs JDK 25 or 26`.
- JDT LS says ready before its first Gradle import ends, so the Java shot hovers again until the Javadoc shows, for up to three minutes. The Go and Rust shots hover the same way. Each of the three waits for its server to stop before the next shot, so that two never run at once.
- The Go and Rust shots need gopls, which `cstudy doctor --fix` builds with the selected Go, and rust-analyzer on `PATH` (`rustup component add rust-analyzer`), which the script never installs. The settings shot waits for both lines.
