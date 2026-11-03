/**
 * The page's chrome around every view (docs/specs/web-ui.md#page): the top bar with the views and
 * the attempts in progress, the command line naming the `cstudy` command the view mirrors, and a
 * status bar in the manner of an editor's, which holds the theme and Vim switches.
 */

import { attemptHash } from "./routes.ts";
import { h } from "./dom.ts";
import type { StreamState } from "./notifications.ts";
import type { ListEntry, Preferences, Theme } from "./types.ts";

/** What the top bar says of a notification stream that is down; nothing while it is up. */
const CONNECTION_TEXTS: Readonly<Partial<Record<StreamState, readonly [string, string]>>> = {
  reconnecting: ["reconnecting…", "The page lost its connection to cstudy serve and tries again; changes made elsewhere show once it is back"],
  lost: ["disconnected", "cstudy serve refused the page's notifications, as after a restart: open the URL it printed again"],
};

export type ViewName = "problems" | "mock" | "progress" | "health" | "settings" | null;

export interface StatusLine {
  /** The leftmost segment: the attempt's mode, or the view. */
  readonly mode: string;
  readonly where: string;
  readonly extra?: readonly Node[];
}

export interface Shell {
  readonly main: HTMLElement;
  setCommand(text: string): void;
  setView(name: ViewName): void;
  setStatus(line: StatusLine): void;
  setAttempts(entries: readonly ListEntry[]): void;
  /** Puts the active file's code intelligence in the status bar (docs/specs/web-ui.md#status-bar),
   * or nothing for null; `src/page/intelligence.ts` builds it. */
  setIntelligence(segment: HTMLElement | null): void;
  /** Puts the mock interview's banner in the top bar. */
  setBanner(banner: HTMLElement): void;
  /** Names the notification stream's state in the top bar while it is down. */
  setConnection(state: StreamState): void;
  showPreferences(preferences: Preferences): void;
  /** Read by screen readers without moving the focus. */
  announce(message: string): void;
}

export interface ShellActions {
  readonly toggleVim: () => void;
  readonly nextTheme: () => void;
}

export const VIEWS: readonly { readonly name: Exclude<ViewName, null>; readonly hash: string; readonly key: string }[] = [
  { name: "problems", hash: "#/", key: "1" },
  { name: "mock", hash: "#/mock", key: "2" },
  { name: "progress", hash: "#/progress", key: "3" },
  { name: "health", hash: "#/health", key: "4" },
  { name: "settings", hash: "#/settings", key: "5" },
];

export const THEMES: readonly Theme[] = ["system", "light", "dark"];

export function nextTheme(theme: Theme): Theme {
  return THEMES[(THEMES.indexOf(theme) + 1) % THEMES.length] ?? "system";
}

export function mountShell(root: HTMLElement, version: string, actions: ShellActions): Shell {
  const links = VIEWS.map(({ name, hash, key }) =>
    h("a", { href: hash, class: "tab", "data-view": name }, h("span", { class: "tab-key", "aria-hidden": "true" }, `${key}:`), name),
  );
  const attemptsCount = h("span", { class: "count" }, "0");
  const attemptsList = h("ul", { class: "menu-list" });
  const attemptsMenu = h(
    "details",
    { class: "attempts-menu" },
    h("summary", {}, "in progress ", attemptsCount),
    attemptsList,
  );
  const commandText = h("code", { class: "command-text" });
  const copy = h("button", { type: "button", class: "ghost", title: "Copy the command" }, "copy");
  const mode = h("span", { class: "segment mode" });
  const where = h("span", { class: "segment where" });
  const extra = h("span", { class: "segment-group" });
  const intelligence = h("span", { class: "segment-group" });
  const vim = h("button", { type: "button", class: "segment toggle", "aria-pressed": "false" }, "vim");
  const theme = h("button", { type: "button", class: "segment toggle" }, "theme");
  const announcer = h("div", { class: "sr-only", "aria-live": "polite", role: "status" });
  const main = h("main", { id: "main", tabindex: "-1" });
  const bannerSlot = h("span", { class: "banner-slot" });
  const connection = h("span", { class: "connection", role: "status", hidden: true });

  copy.addEventListener("click", () => {
    void navigator.clipboard?.writeText(commandText.textContent ?? "").then(() => shell.announce("command copied"));
  });
  vim.addEventListener("click", actions.toggleVim);
  theme.addEventListener("click", actions.nextTheme);
  attemptsList.addEventListener("click", (event) => {
    if ((event.target as Element).closest("a")) attemptsMenu.open = false;
  });

  root.replaceChildren(
    h("a", { class: "skip", href: "#main" }, "Skip to content"),
    h(
      "header",
      { class: "topbar" },
      h("a", { class: "brand", href: "#/" }, h("span", { class: "brand-mark", "aria-hidden": "true" }, "❯"), "cstudy"),
      h("nav", { "aria-label": "Views" }, ...links),
      bannerSlot,
      connection,
      attemptsMenu,
    ),
    h(
      "section",
      { class: "command", "aria-label": "The terminal command this view mirrors" },
      h("span", { class: "sigil", "aria-hidden": "true" }, "$"),
      commandText,
      h("span", { class: "cursor", "aria-hidden": "true" }),
      copy,
    ),
    main,
    h(
      "footer",
      { class: "statusbar", "aria-label": "Status" },
      mode,
      where,
      extra,
      intelligence,
      h("span", { class: "spacer" }),
      vim,
      theme,
      h("span", { class: "segment version" }, `cstudy ${version}`),
    ),
    announcer,
  );

  const shell: Shell = {
    main,
    setCommand(text) {
      commandText.textContent = text;
    },
    setView(name) {
      for (const link of links) {
        if (link.dataset["view"] === name) link.setAttribute("aria-current", "page");
        else link.removeAttribute("aria-current");
      }
    },
    setStatus(line) {
      mode.textContent = line.mode;
      where.textContent = line.where;
      extra.replaceChildren(...(line.extra ?? []));
    },
    setAttempts(entries) {
      const attempts = entries.flatMap((entry) =>
        entry.in_progress.map((attempt) =>
          h(
            "li",
            {},
            h(
              "a",
              { href: attemptHash(attempt.attempt_id) },
              h("span", { class: "menu-slug" }, entry.slug),
              h("span", { class: "menu-meta" }, [attempt.language, attempt.mode].filter(Boolean).join(" · ")),
            ),
          ),
        ),
      );
      attemptsCount.textContent = String(attempts.length);
      attemptsList.replaceChildren(...(attempts.length ? attempts : [h("li", { class: "menu-empty" }, "none")]));
    },
    setIntelligence(segment) {
      intelligence.replaceChildren(...(segment === null ? [] : [segment]));
    },
    setBanner(banner) {
      bannerSlot.replaceChildren(banner);
    },
    setConnection(state) {
      const [text, title] = CONNECTION_TEXTS[state] ?? ["", ""];
      connection.hidden = text === "";
      connection.textContent = text;
      connection.title = title;
      connection.dataset["state"] = state;
    },
    showPreferences(preferences) {
      vim.textContent = preferences.vim ? "vim on" : "vim off";
      vim.setAttribute("aria-pressed", String(preferences.vim));
      vim.title = "Vim keybindings in the editors (a preference)";
      theme.textContent = `theme ${preferences.theme}`;
      theme.title = `Theme: ${preferences.theme}; next: ${nextTheme(preferences.theme)}`;
    },
    announce(message) {
      announcer.textContent = "";
      window.setTimeout(() => {
        announcer.textContent = message;
      }, 50);
    },
  };
  return shell;
}
