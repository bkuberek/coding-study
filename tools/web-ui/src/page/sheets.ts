/**
 * The page's dialogs as one chunk, with one stylesheet, fetched the first time a control opens any
 * of them (docs/specs/web-ui.md#front-end-assets): they share most of their code and words, so
 * together they weigh less than each on its own would (NFR-12).
 */

export { askNames, confirmAction, openSheet } from "./dialogs.ts";
export { openDoneDialog } from "./doneDialog.ts";
export { showPastFiles } from "./pastFiles.ts";
export { openSolution } from "./solutionPane.ts";
export { openStartDialog } from "./startDialog.ts";
export { TreeActions } from "./treeActions.ts";
