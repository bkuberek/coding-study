const ALLOW = "allow";
const DENY = "deny";
const ASK = "ask";
const STRICTNESS: Record<string, number> = { allow: 0, ask: 1, deny: 2 };
const MAX_LINK_HOPS = 40;
const USER = "user";
const PATTERN = /^([a-z0-9_]+\*?|\*)$/;
const REQUEST_ID = /^[1-9][0-9]*$/;
const PORT = /^[0-9]*$/;
const HOST_CHARS = /^[a-z0-9.-]+$/;
const URL_START = /^(https?):\/\/([^/?#]*)/i;
const ANSWERS: Record<string, [string, string | null]> = {
  yes: [ALLOW, null],
  no: [DENY, null],
  "yes-tool": [ALLOW, "tool"],
  "no-tool": [DENY, "tool"],
  "yes-exact": [ALLOW, "exact"],
  "no-exact": [DENY, "exact"],
};

type Args = string[][];
type Rule = { effect: string; pattern: string };

interface Request {
  tool: string;
  args: Args;
  status: string;
}

interface Verdict {
  decision: string;
  reason: string;
  asks: boolean;
}

function matches(pattern: string, tool: string): boolean {
  return pattern.endsWith("*") ? tool.startsWith(pattern.slice(0, -1)) : pattern === tool;
}

// Exact names beat wildcards; a longer prefix beats a shorter one.
function specificity(pattern: string): [number, number] {
  return pattern.endsWith("*") ? [0, pattern.length - 1] : [1, pattern.length];
}

function compareRules(a: Rule, b: Rule): number {
  const [aExact, aLength] = specificity(a.pattern);
  const [bExact, bLength] = specificity(b.pattern);
  return (
    aExact - bExact || aLength - bLength || STRICTNESS[a.effect] - STRICTNESS[b.effect]
  );
}

// The lower-cased host of an http or https URL, or null when it cannot be trusted.
function hostOf(value: string): string | null {
  for (const ch of value) {
    const code = ch.charCodeAt(0);
    if (code <= 32 || code === 127 || ch === "\\") {
      return null;
    }
  }
  const found = URL_START.exec(value);
  if (found === null || found[2].split("@").length > 2) {
    return null;
  }
  const hostPort = found[2].slice(found[2].lastIndexOf("@") + 1);
  const colon = hostPort.indexOf(":");
  const port = colon < 0 ? "" : hostPort.slice(colon + 1);
  if (!PORT.test(port)) {
    return null;
  }
  let host = (colon < 0 ? hostPort : hostPort.slice(0, colon)).toLowerCase();
  if (host.endsWith(".")) {
    host = host.slice(0, -1);
  }
  return HOST_CHARS.test(host) ? host : null;
}

function hostAllowed(host: string, allowed: string[]): boolean {
  return allowed.some((entry) => {
    if (entry.startsWith("*.")) {
      return host.endsWith(entry.slice(1)) && host.length > entry.length - 1;
    }
    return host === entry;
  });
}

function sortedPairs(args: Args): [string, string][] {
  return args
    .map((row): [string, string] => [row[0], row[1]])
    .sort((a, b) => (a[0] < b[0] ? -1 : a[0] > b[0] ? 1 : a[1] < b[1] ? -1 : a[1] > b[1] ? 1 : 0));
}

function keyOf(args: Args): string {
  return JSON.stringify(sortedPairs(args));
}

function render(args: Args): string {
  return sortedPairs(args)
    .map(([name, value]) => `${name}=${value}`)
    .join(";");
}

export class PermissionGate {
  private readonly rules: Rule[] = [];
  private readonly scopes = new Map<string, Map<string, [string, string[]]>>();
  private readonly aliases = new Map<string, string>();
  private readonly readOnly = new Set<string>();
  private readonly risks: [string, string, string][] = [];
  private readonly rememberedExact = new Map<string, string>();
  private readonly rememberedTool = new Map<string, string>();
  private readonly requests: Request[] = [];
  private readonly audit: string[][] = [];

  // Level 1
  addRule(effect: string, pattern: string): boolean {
    if (this.rules.some((rule) => rule.effect === effect && rule.pattern === pattern)) {
      return false;
    }
    this.rules.push({ effect, pattern });
    return true;
  }

  removeRule(effect: string, pattern: string): boolean {
    const index = this.rules.findIndex((rule) => rule.effect === effect && rule.pattern === pattern);
    if (index < 0) {
      return false;
    }
    this.rules.splice(index, 1);
    return true;
  }

  decide(tool: string): string {
    return this.bestRule(tool)?.effect ?? ASK;
  }

  // Level 2
  setScope(tool: string, param: string, kind: string, allowed: string[]): void {
    const scopes = this.scopes.get(tool) ?? new Map<string, [string, string[]]>();
    scopes.set(param, [kind, [...allowed]]);
    this.scopes.set(tool, scopes);
  }

  addAlias(link: string, target: string): void {
    this.aliases.set(link, target);
  }

  check(tool: string, args: Args): string {
    const verdict = this.judge(tool, args, true);
    let request = "";
    if (verdict.decision === ASK) {
      this.requests.push({ tool, args: args.map((row) => [...row]), status: "pending" });
      request = String(this.requests.length);
    }
    this.log("check", tool, render(args), verdict.decision, verdict.reason, request);
    return verdict.decision;
  }

  // Level 3
  markReadOnly(tool: string): boolean {
    if (this.readOnly.has(tool)) {
      return false;
    }
    this.readOnly.add(tool);
    return true;
  }

  addRisk(tool: string, param: string, text: string): boolean {
    if (this.risks.some((risk) => risk[0] === tool && risk[1] === param && risk[2] === text)) {
      return false;
    }
    this.risks.push([tool, param, text]);
    return true;
  }

  remember(tool: string, args: Args, decision: string, scope: string): boolean {
    if (!this.judge(tool, args, false).asks) {
      return false;
    }
    if (scope === "tool") {
      this.rememberedTool.set(tool, decision);
    } else {
      this.rememberedExact.set(JSON.stringify([tool, keyOf(args)]), decision);
    }
    return true;
  }

  endSession(): void {
    this.rememberedExact.clear();
    this.rememberedTool.clear();
  }

  // Level 4
  receive(channel: string, text: string): string {
    const [outcome, reason, request] = this.interpret(channel, text);
    this.log("receive", channel, text, outcome, reason, request);
    return outcome;
  }

  status(request: number): string {
    if (request < 1 || request > this.requests.length) {
      return "unknown";
    }
    return this.requests[request - 1].status;
  }

  auditLog(): string[][] {
    return this.audit;
  }

  private bestRule(tool: string): Rule | undefined {
    let best: Rule | undefined;
    for (const rule of this.rules) {
      if (matches(rule.pattern, tool) && (best === undefined || compareRules(rule, best) > 0)) {
        best = rule;
      }
    }
    return best;
  }

  // The decision for a call and the reason; `asks` says that only the user can settle it.
  private judge(tool: string, args: Args, useMemory: boolean): Verdict {
    const violated = this.scopeViolation(tool, args);
    if (violated !== "") {
      return { decision: DENY, reason: `scope:${violated}`, asks: false };
    }
    const rule = this.bestRule(tool);
    if (rule?.effect === DENY) {
      return { decision: DENY, reason: `rule:${DENY}:${rule.pattern}`, asks: false };
    }
    const risk = this.riskParam(tool, args);
    let base: Verdict;
    if (risk !== "") {
      base = { decision: ASK, reason: `risk:${risk}`, asks: true };
    } else if (rule?.effect === ALLOW) {
      return { decision: ALLOW, reason: `rule:${ALLOW}:${rule.pattern}`, asks: false };
    } else if (rule !== undefined) {
      base = { decision: ASK, reason: `rule:${ASK}:${rule.pattern}`, asks: true };
    } else if (this.readOnly.has(tool)) {
      return { decision: ALLOW, reason: "read-only", asks: false };
    } else {
      base = { decision: ASK, reason: "default", asks: true };
    }
    if (!useMemory) {
      return base;
    }
    const exact = this.rememberedExact.get(JSON.stringify([tool, keyOf(args)]));
    if (exact !== undefined) {
      return { decision: exact, reason: "remembered:exact", asks: false };
    }
    const wide = this.rememberedTool.get(tool);
    if (wide !== undefined && (wide === DENY || risk === "")) {
      return { decision: wide, reason: "remembered:tool", asks: false };
    }
    return base;
  }

  private riskParam(tool: string, args: Args): string {
    const values = new Map(args.map((row): [string, string] => [row[0], row[1]]));
    const hits = this.risks
      .filter(([riskTool, param, text]) => riskTool === tool && (values.get(param) ?? "").includes(text))
      .map(([, param]) => param)
      .sort();
    return hits.length > 0 ? hits[0] : "";
  }

  private scopeViolation(tool: string, args: Args): string {
    const scopes = this.scopes.get(tool);
    if (scopes === undefined) {
      return "";
    }
    const values = new Map(args.map((row): [string, string] => [row[0], row[1]]));
    for (const param of [...scopes.keys()].sort()) {
      const [kind, allowed] = scopes.get(param) as [string, string[]];
      const value = values.get(param);
      if (value === undefined) {
        return param;
      }
      let inside: boolean;
      if (kind === "path") {
        inside = this.pathUnder(value, allowed);
      } else {
        const host = hostOf(value);
        inside = host !== null && hostAllowed(host, allowed);
      }
      if (!inside) {
        return param;
      }
    }
    return "";
  }

  // The components of an absolute path with `.`, `..` and aliases resolved, as a file system
  // would: an alias is replaced by its target as soon as it is reached, so a `..` that follows it
  // applies to the target.
  private resolve(path: string): string[] | null {
    if (!path.startsWith("/")) {
      return null;
    }
    let pending = path.split("/");
    let resolved: string[] = [];
    let hops = 0;
    while (pending.length > 0) {
      const part = pending.shift() as string;
      if (part === "" || part === ".") {
        continue;
      }
      if (part === "..") {
        resolved.pop();
        continue;
      }
      resolved.push(part);
      const target = this.aliases.get(`/${resolved.join("/")}`);
      if (target !== undefined) {
        hops += 1;
        if (hops > MAX_LINK_HOPS) {
          return null;
        }
        pending = [...target.split("/"), ...pending];
        resolved = [];
      }
    }
    return resolved;
  }

  private pathUnder(value: string, roots: string[]): boolean {
    const resolved = this.resolve(value);
    if (resolved === null) {
      return false;
    }
    return roots.some((root) => {
      const base = this.resolve(root);
      return base !== null && base.every((part, i) => resolved[i] === part);
    });
  }

  private interpret(channel: string, text: string): [string, string, string] {
    if (channel !== USER) {
      return ["ignored", "untrusted-channel", ""];
    }
    const words = text.split(" ");
    if (words.length !== 2 || words[1] === "") {
      return ["ignored", "not-a-directive", ""];
    }
    const [verb, argument] = words;
    if (Object.hasOwn(STRICTNESS, verb) && PATTERN.test(argument)) {
      return this.addRule(verb, argument)
        ? ["applied", "rule-added", ""]
        : ["ignored", "no-change", ""];
    }
    if (Object.hasOwn(ANSWERS, verb) && REQUEST_ID.test(argument)) {
      return this.answer(verb, argument);
    }
    return ["ignored", "not-a-directive", ""];
  }

  // `requestText` is a valid number written in decimal; it is logged as written, so a number too
  // large for a double is not rounded.
  private answer(verb: string, requestText: string): [string, string, string] {
    const requestId = Number(requestText);
    if (this.status(requestId) !== "pending") {
      return ["ignored", "not-pending", requestText];
    }
    const [decision, scope] = ANSWERS[verb];
    const request = this.requests[requestId - 1];
    request.status = decision;
    if (scope === null) {
      return ["applied", "answered", requestText];
    }
    const remembered = this.remember(request.tool, request.args, decision, scope);
    return ["applied", remembered ? `answered:${scope}` : "answered", requestText];
  }

  private log(
    kind: string,
    subject: string,
    detail: string,
    outcome: string,
    reason: string,
    request: string,
  ): void {
    this.audit.push([String(this.audit.length + 1), kind, subject, detail, outcome, reason, request]);
  }
}
