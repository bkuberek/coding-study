/** The Settings view (docs/specs/web-ui.md#settings-view): the preferences, each stored at once. */

import "./settings.css";

import type { Cleanup, PageContext } from "../context.ts";
import { h } from "../dom.ts";
import { THEMES } from "../shell.ts";
import type { Preferences } from "../types.ts";

type Switch = "vim" | "run_on_save" | "typecheck";

const SWITCHES: readonly { readonly key: Switch; readonly label: string; readonly help: string }[] = [
  { key: "vim", label: "Vim keybindings", help: "In every editor; loaded the first time you turn them on." },
  { key: "run_on_save", label: "Run on save", help: "Re-runs the tests after a save, as cstudy test --watch does." },
  { key: "typecheck", label: "Type-check TypeScript", help: "Runs tsc with the tests, so type errors reach the editor." },
];

export function settingsView(context: PageContext): Cleanup {
  const { shell } = context;
  shell.setView("settings");
  shell.setCommand("cstudy serve");
  shell.setStatus({ mode: "SETTINGS", where: ".cs/serve/preferences.json" });
  const saved = h("p", { class: "quiet", role: "status" });
  const save = (change: Partial<Omit<Preferences, "format">>) => {
    saved.textContent = "saving…";
    void context
      .savePreferences(change)
      .then(() => {
        saved.textContent = "saved in .cs/serve/preferences.json";
      })
      .catch((error: unknown) => {
        saved.textContent = `error: ${error instanceof Error ? error.message : String(error)}`;
      });
  };
  const preferences = context.preferences();
  const switches = SWITCHES.map(({ key, label, help }) => {
    const input = h("input", { type: "checkbox", id: `pref-${key}`, checked: preferences[key], "aria-describedby": `pref-${key}-help` });
    input.addEventListener("change", () => save({ [key]: input.checked }));
    return h(
      "div",
      { class: "switch" },
      input,
      h("label", { for: `pref-${key}` }, label),
      h("p", { id: `pref-${key}-help`, class: "quiet" }, help),
    );
  });
  const themes = THEMES.map((theme) => {
    const input = h("input", { type: "radio", name: "theme", id: `theme-${theme}`, value: theme, checked: preferences.theme === theme });
    input.addEventListener("change", () => save({ theme }));
    return h("div", { class: "radio" }, input, h("label", { for: `theme-${theme}` }, theme));
  });
  shell.main.replaceChildren(
    h(
      "section",
      { class: "settings", "aria-labelledby": "settings-heading" },
      h("header", { class: "view-head" }, h("h1", { id: "settings-heading" }, "settings")),
      h(
        "form",
        { class: "settings-form" },
        h("fieldset", {}, h("legend", {}, "editor and runs"), ...switches),
        h("fieldset", {}, h("legend", {}, "theme"), h("div", { class: "radios" }, ...themes)),
      ),
      saved,
      h("dl", { class: "facts" }, h("dt", {}, "workspace"), h("dd", {}, h("code", {}, context.session.workspace))),
    ),
  );
  return () => {};
}
