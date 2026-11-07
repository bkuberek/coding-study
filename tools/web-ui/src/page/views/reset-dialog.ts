/**
 * The Settings view's Danger section (docs/specs/web-ui.md#settings-view): `cstudy reset`, after a
 * preview of what goes, with the word typed in a dialog, which the server needs too.
 */

import { refreshAttemptsMenu } from "../attempts.ts";
import type { PageContext } from "../context.ts";
import { command, h } from "../dom.ts";
import { failure, messageOf } from "../states.ts";

const RESET = "/api/v1/reset";

interface ResetEntry {
  readonly label: string;
  readonly count: number;
}

interface ResetPreview {
  readonly word: string;
  readonly warning: string;
  readonly busy: string | null;
  readonly kept: readonly string[];
  readonly groups: readonly { readonly option: string | null; readonly title: string; readonly entries: readonly ResetEntry[] }[];
}

export function dangerSection(context: PageContext): HTMLElement {
  const status = h("p", { class: "quiet", role: "status" });
  const open = h("button", { type: "button", class: "button danger" }, "Reset progress…");
  open.addEventListener("click", () => {
    void askReset(context, status).catch((error: unknown) => {
      status.textContent = `error: ${messageOf(error)}`;
    });
  });
  return h(
    "section",
    { class: "danger-zone", "aria-labelledby": "danger-heading" },
    h("h3", { id: "danger-heading", class: "eyebrow" }, "danger"),
    h("p", { class: "quiet" }, "Delete your progress in this workspace, as ", command("cstudy reset"), " does. You see what goes before anything does."),
    open,
    status,
  );
}

function entries(found: readonly ResetEntry[]): HTMLElement {
  return h("ul", { class: "plain" }, ...found.map((entry) => h("li", {}, `${entry.label}: ${entry.count}`)));
}

async function askReset(context: PageContext, status: HTMLElement): Promise<void> {
  const [preview, { askNames }] = await Promise.all([context.api.get<ResetPreview>(RESET), import("../sheets.ts")]);
  const options = new Map<string, HTMLInputElement>();
  const groups = preview.groups.map(({ option, title, entries: found }) => {
    if (option === null) return h("div", { class: "field" }, h("strong", {}, title), entries(found));
    const box = h("input", { type: "checkbox", id: `reset-${option}` });
    options.set(option, box);
    return h("div", {}, h("div", { class: "field check" }, box, h("label", { for: box.id }, `also delete ${title}`)), entries(found));
  });
  await askNames({
    title: "reset progress and state",
    destructive: true,
    action: "Reset",
    content: [
      h("p", { class: "question" }, preview.warning),
      ...(preview.busy === null ? [] : [failure(new Error(preview.busy))]),
      ...groups,
      h("p", { class: "quiet" }, `Kept: ${preview.kept.join("; ")}.`),
    ],
    fields: [{ label: `Type ${preview.word} to confirm`, prefix: "", value: "", issue: (typed) => (typed === preview.word ? null : `type ${preview.word}`) }],
    submit: async ([word]) => {
      const switches = Object.fromEntries([...options].map(([option, box]) => [option, box.checked]));
      const { deleted } = await context.api.post<{ readonly deleted: readonly ResetEntry[] }>(RESET, { confirm: word, ...switches });
      status.textContent = `deleted ${deleted.map((entry) => `${entry.label} ${entry.count}`).join(" · ")}`;
      refreshAttemptsMenu(context);
      void context.mock.refresh();
      return null;
    },
  });
}
