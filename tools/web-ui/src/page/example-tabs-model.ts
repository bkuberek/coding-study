/**
 * The rules of a guide's examples in several languages (docs/specs/guides.md#variants), apart
 * from the page so the tests read them without a browser: the tab order, each tab's name, the
 * language an example shows (docs/specs/guides.md#the-language-shown), the keys that move between
 * tabs, and the language chosen on the page, which every example follows.
 */

const LABELS = {
  bash: "Bash",
  python: "Python",
  typescript: "TypeScript",
  java: "Java",
  kotlin: "Kotlin",
  go: "Go",
  rust: "Rust",
  javascript: "JavaScript",
} as const satisfies Record<string, string>;
const TAB_ORDER: readonly string[] = Object.keys(LABELS);
const BASH = "bash";
const PYTHON = "python";

export function languageLabel(language: string): string {
  return Object.hasOwn(LABELS, language) ? LABELS[language as keyof typeof LABELS] : language;
}

function rank(language: string): number {
  const found = TAB_ORDER.indexOf(language);
  return found === -1 ? TAB_ORDER.length : found;
}

export function inTabOrder(languages: readonly string[]): string[] {
  return [...languages].sort((a, b) => rank(a) - rank(b));
}

/** The first of the page's choice, bash, `default_lang` and Python that the example has, else its
 * first language in the tab order. */
export function shownLanguage(languages: readonly string[], chosen: string | null, defaultLanguage: string): string {
  const wanted = [chosen, BASH, defaultLanguage, PYTHON].find((language) => language !== null && languages.includes(language));
  return wanted ?? inTabOrder(languages)[0] ?? PYTHON;
}

/** The tab a key moves to from the tab at `index` of `count`, as the open files' tabs move; null
 * for another key or past an end. */
export function keyedTab(key: string, index: number, count: number): number | null {
  const moves: Record<string, number> = { ArrowRight: index + 1, ArrowLeft: index - 1, Home: 0, End: count - 1 };
  const target = moves[key];
  return target === undefined || target < 0 || target >= count ? null : target;
}

type Listener = (language: string) => void;

/** The language chosen on the page: every example follows it until the page reloads. */
export class LanguageChoice {
  #chosen: string | null = null;
  readonly #listeners = new Set<Listener>();

  get chosen(): string | null {
    return this.#chosen;
  }

  choose(language: string): void {
    if (language === this.#chosen) return;
    this.#chosen = language;
    for (const listener of [...this.#listeners]) listener(language);
  }

  /** Calls `listener` on each change; the function it returns stops that. */
  subscribe(listener: Listener): () => void {
    this.#listeners.add(listener);
    return () => this.#listeners.delete(listener);
  }
}
