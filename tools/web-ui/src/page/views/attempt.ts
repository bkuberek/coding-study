/**
 * The Attempt view (docs/specs/web-ui.md#attempt-view): the header with the timer, the file tree,
 * the editor tabs, the statement with its levels and hints, and the results panel, which shows the
 * latest recorded run until the page runs tests itself.
 */

import type { Cleanup, PageContext } from "../context.ts";
import { badge, command, h, rendered } from "../dom.ts";
import { secondsSince, timerText } from "../format.ts";
import { problemHash } from "../routes.ts";
import { loading, showFailure } from "../states.ts";
import { FileTreePanel } from "../fileTreePanel.ts";
import type { AttemptStatus, Rendered, Tree } from "../types.ts";
import { EditorTabs } from "../workbench.ts";

const TICK_MS = 1000;

export function attemptView(context: PageContext, id: number): Cleanup {
  const { api, shell } = context;
  shell.setView(null);
  shell.setCommand("cstudy status");
  shell.setStatus({ mode: "ATTEMPT", where: `attempt ${id}` });
  const page = h("div", { class: "workbench", "aria-busy": "true" }, loading());
  shell.main.replaceChildren(h("h1", { class: "sr-only" }, `Attempt ${id}`), page);

  const tabs = new EditorTabs(context, id);
  const unsubscribe = context.onPreferences((preferences) => tabs.applyPreferences(preferences));
  let timer: number | undefined;
  let files: FileTreePanel | null = null;

  void Promise.all([api.get<AttemptStatus>(`/api/v1/attempts/${id}`), api.get<Tree>(`/api/v1/attempts/${id}/files`)])
    .then(async ([status, tree]) => {
      const statement = await api.get<Rendered>(`/api/v1/problems/${encodeURIComponent(status.slug)}/statement`);
      const clock = h("span", { class: "timer", role: "timer", "aria-label": "Time on this attempt" });
      const statusClock = h("span", { class: "segment timer-segment" });
      const tick = () => {
        const text = timerText(secondsSince(status.started_at, Date.now()), status.timer?.limit_s ?? null);
        clock.textContent = text;
        statusClock.textContent = text;
        const over = text.startsWith("over");
        clock.classList.toggle("is-over", over);
        statusClock.classList.toggle("is-over", over);
      };
      tick();
      timer = window.setInterval(tick, TICK_MS);
      page.removeAttribute("aria-busy");
      files = new FileTreePanel({ attempt: status, tree, tabs, announce: (message) => shell.announce(message) });
      const panel = files;
      tabs.onSaved(() => void panel.refresh().catch(() => {}));
      page.replaceChildren(
        head(status, clock),
        files.element,
        tabs.element,
        brief(status, statement),
        results(status),
      );
      shell.setCommand(`cstudy status ${status.slug}`);
      shell.setStatus({
        mode: status.mode.toUpperCase(),
        where: [status.slug, status.language, status.kind].filter(Boolean).join(" · "),
        extra: [levelSegment(status), statusClock].filter((node): node is HTMLElement => node !== null),
      });
      document.title = `${status.slug} · cstudy`;
      const first = tree.entries.find((entry) => entry.origin === "stub" || entry.origin === "notes");
      if (first) void tabs.open(first.path);
    })
    .catch((error: unknown) => showFailure(page, error));

  return () => {
    window.clearInterval(timer);
    unsubscribe();
    tabs.destroy();
    files?.destroy();
  };
}

function head(status: AttemptStatus, clock: HTMLElement): HTMLElement {
  return h(
    "header",
    { class: "attempt-head" },
    h("a", { href: problemHash(status.slug), class: "attempt-slug" }, status.slug),
    h(
      "span",
      { class: "attempt-facts" },
      [status.language, status.kind].filter(Boolean).join(" · "),
    ),
    badge("", status.mode, status.mode === "mock" ? "fail" : status.mode === "review" ? "info" : "quiet"),
    status.levels ? h("span", { class: "level" }, `level ${status.levels.unlocked} of ${status.levels.last}`) : null,
    clock,
    h("span", { class: "spacer" }),
    h("span", { class: "next-step" }, h("span", { class: "quiet" }, "next "), command(status.next)),
  );
}

function levelSegment(status: AttemptStatus): HTMLElement | null {
  if (!status.levels) return null;
  return h("span", { class: "segment" }, `level ${status.levels.unlocked}/${status.levels.last}`);
}

function brief(status: AttemptStatus, statement: Rendered): HTMLElement {
  const levels = status.levels;
  const hints = status.hints;
  return h(
    "aside",
    { class: "brief", "aria-label": "Statement" },
    levels
      ? h(
          "ol",
          { class: "levels", "aria-label": "Levels" },
          ...Array.from({ length: levels.last }, (_, index) => {
            const number = index + 1;
            const title = levels.titles[index];
            const open = number <= levels.unlocked;
            return h(
              "li",
              { class: open ? (number === levels.unlocked ? "is-current" : "is-open") : "is-locked" },
              h("span", { class: "level-number" }, String(number)),
              open ? title ?? `level ${number}` : "locked",
            );
          }),
        )
      : null,
    rendered(statement.html, "prose prose-compact"),
    h(
      "footer",
      { class: "brief-notes" },
      hints.total
        ? h(
            "p",
            {},
            `hints ${hints.used} of ${hints.total}`,
            hints.locked_until_level ? ` · the next opens with level ${hints.locked_until_level}` : "",
            h("span", { class: "quiet" }, " · any hint caps the review grade at ok"),
          )
        : null,
      status.solution_revealed ? h("p", { class: "tone-warn" }, "solution revealed: the attempt is graded as again") : null,
      hints.total ? h("p", { class: "quiet" }, "hint: ", command(`cstudy hint ${status.slug}`)) : null,
    ),
  );
}

function results(status: AttemptStatus): HTMLElement {
  const run = status.last_test_run;
  const test = `cstudy test ${status.slug}` + (status.language && status.kind !== "project" ? ` --lang ${status.language}` : "");
  return h(
    "section",
    { class: "results", "aria-label": "Results" },
    h("h2", { class: "eyebrow" }, "results"),
    run
      ? h(
          "p",
          { class: "last-run" },
          badge(run.passed === run.total ? "✓" : "✕", `${run.passed}/${run.total} passed`, run.passed === run.total ? "ok" : "fail"),
          h("span", { class: "quiet" }, ` latest cstudy test, ${new Date(run.ran_at).toLocaleString()}`),
        )
      : status.kind === "item"
        ? h("p", { class: "quiet" }, "Items have no runs: answer in the notes.")
        : h("p", { class: "quiet" }, "No test run yet."),
    status.kind === "item"
      ? null
      : h("p", { class: "quiet" }, "Runs stream here once the page runs tests; for now run ", command(test), " in a terminal."),
  );
}
