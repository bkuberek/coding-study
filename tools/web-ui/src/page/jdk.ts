/**
 * Whether the selected JDK can run a problem's Java and Kotlin (docs/specs/web-ui.md#problems-view),
 * decided as a consumer of `cstudy list --json` does: the entry's `jdk` range against the
 * document's `selected_jdk` (docs/specs/cli.md#the-selected-jdk). A refusal reads as the one
 * `cstudy start` prints for the same problem and language.
 */

/** `selected_jdk` of the session and of `cstudy list --json`. */
export interface SelectedJdk {
  /** As the JDK's `release` file spells it, such as `26.0.1`. */
  readonly version: string;
  readonly feature: number;
  /** `JAVA_HOME` or `PATH`. */
  readonly source: string;
  /** The feature release lies in the range cstudy supports. */
  readonly supported: boolean;
}

/** An entry's `jdk`: the feature releases its Java and Kotlin run on, bounds included. */
export interface JdkRange {
  readonly min: number;
  readonly max: number;
}

const JVM_LANGUAGES: ReadonlySet<string> = new Set(["java", "kotlin"]);

/** `JDK 21 to 26`, or `JDK 24` for a range of one release. */
export function rangeText(range: JdkRange): string {
  return range.min === range.max ? `JDK ${range.min}` : `JDK ${range.min} to ${range.max}`;
}

/**
 * Why the selected JDK cannot run `slug` in `language`, or null when it can, when `language` takes
 * no JDK, or when the problem lists neither Java nor Kotlin (`range` null). No JDK at all is
 * outside every range.
 *
 * A JDK above the range is "not supported yet" when cstudy does not support it; the page cannot
 * tell it from "newer than the problem supports" for a problem whose own maximum is below the
 * supported one, since it knows no supported range, and says the first: both hold.
 */
export function jdkRefusal(slug: string, language: string, selected: SelectedJdk | null, range: JdkRange | null): string | null {
  if (range === null || !JVM_LANGUAGES.has(language)) return null;
  if (selected !== null && selected.feature >= range.min && selected.feature <= range.max) return null;
  const head = `${slug} runs its ${language} version on ${rangeText(range)}; `;
  if (selected === null) return `${head}no JDK was found`;
  const selection = `${selected.source} selects JDK ${selected.feature}`;
  if (selected.feature < range.min) return `${head}${selection}, which is too old`;
  return `${head}${selection}, ${selected.supported ? "which is newer than the problem supports" : "which cstudy does not support yet"}`;
}

/** The refusal of each of `languages` the selected JDK cannot run, by language, in their order. */
export function jdkRefusals(
  slug: string,
  languages: readonly string[],
  selected: SelectedJdk | null,
  range: JdkRange | null,
): ReadonlyMap<string, string> {
  const refusals = new Map<string, string>();
  for (const language of languages) {
    const refusal = jdkRefusal(slug, language, selected, range);
    if (refusal !== null) refusals.set(language, refusal);
  }
  return refusals;
}
