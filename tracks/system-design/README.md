# System design

Non-autograded system design items. Each item is a directory `tracks/system-design/<slug>/`; the full format is in [docs/specs/content.md](../../docs/specs/content.md#non-autograded-item-format) and the checks in [docs/specs/authoring.md](../../docs/specs/authoring.md#items).

## Practice loop

| Step | Command | Effect |
|------|---------|--------|
| 1 | `cstudy next --track system-design` | Picks a due or new item |
| 2 | `cstudy start <slug>` | Copies `template.md` to `notes/system-design/<slug>.md` in your workspace and renders the prompt to `.statements/<slug>.md` |
| 3 | Answer in the notes file | Time box with `cstudy start <slug> --timer 45m` |
| 4 | `cstudy solution <slug>` | Shows the rubric, then the reference answer |
| 5 | `cstudy done <slug> --rating easy\|ok\|hard` | Self-graded; schedules the next review |

## Item files

```text
tracks/system-design/<slug>/
  item.yaml       # slug, title, track, difficulty, estimate_minutes, status, order, references, related
  prompt.md       # Question, Functional requirements, Non-functional requirements, Scale
  rubric.md       # "- [ ] <criterion>" lines grouped under "## <area>"
  reference.md    # Requirements, Estimates, API, Data model, High-level design, Deep dives, Trade-offs
  template.md     # the notes skeleton: "# <title>: Notes" plus the reference's sections
```

List public sources in `references.links` and, optionally, sections of your own study guide in `references.study_guides`, relative to your [study-guides root](../../docs/specs/content.md#study-guides). `status: ready` needs at least one of the two. Never copy a guide's content here.

## Notes template

```markdown
# <title>: Notes

## Requirements

<!-- Functional and non-functional requirements you clarified, with the numbers you assume. -->

## Estimates

## API

## Data model

## High-level design

## Deep dives

## Trade-offs
```

Gate before merging items: `cstudy verify --track system-design --require-ready` exits 0.
