---
title: Practice in your browser
summary: cstudy serve opens the whole practice loop in a page on your computer, beside the terminal and your IDE.
section: The web UI
order: 100
---

# Practice in your browser

`cstudy serve` opens a page on your own computer where the whole practice loop happens: pick a problem, read the statement, edit the code, run the tests and submit with results arriving as they run, take hints, reveal solutions, finish the attempt, run mock interviews, and check your progress and your setup. It is another way to use `cstudy`, not a separate app: the page works on the same workspace files and the same `progress.db` as the terminal and your IDE, and every run is the same `cstudy test` or `cstudy submit` command.

## Quick path

1. In your workspace, start the server and let it open the page:

   ```bash
   cd ~/cstudy-workspace
   cstudy serve --open
   ```

2. Pick a problem in the list, choose **Start…**, and open a file from the tree.
3. Edit, save with `Cmd+S` (`Ctrl+S` on Linux), and run the tests with `Cmd+Enter`.
4. Choose **Done…** when you finish, then stop the server with `Ctrl+C` in its terminal.

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
| Stop it | `Ctrl+C`. Runs in progress stop as Ctrl-C stops them in the terminal, and record nothing |

The page works in any current browser. It loads everything from `cstudy serve` and needs no internet.

## The views

The top bar holds the views, the attempts in progress while one is open, and the mock banner while a mock runs; it stays at the top of the window when you scroll, and so do the header rows of the tables. Under it, a command line shows the `cstudy` command that the view mirrors, with a button that copies it. The status bar at the bottom switches Vim keybindings and the theme, and the version at its end opens the About view.

| View | Opens with | Shows |
|------|------------|-------|
| Problems | `Alt+1` | The `cstudy next` pick (an attempt you have open first, with links to the others, then a due review or a new problem) with a **Start…** or **Resume** button, a search by title or slug that narrows as you type (`/` focuses it), one slim row of the filters of `cstudy list` (status, difficulty, domain and language, and under **more** track, kind, checked, role, scope, pattern, content status and set), a removable chip per active filter with a live count and **clear**, and every problem within your [learner profile](#filters-and-your-profile) with its status (`in progress` while you have an attempt open) and due date. Each row has a button to add the problem to a set. The first column, **checked by**, says how the problem is checked: `tests`, `tests + rubric` or `rubric`. The `columns` menu chooses what the table shows, and adds its kind, scope, domain and role |
| Problem | A click on a row of the list | The statement, Start or Resume, Solution, and the problem's history: its review schedule, attempts, runs and submissions, and the code of each attempt that is over. For a problem with levels, it also shows your best level in each language and, when you stopped below the last level, the level to try next. A problem whose reviews keep reaching level 2 of 4 reads *mastered through level 2 of 4*: each level is mastered on its own reviews, so a level you have just reached starts over. The **Start…** dialog offers the workspace's languages: another language of the problem shows disabled, with `not in this workspace: cstudy lang add rust` beside it, except in a service project, which runs in Docker |
| Attempt | Start, Resume, or the in-progress menu | The file tree, the editor, the results of the latest run, and the statement with its levels and hints |
| Sets | `Alt+2` | [Your own lists of problems](planning.md#problem-sets), with passed of total; one open shows its pick and its rows, to start, resume or reorder |
| Guides | `Alt+3` | [Short readings that teach an idea](guides.md) before you practice it, and the paths that order them with problems, with how far you have come |
| Mock | `Alt+4` | The start form, with the workspace's languages and the profile chip, or the running mock's countdown and problems |
| Progress | `Alt+5` | `cstudy stats`, the reviews due, export and import |
| Health | `Alt+6` | The `cstudy doctor` checks, a **Fix** button on each row that `cstudy doctor --fix` repairs, and Verify for your own problems |
| Settings | `Alt+7` | Your learner profile, this workspace's preferences, and your `config.toml`, which every workspace reads ([settings](settings.md)) |
| Docs | `Alt+8` | These pages: every topic by section, a search over all of them, and a link to each heading. `cstudy docs` reads the same pages in the terminal |
| About | The version in the status bar | Who made cstudy, with a link to his site, and below it two plain links that say where to sponsor cstudy if you want to; then the version, the license, the website and project links, and the credits, with the full license texts one click away. `cstudy about` prints the same, in the same order. It is not in the top bar, and has no number key |

## Filters and your profile

The Problems and Guides views filter through the same row: a search that narrows as you type, then a few lists, with the less used ones of the Problems view under **more**. Every filter is kept in the page's address, so a reload and Back keep it, and the command line above the view shows the `cstudy list` or `cstudy learn` command that lists the same rows.

Your [learner profile](settings.md#your-learner-profile) narrows the Problems, Guides and Mock views by default, as it narrows the commands. While it narrows the languages, the roles or the domains, that list starts on `your profile`. Choose `any` to widen it for this view, as `--widen` does, or a value to filter by that value alone. Neither changes the profile.

While the profile hides some rows, the line under the filters starts with a quiet chip that counts what shows and names the values that narrowed it:

| View | The chip |
|------|----------|
| Problems | `120 of 400 · your profile: python, go · backend ×` |
| Guides | `40 of 132 guides · 9 of 20 paths · your profile: security ×` |
| Mock | `30 of 95 · your profile: backend ×`, the new medium and hard problems a mock picks from |

Its counts are those of the command's last line, without the search. The chip is a button, reached with `Tab` like every chip: choosing it widens every part it names, as `--widen` does; on the Mock view, it widens the next mock only. **edit profile**, after it, opens the profile in Settings ([the Profile section](settings.md#the-profile-section)). Then come a removable chip per filter, how many rows show of the whole list, and **clear**, which empties the filters and the widening, so the profile applies again. While the profile hides nothing, there is no chip.

## Edit and save

Open a file by choosing it in the tree; each opens in a tab of its own, and `Cmd+S` saves it. [The editor and code intelligence](editor.md) covers saving, changes made elsewhere, indentation, and the help the editor can give.

## Run the tests and submit

| Action | Button | Keys | Same as |
|--------|--------|------|---------|
| Run the tests | Run tests | `Cmd+Enter` | `cstudy test` |
| Submit a project level | Submit | `Cmd+Shift+Enter` | `cstudy submit` |
| Cancel a run | The button that started it, which reads Cancel while the run is active | `Escape` in the results; both ask a question first | Ctrl-C in the terminal |
| Go to the next error | | `F8` | |

Results arrive as the run goes: one row per case or test, the build line, errors with a link to their line, and the summary. **Run options** sets what `cstudy test` takes as flags: chosen cases, a level, stress runs and a seed, the time limit, `--perf`, and type-checking for TypeScript. A submission that passes a level opens the next one: the statement, the tree and the header follow at once.

Run tests, Submit and Bench save every tab with unsaved edits first. If a file changed or was deleted on disk, or a save is refused, nothing runs: the results name the file and why, and its tab's banner offers the way on. Only one run per attempt runs at a time. A run started in another tab shows in this one too, and either tab can cancel it.

## Project files

For a project problem, the tree shows every file of the project folder with its origin (starter, level N test, yours) and its state: `modified`, `added` or `deleted`.

| Do | How |
|----|-----|
| Open a file's actions | Its ⋯ button, a right click, `Shift+F10` or the context-menu key |
| New file, new folder | The `+ file` and `+ folder` buttons above the tree |
| Rename or move | `F2`, or the file's actions |
| Delete | `Delete`, or the file's actions; the question says whether Restore can bring it back |
| Restore a starter or test file | The file's actions, as `cstudy start --restore`; a modified file asks first |

For other problems the tree shows the files you may edit: the stub `cstudy start` wrote, and for Java, Kotlin and Go any other file in the problem's package.

## Service projects in the page

A [service project](service-projects.md) runs your app in a Docker sandbox, with mock servers for the APIs it calls. The page runs the same commands as the terminal, and shows the stack as it starts, runs and stops.

| Part | What you see |
|------|--------------|
| Before you start | The Problems view, the Problem view and the Start dialog list what the project needs: Docker, its images, the size of its install and the memory it takes. Start downloads nothing: the first run, or the first dev stack, pulls the images and installs the dependencies |
| Docker messages | A Docker that is missing or refuses you is said in the words of `cstudy start`: in the Start dialog, in the Attempt view before any run, at the end of a run that Docker stopped, and in the Health view. A stopped Docker is no problem: the first run starts it |
| Run tests and Submit | `cstudy test` and `cstudy submit`, with progress as they go. The results panel's `stack` line follows the stack: `starting Docker`, `pulling images`, `installing dependencies`, `starting`, then `ready after 2.4 s, not counted`. The startup never counts toward a time limit or a result. `commands.test` is one test row, and the visible cases follow it. **Run options** offers only the level, for Submit |
| Cancel | Stops the run, as for any run. `cstudy` takes the stack down before it exits, so the `stack` line ends on `down` |
| The dev stack | The panel above the results starts `cstudy dev` only when you choose **Start dev stack**, since a stack holds memory. It shows the stack's stage, your app's address on this computer as a link (`http://127.0.0.1:<port>`), a scenario picker per mock server that switches it while the stack runs, and your app's last 200 lines. **Stop** takes the stack down and keeps its data; leaving the Attempt view or the page stops it too. If a terminal already runs `cstudy dev` for the project, the panel says so and starts no second one |
| Code intelligence | For TypeScript, Python, Java, Kotlin and Go, the language server runs in a sandboxed container of its own, with no network, and reads the packages the install put in the project. Java's runs on the project's own image, so it needs no JDK 25 on your computer, and starts afresh with each session, so its first errors take a while. Go's gopls is built into the project's install cache by the install, once code intelligence is on: turn it on, then run the tests once. Kotlin's needs the Linux build of the Kotlin language server, which `cstudy doctor --fix` fetches once you start a Kotlin service project, a large download, and the image `gradle:9.8.2-jdk25`, also large, which you pull once yourself with the command the status bar names; its first errors take a while too. While Docker does not answer, or the container's image is missing, the status bar says so with **Restart**, and the editor works without it |

The flags of `cstudy dev` that serve your own IDE, `--no-run`, `--debug`, `--reset-data` and `--exec`, stay in the terminal ([your own IDE](service-projects.md#your-own-ide-and-debugger)).

## Read an earlier attempt

An attempt you finished is not lost when you start the review: its files stay in your workspace, and the Problem view's **History** opens them. Expand an attempt's row, then choose **View** to read its code in a dialog, with the same highlighting as the editor and no way to change it.

| What the row says | Where the files are read from |
|-------------------|-------------------------------|
| `archived` | `.archive/<slug>/<attempt id>-<language>/`, where the next start moved them. A review attempt and `--fresh` both do that; nothing is deleted |
| `current files` | Your practice file, project folder or notes, where the attempt left them. Only the latest attempt of a problem and language can read from there, and you may have edited them since it ended |
| `not available` | An older attempt whose files were never archived, or that you deleted |

An attempt still in progress links to its Attempt view instead, where its files are editable.

## Hints, solutions, Done and Abort

| Button | What happens |
|--------|--------------|
| Hint | Shows the next hint under the statement. Any hint caps the review grade at `ok` |
| Solution… | Asks first when an unsolved attempt is in progress, since the attempt is then graded as `again`; the reference opens in a read-only pane, never in your files |
| Done… | Finishes the attempt with a rating (`easy`, `ok`, `hard`) or as given up, and optional notes; it shows the lines `cstudy done` prints, with the next review date. It grades the latest run, so it refuses while a tab has unsaved edits: save and run first. For a problem with levels, passing level 1 is enough for a rating: the attempt passes through the highest level you passed (`passed · through level 2 of 4`) and comes back on its normal review schedule. A mock still needs every level |
| Abort… | Stops working on the problem, as `cstudy abort` does, after a question: the attempt ends as abandoned, leaves the menu of attempts in progress, and the page opens the problem. Your files stay, and your progress and review schedule do not change; a new Start begins a fresh attempt in the same file (for a problem with a review due, the file first moves to `.archive/`). It refuses while a run is active and while a tab has unsaved edits |

## Problem sets

A set is a list of problems you choose, in the order you want to study them ([plan your practice](planning.md#problem-sets)). Open **Sets** (`Alt+2`) and choose **New set…**, or start from a problem: each row of the Problems view, and the Problem view, has a button that shows the sets the problem is in and opens a dialog to tick others or name a new one.

An open set lists its rows in order with their status and a **Start…** or **Resume** on each, and **Up**, **Down** and **Remove** to change it. It shows passed of total, and the pick `cstudy next --set` makes: an attempt you have open in the set, then the first entry you have not passed, then a due review. The Set filter of the Problems view shows the same rows in the same order, and its Next card follows the filter.

## Learn with guides

Open **Guides** (`Alt+3`) to read the [guides and learning paths](guides.md): each path with its level and progress, from the introductory ones to the advanced, then every guide with its level and whether you have read it. Type in the search (`/` jumps there) to find guides and paths by title, summary or slug, and narrow them by domain and job role, within your [learner profile](#filters-and-your-profile), by level, by path, which lists that path's guides in its order, and by what you have read; a reload or Back from a guide keeps them, and **clear** empties them. A guide shows its diagrams in the page's theme, its code highlighted, what to read first, the problems that practice it and what to read next, and **Mark as read** at its end. An example in several languages shows as tabs, starting on your `default_lang` (bash in a guide about the shell); choosing a tab switches every example that has that language, and the choice holds for the guides you read until the page reloads. A path shows each step in order, with a check once it is done. The page is the best place to read guides, since it draws the diagrams.

## Read the docs

Open **Docs** (`Alt+8`) for these pages. The list shows every topic by section, with a search field: type a few words and the results show each section of a page that holds all of them, with the words around the first match. `/` focuses the field. A page shows its sections under **on this page**, every other page beside it, and the previous and next page at its end. Each heading has an address of its own, such as `#/docs/web-ui/keyboard`, so a link can open a page at one section. `cstudy docs --open` and `cstudy docs <topic> --open` open the page from the terminal.

## Mock interviews

The Mock view starts a mock as `cstudy mock` does: new medium and hard problems, a shared timer, and hints and solutions locked until the timer ends or every problem is done. Each problem opens as an ordinary attempt. A mock started in the terminal shows in the page too. Its language list holds the workspace's languages, and its picks stay within your learner profile: the profile chip shows while the profile hides some of them, and removing it widens this mock ([filters and your profile](#filters-and-your-profile)).

## Keyboard

Every view works with the keyboard alone. On Linux, read `Ctrl` for `Cmd`.

| Keys | Do |
|------|----|
| `Alt+1` to `Alt+8` | Problems, Sets, Guides, Mock, Progress, Health, Settings, Docs |
| `/` | Focus the search of the Problems, Guides or Docs view |
| `Cmd+S` | Save the active tab |
| `Cmd+Enter` | Run the tests |
| `Cmd+Shift+Enter` | Submit a project level |
| `Escape` in the results | Cancel the run, after a question |
| `F8`, `Shift+F8` | Go to the next and the previous error in the editor |
| `F12`, `Cmd`-click, `Ctrl+-` | Go to a definition, and back: [code intelligence](editor.md#keys-and-mouse) |
| `Alt+Shift`-click in the editor | Add a second cursor |
| `Tab` in the editor | Accept the selected completion when the list is open, otherwise indent; `Escape` then `Tab` moves on to the next control |
| `Alt+Shift+M` (`Ctrl+M` on Linux) | Make `Tab` move the focus out of the editor until pressed again |
| `Shift+F10`, `F2`, `Delete` in the tree | A file's actions, rename, delete |
| `Escape` in a dialog | Close it; the focus returns where it was |

Each button names its keys and the `cstudy` command it runs when you point at it. With "Reduce motion" on in your system, the page shows no animation.

## With the terminal and your IDE

The page, the terminal and your IDE always agree, because they share the workspace and its progress. Start an attempt in the terminal and it appears in the page's in-progress menu; submit in the terminal and the page opens the new level; edit in your IDE and the open tab follows. The command line under the top bar names the `cstudy` command each view mirrors, so you can switch to the terminal at any point.

A few things stay in the terminal: `cstudy init`, `cstudy ide`, `cstudy new`, `cstudy verify` on catalog problems, `cstudy test --debug`, which needs your IDE's debugger, and the flags of `cstudy dev` beyond its scenarios. `cstudy test --watch` becomes the Run on save preference.

## When something goes wrong

[Troubleshooting](troubleshooting.md#the-web-ui) lists what the page may say and what to do.

## Security, in plain words

- **Only your computer can reach it.** The server listens on `127.0.0.1`, which other machines cannot connect to.
- **The URL is a password.** Its token is new each time the server starts; anyone with the URL can use the page while it runs, so do not share it. The browser keeps a session cookie after the first visit.
- **Other websites cannot use it.** The page refuses requests that come from other sites, even from tabs in the same browser.
- **It runs your code, as `cstudy test` does.** Saving a file and running it executes that code as you, which is why the page asks for the token.
- **It touches only your attempt's files.** The page edits the files of the attempts in progress and nothing else, and never follows a link out of them.
- **Language servers stay on your computer.** With code intelligence on, the servers run as you, one per tab and project, and read only what a definition names, as read-only text. They cannot reach the network or the folders that hold reference solutions. A service project's server runs in a sandboxed container on your own Docker instead, with no network.
- **Nothing leaves your machine.** The page loads everything from the server and sends nothing elsewhere.
