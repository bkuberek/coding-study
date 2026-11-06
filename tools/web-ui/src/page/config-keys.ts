/** The keys of `config.toml` as `GET /api/v1/config` describes them (docs/specs/web-ui.md#settings-view). */

export type ConfigValue = boolean | number | string | readonly string[] | null;

export interface ConfigKey {
  /** Dotted: `schedule.max_interval_days`. */
  readonly name: string;
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

/** The keys by table, in file order; a top-level key's table is empty. */
export function tablesOf(keys: readonly ConfigKey[]): [string, ConfigKey[]][] {
  const tables = new Map<string, ConfigKey[]>();
  for (const key of keys) {
    const table = key.name.split(".").slice(0, -1).join(".");
    tables.set(table, [...(tables.get(table) ?? []), key]);
  }
  return [...tables];
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

/** Only the keys whose field differs from the value in force, as `POST /api/v1/config` takes them. */
export function changedKeys(fields: readonly (readonly [ConfigKey, ConfigValue])[]): Record<string, ConfigValue> {
  return Object.fromEntries(
    fields
      .filter(([key, value]) => !key.reserved && JSON.stringify(value) !== JSON.stringify(key.value))
      .map(([key, value]) => [key.name, value]),
  );
}
