/** The Health view (docs/specs/web-ui.md#health-view): the `cstudy doctor` rows, read-only. */

import type { Cleanup, PageContext } from "../context.ts";
import { badge, command, h } from "../dom.ts";
import { checkBadge } from "../format.ts";
import { loading, showFailure } from "../states.ts";
import type { Doctor } from "../types.ts";

export function healthView(context: PageContext): Cleanup {
  const { api, shell } = context;
  shell.setView("health");
  shell.setCommand("cstudy doctor");
  shell.setStatus({ mode: "HEALTH", where: context.session.workspace });
  const summary = h("p", { class: "health-summary", role: "status" });
  const rows = h("div", { class: "checks-region" });
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
  shell.main.replaceChildren(
    h(
      "section",
      { class: "health", "aria-labelledby": "health-heading" },
      h("header", { class: "view-head" }, h("h1", { id: "health-heading" }, "health"), summary, recheck),
      h("p", { class: "quiet" }, "To repair what fails, run ", command("cstudy doctor --fix"), " in a terminal."),
      rows,
    ),
  );
  check();
  return () => {
    current += 1;
  };
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
          h("td", {}, found.fix ? command(found.fix) : null),
        );
      }),
    ),
  );
}
