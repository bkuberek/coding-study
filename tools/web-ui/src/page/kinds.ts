/**
 * The kinds of problem the page tells apart (docs/specs/compatibility.md#rubric-checked-problems).
 * A self-graded kind is checked against a rubric by the person: it has no language and no runs,
 * the answer is a notes file, and Done takes a rating only.
 */

const SELF_GRADED = new Set(["system-design", "code-review"]);

/** Whether a problem of this kind is checked by a rubric and graded by the person. */
export function selfGraded(kind: string): boolean {
  return SELF_GRADED.has(kind);
}
