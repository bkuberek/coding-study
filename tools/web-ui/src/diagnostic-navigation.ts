/**
 * F8, Shift-F8 and Vim's `]d` and `[d` (docs/specs/web-ui.md#live-diagnostics): move to the next or
 * previous diagnostic and open its tooltip, skipping hints. A chunk of its own, fetched at the
 * first key, so a file is editable without it.
 */
import { forEachDiagnostic } from "@codemirror/lint";
import type { EditorState } from "@codemirror/state";
import { activateHover, type Command, type EditorView } from "@codemirror/view";

export interface Range {
  readonly from: number;
  readonly to: number;
}

/**
 * The range F8 or Shift-F8 moves the selection to: the first one that starts after the
 * selection's start (before it, going back), wrapping around; null when that is the selection
 * itself or there is none.
 */
export function neighbouringRange(ranges: readonly Range[], selection: Range, forward: boolean): Range | null {
  const sorted = [...ranges].sort((a, b) => a.from - b.from || a.to - b.to);
  const beyond = forward ? sorted.filter((range) => range.from > selection.from) : sorted.filter((range) => range.from < selection.from);
  const found = (forward ? beyond[0] : beyond.at(-1)) ?? (forward ? sorted[0] : sorted.at(-1));
  if (found === undefined || (found.from === selection.from && found.to === selection.to)) return null;
  return found;
}

function visibleRanges(state: EditorState): Range[] {
  const found = new Map<string, Range>();
  forEachDiagnostic(state, (diagnostic, from, to) => {
    if (diagnostic.severity !== "hint") found.set(`${from}:${to}`, { from, to });
  });
  return [...found.values()];
}

/** Selects the diagnostic's range, as `@codemirror/lint` does; or only puts the cursor at its start, for Vim's normal mode. */
function moveToDiagnostic(forward: boolean, select: boolean): Command {
  return (view: EditorView): boolean => {
    const { from, to } = view.state.selection.main;
    const next = neighbouringRange(visibleRanges(view.state), { from, to }, forward);
    if (next === null) return false;
    const selection = select ? { anchor: next.from, head: next.to } : { anchor: next.from };
    view.dispatch({ selection, scrollIntoView: true });
    activateHover(view, next.from, 1, {
      until: (transaction) =>
        transaction.docChanged || transaction.newSelection.main.head < next.from || transaction.newSelection.main.head > next.to,
    });
    return true;
  };
}


export const selectNextDiagnostic: Command = moveToDiagnostic(true, true);
export const selectPreviousDiagnostic: Command = moveToDiagnostic(false, true);
export const cursorToNextDiagnostic: Command = moveToDiagnostic(true, false);
export const cursorToPreviousDiagnostic: Command = moveToDiagnostic(false, false);
