import type { IsoDate } from "#support";

// Manifests are kept as trees by id, rules as data in the order they were added. A check expands
// each rule's pointer pattern over each manifest and tests the concrete pointers; a service's port
// rule looks up the workloads its selector picks. Exceptions, severities, modes and fixes are
// applied on top of the same list of violations.
const SEVERITY_RANK = new Map([
  ["critical", 0],
  ["high", 1],
  ["medium", 2],
  ["low", 3],
]);
const SEP = "\u0000";

class ValueNode {
  kind: string;
  text: string;
  members = new Map<string, ValueNode>();
  items: ValueNode[] = [];

  constructor(kind: string, text = "") {
    this.kind = kind;
    this.text = text;
  }
}

interface Rule {
  check: "field" | "tags" | "ports";
  kind: string;
  pointer: string;
  tags: string[];
  severity: string;
  mode: string;
  fix: string;
}

interface Allowance {
  reason: string;
  expires: IsoDate;
}

type Violation = [string, string, string];

function decode(rows: string[][]): ValueNode {
  const root = new ValueNode("object");
  for (const [pointer, kind, text] of rows) {
    const segments = pointer.split("/").slice(1);
    const last = segments.pop()!;
    let parent = root;
    for (const segment of segments) {
      parent = parent.kind === "object" ? parent.members.get(segment)! : parent.items[Number(segment)];
    }
    const node = new ValueNode(kind, text);
    if (parent.kind === "object") parent.members.set(last, node);
    else parent.items.push(node);
  }
  return root;
}

function resolve(root: ValueNode, pointer: string): ValueNode | undefined {
  let node: ValueNode | undefined = root;
  for (const segment of pointer === "" ? [] : pointer.split("/").slice(1)) {
    if (node === undefined) return undefined;
    if (node.kind === "object") node = node.members.get(segment);
    else if (node.kind === "array" && /^[0-9]+$/.test(segment)) node = node.items[Number(segment)];
    else return undefined;
  }
  return node;
}

function expand(root: ValueNode, pattern: string): string[] {
  let pointers = [""];
  for (const segment of pattern.split("/").slice(1)) {
    if (segment !== "*") {
      pointers = pointers.map((pointer) => `${pointer}/${segment}`);
      continue;
    }
    const expanded: string[] = [];
    for (const pointer of pointers) {
      const node = resolve(root, pointer);
      if (node !== undefined && node.kind === "array") {
        node.items.forEach((_, index) => expanded.push(`${pointer}/${index}`));
      }
    }
    pointers = expanded;
  }
  return pointers;
}

/** The repository and the tag of an image reference; the tag is null when there is none. */
function tagSplit(image: string): [string, string | null] {
  const colon = image.lastIndexOf(":");
  if (colon > image.lastIndexOf("/")) return [image.slice(0, colon), image.slice(colon + 1)];
  return [image, null];
}

function textOf(root: ValueNode, pointer: string): string | null {
  const node = resolve(root, pointer);
  return node !== undefined && node.kind === "string" ? node.text : null;
}

function compareText(a: string, b: string): number {
  return a < b ? -1 : a > b ? 1 : 0;
}

export class PolicyChecker {
  private readonly manifests = new Map<string, ValueNode>();
  private readonly rules = new Map<string, Rule>();
  private readonly allowances = new Map<string, Allowance>();

  // Level 1
  addManifest(rows: string[][]): boolean {
    const root = decode(rows);
    const id = `${textOf(root, "/kind")}/${textOf(root, "/name")}`;
    const isNew = !this.manifests.has(id);
    this.manifests.set(id, root);
    return isNew;
  }

  requireField(ruleId: string, kind: string, pointer: string): boolean {
    return this.define(ruleId, "field", kind, pointer, []);
  }

  forbidTags(ruleId: string, kind: string, pointer: string, tags: string[]): boolean {
    return this.define(ruleId, "tags", kind, pointer, tags);
  }

  check(): string[][] {
    return this.violations().map((violation) => [...violation]);
  }

  // Level 2
  requirePortTargets(ruleId: string): boolean {
    return this.define(ruleId, "ports", "service", "", []);
  }

  // Level 3
  allow(ruleId: string, manifestId: string, reason: string, expires: IsoDate): boolean {
    const key = ruleId + SEP + manifestId;
    const isNew = !this.allowances.has(key);
    this.allowances.set(key, { reason, expires });
    return isNew;
  }

  checkOn(today: IsoDate): string[][] {
    const rows: string[][] = this.violations().map(([manifestId, ruleId, pointer]) => {
      const allowance = this.active(ruleId, manifestId, today);
      return allowance === undefined
        ? [manifestId, ruleId, pointer, "violation", ""]
        : [manifestId, ruleId, pointer, "excepted", allowance.reason];
    });
    const expired: string[][] = [];
    for (const [key, allowance] of this.allowances) {
      const [ruleId, manifestId] = key.split(SEP);
      if (today > allowance.expires) expired.push([manifestId, ruleId, "", "expired", allowance.expires]);
    }
    expired.sort((a, b) => compareText(a[0], b[0]) || compareText(a[1], b[1]));
    return [...rows, ...expired];
  }

  // Level 4
  configure(ruleId: string, severity: string, mode: string, fix: string): boolean {
    const rule = this.rules.get(ruleId);
    if (rule === undefined) return false;
    rule.severity = severity;
    rule.mode = mode;
    rule.fix = fix;
    return true;
  }

  findings(today: IsoDate): string[][] {
    const rows: string[][] = [];
    for (const [manifestId, ruleId, pointer] of this.violations()) {
      if (this.active(ruleId, manifestId, today) !== undefined) continue;
      const rule = this.rules.get(ruleId)!;
      const [op, value] = fixFor(rule, this.manifests.get(manifestId)!, pointer);
      rows.push([manifestId, ruleId, pointer, rule.severity, rule.mode, op, value]);
    }
    return rows.sort((a, b) => SEVERITY_RANK.get(a[3])! - SEVERITY_RANK.get(b[3])!);
  }

  decide(today: IsoDate): string[][] {
    const counts = new Map<string, [number, number]>();
    for (const id of this.manifests.keys()) counts.set(id, [0, 0]);
    for (const row of this.findings(today)) counts.get(row[0])![row[4] === "deny" ? 0 : 1] += 1;
    return [...counts.keys()]
      .sort(compareText)
      .map((id) => {
        const [deny, warn] = counts.get(id)!;
        return [id, deny > 0 ? "reject" : "admit", String(deny), String(warn)];
      });
  }

  // Rules
  private define(ruleId: string, check: Rule["check"], kind: string, pointer: string, tags: string[]): boolean {
    const rule = this.rules.get(ruleId);
    if (rule === undefined) {
      this.rules.set(ruleId, { check, kind, pointer, tags: [...tags], severity: "medium", mode: "deny", fix: "" });
      return true;
    }
    rule.check = check;
    rule.kind = kind;
    rule.pointer = pointer;
    rule.tags = [...tags];
    return false;
  }

  private violations(): Violation[] {
    const found: Violation[] = [];
    for (const manifestId of [...this.manifests.keys()].sort(compareText)) {
      const root = this.manifests.get(manifestId)!;
      const kind = textOf(root, "/kind");
      for (const [ruleId, rule] of this.rules) {
        if (rule.kind !== "*" && rule.kind !== kind) continue;
        for (const pointer of this.broken(rule, root)) found.push([manifestId, ruleId, pointer]);
      }
    }
    return found;
  }

  private broken(rule: Rule, root: ValueNode): string[] {
    if (rule.check === "ports") return this.unservedPorts(root);
    return expand(root, rule.pointer).filter((pointer) => {
      const node = resolve(root, pointer);
      if (rule.check === "field") {
        return node === undefined || node.kind === "null" || (node.kind === "string" && node.text === "");
      }
      if (node === undefined || node.kind !== "string" || node.text.includes("@")) return false;
      const tag = tagSplit(node.text)[1];
      return tag === null || rule.tags.includes(tag);
    });
  }

  private unservedPorts(service: ValueNode): string[] {
    const selector = resolve(service, "/selector");
    if (selector === undefined || selector.kind !== "object" || selector.members.size === 0) return ["/selector"];
    const selected = [...this.manifests.values()].filter(
      (root) => textOf(root, "/kind") === "workload" && selects(selector, root),
    );
    if (selected.length === 0) return ["/selector"];
    const served = selected.map(
      (root) => new Set(expand(root, "/containers/*/ports/*/name").map((pointer) => textOf(root, pointer))),
    );
    const broken: string[] = [];
    for (const pointer of expand(service, "/ports/*")) {
      const target = textOf(service, `${pointer}/target`);
      if (target !== null && served.some((names) => !names.has(target))) broken.push(`${pointer}/target`);
    }
    return broken;
  }

  private active(ruleId: string, manifestId: string, today: IsoDate): Allowance | undefined {
    const allowance = this.allowances.get(ruleId + SEP + manifestId);
    return allowance !== undefined && today <= allowance.expires ? allowance : undefined;
  }
}

function selects(selector: ValueNode, workload: ValueNode): boolean {
  for (const [key, value] of selector.members) {
    if (value.kind !== "string" || textOf(workload, `/labels/${key}`) !== value.text) return false;
  }
  return true;
}

function fixFor(rule: Rule, root: ValueNode, pointer: string): [string, string] {
  if (rule.fix === "" || rule.check === "ports") return ["", ""];
  const node = resolve(root, pointer);
  if (rule.check === "tags") return ["replace", `${tagSplit(node!.text)[0]}:${rule.fix}`];
  if (node !== undefined) return ["replace", rule.fix];
  const parent = resolve(root, pointer.slice(0, pointer.lastIndexOf("/")));
  return parent !== undefined && parent.kind === "object" ? ["add", rule.fix] : ["", ""];
}
