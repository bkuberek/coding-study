/**
 * The Health view (docs/specs/web-ui.md#health-view): the `cstudy doctor` rows, Fix, which runs
 * `cstudy doctor --fix` as a job and checks again, and Verify of the workspace's own problems.
 */

import "./health.css";

import type { Cleanup, PageContext } from "../context.ts";
import { badge, command, fixHint, h } from "../dom.ts";
import { checkBadge } from "../format.ts";
import { JobPanel } from "../jobs.ts";
import { loading, showFailure } from "../states.ts";
import type { Doctor, ProblemList } from "../types.ts";

export function healthView(context: PageContext): Cleanup {
  const { api, shell } = context;
  shell.setView("health");
  shell.setCommand("cstudy doctor");
  shell.setStatus({ mode: "HEALTH", where: context.session.workspace });
  const summary = h("p", { class: "health-summary", role: "status" });
  // Focusable, so the keyboard scrolls the checks where they are wider than the window.
  const rows = h("div", { class: "checks-region table-scroll", role: "region", tabindex: "0", "aria-label": "Checks" });
  const recheck = h("button", { type: "button", class: "button" }, "Re-check");
  let current = 0;

  const check = () => {
    const request = ++current;
    recheck.disabled = true;
    summary.textContent = "";
    rows.replaceChildren(loading("running cstudy doctor… each runner answers a handshake, which can take a while"));
    void api
      .get<Doctor>("/api/v1/doctor")
      .then((doctor) => {
        if (request !== current) return;
        const failed = doctor.checks.filter((found) => found.status === "fail").length;
        const warned = doctor.checks.filter((found) => found.status === "warn").length;
        summary.replaceChildren(
          doctor.passed ? badge("✓", "passed", "ok") : badge("✕", "failing", "fail"),
          ` ${doctor.checks.length} checks · ${failed} fail · ${warned} warn`,
        );
        rows.replaceChildren(table(doctor));
        context.shell.announce(doctor.passed ? "every check passed" : `${failed} checks fail`);
      })
      .catch((error: unknown) => showFailure(rows, error))
      .finally(() => {
        if (request === current) recheck.disabled = false;
      });
  };
  recheck.addEventListener("click", check);
  const fixJob = new JobPanel(context, { ended: check });
  const fix = h("button", { type: "button", class: "button", title: "cstudy doctor --fix, after its question" }, "Fix");
  fix.addEventListener("click", () => void fixJob.start({ command: "doctor_fix" }, "cstudy doctor --fix"));
  const verifyJob = new JobPanel(context);
  shell.main.replaceChildren(
    h(
      "section",
      { class: "health", "aria-labelledby": "health-heading" },
      h("header", { class: "view-head" }, h("h1", { id: "health-heading" }, "health"), summary, recheck),
      h("p", { class: "health-fix" }, fix, h("span", { class: "quiet" }, " repairs what fails: ", command("cstudy doctor --fix"))),
      fixJob.element,
      rows,
      yourProblems(context, verifyJob),
    ),
  );
  check();
  return () => {
    current += 1;
    fixJob.destroy();
    verifyJob.destroy();
  };
}

const VERIFY_SWITCHES = ["static", "oracle", "ladder"] as const;

/** The workspace's own problems, each with Verify, run as a job (docs/specs/web-ui.md#health-view). */
function yourProblems(context: PageContext, job: JobPanel): HTMLElement {
  const list = h("div", { class: "own-problems" }, loading("reading your problems…"));
  const switches = VERIFY_SWITCHES.map((name) => h("input", { type: "checkbox", id: `verify-${name}` }));
  const verify = (slug: string) => {
    const chosen = VERIFY_SWITCHES.filter((_, index) => switches[index]?.checked);
    const body = { command: "verify", slugs: [slug], ...Object.fromEntries(chosen.map((name) => [name, true])) };
    void job.start(body, ["cstudy verify", slug, ...chosen.map((name) => `--${name}`)].join(" "));
  };
  void context.api
    .get<ProblemList>("/api/v1/problems")
    .then((problems) => {
      const own = problems.entries.filter((entry) => entry.source === "workspace");
      list.replaceChildren(
        own.length
          ? h(
              "ul",
              { class: "plain own-problem-list" },
              ...own.map((entry) => {
                const button = h("button", { type: "button", class: "button", title: `cstudy verify ${entry.slug}` }, "Verify");
                button.addEventListener("click", () => verify(entry.slug));
                return h("li", {}, button, " ", h("span", { class: "slug" }, entry.slug), h("span", { class: "quiet" }, ` ${entry.title} · ${entry.kind}`));
              }),
            )
          : h("p", { class: "quiet" }, "No problems of your own yet: ", command("cstudy new <slug>"), " writes one into the workspace."),
      );
    })
    .catch((error: unknown) => showFailure(list, error));
  return h(
    "section",
    { class: "own", "aria-labelledby": "own-heading" },
    h("h2", { id: "own-heading", class: "eyebrow" }, "your problems"),
    h(
      "p",
      { class: "verify-switches" },
      ...VERIFY_SWITCHES.flatMap((name, index) => [switches[index]!, h("label", { for: `verify-${name}` }, `--${name}`), " "]),
    ),
    list,
    job.element,
  );
}

function table(doctor: Doctor): HTMLElement {
  return h(
    "table",
    { class: "checks" },
    h("caption", { class: "sr-only" }, "cstudy doctor checks"),
    h("thead", {}, h("tr", {}, ...["status", "check", "detail", "fix"].map((name) => h("th", { scope: "col" }, name)))),
    h(
      "tbody",
      {},
      ...doctor.checks.map((found) => {
        const status = checkBadge(found.status);
        return h(
          "tr",
          { class: `check-${found.status}` },
          h("td", {}, badge(status.glyph, status.text, status.tone)),
          h("td", { class: "check-name" }, found.name),
          h("td", { class: "check-detail" }, found.detail),
          h("td", {}, found.fix ? fixHint(found.fix) : null),
        );
      }),
    ),
  );
}
