/**
 * The Settings view's form of `config.toml` (docs/specs/web-ui.md#settings-view), drawn from what the
 * server describes of each key, so a new key needs nothing here. A change stays in its field until
 * the view's Save.
 */

import { changedKeys, type ConfigDocument, type ConfigKey, type ConfigValue, sectionsOf, shownValue, typedValue } from "../config-keys.ts";
import { confirmed } from "../confirmation.ts";
import type { PageContext } from "../context.ts";
import { command, h } from "../dom.ts";
import { confirmLazily } from "../lazy.ts";
import { failure, loading, showFailure } from "../states.ts";

const CONFIG = "/api/v1/config";

interface Field {
  readonly row: HTMLElement;
  readonly read: () => ConfigValue;
  /** What `read` gave when the field was drawn, which a change differs from. */
  readonly drawn: ConfigValue;
}

export interface ConfigStage {
  readonly element: HTMLElement;
  /** What differs from the file, by each key's name, as `POST /api/v1/config` takes it. */
  changes(): Record<string, ConfigValue>;
  /** Marks the rows of what differs. */
  mark(): void;
  /** Draws the file's values again. */
  undo(): void;
  /** Writes what differs and says what became of it; null after a no to the server's question.
   * A refusal rejects, and the fields stay as they are. */
  save(): Promise<string | null>;
}

export function configStage(context: PageContext): ConfigStage {
  const element = h("div", {}, loading("reading config.toml…"));
  let shown: ConfigDocument | null = null;
  let fields: ReadonlyMap<ConfigKey, Field> = new Map();
  const show = (found: ConfigDocument) => {
    const focused = element.contains(document.activeElement) ? document.activeElement?.id : undefined;
    shown = found;
    const drawn = new Map(found.keys.map((key) => [key, fieldOf(key)]));
    fields = drawn;
    element.replaceChildren(
      h("p", { class: "quiet" }, "Stored in ", h("code", {}, found.path), found.exists ? "" : ", made when you save", ", for every workspace; ", command("cstudy config edit"), " opens it."),
      ...found.issues.map((issue) => failure(new Error(issue))),
      ...sectionsOf(found.keys).map(([section, keys]) =>
        h("fieldset", { class: "config-section", disabled: !found.writable }, h("legend", {}, section), ...keys.map((key) => drawn.get(key)?.row)),
      ),
    );
    if (focused) document.getElementById(focused)?.focus();
  };
  const changes = () => changedKeys([...fields].map(([key, { read, drawn }]) => [key, read(), drawn] as const));
  context.api
    .get<ConfigDocument>(CONFIG)
    .then(show)
    .catch((error: unknown) => showFailure(element, error));
  return {
    element,
    changes,
    mark() {
      const changed = changes();
      for (const [key, { row }] of fields) row.classList.toggle("changed", key.name in changed);
    },
    undo() {
      if (shown !== null) show(shown);
    },
    async save() {
      const body = changes();
      const after = await confirmed(
        (confirm) => context.api.post<ConfigDocument>(CONFIG, { changes: body, confirm }),
        (question) => confirmLazily({ title: "change progress_db", message: question, action: "Change it", destructive: false, command: "cstudy config edit" }),
      );
      if (after === null) return null;
      show(after);
      return savedNote(after);
    },
  };
}

function savedNote(document: ConfigDocument): string {
  const changed = document.keys.filter((key) => document.changed?.includes(key.name));
  return changed.length ? `saved: ${changed.map((key) => `${key.name} applies ${key.applies}`).join("; ")}` : "unchanged";
}

function fieldOf(key: ConfigKey): Field {
  const [control, read] = controlOf(key);
  return { row: rowOf(key, control), read, drawn: read() };
}

function rowOf(key: ConfigKey, control: HTMLElement): HTMLElement {
  const id = idOf(key);
  control.setAttribute("aria-describedby", `${id}-name ${id}-help`);
  const label = h("label", { for: id }, key.label);
  const boxed = key.kind === "boolean";
  return h(
    "div",
    { class: "config-key" },
    h("div", { class: "config-head" }, boxed ? h("span", { class: "config-check" }, control, label) : label, h("code", { id: `${id}-name`, class: "config-name" }, key.name)),
    boxed ? null : control,
    h("p", { id: `${id}-help`, class: "quiet" }, `${key.help} Default: ${shownValue(key.default)}. Applies ${key.applies}.`),
  );
}

function idOf(key: ConfigKey): string {
  return `config-${key.name.replace(/\W/g, "-")}`;
}

function controlOf(key: ConfigKey): readonly [control: HTMLElement, read: () => ConfigValue] {
  const id = idOf(key);
  if (key.kind === "boolean") {
    const input = h("input", { type: "checkbox", id, checked: key.value === true, disabled: key.reserved });
    return [input, () => input.checked];
  }
  if (key.choices.length > 0) {
    const multiple = key.kind === "choices";
    const held = [key.value].flat();
    const select = h("select", { id, multiple, size: multiple ? key.choices.length : null }, ...key.choices.map((choice) => h("option", { value: choice, selected: held.includes(choice) }, choice)));
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
