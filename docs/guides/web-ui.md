# Practise in your browser with `cstudy serve`

`cstudy serve` opens a page on your own computer where the whole practice loop happens: pick a problem, read the statement, edit the code, run the tests and submit with results arriving as they run, take hints, reveal solutions, finish the attempt, run mock interviews, and check your progress and your setup. It is another way to use `cstudy`, not a separate app: the page works on the same workspace files and the same `progress.db` as the terminal and your IDE, and every run is the same `cstudy test` or `cstudy submit` command.

![The attempt view: the file tree, a file in the editor, a run's results and the statement](../images/web-ui-attempt-dark.png)

## Quick path

1. In your workspace, start the server and let it open the page:

   ```bash
   cd ~/cstudy-workspace
   cstudy serve --open
   ```

2. Pick a problem in the list, choose **Start…**, and open a file from the tree.
3. Edit, save with <kbd>Cmd</kbd>+<kbd>S</kbd> (<kbd>Ctrl</kbd>+<kbd>S</kbd> on Linux), and run the tests with <kbd>Cmd</kbd>+<kbd>Enter</kbd>.
4. Choose **Done…** when you finish, then stop the server with <kbd>Ctrl</kbd>+<kbd>C</kbd> in its terminal.

## Start the server

```text
$ cstudy serve --open
cstudy serve 0.9.0 · workspace ~/cstudy-workspace
open       http://127.0.0.1:53817/?token=QmFua1Byb2plY3Q...
run        test two-sum · kotlin · passed · 14/14 · 2.1s
stop       Ctrl-C
```

| Step | What to know |
|------|--------------|
| Run it | `cstudy serve` in your workspace, or anywhere with `--workspace PATH`, as for every command. It needs a workspace: run `cstudy init` first |
| Open the page | `--open` opens your default browser. Without it, open the `open` URL the server prints, in any browser on this computer |
| Pick a port | `--port N` listens on port N; by default the system picks a free port each time |
| While it runs | The terminal prints one line per finished run or job, and nothing else |
| Stop it | <kbd>Ctrl</kbd>+<kbd>C</kbd>. Runs in progress stop as Ctrl-C stops them in the terminal, and record nothing |

The page is made for current Chrome, Edge, Firefox and Safari. Its tests run in the engines of all of them, through Playwright: Chromium, Firefox, and WebKit, the engine of Safari. A check in the Safari app itself is still pending.

## The views

The top bar holds the views, the attempts in progress, and the mock banner while a mock runs. Under it, a command line shows the `cstudy` command that the view mirrors, with a button that copies it. The status bar at the bottom switches Vim keybindings and the theme.

| View | Opens with | Shows |
|------|------------|-------|
| Problems | <kbd>Alt</kbd>+<kbd>1</kbd> | The `cstudy next` pick, the filters of `cstudy list` (track, kind, language, difficulty, status, pattern, content status), and every problem with its status and due date |
| Problem | A row of the list | The statement, Start or Resume, Solution, and the problem's history: its review schedule, attempts, runs and submissions |
| Attempt | Start, Resume, or the in-progress menu | The file tree, the editor, the results of the latest run, and the statement with its levels and hints |
| Mock | <kbd>Alt</kbd>+<kbd>2</kbd> | The start form, or the running mock's countdown and problems |
| Progress | <kbd>Alt</kbd>+<kbd>3</kbd> | `cstudy stats`, the reviews due, export and import |
| Health | <kbd>Alt</kbd>+<kbd>4</kbd> | The `cstudy doctor` checks, Fix, and Verify for your own problems |
| Settings | <kbd>Alt</kbd>+<kbd>5</kbd> | The preferences, and where the workspace and the settings file are |

![The problem list in the light theme](../images/web-ui-problems-light.png)

## Edit and save

Open a file by choosing it in the tree; each opens in a tab of its own.

- **Saving is explicit.** <kbd>Cmd</kbd>+<kbd>S</kbd> saves the active tab, or `:w` with Vim on. The page never saves on its own. A tab with unsaved edits shows a dot in place of its close button.
- **Changes from elsewhere show up.** When your IDE or the terminal changes a file, a tab without unsaved edits takes the new version in place and keeps your cursor. A tab with unsaved edits shows a banner instead: **Reload theirs** drops your edits, **Overwrite** saves yours over the file.
- **Leaving asks first.** Closing a tab, leaving the view or closing the page with unsaved edits asks before anything is lost.
- **Generated test files** of a project are editable, as in the terminal, but editing one never changes a grade.

The editor highlights Python, TypeScript, Java, Kotlin, Go, Rust, JSON, TOML and Markdown. It has no code completion: errors come from the runs, as underlines and gutter markers on the lines they name.

## Run the tests and submit

| Action | Button | Keys | Same as |
|--------|--------|------|---------|
| Run the tests | Run tests | <kbd>Cmd</kbd>+<kbd>Enter</kbd> | `cstudy test` |
| Submit a project level | Submit | <kbd>Cmd</kbd>+<kbd>Shift</kbd>+<kbd>Enter</kbd> | `cstudy submit` |
| Cancel a run | Cancel | <kbd>Escape</kbd> in the results, after a question | Ctrl-C in the terminal |
| Go to the next error | | <kbd>F8</kbd> | |

Results arrive as the run goes: one row per case or test, the build line, errors with a link to their line, and the summary. **Run options** sets what `cstudy test` takes as flags: chosen cases, a level, stress runs and a seed, the time limit, `--perf`, and type-checking for TypeScript. A submission that passes a level opens the next one: the statement, the tree and the header follow at once.

Only one run per attempt runs at a time. A run started in another tab shows in this one too, and either tab can cancel it.

## Project files

For a project problem, the tree shows every file of the project folder with its origin (starter, level N test, yours) and its state: `modified`, `added` or `deleted`.

| Do | How |
|----|-----|
| Open a file's actions | Its ⋯ button, a right click, <kbd>Shift</kbd>+<kbd>F10</kbd> or the context-menu key |
| New file, new folder | The `+ file` and `+ folder` buttons above the tree |
| Rename or move | <kbd>F2</kbd>, or the file's actions |
| Delete | <kbd>Delete</kbd>, or the file's actions; the question says whether Restore can bring it back |
| Restore a starter or test file | The file's actions, as `cstudy start --restore`; a modified file asks first |

For other problems the tree shows the files you may edit: the stub `cstudy start` wrote, and for Java, Kotlin and Go any other file in the problem's package.

## Hints, solutions and Done

| Button | What happens |
|--------|--------------|
| Hint | Shows the next hint under the statement. Any hint caps the review grade at `ok` |
| Solution… | Asks first when an unsolved attempt is in progress, since the attempt is then graded as `again`; the reference opens in a read-only pane, never in your files |
| Done… | Finishes the attempt with a rating (`easy`, `ok`, `hard`) or as given up, and optional notes; it shows the lines `cstudy done` prints, with the next review date |

## Mock interviews

The Mock view starts a mock as `cstudy mock` does: new medium and hard problems, a shared timer, and hints and solutions locked until the timer ends or every problem is done. Each problem opens as an ordinary attempt. A mock started in the terminal shows in the page too.

## Preferences

Settings apply at once and are stored in `.cs/serve/preferences.json` in the workspace, so they follow the workspace, not the browser.

| Preference | Default | Effect |
|------------|---------|--------|
| Vim keybindings | off | Vim keys in every editor; `:w` saves |
| Run on save | off | Each save, from the page or from your IDE, runs the tests again, as `cstudy test --watch` does |
| Type-check TypeScript | on | TypeScript runs type-check, so type errors show in the editor |
| Theme | system | Light or dark, or follow your system |

## Keyboard

Every view works with the keyboard alone. On Linux, read <kbd>Ctrl</kbd> for <kbd>Cmd</kbd>.

| Keys | Do |
|------|----|
| <kbd>Alt</kbd>+<kbd>1</kbd> to <kbd>5</kbd> | Problems, Mock, Progress, Health, Settings |
| <kbd>Cmd</kbd>+<kbd>S</kbd> | Save the active tab |
| <kbd>Cmd</kbd>+<kbd>Enter</kbd> | Run the tests |
| <kbd>Cmd</kbd>+<kbd>Shift</kbd>+<kbd>Enter</kbd> | Submit a project level |
| <kbd>Escape</kbd> in the results | Cancel the run, after a question |
| <kbd>F8</kbd> | Go to the next error in the editor |
| <kbd>Tab</kbd> in the editor | Indent; <kbd>Escape</kbd> then <kbd>Tab</kbd> moves on to the next control |
| <kbd>Alt</kbd>+<kbd>Shift</kbd>+<kbd>M</kbd> (<kbd>Ctrl</kbd>+<kbd>M</kbd> on Linux) | Make <kbd>Tab</kbd> move the focus out of the editor until pressed again |
| <kbd>Shift</kbd>+<kbd>F10</kbd>, <kbd>F2</kbd>, <kbd>Delete</kbd> in the tree | A file's actions, rename, delete |
| <kbd>Escape</kbd> in a dialog | Close it; the focus returns where it was |

Each button names its keys and the `cstudy` command it runs when you point at it. With "Reduce motion" on in your system, the page shows no animation.

## With the terminal and your IDE

The page, the terminal and your IDE always agree, because they share the workspace and its progress. Start an attempt in the terminal and it appears in the page's in-progress menu; submit in the terminal and the page opens the new level; edit in your IDE and the open tab follows. The command line under the top bar names the `cstudy` command each view mirrors, so you can switch to the terminal at any point.

A few things stay in the terminal: `cstudy init`, `cstudy ide`, `cstudy new`, `cstudy verify` on catalog problems, and `cstudy test --debug`, which needs your IDE's debugger. `cstudy test --watch` becomes the Run on save preference.

## Troubleshooting

| You see | Do |
|---------|----|
| "This browser has no session with this server" | Open the URL the server printed. The token in it is new every time the server starts |
| `port … is already in use` | Another program holds the port: pick another with `--port`, or leave it out to get a free one |
| `reconnecting…` in the top bar | The page lost the server for a moment and tries again |
| `disconnected` in the top bar | The server stopped or restarted: start it again and open the new URL |
| `cstudy serve` exits 4, or `cstudy doctor` warns on `web ui assets` or `web server` | The page's files or the web server libraries are missing or damaged: reinstall `cstudy` with the command `cstudy doctor` prints, which names the install that runs; if it also warns on `installs`, keep one install first |
| A language fails in the Health view | Install its toolchain ([toolchains](toolchains.md)), then use **Fix**, which runs `cstudy doctor --fix` |
| The first Java or Kotlin run is slow | Gradle warms up on the first build, as in the terminal |
| <kbd>Tab</kbd> skips buttons and links in Safari | Use <kbd>Option</kbd>+<kbd>Tab</kbd>, or turn on "Press Tab to highlight each item on a webpage" in Safari's Advanced settings |

## Security, in plain words

- **Only your computer can reach it.** The server listens on `127.0.0.1`, which other machines cannot connect to.
- **The URL is a password.** Its token is new each time the server starts; anyone with the URL can use the page while it runs, so do not share it. The browser keeps a session cookie after the first visit.
- **Other websites cannot use it.** The page refuses requests that come from other sites, even from tabs in the same browser.
- **It runs your code, as `cstudy test` does.** Saving a file and running it executes that code as you, which is why the page asks for the token.
- **It touches only your attempt's files.** The page edits the files of the attempts in progress and nothing else, and never follows a link out of them.
- **Nothing leaves your machine.** The page loads everything from the server and sends nothing elsewhere.
