// Keeps user code from writing to the real standard streams or ending the runner
// (docs/specs/runners.md#execution-environment).

import { Buffer } from "node:buffer";
import { format } from "node:util";

export const CAPTURE_LIMIT_BYTES = 4096;
/** Appended when output was dropped; identical in every runner (docs/specs/runners.md). */
export const TRUNCATION_NOTICE = "\n[output truncated at 4 KiB]\n";
const CONSOLE_METHODS = ["log", "info", "debug", "warn", "error"] as const;

/** Thrown in place of `process.exit` while user code runs. */
export class ProcessExitError extends Error {
  constructor(code: unknown) {
    super(
      `process.exit(${code === undefined ? "" : String(code)}) was called; return a value instead`,
    );
  }
}

/** Replaces `process.exit` with a throwing stub and returns the real one for the runner. */
export function blockProcessExit(): (code: number) => never {
  const exit = process.exit.bind(process);
  process.exit = ((code?: unknown) => {
    throw new ProcessExitError(code);
  }) as typeof process.exit;
  return exit;
}

/**
 * Collects console output and direct `process.stdout`/`process.stderr` writes made between
 * `start` and `stop`, keeping at most CAPTURE_LIMIT_BYTES of UTF-8, then TRUNCATION_NOTICE
 * when anything was dropped.
 */
export class OutputCapture {
  readonly #chunks: string[] = [];
  readonly #restorers: (() => void)[] = [];
  #bytes = 0;
  #truncated = false;

  start(): void {
    for (const method of CONSOLE_METHODS) {
      const original = console[method];
      console[method] = (...args: unknown[]) =>
        this.#append(`${format(...args)}\n`);
      this.#restorers.push(() => {
        console[method] = original;
      });
    }
    for (const stream of [process.stdout, process.stderr]) {
      const original = stream.write;
      stream.write = ((chunk: unknown, ...rest: unknown[]) => {
        this.#append(
          typeof chunk === "string"
            ? chunk
            : Buffer.from(chunk as Uint8Array).toString("utf8"),
        );
        const callback = rest.find(
          (argument) => typeof argument === "function",
        );
        if (callback !== undefined) {
          process.nextTick(callback as () => void);
        }
        return true;
      }) as typeof stream.write;
      this.#restorers.push(() => {
        stream.write = original;
      });
    }
  }

  /** Restores the streams and returns what was written. */
  stop(): string {
    this.#restorers
      .splice(0)
      .reverse()
      .forEach((restore) => restore());
    const text = this.#chunks.splice(0).join("");
    return this.#truncated ? text + TRUNCATION_NOTICE : text;
  }

  #append(text: string): void {
    const remaining = CAPTURE_LIMIT_BYTES - this.#bytes;
    const kept = remaining > 0 ? truncateUtf8(text, remaining) : "";
    this.#truncated ||= kept.length < text.length;
    this.#chunks.push(kept);
    this.#bytes += Buffer.byteLength(kept, "utf8");
  }
}

/** The longest prefix of `text` that fits in `limit` UTF-8 bytes, never splitting a character. */
function truncateUtf8(text: string, limit: number): string {
  if (Buffer.byteLength(text, "utf8") <= limit) {
    return text;
  }
  let bytes = 0;
  let end = 0;
  for (const character of text) {
    bytes += Buffer.byteLength(character, "utf8");
    if (bytes > limit) {
      break;
    }
    end += character.length;
  }
  return text.slice(0, end);
}
