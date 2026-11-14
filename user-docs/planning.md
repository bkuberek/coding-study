---
title: Plan your practice
summary: What cstudy next picks and why, problem sets for an interview or a topic, timed mock interviews, and your progress in numbers.
section: Practise
order: 90
---

# Plan your practice

You can let `cstudy` choose what to practise, choose yourself from a list you made, or test yourself under a timer.

## What to do next

```bash
cstudy next
```

`cstudy next` picks one thing, in this order:

1. **An attempt you have open**, so you finish what you started. Other open attempts are listed after it.
2. **A review that is due**: a problem you solved before, which the schedule brings back before you forget it.
3. **A new problem from your weakest area**: the pattern, or the track outside `dsa`, where your recent attempts failed most, you have mastered least, and you have not practised for longest. Within it, easy problems come first, then medium once you passed an easy one, then hard.

```text
review  merge-intervals  (medium · intervals)  overdue 3d, interval 7d
start   cstudy start merge-intervals --lang kotlin
```

It prints the command that starts the pick; `--start` runs it for you.

| Flag | Does |
|------|------|
| `--track T` | Only this track; repeat it for several. Without it, the tracks of `next.tracks` in your [configuration](settings.md#your-configuration), `dsa` unless you change it |
| `--pattern`, `--difficulty`, `--domain`, `--role`, `--scope` | Narrow the pick, as the same filters of `cstudy list` do |
| `--lang L` | Only problems in this language, which `--start` then uses |
| `--new`, `--review` | Only new problems, or only reviews |
| `--set NAME` | From one of your [sets](#problem-sets), in its order |
| `--start` | Start the pick |
| `--json` | The pick as JSON |

## Problem sets

A set is a list you choose, in the order you want to study it: make one for an upcoming interview or a topic, add problems to it, and study from it without searching. A problem can be in several sets.

```bash
cstudy set create backend-loop --description "The backend loop on the 12th"
cstudy set add backend-loop two-sum lru-cache url-shortener
cstudy next --set backend-loop           # the next entry to do
cstudy list --set backend-loop           # every entry, in order, with its status
cstudy set list                          # your sets, with passed of total
```

`cstudy next --set` picks an attempt you have open in the set first, then the first entry you have not passed, then a due review from the set.

| Command | Does |
|---------|------|
| `cstudy set create <name>` | Makes an empty set; `--description` says what it is for |
| `cstudy set add <name> <slug>...` | Adds problems or items to its end |
| `cstudy set remove <name> <slug>...` | Takes them out |
| `cstudy set move <name> <slug> <position>` | Moves one, counting from 1 |
| `cstudy set show <name>` | Its entries in order, with their status |
| `cstudy set rename <name> <new-name>` | Renames it, keeping its entries |
| `cstudy set delete <name>` | Deletes it, after a question; your progress stays |

Sets live in `sets.yaml` at the root of your workspace, so you can read it, edit it by hand and commit it. A change from `cstudy` or the web UI touches only the lines it must, so your comments stay. `cstudy reset` keeps your sets. A problem the catalog no longer has shows as `missing` and stops nothing, and a file that does not parse shows as an error and is never overwritten.

For a problem with levels, an entry may aim lower than every level: `cstudy set add backend-loop tamper-evident-ledger --level 2` counts the entry once you pass level 2, and its row says `through level 2 (target)`. In the file, that entry is `- {slug: tamper-evident-ledger, level: 2}`.

The web UI's **Sets** view (`Alt+2`) shows the same sets, and each problem has a button to add it to one ([the web UI](web-ui.md#problem-sets)).

## Mock interviews

A mock interview starts new medium and hard problems together under one shared timer, as in an interview:

```bash
cstudy mock                              # two problems, 45 minutes
cstudy mock --count 3 --minutes 60 --lang java
```

Each problem opens as an ordinary attempt. Until the timer ends or every problem is done, `cstudy hint` and `cstudy solution` are locked. Finishing a problem over the timer caps its grade at `hard`, and a problem with levels passes only with every level. The Mock view of the web UI (`Alt+4`) starts the same mock and shows its countdown.

| Flag | Does |
|------|------|
| `--minutes` | The shared timer, 45 by default |
| `--count` | How many problems, 2 by default |
| `--track` | Only this track; repeat it for several |
| `--lang` | The language, `default_lang` by default |

## Your progress

```bash
cstudy stats                             # by pattern
cstudy stats --by track                  # or lang, or difficulty
cstudy stats --since 2026-10-01
```

```text
GROUP           PROBLEMS  ATTEMPTED  PASSED  MASTERED  PASS RATE  SOLVE TIME  WEAKNESS
arrays-hashing        17          5       4         1        80%     14m 10s      0.42
two-pointers          10          0       0         0          -           -      0.75

attempts  6 finished · 5 in the last 7 days · streak 3 days
reviews   1 due today · 1 overdue
bench     4 benched · 2 optimal · 1 near-optimal · 1 suboptimal · 0 unknown
```

The weakness column is what `cstudy next` reads to pick a new problem: the higher it is, the sooner that area comes up. The Progress view of the web UI (`Alt+5`) shows the same numbers, with the reviews due.

## How reviews are scheduled

Each time you finish an attempt, its grade sets when the problem comes back ([how the grade is set](practice.md#how-the-grade-is-set)). Problems you find easy come back rarely, and problems you struggle with come back soon, so your time goes where it helps most. A problem counts as mastered once its review interval reaches 21 days. The intervals are yours to change, under `[schedule]` in your [configuration](settings.md#your-configuration).
