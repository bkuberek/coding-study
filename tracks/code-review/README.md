# Code review

Non-autograded code review items: a change plus a prompt ("review this pull request"). Each item is a directory `tracks/code-review/<slug>/`; the full format is in [docs/specs/content.md](../../docs/specs/content.md#non-autograded-item-format) and the checks in [docs/specs/authoring.md](../../docs/specs/authoring.md#items).

## Practice loop

| Step | Command | Effect |
|------|---------|--------|
| 1 | `cstudy next --track code-review` | Picks a due or new item |
| 2 | `cstudy start <slug>` | Copies `template.md` to `notes/code-review/<slug>.md` in your workspace and renders the prompt with the change to `.statements/<slug>.md` |
| 3 | Write your review in the notes file | Issues by severity, each with its location and the change you would ask for |
| 4 | `cstudy solution <slug>` | Shows the rubric, then the issues a strong reviewer finds |
| 5 | `cstudy done <slug> --rating easy\|ok\|hard` | Self-graded; schedules the next review |

## Item files

```text
tracks/code-review/<slug>/
  item.yaml       # slug, title, track, difficulty, estimate_minutes, status, order, references, related
  prompt.md       # Context, Task
  change.diff     # the change as a unified diff; or files/ with the code under review (exactly one)
  rubric.md       # "- [ ] <criterion>" lines grouped under "## <area>"
  reference.md    # "## Blocker", "## Major", "## Minor", "## Nit" (in this order, any subset), each a "- " list
  template.md     # the notes skeleton: "# <title>: Notes" plus the severity sections
```

Write the change yourself (original code, never copied from a real project), small enough to review in the item's `estimate_minutes`, and plant issues across severities. Each `reference.md` issue names its location first, for example ``- `charge`: retrying a POST without an idempotency key can charge twice.``

## Notes template

```markdown
# <title>: Notes

## Blocker

## Major

## Minor

## Nit
```

Gate before merging items: `cstudy verify --track code-review --require-ready` exits 0.
