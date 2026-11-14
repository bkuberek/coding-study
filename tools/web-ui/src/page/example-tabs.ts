/**
 * The tabs of a guide's examples in several languages (docs/specs/web-ui.md#guides-view). The
 * server sends each example with variants as a group of panels, one per language; this makes a
 * tablist of them, starting on the language the rule shows, and a tab chosen in one example
 * chooses that language for every example, in this guide and in the next, until the page reloads.
 */

import { h } from "./dom.ts";
import { inTabOrder, keyedTab, LanguageChoice, languageLabel, shownLanguage } from "./example-tabs-model.ts";

/** The page's choice: it lasts until the page reloads, and is not stored. */
const pageChoice = new LanguageChoice();
let groupsMade = 0;

interface TabGroup {
  readonly languages: readonly string[];
  show(language: string): void;
}

/** Turns every group of panels under `root` into tabs; the function it returns stops following
 * the page's choice, for when the view goes. */
export function exampleTabs(root: HTMLElement, defaultLanguage: string, announce: (message: string) => void): () => void {
  const groups = [...root.querySelectorAll<HTMLElement>(".example-tabs")].map((group) => tabGroup(group, choose));
  const showAll = (): void => {
    for (const group of groups) group.show(shownLanguage(group.languages, pageChoice.chosen, defaultLanguage));
  };
  function choose(language: string): void {
    if (language === pageChoice.chosen) return;
    pageChoice.choose(language);
    if (groups.length > 1) announce(`Examples in ${languageLabel(language)}`);
  }
  showAll();
  return pageChoice.subscribe(showAll);
}

function tabGroup(group: HTMLElement, choose: (language: string) => void): TabGroup {
  const prefix = `example-${(groupsMade += 1)}`;
  const panels = new Map<string, HTMLElement>();
  for (const panel of group.querySelectorAll<HTMLElement>(":scope > .example-variant")) panels.set(panel.dataset.language ?? "", panel);
  const languages = inTabOrder([...panels.keys()]);
  const tabs = languages.map((language, index) => {
    const id = `${prefix}-${language}`;
    const panel = panels.get(language);
    panel?.setAttribute("id", `${id}-panel`);
    panel?.setAttribute("role", "tabpanel");
    panel?.setAttribute("aria-labelledby", id);
    const tab = h("button", { type: "button", role: "tab", id, class: "example-tab", "aria-controls": `${id}-panel` }, languageLabel(language));
    tab.addEventListener("click", () => choose(language));
    tab.addEventListener("keydown", (event) => {
      const next = keyedTab(event.key, index, languages.length);
      const nextLanguage = next === null ? undefined : languages[next];
      if (next === null || nextLanguage === undefined) return;
      event.preventDefault();
      choose(nextLanguage);
      tabs[next]?.focus();
    });
    return tab;
  });
  group.prepend(h("div", { class: "example-tablist", role: "tablist", "aria-label": "Language of the example" }, ...tabs));
  return {
    languages,
    show(shown: string): void {
      languages.forEach((language, index) => {
        const selected = language === shown;
        tabs[index]?.setAttribute("aria-selected", String(selected));
        if (tabs[index]) tabs[index].tabIndex = selected ? 0 : -1;
        const panel = panels.get(language);
        if (panel) panel.hidden = !selected;
      });
    },
  };
}
