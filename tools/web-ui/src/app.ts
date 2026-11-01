/**
 * The page of `cstudy serve` (docs/specs/web-ui.md#page): reads the session and the preferences,
 * draws the chrome, and shows the view the URL's fragment names. The editor module and its
 * languages load the first time a file opens.
 */
// The stylesheets of what the page loads at start; a chunk links its own (scripts/build.ts).
import "./page/app.css";
import "./page/flows.css";
import "./page/runs.css";
import "./page/files.css";

import { createApi } from "./page/api.ts";
import type { Cleanup, PageContext, PreferencesListener } from "./page/context.ts";
import { h } from "./page/dom.ts";
import { mockBanner, MockWatch } from "./page/mock.ts";
import { parseRoute, type Route } from "./page/routes.ts";
import { leaveWarning, unsavedPaths } from "./page/save.ts";
import { mountShell, nextTheme, VIEWS } from "./page/shell.ts";
import { failure, loading } from "./page/states.ts";
import type { Preferences, ProblemList, Session } from "./page/types.ts";
import { attemptView } from "./page/views/attempt.ts";
import { missingView } from "./page/views/elsewhere.ts";
import { problemView } from "./page/views/problem.ts";
import { problemsView } from "./page/views/problems.ts";

/** Alt and a view's number opens the view, as the top bar's tabs show. */
const VIEW_KEYS: Readonly<Record<string, string>> = Object.fromEntries(VIEWS.map(({ key, hash }) => [`Digit${key}`, hash]));

function meta(name: string): string {
  return document.querySelector<HTMLMetaElement>(`meta[name="${name}"]`)?.content ?? "";
}

function applyTheme(preferences: Preferences): void {
  document.documentElement.dataset["theme"] = preferences.theme;
}

function show(context: PageContext, route: Route): Cleanup {
  document.title = "cstudy";
  switch (route.view) {
    case "problems":
      return problemsView(context, route.filters);
    case "problem":
      return problemView(context, route.slug);
    case "attempt":
      return attemptView(context, route.id);
    case "mock":
      return lazyView(context, () => import("./page/views/mock.ts").then((module) => module.mockView));
    case "progress":
      return lazyView(context, () => import("./page/stats.ts").then((module) => module.progressView));
    case "health":
      return lazyView(context, () => import("./page/views/health.ts").then((module) => module.healthView));
    case "settings":
      return lazyView(context, () => import("./page/views/settings.ts").then((module) => module.settingsView));
    case "missing":
      return missingView(context, route.fragment);
  }
}

/** A view in a chunk of its own, fetched when it first opens, so the page loads less before a
 * file is editable (NFR-12). */
function lazyView(context: PageContext, load: () => Promise<(context: PageContext) => Cleanup>): Cleanup {
  let cleanup: Cleanup | null = null;
  let left = false;
  context.shell.main.replaceChildren(loading());
  load()
    .then((view) => {
      if (!left) cleanup = view(context);
    })
    .catch((error: unknown) => context.shell.main.replaceChildren(failure(error)));
  return () => {
    left = true;
    cleanup?.();
  };
}

function isTyping(target: EventTarget | null): boolean {
  return target instanceof HTMLElement && (target.isContentEditable || /^(INPUT|SELECT|TEXTAREA)$/.test(target.tagName));
}

async function start(root: HTMLElement): Promise<void> {
  const api = createApi(meta("cstudy-csrf"));
  const [session, stored] = await Promise.all([
    api.get<Session>("/api/v1/session"),
    api.get<Preferences>("/api/v1/preferences"),
  ]);
  let preferences = stored;
  const listeners = new Set<PreferencesListener>();
  const savePreferences = async (change: Partial<Omit<Preferences, "format">>) => {
    preferences = await api.put<Preferences>("/api/v1/preferences", { ...preferences, ...change });
    applyTheme(preferences);
    shell.showPreferences(preferences);
    for (const listener of listeners) listener(preferences);
  };
  const shell = mountShell(root, session.cstudy, {
    toggleVim: () => void savePreferences({ vim: !preferences.vim }).then(() => shell.announce(`vim ${preferences.vim ? "on" : "off"}`)),
    nextTheme: () => void savePreferences({ theme: nextTheme(preferences.theme) }).then(() => shell.announce(`theme ${preferences.theme}`)),
  });
  applyTheme(preferences);
  shell.showPreferences(preferences);
  const mock = new MockWatch(api);
  shell.setBanner(mockBanner(mock));
  mock.watch();
  const context: PageContext = {
    api,
    session,
    nonce: meta("cstudy-csp-nonce"),
    shell,
    mock,
    preferences: () => preferences,
    savePreferences,
    onPreferences(listener) {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
  };

  let cleanup: Cleanup = () => {};
  let shown: Route["view"] | null = null;
  let shownHash = location.hash;
  const render = () => {
    // Leaving a view drops its editors, so unsaved changes keep the view unless the user agrees.
    const warning = shown === null ? null : leaveWarning(unsavedPaths());
    if (warning !== null && !window.confirm(warning)) {
      history.replaceState(null, "", shownHash || "#/");
      return;
    }
    shownHash = location.hash;
    cleanup();
    const route = parseRoute(location.hash);
    cleanup = show(context, route);
    // A new view takes the focus, as a page load would; a filter change keeps it where it is.
    if (shown !== null && shown !== route.view) shell.main.focus({ preventScroll: true });
    shown = route.view;
    window.scrollTo(0, 0);
  };
  window.addEventListener("hashchange", render);
  document.addEventListener("keydown", (event) => {
    const hash = VIEW_KEYS[event.code];
    if (!event.altKey || event.ctrlKey || event.metaKey || hash === undefined || isTyping(event.target)) return;
    event.preventDefault();
    location.hash = hash;
  });
  void api
    .get<ProblemList>("/api/v1/problems")
    .then((list) => shell.setAttempts(list.entries))
    .catch(() => {});
  render();
}

const root = document.getElementById("app");
if (root) {
  start(root).catch((error: unknown) => {
    root.replaceChildren(h("main", { id: "main", class: "boot-error" }, h("h1", {}, "cstudy"), failure(error)));
  });
}
