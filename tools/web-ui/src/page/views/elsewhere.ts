/** A fragment the page has no view for. */

import type { Cleanup, PageContext } from "../context.ts";
import { h } from "../dom.ts";

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
