/**
 * The dialog of the add-to-set control (docs/specs/web-ui.md#sets-view): one checkbox per set, each
 * change applied at once, and a field that makes a set and adds the problem to it.
 */

import type { PageContext } from "./context.ts";
import { command, h } from "./dom.ts";
import { openSheet } from "./dialogs.ts";
import { setNameIssue } from "./sets-model.ts";
import { setsHolding } from "./setControl.ts";
import { failure, loading, messageOf } from "./states.ts";
import type { SetList } from "./types.ts";

const SETS = "/api/v1/sets";

/** Resolves with the sets the problem is in, once the dialog closes; `changed` hears each change. */
export async function openSetMembership(context: PageContext, slug: string, changed: (names: readonly string[]) => void): Promise<readonly string[]> {
  const sheet = openSheet(`sets · ${slug}`);
  sheet.body.append(loading());
  let held: readonly string[] = [];
  try {
    const { sets } = await context.api.get<SetList>(SETS);
    held = setsHolding(sets, slug);
    fill(sets.map((found) => found.name));
  } catch (error) {
    sheet.body.replaceChildren(failure(error));
  }
  await sheet.closed;
  return held;

  function fill(names: readonly string[]): void {
    const said = h("p", { class: "quiet set-said", role: "status" }, command(`cstudy set add <name> ${slug}`));
    const issue = h("p", { class: "dialog-issue", "aria-live": "polite" });
    const choices = h("ul", { class: "plain set-choices" }, ...names.map((name) => choice(name, held.includes(name))));
    const hint = names.length ? null : h("p", { class: "quiet set-none" }, "You have no sets yet. Name one, and this problem joins it.");

    function report(name: string, joined: boolean): void {
      const others = held.filter((found) => found !== name);
      held = joined ? [...others, name] : others;
      changed(held);
      said.replaceChildren(command(`cstudy set ${joined ? "add" : "remove"} ${name} ${slug}`));
    }

    function choice(name: string, ticked: boolean): HTMLElement {
      const box = h("input", { type: "checkbox", id: `set-choice-${name}`, checked: ticked });
      box.addEventListener("change", () => {
        const joined = box.checked;
        box.disabled = true;
        issue.textContent = "";
        context.api
          .post(`${SETS}/${encodeURIComponent(name)}/${joined ? "add" : "remove"}`, { slugs: [slug] })
          .then(() => report(name, joined))
          .catch((error: unknown) => {
            box.checked = !joined;
            issue.textContent = messageOf(error);
          })
          .finally(() => {
            box.disabled = false;
            box.focus();
          });
      });
      return h("li", {}, box, " ", h("label", { for: box.id }, name));
    }

    const field = h("input", { id: "set-new-name", type: "text", spellcheck: "false", autocomplete: "off", autocapitalize: "off", placeholder: "backend-loop", "aria-describedby": "set-new-note" });
    const create = h("button", { type: "submit", class: "button" }, "Create and add");
    const form = h(
      "form",
      { class: "set-new", novalidate: true },
      h("div", { class: "field" }, h("label", { for: field.id }, "New set"), field),
      create,
    );
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      const name = field.value.trim();
      const refused = setNameIssue(name);
      issue.textContent = refused ?? "";
      if (refused !== null) return;
      create.disabled = true;
      context.api
        .post(SETS, { name })
        .then(() => context.api.post(`${SETS}/${encodeURIComponent(name)}/add`, { slugs: [slug] }))
        .then(() => {
          hint?.remove();
          choices.append(choice(name, true));
          report(name, true);
          field.value = "";
          field.focus();
        })
        .catch((error: unknown) => {
          issue.textContent = messageOf(error);
        })
        .finally(() => {
          create.disabled = false;
        });
    });
    sheet.body.replaceChildren(
      hint ?? choices,
      ...(hint === null ? [] : [choices]),
      form,
      h("p", { id: "set-new-note", class: "quiet" }, "A name is lowercase letters, digits and hyphens."),
      issue,
      said,
    );
    (sheet.body.querySelector<HTMLElement>("input") ?? field).focus();
  }
}
