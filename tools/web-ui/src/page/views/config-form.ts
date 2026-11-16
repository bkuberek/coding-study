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
/** The section of `profile.job_roles` and `profile.domains`, which the Profile section draws. */
const PROFILE_SECTION = "profile";
/** What each profile key says under its legend (docs/specs/web-ui.md#settings-view). */
const PROFILE_NOTES: Readonly<Record<string, string>> = {
  "profile.job_roles": "Problems for any engineer (general) always show.",
  "profile.domains": "Keep algorithms for the data structures and algorithms problems.",
};

/** What a profile group asks for, in the message under it when every box is unchecked. */
const PROFILE_NOUNS: Readonly<Record<string, string>> = {
  "profile.job_roles": "job role",
  "profile.domains": "domain",
};

interface Field {
  readonly row: HTMLElement;
  /** For a group of checkboxes: refuses it, with a message next to it, while every box is unchecked. */
  readonly refuse?: () => HTMLElement | null;
  readonly read: () => ConfigValue;
  /** What `read` gave when the field was drawn, which a change differs from. */
  readonly drawn: ConfigValue;
}

export interface ConfigStage {
  readonly element: HTMLElement;
  /** The profile's keys, as groups of checkboxes, for the Profile section to place. */
  readonly profile: HTMLElement;
  /** What differs from the file, by each key's name, as `POST /api/v1/config` takes it. */
  changes(): Record<string, ConfigValue>;
  /** Refuses each profile group with every box unchecked, with a message next to it; the first
   * such group's first box, or null when none is refused. */
  refuse(): HTMLElement | null;
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
  const profile = h("div", { class: "profile-config" }, loading("reading config.toml…"));
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
      ...sectionsOf(found.keys)
        .filter(([section]) => section !== PROFILE_SECTION)
        .map(([section, keys]) =>
          h("fieldset", { class: "config-section", disabled: !found.writable }, h("legend", {}, section), ...keys.map((key) => drawn.get(key)?.row)),
        ),
    );
    profile.replaceChildren(...found.keys.filter((key) => key.section === PROFILE_SECTION).flatMap((key) => drawn.get(key)?.row ?? []));
    for (const group of profile.querySelectorAll("fieldset")) group.disabled = !found.writable;
    if (focused) document.getElementById(focused)?.focus();
  };
  const changes = () => changedKeys([...fields].map(([key, { read, drawn }]) => [key, read(), drawn] as const));
  context.api
    .get<ConfigDocument>(CONFIG)
    .then(show)
    .catch((error: unknown) => {
      showFailure(element, error);
      showFailure(profile, error);
    });
  return {
    element,
    profile,
    changes,
    refuse() {
      const refused = [...fields.values()].map((field) => field.refuse?.() ?? null);
      return refused.find((box) => box !== null) ?? null;
    },
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
  if (key.section === PROFILE_SECTION) return profileField(key);
  const [control, read] = controlOf(key);
  return { row: rowOf(key, control), read, drawn: read() };
}

/** A profile key as a group of checkboxes, one per choice, with where it is stored and its note.
 * Unchecking every box stages a list that cannot be saved: a Save refuses it in the page, with a
 * message tied to the group, and keeps the change staged. */
function profileField(key: ConfigKey): Field {
  const id = idOf(key);
  const held = [key.value].flat();
  const boxes = key.choices.map((choice) => h("input", { type: "checkbox", id: `${id}-${choice}`, value: choice, checked: held.includes(choice) }));
  const note = PROFILE_NOTES[key.name];
  const noun = PROFILE_NOUNS[key.name] ?? key.label;
  const message = h("p", { id: `${id}-error`, class: "profile-error", hidden: true }, `Choose at least one ${noun}.`);
  const row = h(
    "fieldset",
    { class: "profile-group", id },
    h("legend", {}, key.label),
    h("p", { class: "quiet" }, "all your workspaces: config.toml · ", h("code", { class: "config-name" }, key.name)),
    note === undefined ? null : h("p", { class: "quiet" }, note),
    h("div", { class: "profile-options" }, ...boxes.map((box) => h("div", { class: "profile-option" }, box, h("label", { for: box.id }, box.value)))),
    message,
  );
  const read = () => boxes.filter((box) => box.checked).map((box) => box.value);
  const show = (shown: boolean) => {
    message.hidden = !shown;
    if (shown) row.setAttribute("aria-describedby", message.id);
    else row.removeAttribute("aria-describedby");
  };
  // Checking a box answers the message.
  row.addEventListener("change", () => show(false));
  const refuse = () => {
    const empty = read().length === 0;
    show(empty);
    return empty ? (boxes[0] ?? null) : null;
  };
  return { row, read, drawn: read(), refuse };
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
