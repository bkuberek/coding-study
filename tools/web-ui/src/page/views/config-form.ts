/**
 * The Settings view's form of `config.toml` (docs/specs/web-ui.md#settings-view), drawn from what the
 * server describes of each key, so a new key needs nothing here.
 */

import { changedKeys, type ConfigDocument, type ConfigKey, type ConfigValue, shownValue, tablesOf, typedValue } from "../config-keys.ts";
import { confirmed } from "../confirmation.ts";
import type { PageContext } from "../context.ts";
import { command, h } from "../dom.ts";
import { confirmLazily } from "../lazy.ts";
import { failure, loading, messageOf, showFailure } from "../states.ts";

const CONFIG = "/api/v1/config";

type Field = readonly [control: HTMLElement, read: () => ConfigValue];

export function configForm(context: PageContext): HTMLElement {
  const region = h("div", {}, loading("reading config.toml…"));
  const show = (document: ConfigDocument, saved = ""): HTMLElement => {
    const save = h("button", { type: "submit", class: "button primary", disabled: !document.writable }, "Save");
    const status = h("p", { class: "quiet", role: "status" }, saved);
    const fields = new Map(document.keys.map((key) => [key, fieldOf(key)]));
    const form = h(
      "form",
      { class: "settings-form" },
      ...tablesOf(document.keys).map(([table, keys]) => h("fieldset", {}, h("legend", {}, table || "general"), ...keys.map((key) => row(key, fields)))),
      save,
      status,
    );
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      const changes = changedKeys([...fields].map(([key, [, read]]) => [key, read()]));
      if (Object.keys(changes).length === 0) {
        status.textContent = "nothing changed";
        return;
      }
      status.textContent = "saving…";
      void confirmed(
        (confirm) => context.api.post<ConfigDocument>(CONFIG, { changes, confirm }),
        (question) => confirmLazily({ title: "change progress_db", message: question, action: "Change it", destructive: false, command: "cstudy config edit" }),
      )
        .then((after) => {
          if (after === null) status.textContent = "not saved";
          else {
            const note = savedNote(after);
            show(after, note).focus();
            context.shell.announce(note);
          }
        })
        .catch((error: unknown) => {
          status.textContent = `error: ${messageOf(error)}`;
        });
    });
    region.replaceChildren(
      h("p", { class: "quiet" }, "Stored in ", h("code", {}, document.path), document.exists ? "" : ", made when you save", ", for every workspace; ", command("cstudy config edit"), " opens it."),
      ...document.issues.map((issue) => failure(new Error(issue))),
      form,
    );
    return save;
  };
  context.api
    .get<ConfigDocument>(CONFIG)
    .then((document) => show(document))
    .catch((error: unknown) => showFailure(region, error));
  return region;
}

function savedNote(document: ConfigDocument): string {
  const changed = document.keys.filter((key) => document.changed?.includes(key.name));
  return changed.length ? `saved: ${changed.map((key) => `${key.name} applies ${key.applies}`).join("; ")}` : "nothing changed";
}

function row(key: ConfigKey, fields: ReadonlyMap<ConfigKey, Field>): HTMLElement {
  const id = idOf(key);
  const control = fields.get(key)?.[0] ?? null;
  control?.setAttribute("aria-describedby", `${id}-help`);
  return h(
    "div",
    { class: "config-key" },
    h("label", { for: id }, key.name),
    control,
    h("p", { id: `${id}-help`, class: "quiet" }, `${key.help} Default: ${shownValue(key.default)}. Applies ${key.applies}.`),
  );
}

function idOf(key: ConfigKey): string {
  return `config-${key.name.replace(/\W/g, "-")}`;
}

function fieldOf(key: ConfigKey): Field {
  const id = idOf(key);
  if (key.kind === "boolean") {
    const input = h("input", { type: "checkbox", id, checked: key.value === true, disabled: key.reserved });
    return [input, () => input.checked];
  }
  if (key.choices.length > 0) {
    const multiple = key.kind === "choices";
    const held = [key.value].flat();
    const select = h("select", { id, multiple }, ...key.choices.map((choice) => h("option", { value: choice, selected: held.includes(choice) }, choice)));
    return [select, () => (multiple ? [...select.selectedOptions].map((option) => option.value) : select.value)];
  }
  const input = h("input", {
    type: "text",
    id,
    value: key.value === null ? "" : shownValue(key.value),
    placeholder: shownValue(key.default ?? key.example),
    inputmode: key.kind === "integer" ? "numeric" : null,
    spellcheck: "false",
    autocomplete: "off",
  });
  return [input, () => typedValue(key, input.value)];
}
