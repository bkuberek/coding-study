/** The Settings view (docs/specs/web-ui.md#settings-view): the preferences, each stored at once. */

import "./settings.css";

import type { Cleanup, PageContext } from "../context.ts";
import { h } from "../dom.ts";
import { languageRow } from "../intelligence-status.ts";
import { messageOf } from "../states.ts";
import { THEMES } from "../shell.ts";
import type { LanguageStates, Preferences } from "../types.ts";

type Switch = "vim" | "run_on_save" | "typecheck" | "code_intelligence" | "autocomplete";
interface SwitchSpec {
  readonly key: Switch;
  readonly label: string;
  readonly help: string;
}

const SWITCHES: readonly SwitchSpec[] = [
  { key: "vim", label: "Vim keybindings", help: "In every editor; loaded the first time you turn them on." },
  { key: "run_on_save", label: "Run on save", help: "Re-runs the tests after a save, as cstudy test --watch does." },
  { key: "typecheck", label: "Type-check TypeScript", help: "Runs tsc with the tests, so type errors reach the editor." },
];
const CODE_INTELLIGENCE: SwitchSpec = {
  key: "code_intelligence",
  label: "Code intelligence",
  help: "Live diagnostics, hover documentation and go to definition from language servers on this machine.",
};
const AUTOCOMPLETE: SwitchSpec = {
  key: "autocomplete",
  label: "Autocomplete",
  help: "Completion and signature help. Off, the editor offers no completion at all.",
};
const AUTOCOMPLETE_NOTE = "Turn on code intelligence first";
const LANGUAGES = "/api/v1/code-intelligence/languages";
const DOCTOR_FIX = "doctor_fix";

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
  const switchFor = ({ key, label, help }: SwitchSpec, ...notes: HTMLElement[]) => {
    const input = h("input", { type: "checkbox", id: `pref-${key}`, checked: preferences[key] });
    input.setAttribute("aria-describedby", [`pref-${key}-help`, ...notes.map((note) => note.id)].join(" "));
    input.addEventListener("change", () => save({ [key]: input.checked }));
    const row = h(
      "div",
      { class: "switch" },
      input,
      h("label", { for: `pref-${key}` }, label),
      h("p", { id: `pref-${key}-help`, class: "quiet" }, help),
      ...notes,
    );
    return { input, row };
  };
  const switches = SWITCHES.map((spec) => switchFor(spec).row);
  const note = h("p", { id: "pref-autocomplete-note", class: "quiet" }, AUTOCOMPLETE_NOTE);
  const codeIntelligence = switchFor(CODE_INTELLIGENCE);
  const autocomplete = switchFor(AUTOCOMPLETE, note);
  // Disabled, not cleared: the stored value comes back when code intelligence does.
  const gateAutocomplete = () => {
    const off = !codeIntelligence.input.checked;
    autocomplete.input.disabled = off;
    note.hidden = !off;
  };
  codeIntelligence.input.addEventListener("change", gateAutocomplete);
  gateAutocomplete();
  const languages = languageList(context);
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
        h("fieldset", {}, h("legend", {}, "code intelligence"), codeIntelligence.row, languages.element, autocomplete.row),
        h("fieldset", {}, h("legend", {}, "theme"), h("div", { class: "radios" }, ...themes)),
      ),
      saved,
      h("dl", { class: "facts" }, h("dt", {}, "workspace"), h("dd", {}, h("code", {}, context.session.workspace))),
    ),
  );
  return languages.stop;
}

/**
 * One line per language and the state of its server, whatever the checkbox says
 * (docs/specs/web-ui.md#settings-view), read when the view opens and after each `doctor_fix` job.
 */
function languageList(context: PageContext): { readonly element: HTMLElement; readonly stop: Cleanup } {
  const element = h("ul", { class: "languages", "aria-label": "Language servers" }, h("li", { class: "quiet" }, "reading the languages…"));
  let current = 0;
  const read = () => {
    const request = ++current;
    context.api
      .get<LanguageStates>(LANGUAGES)
      .then((found) => {
        if (request !== current) return;
        element.replaceChildren(
          ...found.languages.map(languageRow).map((row) =>
            h(
              "li",
              {},
              h("span", { class: "language-name" }, row.name),
              " ",
              row.health ? h("a", { href: "#/health", title: "Opens Health, where Fix installs it" }, row.detail) : h("span", { class: "quiet" }, row.detail),
            ),
          ),
        );
      })
      .catch((error: unknown) => {
        if (request === current) element.replaceChildren(h("li", { class: "quiet" }, `could not read the languages: ${messageOf(error)}`));
      });
  };
  read();
  const unsubscribe = context.notifications.subscribe((notice) => {
    if (notice.type === "job_ended" && notice.command === DOCTOR_FIX) read();
  });
  return {
    element,
    stop: () => {
      current += 1;
      unsubscribe();
    },
  };
}
