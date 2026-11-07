/**
 * The About view (docs/specs/web-ui.md#about-view): the version, the license, the links and the
 * credits `cstudy about` prints, the full license texts one click away, headed by the author and,
 * quiet, where to sponsor cstudy. The status bar's version opens it; the top bar does not list it.
 */

import "./about.css";

import type { Cleanup, PageContext } from "../context.ts";
import { command, h } from "../dom.ts";
import { loading, showFailure } from "../states.ts";
import type { About, AboutCredit, AboutLicenses, AboutLink } from "../types.ts";

/** A plain link to another site: nothing is fetched until it is followed, and the page it opens
 * gets neither the opener nor the referrer. */
function outside(link: AboutLink): HTMLAnchorElement {
  return h("a", { href: link.url, target: "_blank", rel: "noopener noreferrer" }, link.url.replace(/^https:\/\//, ""));
}

/** The author, first: the name and a plain link to their site, whose text is the label, not the address. */
function author(about: About): HTMLElement {
  const { credit, link } = about.author;
  return h("p", { class: "about-author" }, credit, " · ", h("a", { href: link.url, target: "_blank", rel: "noopener noreferrer" }, link.label));
}

function facts(about: About): HTMLElement {
  const rows: readonly (readonly [string, Node | string])[] = [
    ["version", about.version],
    ["license", about.license],
    [about.website.label.toLowerCase(), outside(about.website)],
    ...about.links.map((link): readonly [string, Node] => [link.label.toLowerCase(), outside(link)]),
  ];
  return h("dl", { class: "about-facts" }, ...rows.flatMap(([name, value]) => [h("dt", {}, name), h("dd", {}, value)]));
}

function creditRow(credit: AboutCredit): HTMLElement {
  return h("tr", {}, h("th", { scope: "row", class: "credit-name" }, credit.name), h("td", {}, credit.version), h("td", {}, credit.license));
}

function credits(about: About): HTMLElement {
  return h(
    "section",
    { class: "about-credits", "aria-labelledby": "credits-heading" },
    h("h2", { id: "credits-heading" }, "credits"),
    h("p", { class: "quiet" }, "cstudy is built on the software below, and each part keeps its own license. ", command("cstudy about --credits"), " lists the same."),
    ...about.credits.map((section, index) =>
      h(
        "div",
        { class: "credit-section" },
        h("h3", { id: `credits-${index}` }, section.title),
        h(
          "div",
          { class: "credits-scroll", role: "region", tabindex: "0", "aria-labelledby": `credits-${index}` },
          h(
            "table",
            { class: "credits", "aria-labelledby": `credits-${index}` },
            h("thead", { class: "sr-only" }, h("tr", {}, ...["name", "version", "license"].map((name) => h("th", { scope: "col" }, name)))),
            h("tbody", {}, ...section.credits.map(creditRow)),
          ),
        ),
      ),
    ),
  );
}

/** The full texts, fetched when the section first opens: they run to many screens. */
function licenseTexts(context: PageContext): HTMLElement {
  const text = h("div", { class: "license-text" });
  const section = h("details", { class: "about-licenses" }, h("summary", {}, "Full license texts"), text);
  let requested = false;
  section.addEventListener("toggle", () => {
    if (!section.open || requested) return;
    requested = true;
    text.replaceChildren(loading());
    void context.api
      .get<AboutLicenses>("/api/v1/about/licenses")
      .then((found) => text.replaceChildren(h("pre", { tabindex: "0", "aria-label": "License texts" }, found.text)))
      .catch((error: unknown) => {
        requested = false;
        showFailure(text, error);
      });
  });
  return section;
}

function sponsor(about: About): HTMLElement {
  const links = about.sponsor.flatMap((link, index) => [index > 0 ? " · " : null, h("a", { href: link.url, target: "_blank", rel: "noopener noreferrer" }, link.label)]);
  return h("p", { class: "about-sponsor quiet" }, "cstudy is free. If it helps you, you can support its work on ", ...links, ".");
}

export function aboutView(context: PageContext): Cleanup {
  const { api, shell } = context;
  shell.setView("about");
  shell.setCommand("cstudy about");
  shell.setStatus({ mode: "ABOUT", where: "credits and licenses" });
  const body = h("div", { class: "about-body" }, loading());
  shell.main.replaceChildren(
    h("section", { class: "about", "aria-labelledby": "about-heading" }, h("header", { class: "view-head" }, h("h1", { id: "about-heading" }, "about")), body),
  );
  let left = false;
  void api
    .get<About>("/api/v1/about")
    .then((about) => {
      if (!left) body.replaceChildren(author(about), sponsor(about), facts(about), credits(about), licenseTexts(context));
    })
    .catch((error: unknown) => {
      if (!left) showFailure(body, error);
    });
  return () => {
    left = true;
  };
}
