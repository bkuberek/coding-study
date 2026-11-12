/**
 * The Attempt view (docs/specs/web-ui.md#attempt-view): the header with the timer, the attempt's
 * Hint, Solution and Done and the run controls, the file tree, the editor tabs, the statement with
 * its levels and hints, and the results panel, where runs stream.
 */

import { ApiError } from "../api.ts";
import { AttemptEnding, type Finishing } from "../attemptEnding.ts";
import { type AttemptFlows, attemptFlows } from "../attempts.ts";
import type { Cleanup, PageContext } from "../context.ts";
import { badge, command, h, rendered } from "../dom.ts";
import { startIntelligence } from "../intelligence-start.ts";
import { secondsSince, timerText } from "../format.ts";
import { problemHash } from "../routes.ts";
import { AttemptRuns } from "../runs.ts";
import { loading, messageOf, showFailure } from "../states.ts";
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
  const intelligence = startIntelligence(context, tabs, id);
  const runs = new AttemptRuns({
    context,
    attemptId: id,
    tabs,
    refresh: () => refresh(true),
    hasFile: (path) => shown?.files.has(path) ?? false,
  });
  const clock = h("span", { class: "timer", role: "timer", "aria-label": "Time on this attempt" });
  const statusClock = h("span", { class: "segment timer-segment" });
  let timer: number | undefined;
  const ending = new AttemptEnding();
  let shown: {
    readonly head: HTMLElement;
    readonly brief: HTMLElement;
    readonly flows: AttemptFlows;
    readonly files: FileTreePanel;
    readonly status: AttemptStatus;
    readonly statement: Rendered;
  } | null = null;

  /**
   * Draws the attempt. Once drawn, a later call, after a level opened or a change from elsewhere,
   * draws again only what changed: the header, the statement (read again with `statement`, or
   * when the level changed), and the tree, so the focus and the statement's scroll stay put.
   */
  const load = async (statement: boolean) => {
    const [status, tree] = await Promise.all([api.get<AttemptStatus>(`/api/v1/attempts/${id}`), api.get<Tree>(`/api/v1/attempts/${id}/files`)]);
    const reread = shown === null || statement || headKey(status) !== headKey(shown.status);
    // The header is drawn at its final height, toolbar included, so nothing below it moves later.
    const [text] = await Promise.all([
      reread ? api.get<Rendered>(`/api/v1/problems/${encodeURIComponent(status.slug)}/statement`) : shown!.statement,
      shown === null ? runs.showToolbar(status) : null,
    ]);
    if (ending.ended) return;
    if (shown) {
      // The hints this tab revealed and the controls live on.
      shown.flows.update(status);
      const next = { ...shown, status, statement: text };
      if (headKey(status) !== headKey(shown.status)) {
        next.head = head(status, clock, shown.flows, runs.toolbar);
        shown.head.replaceWith(next.head);
      }
      if (text.html !== shown.statement.html || briefKey(status) !== briefKey(shown.status)) {
        next.brief = brief(status, text, shown.flows.hints);
        shown.brief.replaceWith(next.brief);
      }
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
      const flows = attemptFlows(context, status, finishing);
      const files = new FileTreePanel({ attempt: status, tree, tabs, announce: (message) => shell.announce(message) });
      tabs.onSaved(() => void files.refresh().catch(() => {}));
      shown = { head: head(status, clock, flows, runs.toolbar), brief: brief(status, text, flows.hints), flows, files, status, statement: text };
      page.removeAttribute("aria-busy");
      page.replaceChildren(shown.head, files.element, tabs.element, shown.brief, runs.panel);
      intelligence.configure({ language: status.language, noCodeIntelligence: status.no_code_intelligence }, tree.root);
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

  /** Reads the attempt again; once it is no longer in progress, or a reset deleted it, the view says
   * so and stays read-only. Another failure keeps what shows and is announced, unless nothing shows yet.
   * While this tab finishes the attempt, nothing reads it: it would answer that it ended. */
  const refresh = (statement: boolean) => {
    if (ending.holds()) return;
    load(statement).catch((error: unknown) => {
      if (error instanceof ApiError && (error.code === ATTEMPT_ENDED || (error.code === NOT_FOUND && shown !== null))) endedElsewhere();
      else if (shown === null) showFailure(page, error);
      else shell.announce(`could not read the attempt again: ${messageOf(error)}`);
    });
  };

  const endedElsewhere = () =>
    ending.end(() => {
      tabs.freeze();
      runs.freeze();
      const slug = shown?.status.slug;
      shown?.head.append(
        h(
          "p",
          { class: "attempt-ended", role: "alert" },
          "This attempt is no longer in progress: ",
          command("cstudy done"),
          " finished it, abort ended it, a fresh start replaced it, or a reset deleted it. Its files stay read-only here. ",
          slug ? h("a", { href: problemHash(slug) }, `Open ${slug}`) : null,
        ),
      );
    });

  const finishing: Finishing = {
    begin: () => ending.finishing(),
    failed: () => {
      if (ending.failed()) refresh(false);
    },
    finished: endedElsewhere,
  };

  const treeSoon = settle(() => void shown?.files.refresh().catch(() => {}));
  const statusSoon = settle(() => refresh(false));
  const unfollow = context.notifications.subscribe((notice) => {
    if (ending.ended || shown === null) return;
    switch (notice.type) {
      case "file_changed":
        if (notice.attempt_id !== id) return;
        void tabs.follow(notice.path, notice.sha256);
        runs.fileChanged(notice.path, notice.sha256);
        treeSoon();
        return;
      case "attempt_changed":
        if (notice.attempt_id === id) refresh(true);
        return;
      case "progress_changed":
        statusSoon();
        return;
      case "run_started":
        if (notice.attempt_id === id) runs.attach(notice.run_id);
        return;
      case "resync":
        refresh(true);
        void tabs.recheck();
        void runs.catchUp();
        return;
      default:
    }
  });
  refresh(true);

  return () => {
    window.clearInterval(timer);
    unsubscribe();
    intelligence.destroy();
    unfollow();
    treeSoon.cancel();
    statusSoon.cancel();
    runs.destroy();
    tabs.destroy();
    shown?.files.destroy();
  };
}

const NOT_FOUND = "not_found";
const ATTEMPT_ENDED = "attempt_ended";
/** How long the view waits after a change from elsewhere, so a burst of them reads once. */
const SETTLE_MS = 100;

interface Settled {
  (): void;
  cancel(): void;
}

/** `action` once no call came for a moment. */
function settle(action: () => void): Settled {
  let due: number | undefined;
  const trigger = (() => {
    window.clearTimeout(due);
    due = window.setTimeout(action, SETTLE_MS);
  }) as Settled;
  trigger.cancel = () => window.clearTimeout(due);
  return trigger;
}

/** What the header shows of the attempt. */
function headKey(status: AttemptStatus): string {
  return JSON.stringify([status.mode, status.language, status.kind, status.levels?.unlocked, status.levels?.last, status.next]);
}

/** What the statement pane shows of the attempt besides the statement. */
function briefKey(status: AttemptStatus): string {
  return JSON.stringify([status.levels, status.solution_revealed]);
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
  // Focusable, so the keyboard scrolls the statement in the wide layout, where it scrolls alone.
  return h(
    "aside",
    { class: "brief", "aria-label": "Statement", tabindex: "0" },
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
