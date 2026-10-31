/**
 * The Solution pane (docs/specs/web-ui.md#solutions): the approach picker and the other
 * selections `cstudy solution` takes, the question it asks before grading an unsolved attempt
 * `again`, and the reference in a read-only pane, never in an editor tab. It is a chunk of its
 * own, fetched when a Solution button is first used (NFR-12).
 */

import { confirmed } from "./confirmation.ts";
import type { PageContext } from "./context.ts";
import { confirmDialog, openSheet } from "./dialogs.ts";
import { h, rendered } from "./dom.ts";
import { SOLUTION_COMMAND } from "./solution.ts";
import { failure, loading } from "./states.ts";
import type { ProblemDocument, SolutionDocument } from "./types.ts";

const ITEM = "item";
const PROJECT = "project";
const DEFAULT = "";
const ALL = "*all";
const FIRST_BROKEN = "*first";
const BROKEN_PREFIX = "broken:";

export interface Selection {
  /** Null: the attempt's language, else `default_lang`. */
  readonly language: string | null;
  /** Null: the first optimal approach. */
  readonly approach: string | null;
  readonly all: boolean;
  /** `true` for the first broken reference, an id for that one, null for none. */
  readonly broken: string | true | null;
  readonly explanationOnly: boolean;
}

export const NO_SELECTION: Selection = { language: null, approach: null, all: false, broken: null, explanationOnly: false };

/** The request body: only the fields the selection sets, as flags left off. */
export function solutionBody(selection: Selection, confirm: boolean): Record<string, unknown> {
  const body: Record<string, unknown> = { confirm };
  if (selection.language !== null) body["language"] = selection.language;
  if (selection.approach !== null) body["approach"] = selection.approach;
  if (selection.all) body["all"] = true;
  if (selection.broken !== null) body["broken"] = selection.broken;
  if (selection.explanationOnly) body["explanation_only"] = true;
  return body;
}

export function solutionCommand(slug: string, selection: Selection): string {
  const broken = selection.broken === true ? "--broken" : selection.broken === null ? null : `--broken=${selection.broken}`;
  const flags = [
    selection.language === null ? null : `--lang ${selection.language}`,
    selection.approach === null ? null : `--approach ${selection.approach}`,
    selection.all ? "--all" : null,
    broken,
    selection.explanationOnly ? "--explanation-only" : null,
  ];
  return [`cstudy solution ${slug}`, ...flags].filter(Boolean).join(" ");
}

/** Opens the Solution pane of `slug` in a dialog. */
export function openSolution(context: PageContext, slug: string): void {
  const sheet = openSheet(`solution · ${slug}`, true);
  sheet.body.append(loading("reading the problem…"));
  context.api
    .get<ProblemDocument>(`/api/v1/problems/${encodeURIComponent(slug)}`)
    .then((problem) => sheet.body.replaceChildren(solutionPane(context, problem)))
    .catch((error: unknown) => sheet.body.replaceChildren(failure(error)));
}

function solutionPane(context: PageContext, problem: ProblemDocument): HTMLElement {
  const isItem = problem.kind === ITEM;
  const pane = h("div", { class: "solution-pane" });
  const line = h("code", { class: "cmd" });
  const show = h("button", { type: "submit", class: "button primary" }, isItem ? "Show the rubric and reference" : "Show");
  const controls = isItem ? null : selectionControls(problem);
  const selection = () => (controls ? controls.selection() : NO_SELECTION);
  const update = () => {
    line.textContent = solutionCommand(problem.slug, selection());
    const locked = context.mock.lock(SOLUTION_COMMAND);
    show.disabled = locked !== null;
    show.title = locked ?? "";
  };
  const reveal = async () => {
    show.disabled = true;
    pane.replaceChildren(loading("reading the reference…"));
    try {
      const send = (confirm: boolean) =>
        context.api.post<SolutionDocument>(`/api/v1/problems/${encodeURIComponent(problem.slug)}/solution`, solutionBody(selection(), confirm));
      const document = await confirmed(send, (question) => confirmDialog(question, "Reveal"));
      pane.replaceChildren(document === null ? h("p", { class: "quiet" }, "not revealed") : shown(document));
      context.shell.announce(document === null ? "not revealed" : `solution of ${problem.slug} shown`);
    } catch (error) {
      pane.replaceChildren(failure(error));
    } finally {
      update();
    }
  };
  const form = h(
    "form",
    { class: "solution-form" },
    controls?.element ?? h("p", { class: "quiet" }, "comparing your notes with the rubric and the reference is the self-review: revealing never lowers an item's grade"),
    isItem ? null : h("p", { class: "quiet" }, "with an unsolved attempt in progress, revealing grades it again; the page asks first"),
    h("p", { class: "sheet-command" }, line, show),
  );
  form.addEventListener("input", update);
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    void reveal();
  });
  update();
  return h("div", { class: "solution" }, form, pane);
}

interface SelectionControls {
  readonly element: HTMLElement;
  selection(): Selection;
}

/** The approach picker, with `all` and the broken references, the language and
 * `--explanation-only`. */
function selectionControls(problem: ProblemDocument): SelectionControls {
  const approach = h(
    "select",
    { id: "solution-approach" },
    h("option", { value: DEFAULT }, "the optimal approach"),
    ...problem.approaches.map((option) => h("option", { value: option.id }, `${option.id} · ${option.name} (${option.role})`)),
    problem.approaches.length > 1 ? h("option", { value: ALL }, "every approach, in ladder order") : null,
    problem.broken.length ? h("option", { value: FIRST_BROKEN }, "a broken reference, to spot the bug") : null,
    ...problem.broken.map((id) => h("option", { value: `${BROKEN_PREFIX}${id}` }, `broken: ${id}`)),
  );
  const language = h(
    "select",
    { id: "solution-language", disabled: problem.kind === PROJECT },
    h("option", { value: DEFAULT }, "default"),
    ...problem.languages.map((name) => h("option", { value: name }, name)),
  );
  const explanationOnly = h("input", { type: "checkbox", id: "solution-explanation-only" });
  const element = h(
    "div",
    { class: "solution-controls" },
    h("div", { class: "field" }, h("label", { for: "solution-approach" }, "approach"), approach),
    h("div", { class: "field" }, h("label", { for: "solution-language" }, "language"), language),
    h("div", { class: "field check" }, explanationOnly, h("label", { for: "solution-explanation-only" }, "explanation only")),
  );
  return {
    element,
    selection(): Selection {
      const picked = approach.value;
      const broken = picked === FIRST_BROKEN ? true : picked.startsWith(BROKEN_PREFIX) ? picked.slice(BROKEN_PREFIX.length) : null;
      const named = picked !== DEFAULT && picked !== ALL && broken === null;
      return {
        language: language.value === DEFAULT ? null : language.value,
        approach: named ? picked : null,
        all: picked === ALL,
        broken,
        explanationOnly: explanationOnly.checked,
      };
    },
  };
}

function shown(document: SolutionDocument): HTMLElement {
  const marked = document.marked_attempt_id;
  return h(
    "article",
    { class: "solution-reference", "aria-label": `Solution of ${document.slug}` },
    marked === null ? null : h("p", { class: "tone-warn" }, `solution revealed: attempt ${marked} is graded as again`),
    rendered(document.html, "prose"),
  );
}
