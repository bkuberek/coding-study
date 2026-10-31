/**
 * The Attempt view (docs/specs/web-ui.md#attempt-view): the header with the timer, the attempt's
 * Hint, Solution and Done and the run controls, the file tree, the editor tabs, the statement with
 * its levels and hints, and the results panel, where runs stream.
 */

import { type AttemptFlows, attemptFlows } from "../attempts.ts";
import type { Cleanup, PageContext } from "../context.ts";
import { badge, command, h, rendered } from "../dom.ts";
import { secondsSince, timerText } from "../format.ts";
import { problemHash } from "../routes.ts";
import { AttemptRuns } from "../runs.ts";
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
  const runs = new AttemptRuns({
    context,
    attemptId: id,
    tabs,
    refresh: () => void load().catch((error: unknown) => showFailure(page, error)),
    hasFile: (path) => shown?.files.has(path) ?? false,
  });
  const clock = h("span", { class: "timer", role: "timer", "aria-label": "Time on this attempt" });
  const statusClock = h("span", { class: "segment timer-segment" });
  let timer: number | undefined;
  let shown: {
    readonly head: HTMLElement;
    readonly brief: HTMLElement;
    readonly flows: AttemptFlows;
    readonly files: FileTreePanel;
  } | null = null;

  /** Draws the attempt; once drawn, a second call, after a run opened a level, redraws the header, tree and statement. */
  const load = async () => {
    const [status, tree] = await Promise.all([api.get<AttemptStatus>(`/api/v1/attempts/${id}`), api.get<Tree>(`/api/v1/attempts/${id}/files`)]);
    const statement = await api.get<Rendered>(`/api/v1/problems/${encodeURIComponent(status.slug)}/statement`);
    if (shown) {
      // The hints this tab revealed and the controls live on; only what the new level changes is drawn again.
      shown.flows.update(status);
      const next = { ...shown, head: head(status, clock, shown.flows, runs.toolbar), brief: brief(status, statement, shown.flows.hints) };
      shown.head.replaceWith(next.head);
      shown.brief.replaceWith(next.brief);
      shown.files.show(tree);
      shown = next;
    } else {
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
      const flows = attemptFlows(context, status);
      const files = new FileTreePanel({ attempt: status, tree, tabs, announce: (message) => shell.announce(message) });
      tabs.onSaved(() => void files.refresh().catch(() => {}));
      shown = { head: head(status, clock, flows, runs.toolbar), brief: brief(status, statement, flows.hints), flows, files };
      page.removeAttribute("aria-busy");
      page.replaceChildren(shown.head, files.element, tabs.element, shown.brief, runs.panel);
      shell.setCommand(`cstudy status ${status.slug}`);
      document.title = `${status.slug} · cstudy`;
      const first = tree.entries.find((entry) => entry.origin === "stub" || entry.origin === "notes");
      if (first) void tabs.open(first.path);
    }
    shell.setStatus({
      mode: status.mode.toUpperCase(),
      where: [status.slug, status.language, status.kind].filter(Boolean).join(" · "),
      extra: [levelSegment(status), statusClock].filter((node): node is HTMLElement => node !== null),
    });
    await runs.setAttempt(status, tree.root);
  };
  void load().catch((error: unknown) => showFailure(page, error));

  return () => {
    window.clearInterval(timer);
    unsubscribe();
    runs.destroy();
    tabs.destroy();
    shown?.files.destroy();
  };
}

function head(status: AttemptStatus, clock: HTMLElement, flows: AttemptFlows, toolbar: HTMLElement): HTMLElement {
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
    flows.actions,
    toolbar,
    h("span", { class: "spacer" }),
    h("span", { class: "next-step" }, h("span", { class: "quiet" }, "next "), command(status.next)),
  );
}

function levelSegment(status: AttemptStatus): HTMLElement | null {
  if (!status.levels) return null;
  return h("span", { class: "segment" }, `level ${status.levels.unlocked}/${status.levels.last}`);
}

function brief(status: AttemptStatus, statement: Rendered, hints: HTMLElement): HTMLElement {
  const levels = status.levels;
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
      hints,
      status.solution_revealed ? h("p", { class: "tone-warn" }, "solution revealed: the attempt is graded as again") : null,
    ),
  );
}
