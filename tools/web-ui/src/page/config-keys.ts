/** The keys of `config.toml` as `GET /api/v1/config` describes them (docs/specs/web-ui.md#settings-view). */

export type ConfigValue = boolean | number | string | readonly string[] | null;

export interface ConfigKey {
  /** Dotted: `schedule.max_interval_days`. */
  readonly name: string;
  /** What Settings calls the key, with `name` beside it. */
  readonly label: string;
  /** The group of related keys it shows under. */
  readonly section: string;
  readonly kind: "boolean" | "integer" | "text" | "choice" | "choices";
  readonly value: ConfigValue;
  readonly default: ConfigValue;
  readonly set: boolean;
  readonly help: string;
  /** When a change takes effect, in words. */
  readonly applies: string;
  readonly choices: readonly string[];
  readonly example: ConfigValue;
  readonly reserved: boolean;
}

export interface ConfigDocument {
  readonly path: string;
  readonly exists: boolean;
  readonly writable: boolean;
  readonly issues: readonly string[];
  readonly keys: readonly ConfigKey[];
  /** After a save. */
  readonly changed?: readonly string[];
}

/** The keys by section, in file order. */
export function sectionsOf(keys: readonly ConfigKey[]): [string, ConfigKey[]][] {
  const sections = new Map<string, ConfigKey[]>();
  for (const key of keys) sections.set(key.section, [...(sections.get(key.section) ?? []), key]);
  return [...sections];
}

/** What a field's text means for its key: empty returns the key to its default, and words in a
 * number's field stay words, for the server to refuse by the key's name. */
export function typedValue(key: ConfigKey, text: string): ConfigValue {
  const trimmed = text.trim();
  if (trimmed === "") return null;
  return key.kind === "integer" && !Number.isNaN(Number(trimmed)) ? Number(trimmed) : trimmed;
}

export function shownValue(value: ConfigValue): string {
  if (value === null) return "unset";
  return Array.isArray(value) ? value.join(", ") : String(value);
}

/** Only the keys whose field differs from how it was drawn, as `POST /api/v1/config` takes them. A
 * field is held to itself, not to the file: a list in another order than the file's, or a field
 * that cannot show what the file holds, is no change until the user makes one. */
export function changedKeys(fields: readonly (readonly [key: ConfigKey, now: ConfigValue, drawn: ConfigValue])[]): Record<string, ConfigValue> {
  return Object.fromEntries(
    fields
      .filter(([key, now, drawn]) => !key.reserved && JSON.stringify(now) !== JSON.stringify(drawn))
      .map(([key, now]) => [key.name, now]),
  );
}
