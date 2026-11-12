const DEFAULT_PORTS = new Map<string, number>([
  ["http", 80],
  ["https", 443],
  ["ws", 80],
  ["wss", 443],
  ["ftp", 21],
]);
const SECURE_SCHEMES = new Set(["https", "wss"]);
const SAFELISTED_METHODS = new Set(["GET", "HEAD", "POST"]);
const NORMALIZED_METHODS = new Set(["DELETE", "GET", "HEAD", "OPTIONS", "POST", "PUT"]);
const OPAQUE = "null";
const WILDCARD = "*";

const SCHEME = /^[A-Za-z][A-Za-z0-9+.-]*$/;
const HOST = /^[A-Za-z0-9.-]+$/;
const PORT = /^[0-9]*$/;
const LABELS = /^[a-z0-9-]+(\.[a-z0-9-]+)*$/;
const PATTERN = /^([^:/]+):\/\/\*\.([A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*)(?::([0-9]+))?$/;
const RANGE = /^bytes=([0-9]+)-([0-9]*)$/;
const LANGUAGE_VALUE = /^[0-9A-Za-z *,\-.;=]*$/;
const UNSAFE_CHARACTERS = new Set(['"', "(", ")", ":", "<", ">", "?", "@", "[", "\\", "]", "{", "}", "\x7f"]);
const SIMPLE_CONTENT_TYPES = new Set(["application/x-www-form-urlencoded", "multipart/form-data", "text/plain"]);
const MAX_SAFELISTED_VALUE = 128;
const MAX_SAFELISTED_TOTAL = 1024;

const ALLOW_ORIGIN = "Access-Control-Allow-Origin";
const ALLOW_CREDENTIALS = "Access-Control-Allow-Credentials";
const ALLOW_METHODS = "Access-Control-Allow-Methods";
const ALLOW_HEADERS = "Access-Control-Allow-Headers";
const MAX_AGE = "Access-Control-Max-Age";

/** `:port` for a port that differs from the scheme's default, "" otherwise, null if invalid. */
function portSuffix(scheme: string, digits: string): string | null {
  if (digits === "") {
    return "";
  }
  const port = Number(digits);
  if (port > 65535) {
    return null;
  }
  return port === DEFAULT_PORTS.get(scheme) ? "" : `:${port}`;
}

function serializeOrigin(url: string): string {
  const colon = url.indexOf(":");
  if (colon < 0 || !SCHEME.test(url.slice(0, colon))) {
    return OPAQUE;
  }
  const scheme = url.slice(0, colon).toLowerCase();
  const rest = url.slice(colon + 1);
  if (!DEFAULT_PORTS.has(scheme) || !rest.startsWith("//")) {
    return OPAQUE;
  }
  const authority = rest.slice(2).split(/[/?#]/, 1)[0];
  const hostAndPort = authority.slice(authority.lastIndexOf("@") + 1);
  const portColon = hostAndPort.indexOf(":");
  const host = portColon < 0 ? hostAndPort : hostAndPort.slice(0, portColon);
  const digits = portColon < 0 ? "" : hostAndPort.slice(portColon + 1);
  if (!HOST.test(host) || !PORT.test(digits)) {
    return OPAQUE;
  }
  const suffix = portSuffix(scheme, digits);
  return suffix === null ? OPAQUE : `${scheme}://${host.toLowerCase()}${suffix}`;
}

function hasUnsafeCharacter(value: string): boolean {
  for (const character of value) {
    const code = character.charCodeAt(0);
    if ((code < 0x20 && character !== "\t") || UNSAFE_CHARACTERS.has(character)) {
      return true;
    }
  }
  return false;
}

function trimSpacesAndTabs(text: string): string {
  return text.replace(/^[ \t]+|[ \t]+$/g, "");
}

/** CORS-safelisted request-header, after the Fetch standard. */
function isSafelistedHeader(name: string, value: string): boolean {
  if (value.length > MAX_SAFELISTED_VALUE) {
    return false;
  }
  switch (name.toLowerCase()) {
    case "accept":
      return !hasUnsafeCharacter(value);
    case "accept-language":
    case "content-language":
      return LANGUAGE_VALUE.test(value);
    case "content-type": {
      const essence = trimSpacesAndTabs(value.split(";", 1)[0]).toLowerCase();
      return !hasUnsafeCharacter(value) && SIMPLE_CONTENT_TYPES.has(essence);
    }
    case "range": {
      // Up to 15 digits by the constraints, so Number is exact.
      const match = RANGE.exec(value);
      return match !== null && (match[2] === "" || Number(match[1]) <= Number(match[2]));
    }
    default:
      return false;
  }
}

/** `scheme://*.host[:port]`: one or more labels in front of `.host`, same scheme and port. */
class OriginPattern {
  readonly text: string;
  readonly secure: boolean;
  readonly broad: boolean;
  private readonly prefix: string;
  private readonly suffix: string;

  constructor(scheme: string, host: string, port: string) {
    this.prefix = `${scheme}://`;
    this.suffix = `.${host}${port}`;
    this.text = `${scheme}://*.${host}${port}`;
    this.secure = SECURE_SCHEMES.has(scheme);
    this.broad = !host.includes(".");
  }

  matches(origin: string): boolean {
    if (!origin.startsWith(this.prefix) || !origin.endsWith(this.suffix)) {
      return false;
    }
    const middle = origin.slice(this.prefix.length, origin.length - this.suffix.length);
    return LABELS.test(middle);
  }
}

export class CorsPolicy {
  private readonly origins = new Set<string>();
  private readonly patterns = new Map<string, OriginPattern>();
  private readonly methods: string[] = [];
  private readonly headers: string[] = [];
  private maxAge: number | null = null;
  private anyOrigin = false;
  private credentials = false;

  // Level 1
  originOf(url: string): string {
    return serializeOrigin(url);
  }

  allowOrigin(url: string): string {
    // Only the literal text null allows the opaque origin; a URL without an origin is refused.
    const origin = serializeOrigin(url);
    if (origin === OPAQUE && url !== OPAQUE) {
      return "";
    }
    this.origins.add(origin);
    return origin;
  }

  allowOriginFor(origin: string): string {
    if (this.anyOrigin && !this.credentials) {
      return WILDCARD;
    }
    if (this.isListed(origin)) {
      return origin;
    }
    return this.anyOrigin ? WILDCARD : "";
  }

  // Level 2
  allowMethod(method: string): boolean {
    if (this.methods.includes(method)) {
      return false;
    }
    this.methods.push(method);
    return true;
  }

  allowHeader(name: string): boolean {
    const lower = name.toLowerCase();
    if (this.headers.includes(lower)) {
      return false;
    }
    this.headers.push(lower);
    return true;
  }

  setMaxAge(seconds: number): void {
    this.maxAge = seconds;
  }

  needsPreflight(method: string, headers: string[][]): boolean {
    const normalized = NORMALIZED_METHODS.has(method.toUpperCase()) ? method.toUpperCase() : method;
    if (!SAFELISTED_METHODS.has(normalized)) {
      return true;
    }
    let total = 0;
    for (const [name, value] of headers) {
      if (!isSafelistedHeader(name, value)) {
        return true;
      }
      total += value.length;
    }
    return total > MAX_SAFELISTED_TOTAL;
  }

  preflightResponse(origin: string, method: string, requestHeaders: string): string[][] {
    const allowedOrigin = this.allowOriginFor(origin);
    if (allowedOrigin === "") {
      return [];
    }
    const credentialed = this.isCredentialed(origin, allowedOrigin);
    const requested = requestHeaders
      .split(",")
      .map((name) => trimSpacesAndTabs(name).toLowerCase())
      .filter((name) => name !== "");
    if (
      !this.isMethodAllowed(method, credentialed) ||
      !requested.every((name) => this.isHeaderAllowed(name, credentialed))
    ) {
      return [];
    }
    const rows = [[ALLOW_ORIGIN, allowedOrigin]];
    if (credentialed) {
      rows.push([ALLOW_CREDENTIALS, "true"]);
    }
    if (this.methods.length > 0) {
      rows.push([ALLOW_METHODS, this.methods.join(", ")]);
    }
    if (this.headers.length > 0) {
      rows.push([ALLOW_HEADERS, this.headers.join(", ")]);
    }
    if (this.maxAge !== null) {
      rows.push([MAX_AGE, String(this.maxAge)]);
    }
    return rows;
  }

  // Level 3
  allowAnyOrigin(): void {
    this.anyOrigin = true;
  }

  allowCredentials(): void {
    this.credentials = true;
  }

  actualResponse(origin: string): string[][] {
    const allowedOrigin = this.allowOriginFor(origin);
    const rows: string[][] = allowedOrigin === "" ? [] : [[ALLOW_ORIGIN, allowedOrigin]];
    if (this.isCredentialed(origin, allowedOrigin)) {
      rows.push([ALLOW_CREDENTIALS, "true"]);
    }
    if (!(this.anyOrigin && !this.credentials)) {
      rows.push(["Vary", "Origin"]);
    }
    return rows;
  }

  // Level 4
  allowPattern(pattern: string): boolean {
    const match = PATTERN.exec(pattern);
    if (match === null || !DEFAULT_PORTS.has(match[1].toLowerCase())) {
      return false;
    }
    const scheme = match[1].toLowerCase();
    const port = portSuffix(scheme, match[3] ?? "");
    if (port === null) {
      return false;
    }
    const compiled = new OriginPattern(scheme, match[2].toLowerCase(), port);
    if (this.patterns.has(compiled.text)) {
      return false;
    }
    this.patterns.set(compiled.text, compiled);
    return true;
  }

  lint(): string[][] {
    const findings: string[][] = [];
    for (const pattern of this.patterns.values()) {
      if (pattern.broad) {
        findings.push(["broad-pattern", pattern.text]);
      }
      if (this.credentials && !pattern.secure) {
        findings.push(["credentials-to-insecure-origin", pattern.text]);
      }
    }
    for (const origin of this.origins) {
      if (origin === OPAQUE) {
        findings.push(["null-origin-allowed", OPAQUE]);
      } else if (this.credentials && !SECURE_SCHEMES.has(origin.split("://")[0])) {
        findings.push(["credentials-to-insecure-origin", origin]);
      }
    }
    return findings.sort((a, b) => compareText(a[0], b[0]) || compareText(a[1], b[1]));
  }

  private isListed(origin: string): boolean {
    if (this.origins.has(origin)) {
      return true;
    }
    for (const pattern of this.patterns.values()) {
      if (pattern.matches(origin)) {
        return true;
      }
    }
    return false;
  }

  /** Credentials are allowed only next to the requesting origin itself, never next to *. */
  private isCredentialed(origin: string, allowedOrigin: string): boolean {
    return this.credentials && allowedOrigin !== "" && allowedOrigin !== WILDCARD && allowedOrigin === origin;
  }

  private isMethodAllowed(method: string, credentialed: boolean): boolean {
    if (SAFELISTED_METHODS.has(method) || this.methods.includes(method)) {
      return true;
    }
    return this.methods.includes(WILDCARD) && !credentialed;
  }

  private isHeaderAllowed(name: string, credentialed: boolean): boolean {
    if (this.headers.includes(name)) {
      return true;
    }
    return this.headers.includes(WILDCARD) && !credentialed && name !== "authorization";
  }
}

function compareText(a: string, b: string): number {
  return a < b ? -1 : a > b ? 1 : 0;
}
