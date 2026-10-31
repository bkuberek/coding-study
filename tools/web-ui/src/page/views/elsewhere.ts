/** Fragments the page has no view for: one the terminal has, or none at all. */

import type { Cleanup, PageContext } from "../context.ts";
import { command, h } from "../dom.ts";

export function terminalView(context: PageContext, text: string): Cleanup {
  context.shell.setView(null);
  context.shell.setCommand(text);
  context.shell.setStatus({ mode: "TERMINAL", where: text });
  context.shell.main.replaceChildren(
    h(
      "section",
      { class: "notice" },
      h("h1", {}, "in the terminal"),
      h("p", {}, "The page has no view for this yet. Run ", command(text), " in a terminal."),
      h("p", {}, h("a", { href: "#/" }, "Back to the problems")),
    ),
  );
  return () => {};
}

export function missingView(context: PageContext, fragment: string): Cleanup {
  context.shell.setView(null);
  context.shell.setCommand("cstudy list");
  context.shell.setStatus({ mode: "?", where: fragment });
  context.shell.main.replaceChildren(
    h(
      "section",
      { class: "notice" },
      h("h1", {}, "no such view"),
      h("p", {}, "Nothing lives at ", h("code", {}, fragment), "."),
      h("p", {}, h("a", { href: "#/" }, "Back to the problems")),
    ),
  );
  return () => {};
}
