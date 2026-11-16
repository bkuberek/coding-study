---
title: Guides and learning paths
summary: Short guides that teach an idea before you practice it, paths that put guides and problems in order, and how to read them in the terminal or the web UI.
section: Practice
order: 80
---

# Guides and learning paths

A **guide** is a short reading that teaches one idea before you practice it: the idea in plain words, a worked example traced step by step, when to use it, the common traps, its cost with the conditions that hold, notes for experts, and the problems that practice it. Every example in a guide is a real program that a test runs, so it prints what the guide says.

A **path** puts guides and problems in order, from a topic's first idea to an expert's. "Getting started" goes from the terminal to your first problem; others cover hashing, AI engineering, data engineering, testing, networking, machine learning, operating systems, distributed systems, database internals, infrastructure as code, knowledge representation, security, and the classic algorithm patterns. Each path has a level, introductory, core or advanced, and the list shows them in that order.

## In the terminal

```bash
cstudy learn                           # the guides and the paths, with what you have read
cstudy learn --path hashing            # a path's steps, what is done, and the next one
cstudy learn --search hash --level core   # the guides and paths that match
cstudy learn hash-functions            # read a guide
cstudy learn hash-functions --done     # mark it read
cstudy learn hash-maps-and-sets --lang go   # the examples in Go, where they have it
```

`--search` keeps the guides and paths whose title, summary or slug holds every word, `--level` those at one level (`intro`, `core` or `advanced`), and `--status read` or `--status not_read` those you have read or not; they combine.

`cstudy learn <guide>` prints the guide, each diagram as a drawing in text. On a terminal it is formatted; piped to a file or another program, it is the guide's Markdown as written. Some examples come in several languages. The terminal prints each in one: the one `--lang` names, else bash in a guide about the shell, else your `default_lang`, else Python, where the example has it, and names the others with the command that shows one. Printing a guide does not mark it read: `--done` does, and it needs a workspace, since it records your progress. Reading needs none.

A path lists its steps with their state, and the command for the next one:

```text
$ cstudy learn --path hashing
hashing  Hashing: from your first hash map to content-addressed storage
From what a hash function is to Merkle proofs, through the problems that practice each idea.
3 of 22 done
#   KIND     STEP                       TARGET   STATUS          TITLE
1   guide    hash-functions                      read            What a hash function is
2   guide    hash-maps-and-sets                  read            Hash maps and sets
3   problem  contains-duplicate                  passed          Contains Duplicate
4   problem  two-sum                             attempted       Two Sum
next    cstudy start two-sum
```

| A step | Is done when |
|--------|--------------|
| A guide | You marked it read |
| A problem | It has a passed attempt, through every level for a problem with levels |
| A problem with a target such as `level 2` | An attempt passed that level |

`--json` prints the same as one document, for scripts.

## In the web UI

The web UI is the best place to read guides, since it draws the diagrams. Open **Guides** (`Alt+3`), or open the page on a guide or a path from the terminal:

```bash
cstudy learn hash-functions --open
cstudy learn --path hashing --open
```

| Where | What you see |
|-------|--------------|
| The list | Each path with its progress, `3 of 22 steps done`, then every guide with its level and whether you have read it |
| A guide | The guide with its diagrams drawn in the page's light or dark theme, its code highlighted, what to read first, the problems that practice it and what to read next. **Mark as read** at the end records it, as `cstudy learn <guide> --done` does |
| A path | Each step in order, with a check once it is done. **Read** opens a guide and **Start** a problem's page. `next:` names the first step not done |
| A problem | Under **read first**, the guides that teach what it practices |

Each diagram is a picture that ships with `cstudy`, in the page's colors, and switches with the theme. Nothing is fetched from the internet. Under it, a caption says what it shows, and a screen reader reads the diagram's title with it.

## Your reading progress

What you mark read is stored in `progress.db` with the rest of your progress, so `cstudy export` carries it and `cstudy reset` clears it. Marking a guide again changes nothing and says when you first marked it.
