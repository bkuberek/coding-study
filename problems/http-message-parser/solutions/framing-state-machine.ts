// A request is read in three stages: skip empty lines, find the end of the head (the first
// CRLF CRLF), then read the body that the framing fields announce. Each stage either finishes,
// needs more bytes, or fails, and the same code serves the one-shot methods and the connection:
// `feed` keeps the unread bytes and runs the stages again each time more arrive, so a message is
// reported by the call that completes it.
const CRLF = "\r\n";
const END_OF_HEAD = "\r\n\r\n";
const TOKEN = /^[!#$%&'*+\-.^_`|~0-9A-Za-z]+$/;
const TARGET = /^[!-~]+$/;
const VERSION = /^HTTP\/[0-9]\.[0-9]$/;
const FIELD_VALUE = /^[\t -~]*$/;
const DECIMAL = /^[0-9]+$/;
const HEX = /^[0-9A-Fa-f]+$/;
// A size with more significant digits than this is larger than any limit, so it is never
// converted: a `number` holds integers exactly only up to 2^53.
const MAX_SIGNIFICANT_DIGITS = 12;

type Rows = string[][];

class Failure extends Error {
  readonly code: string;

  constructor(code: string) {
    super(code);
    this.code = code;
  }
}

class NeedMore extends Error {}

function trimOws(text: string): string {
  let start = 0;
  let end = text.length;
  while (start < end && (text[start] === " " || text[start] === "\t")) start++;
  while (end > start && (text[end - 1] === " " || text[end - 1] === "\t")) end--;
  return text.slice(start, end);
}

/** The value of a run of digits, or Infinity when it has too many digits to matter. */
function sizeOf(digits: string, base: number): number {
  const significant = digits.replace(/^0+/, "");
  if (significant.length > MAX_SIGNIFICANT_DIGITS) return Infinity;
  return significant === "" ? 0 : parseInt(significant, base);
}

function skipEmptyLines(data: string, pos: number): number {
  while (data.startsWith(CRLF, pos)) pos += 2;
  return pos;
}

function checkLineEndings(text: string): void {
  const rest = text.split(CRLF).join("");
  if (rest.includes("\r") || rest.includes("\n")) throw new Failure("bad-line-ending");
}

function parseRequestLine(line: string): string[] {
  const parts = line.split(" ");
  if (
    parts.length !== 3 ||
    !TOKEN.test(parts[0]) ||
    !TARGET.test(parts[1]) ||
    !VERSION.test(parts[2])
  ) {
    throw new Failure("bad-request-line");
  }
  return ["request", ...parts];
}

function parseFieldLine(line: string): [string, string] {
  if (line.startsWith(" ") || line.startsWith("\t")) throw new Failure("obs-fold");
  const colon = line.indexOf(":");
  if (colon === -1 || !TOKEN.test(line.slice(0, colon))) throw new Failure("bad-field");
  const value = trimOws(line.slice(colon + 1));
  if (!FIELD_VALUE.test(value)) throw new Failure("bad-field");
  return [line.slice(0, colon).toLowerCase(), value];
}

/** A comma-separated list over every field line, with empty elements dropped. */
function listElements(values: string[]): string[] {
  return values
    .join(",")
    .split(",")
    .map(trimOws)
    .filter((element) => element !== "");
}

export class HttpParser {
  private headLimit: number | null = null;
  private bodyLimit: number | null = null;
  private buffer = "";
  private closed = false;

  // Level 1
  parseHead(data: string): string[][] {
    try {
      const start = skipEmptyLines(data, 0);
      const end = this.endOfHead(data, start);
      return this.headRows(data.slice(start, end - 4));
    } catch (error) {
      return HttpParser.failure(error);
    }
  }

  // Level 2
  parseMessage(data: string): string[][] {
    try {
      return this.message(data, skipEmptyLines(data, 0))[0];
    } catch (error) {
      return HttpParser.failure(error);
    }
  }

  // Level 3
  feed(data: string): string[][] {
    if (this.closed) return [];
    this.buffer += data;
    const rows: Rows = [];
    for (;;) {
      this.buffer = this.buffer.slice(skipEmptyLines(this.buffer, 0));
      let message: Rows;
      let end: number;
      try {
        [message, end] = this.message(this.buffer, 0);
      } catch (error) {
        if (error instanceof NeedMore) return rows;
        if (!(error instanceof Failure)) throw error;
        this.closed = true;
        this.buffer = "";
        return [...rows, ["error", error.code]];
      }
      rows.push(...message);
      this.buffer = this.buffer.slice(end);
    }
  }

  close(): string[][] {
    if (this.closed) return [];
    this.closed = true;
    return this.buffer !== "" ? [["error", "incomplete"]] : [];
  }

  // Level 4
  setLimits(maxHeadBytes: number, maxBodyBytes: number): void {
    this.headLimit = maxHeadBytes;
    this.bodyLimit = maxBodyBytes;
  }

  // The stages
  private static failure(error: unknown): Rows {
    if (error instanceof NeedMore) return [["error", "incomplete"]];
    if (error instanceof Failure) return [["error", error.code]];
    throw error;
  }

  /** The index just after the head's empty line. With a limit, only the first `limit` bytes
   * are searched, so a head that cannot fit fails without waiting. */
  private endOfHead(data: string, start: number): number {
    let found: number;
    if (this.headLimit === null) {
      found = data.indexOf(END_OF_HEAD, start);
    } else {
      const window = data.slice(start, start + this.headLimit).indexOf(END_OF_HEAD);
      found = window === -1 ? -1 : start + window;
      if (found === -1 && data.length - start >= this.headLimit) {
        throw new Failure("head-too-large");
      }
    }
    if (found === -1) throw new NeedMore();
    return found + 4;
  }

  private headRows(text: string): Rows {
    checkLineEndings(text);
    const lines = text.split(CRLF);
    const rows: Rows = [parseRequestLine(lines[0])];
    for (const line of lines.slice(1)) rows.push(["field", ...parseFieldLine(line)]);
    const hosts = rows.filter((row) => row[0] === "field" && row[1] === "host").length;
    if (hosts > 1 || (hosts === 0 && rows[0][3] === "HTTP/1.1")) throw new Failure("bad-host");
    return rows;
  }

  private message(data: string, start: number): [Rows, number] {
    const headEnd = this.endOfHead(data, start);
    const rows = this.headRows(data.slice(start, headEnd - 4));
    const codings: string[] = [];
    const lengths: string[] = [];
    for (const row of rows.slice(1)) {
      if (row[1] === "transfer-encoding") codings.push(row[2]);
      if (row[1] === "content-length") lengths.push(row[2]);
    }
    if (codings.length > 0 && lengths.length > 0) throw new Failure("ambiguous-length");
    if (codings.length > 0) {
      const list = listElements(codings).map((coding) => coding.toLowerCase());
      if (list.length !== 1 || list[0] !== "chunked") {
        throw new Failure("unsupported-transfer-coding");
      }
      return this.chunked(data, headEnd, rows);
    }
    const length = lengths.length > 0 ? this.contentLength(lengths) : 0;
    if (data.length - headEnd < length) throw new NeedMore();
    rows.push(["body", data.slice(headEnd, headEnd + length)]);
    return [rows, headEnd + length];
  }

  private contentLength(lines: string[]): number {
    const elements = listElements(lines);
    if (elements.length === 0 || !elements.every((element) => DECIMAL.test(element))) {
      throw new Failure("bad-content-length");
    }
    const distinct = new Set(elements.map((element) => element.replace(/^0+/, "")));
    if (distinct.size > 1) throw new Failure("conflicting-content-length");
    const length = sizeOf(elements[0], 10);
    if (this.tooLarge(length, 0)) throw new Failure("body-too-large");
    return length;
  }

  private tooLarge(size: number, used: number): boolean {
    return this.bodyLimit !== null && used + size > this.bodyLimit;
  }

  private chunked(data: string, start: number, rows: Rows): [Rows, number] {
    let pos = start;
    let content = "";
    let total = 0;
    for (;;) {
      const lineEnd = data.indexOf(CRLF, pos);
      if (lineEnd === -1) throw new NeedMore();
      const size = HttpParser.chunkSize(data.slice(pos, lineEnd));
      if (this.tooLarge(size, total)) throw new Failure("body-too-large");
      pos = lineEnd + 2;
      if (size === 0) break;
      if (data.length - pos < size + 2) throw new NeedMore();
      if (data.slice(pos + size, pos + size + 2) !== CRLF) throw new Failure("bad-chunk");
      content += data.slice(pos, pos + size);
      total += size;
      pos += size + 2;
    }
    rows.push(["body", content]);
    if (data.startsWith(CRLF, pos)) return [rows, pos + 2];
    const found = data.indexOf(END_OF_HEAD, pos);
    if (found === -1) throw new NeedMore();
    const text = data.slice(pos, found);
    checkLineEndings(text);
    for (const line of text.split(CRLF)) rows.push(["trailer", ...parseFieldLine(line)]);
    return [rows, found + 4];
  }

  private static chunkSize(line: string): number {
    if (line.includes("\r") || line.includes("\n")) throw new Failure("bad-chunk-size");
    const semicolon = line.indexOf(";");
    const digits = semicolon === -1 ? line : line.slice(0, semicolon).replace(/[ \t]+$/, "");
    if (!HEX.test(digits)) throw new Failure("bad-chunk-size");
    return sizeOf(digits, 16);
  }
}
