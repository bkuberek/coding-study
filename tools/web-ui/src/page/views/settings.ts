/**
 * The Settings view (docs/specs/web-ui.md#settings-view): the workspace's preferences and the user's
 * `config.toml`, whose changes both stage until the bar's Save, and resetting progress, which does not.
 */

import "./settings.css";

import type { Cleanup, PageContext } from "../context.ts";
import { h } from "../dom.ts";
import { languageRow } from "../intelligence-status.ts";
import { messageOf } from "../states.ts";
import { trackUnsaved } from "../save.ts";
import { changesText, type SaveLine, saveLines, type StoreOutcome } from "../settings-model.ts";
import { THEMES } from "../shell.ts";
import type { LanguageStates, Preferences, Theme } from "../types.ts";
import { configStage } from "./config-form.ts";
import { dangerSection } from "./reset-dialog.ts";

type Switch = "vim" | "run_on_save" | "typecheck" | "code_intelligence" | "autocomplete";
type StagedKey = Switch | "theme";
interface SwitchSpec {
  readonly key: Switch;
  readonly label: string;
  readonly help: string;
}
/** A preference's control, which holds a change until the bar's Save. */
interface Control {
  readonly row: HTMLElement;
  read(): boolean | Theme;
  write(value: boolean | Theme): void;
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
const COPIED_MS = 1500;
const PREFERENCES_FILE = ".cs/serve/preferences.json";
/** What the question before leaving calls the view. */
const LEAVING = "Settings";

export function settingsView(context: PageContext): Cleanup {
  const { shell } = context;
  shell.setView("settings");
  shell.setCommand("cstudy config edit");
  shell.setStatus({ mode: "SETTINGS", where: PREFERENCES_FILE });
  const preferences = preferencesStage(context);
  const config = configStage(context);
  const title = h("h1", { id: "settings-heading", tabindex: "-1" }, "settings");
  const count = h("span", { class: "settings-count" });
  const undo = h("button", { type: "button", class: "button", title: "Undo every unsaved change" }, "Reset");
  const save = h("button", { type: "submit", class: "button primary" }, "Save");
  const status = h("p", { class: "quiet settings-status", role: "status" });
  let saving = false;
  const unsaved = () => Object.keys(preferences.changes()).length + Object.keys(config.changes()).length;
  const refresh = () => {
    preferences.sync();
    config.mark();
    const changes = unsaved();
    count.textContent = changesText(changes);
    count.hidden = changes === 0;
    undo.hidden = changes === 0;
    undo.disabled = saving;
    save.disabled = saving || changes === 0;
  };
  const say = (lines: readonly SaveLine[]) => {
    status.replaceChildren(...lines.map(({ text, failed }) => h("span", { class: failed ? "failed" : null }, text)));
  };
  /** A Save or a Reset can disable, hide or draw again the control that held the focus. */
  const settle = (lines: readonly SaveLine[]) => {
    saving = false;
    say(lines);
    refresh();
    const active = document.activeElement;
    if (active === null || active === document.body || active.matches(":disabled, [hidden]")) title.focus({ preventScroll: true });
  };
  const saveAll = async () => {
    saving = true;
    say([{ text: "saving…", failed: false }]);
    refresh();
    let configOutcome: StoreOutcome = null;
    // First, so its question can still stop the Save before anything is written.
    if (Object.keys(config.changes()).length > 0) {
      try {
        const note = await config.save();
        if (note === null) {
          settle([{ text: "not saved", failed: false }]);
          return;
        }
        configOutcome = { saved: note };
      } catch (error) {
        configOutcome = { error: messageOf(error) };
      }
    }
    let preferencesOutcome: StoreOutcome = null;
    const staged = preferences.changes();
    if (Object.keys(staged).length > 0) {
      try {
        await context.savePreferences(staged);
        preferencesOutcome = { saved: `saved in ${PREFERENCES_FILE}` };
      } catch (error) {
        preferencesOutcome = { error: messageOf(error) };
      }
    }
    settle(saveLines(configOutcome, preferencesOutcome));
  };
  undo.addEventListener("click", () => {
    preferences.undo();
    config.undo();
    settle([{ text: "changes undone", failed: false }]);
  });
  const form = h(
    "form",
    { class: "settings-form" },
    h("header", { class: "view-head settings-bar" }, title, count, h("span", { class: "spacer" }), undo, save, status),
    h(
      "div",
      { class: "settings-columns" },
      h(
        "div",
        { class: "settings-column" },
        h("h2", { class: "eyebrow" }, "this workspace"),
        workspacePath(context),
        h("p", { class: "quiet" }, `Stored in ${PREFERENCES_FILE}.`),
        ...preferences.sections,
        dangerSection(context),
      ),
      h("div", { class: "settings-column" }, h("h2", { class: "eyebrow" }, "all your workspaces"), config.element),
    ),
  );
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    void saveAll();
  });
  form.addEventListener("input", () => {
    say([]);
    refresh();
  });
  shell.main.replaceChildren(h("section", { class: "settings", "aria-labelledby": "settings-heading" }, form));
  refresh();
  const stopFollowing = context.onPreferences((stored) => {
    preferences.follow(stored);
    refresh();
  });
  const untrack = trackUnsaved(() => (unsaved() > 0 ? [LEAVING] : []));
  const onUnload = (event: BeforeUnloadEvent) => {
    if (unsaved() > 0) event.preventDefault();
  };
  window.addEventListener("beforeunload", onUnload);
  return () => {
    window.removeEventListener("beforeunload", onUnload);
    untrack();
    stopFollowing();
    preferences.stop();
  };
}

/** The workspace's preferences, whose controls hold a change until the bar's Save. */
function preferencesStage(context: PageContext) {
  const initial = context.preferences();
  const controls = new Map<StagedKey, Control>();
  const switchFor = ({ key, label, help }: SwitchSpec, ...notes: HTMLElement[]) => {
    const input = h("input", { type: "checkbox", id: `pref-${key}`, checked: initial[key] });
    input.setAttribute("aria-describedby", [`pref-${key}-help`, ...notes.map((note) => note.id)].join(" "));
    const row = h(
      "div",
      { class: "switch" },
      input,
      h("label", { for: `pref-${key}` }, label),
      h("p", { id: `pref-${key}-help`, class: "quiet" }, help),
      ...notes,
    );
    controls.set(key, {
      row,
      read: () => input.checked,
      write: (value) => {
        input.checked = value === true;
      },
    });
    return { input, row };
  };
  const switches = SWITCHES.map((spec) => switchFor(spec).row);
  const note = h("p", { id: "pref-autocomplete-note", class: "quiet" }, AUTOCOMPLETE_NOTE);
  const codeIntelligence = switchFor(CODE_INTELLIGENCE);
  const autocomplete = switchFor(AUTOCOMPLETE, note);
  const languages = languageList(context);
  const radios = THEMES.map((theme) => h("input", { type: "radio", name: "theme", id: `theme-${theme}`, value: theme, checked: initial.theme === theme }));
  const themes = h("div", { class: "radios" }, ...radios.map((radio) => h("div", { class: "radio" }, radio, h("label", { for: radio.id }, radio.value))));
  const stagedTheme = () => (radios.find((radio) => radio.checked)?.value ?? context.preferences().theme) as Theme;
  controls.set("theme", {
    row: themes,
    read: stagedTheme,
    write: (value) => {
      for (const radio of radios) radio.checked = radio.value === value;
    },
  });
  /** The page's theme, and the status bar's word for it, whether stored or still staged. */
  const showTheme = (theme: Theme) => {
    document.documentElement.dataset["theme"] = theme;
    context.shell.showPreferences({ ...context.preferences(), theme });
  };
  const differs = (key: StagedKey, control: Control) => control.read() !== context.preferences()[key];
  let known = initial;
  return {
    sections: [
      h("fieldset", {}, h("legend", {}, "editor and runs"), ...switches),
      h("fieldset", {}, h("legend", {}, "code intelligence"), codeIntelligence.row, languages.element, autocomplete.row),
      h("fieldset", {}, h("legend", {}, "theme"), themes),
    ],
    changes(): Partial<Omit<Preferences, "format">> {
      return Object.fromEntries([...controls].filter(([key, control]) => differs(key, control)).map(([key, control]) => [key, control.read()]));
    },
    /** Brings what follows from the controls up to them. */
    sync() {
      for (const [key, control] of controls) control.row.classList.toggle("changed", differs(key, control));
      // Disabled, not cleared: the stored value comes back when code intelligence does.
      const off = !codeIntelligence.input.checked;
      autocomplete.input.disabled = off;
      note.hidden = !off;
      showTheme(stagedTheme());
    },
    undo() {
      const stored = context.preferences();
      for (const [key, control] of controls) control.write(stored[key]);
    },
    /** A value stored elsewhere, by the status bar's switches, wins over what was staged for it. */
    follow(stored: Preferences) {
      for (const [key, control] of controls) if (stored[key] !== known[key]) control.write(stored[key]);
      known = stored;
    },
    stop() {
      languages.stop();
      showTheme(context.preferences().theme);
    },
  };
}

/** Where this workspace is, with a way to take the path to a terminal. */
function workspacePath({ session, shell }: PageContext): HTMLElement {
  const copy = h("button", { type: "button", class: "button", "aria-label": "Copy the workspace path" }, "copy");
  const said = (word: string) => {
    shell.announce(`path ${word}`);
    copy.textContent = word;
    window.setTimeout(() => {
      copy.textContent = "copy";
    }, COPIED_MS);
  };
  copy.addEventListener("click", () => {
    void navigator.clipboard?.writeText(session.workspace).then(
      () => said("copied"),
      () => said("not copied"),
    );
  });
  return h("p", { class: "workspace-path" }, h("code", {}, session.workspace), copy);
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
