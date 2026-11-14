// Layers are kept as given and merged on demand, oldest first, with the rules of RFC 7396. Every
// node of the merged tree remembers the layer that set it. A template is parsed in one
// left-to-right pass into a tree of text, substitutions, conditionals and loops, and rendered with
// a stack of loop bindings that shadow the values.
const KEY = /^[A-Za-z_][A-Za-z0-9_]*$/;
const INDEX = /^(0|[1-9][0-9]*)$/;
const SEGMENT = "(?:[A-Za-z_][A-Za-z0-9_]*|0|[1-9][0-9]*)";
const PATH = new RegExp(`^${SEGMENT}(?:\\.${SEGMENT})*$`);
const WORD = /[A-Za-z0-9_.]/;
const BLOCK_WORDS = new Set(["if", "else", "end", "for"]);
const RESERVED = new Set(["if", "else", "end", "for", "in"]);

class ValueNode {
  kind: string;
  text: string;
  layer: string;
  members = new Map<string, ValueNode>();
  items: ValueNode[] = [];

  constructor(kind: string, text = "", layer = "") {
    this.kind = kind;
    this.text = text;
    this.layer = layer;
  }

  copy(layer: string): ValueNode {
    const twin = new ValueNode(this.kind, this.text, layer);
    for (const [key, child] of this.members) twin.members.set(key, child.copy(layer));
    twin.items = this.items.map((child) => child.copy(layer));
    return twin;
  }
}

class TemplateError extends Error {
  code: string;
  position: number;
  detail: string;

  constructor(code: string, position: number, detail = "") {
    super(code);
    this.code = code;
    this.position = position;
    this.detail = detail;
  }
}

type Token = { kind: "word" | "string" | "punct"; value: string };

type Tag =
  | { kind: "text"; text: string }
  | { kind: "out"; path: string; fallback: string | null }
  | { kind: "if"; path: string }
  | { kind: "else" }
  | { kind: "end" }
  | { kind: "for"; names: string[]; path: string };

type Segment = string | { tag: Tag; at: number; trimLeft: boolean; trimRight: boolean };

type Part =
  | string
  | { kind: "out"; path: string; fallback: string | null; at: number }
  | IfPart
  | ForPart;

type IfPart = { kind: "if"; path: string; then: Part[]; otherwise: Part[]; at: number };
type ForPart = { kind: "for"; names: string[]; path: string; body: Part[]; at: number };

type Binding = [string, ValueNode];

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

function sortedKeys(node: ValueNode): string[] {
  return [...node.members.keys()].sort((a, b) => (a < b ? -1 : a > b ? 1 : 0));
}

function walk(node: ValueNode, pointer: string, visit: (pointer: string, node: ValueNode) => void): void {
  if (node.kind === "object") {
    for (const key of sortedKeys(node)) {
      const child = node.members.get(key)!;
      visit(`${pointer}/${key}`, child);
      walk(child, `${pointer}/${key}`, visit);
    }
  } else if (node.kind === "array") {
    node.items.forEach((child, index) => {
      visit(`${pointer}/${index}`, child);
      walk(child, `${pointer}/${index}`, visit);
    });
  }
}

function mergeInto(target: ValueNode, patch: ValueNode, layer: string): void {
  for (const [key, value] of patch.members) {
    if (value.kind === "null") {
      target.members.delete(key);
    } else if (value.kind === "object") {
      let current = target.members.get(key);
      if (current === undefined || current.kind !== "object") {
        current = new ValueNode("object", "", layer);
        target.members.set(key, current);
      }
      mergeInto(current, value, layer);
    } else {
      target.members.set(key, value.copy(layer));
    }
  }
}

function tokenize(body: string, position: number): Token[] {
  const tokens: Token[] = [];
  let i = 0;
  while (i < body.length) {
    const c = body[i];
    if (c === " ") {
      i += 1;
    } else if (c === "|" || c === ",") {
      tokens.push({ kind: "punct", value: c });
      i += 1;
    } else if (c === '"') {
      let text = "";
      i += 1;
      for (;;) {
        if (i >= body.length) throw new TemplateError("bad_expression", position);
        const d = body[i];
        if (d === '"') break;
        if (d === "\\") {
          const next = body[i + 1];
          if (next !== '"' && next !== "\\") throw new TemplateError("bad_expression", position);
          text += next;
          i += 2;
        } else {
          text += d;
          i += 1;
        }
      }
      tokens.push({ kind: "string", value: text });
      i += 1;
    } else if (WORD.test(c)) {
      const start = i;
      while (i < body.length && WORD.test(body[i])) i += 1;
      tokens.push({ kind: "word", value: body.slice(start, i) });
    } else {
      throw new TemplateError("bad_expression", position);
    }
  }
  return tokens;
}

function shapeOf(tokens: Token[]): string {
  return tokens.map((token) => token.kind).join(" ");
}

function classify(tokens: Token[], position: number): Tag {
  const shape = shapeOf(tokens);
  const words = tokens.map((token) => token.value);
  if (tokens.length > 0 && tokens[0].kind === "word" && BLOCK_WORDS.has(words[0])) {
    return classifyBlock(shape, words, position);
  }
  if (shape === "string") return { kind: "text", text: words[0] };
  if (shape === "word" && PATH.test(words[0])) return { kind: "out", path: words[0], fallback: null };
  if (shape === "word punct word string" && PATH.test(words[0]) && words[1] === "|" && words[2] === "default") {
    return { kind: "out", path: words[0], fallback: words[3] };
  }
  throw new TemplateError("bad_expression", position);
}

function classifyBlock(shape: string, words: string[], position: number): Tag {
  const head = words[0];
  if (head === "else" && words.length === 1) return { kind: "else" };
  if (head === "end" && words.length === 1) return { kind: "end" };
  if (head === "if" && shape === "word word" && PATH.test(words[1])) return { kind: "if", path: words[1] };
  if (head === "for") {
    let names: string[] = [];
    if (shape === "word word word word" && words[2] === "in") names = [words[1]];
    if (shape === "word word punct word word word" && words[2] === "," && words[4] === "in") {
      names = [words[1], words[3]];
    }
    const valid = names.every((name) => KEY.test(name) && !RESERVED.has(name));
    if (names.length > 0 && valid && new Set(names).size === names.length && PATH.test(words[words.length - 1])) {
      return { kind: "for", names, path: words[words.length - 1] };
    }
  }
  throw new TemplateError("bad_expression", position);
}

function parse(template: string): Part[] {
  const segments: Segment[] = [];
  const stack: Array<{ kind: string; at: number; hasElse: boolean }> = [];
  let i = 0;
  for (;;) {
    const start = template.indexOf("{{", i);
    if (start < 0) {
      segments.push(template.slice(i));
      break;
    }
    segments.push(template.slice(i, start));
    const end = template.indexOf("}}", start + 2);
    if (end < 0) throw new TemplateError("unclosed_tag", start);
    let body = template.slice(start + 2, end);
    const trimLeft = body.startsWith("-");
    if (trimLeft) body = body.slice(1);
    const trimRight = body.endsWith("-");
    if (trimRight) body = body.slice(0, -1);
    const tag = classify(tokenize(body.replace(/^ +| +$/g, ""), start), start);
    if (tag.kind === "if" || tag.kind === "for") {
      stack.push({ kind: tag.kind, at: start, hasElse: false });
    } else if (tag.kind === "else") {
      const top = stack[stack.length - 1];
      if (top === undefined || top.kind !== "if" || top.hasElse) throw new TemplateError("unexpected_tag", start);
      top.hasElse = true;
    } else if (tag.kind === "end") {
      if (stack.length === 0) throw new TemplateError("unexpected_tag", start);
      stack.pop();
    }
    segments.push({ tag, at: start, trimLeft, trimRight });
    i = end + 2;
  }
  if (stack.length > 0) throw new TemplateError("unclosed_block", stack[stack.length - 1].at);
  segments.forEach((segment, index) => {
    if (typeof segment === "string") return;
    if (segment.trimLeft) segments[index - 1] = (segments[index - 1] as string).replace(/[ \n]+$/, "");
    if (segment.trimRight) segments[index + 1] = (segments[index + 1] as string).replace(/^[ \n]+/, "");
  });
  return build(segments);
}

function build(segments: Segment[]): Part[] {
  const root: Part[] = [];
  const stack: Array<{ node: IfPart | ForPart; outer: Part[] }> = [];
  let current = root;
  for (const segment of segments) {
    if (typeof segment === "string") {
      if (segment !== "") current.push(segment);
      continue;
    }
    const { tag, at } = segment;
    if (tag.kind === "if") {
      const node: IfPart = { kind: "if", path: tag.path, then: [], otherwise: [], at };
      current.push(node);
      stack.push({ node, outer: current });
      current = node.then;
    } else if (tag.kind === "for") {
      const node: ForPart = { kind: "for", names: tag.names, path: tag.path, body: [], at };
      current.push(node);
      stack.push({ node, outer: current });
      current = node.body;
    } else if (tag.kind === "else") {
      const top = stack[stack.length - 1].node;
      if (top.kind === "if") current = top.otherwise;
    } else if (tag.kind === "end") {
      current = stack.pop()!.outer;
    } else if (tag.kind === "text") {
      current.push(tag.text);
    } else {
      current.push({ kind: "out", path: tag.path, fallback: tag.fallback, at });
    }
  }
  return root;
}

function lineAndColumn(template: string, position: number): string {
  const before = template.slice(0, position);
  const line = before.split("\n").length;
  const column = position - (before.lastIndexOf("\n") + 1) + 1;
  return `${line}:${column}`;
}

function truthy(node: ValueNode | null): boolean {
  if (node === null) return false;
  switch (node.kind) {
    case "boolean":
      return node.text === "true";
    case "string":
      return node.text !== "";
    case "number":
      return node.text !== "0";
    case "object":
      return node.members.size > 0;
    default:
      return node.items.length > 0;
  }
}

function lookup(path: string, values: ValueNode, scope: Binding[]): ValueNode | null {
  let segments = path.split(".");
  let current: ValueNode | undefined = values;
  for (let i = scope.length - 1; i >= 0; i--) {
    if (scope[i][0] === segments[0]) {
      current = scope[i][1];
      segments = segments.slice(1);
      break;
    }
  }
  for (const segment of segments) {
    if (current === undefined) return null;
    if (current.kind === "object") current = current.members.get(segment);
    else if (current.kind === "array" && INDEX.test(segment)) current = current.items[Number(segment)];
    else return null;
  }
  return current === undefined || current.kind === "null" ? null : current;
}

function emit(parts: Part[], values: ValueNode, scope: Binding[], out: string[]): void {
  for (const part of parts) {
    if (typeof part === "string") {
      out.push(part);
    } else if (part.kind === "out") {
      const found = lookup(part.path, values, scope);
      if (found === null) {
        if (part.fallback === null) throw new TemplateError("missing_value", part.at, part.path);
        out.push(part.fallback);
      } else if (found.kind === "object" || found.kind === "array") {
        throw new TemplateError("not_scalar", part.at, part.path);
      } else {
        out.push(found.text);
      }
    } else if (part.kind === "if") {
      emit(truthy(lookup(part.path, values, scope)) ? part.then : part.otherwise, values, scope, out);
    } else {
      loop(part, values, scope, out);
    }
  }
}

function loop(part: ForPart, values: ValueNode, scope: Binding[], out: string[]): void {
  const found = lookup(part.path, values, scope);
  if (found === null) throw new TemplateError("missing_value", part.at, part.path);
  let pairs: Array<[ValueNode, ValueNode]>;
  if (found.kind === "array") {
    pairs = found.items.map((item, i) => [new ValueNode("number", String(i)), item]);
  } else if (found.kind === "object") {
    pairs = sortedKeys(found).map((key) => [new ValueNode("string", key), found.members.get(key)!]);
  } else {
    throw new TemplateError("not_iterable", part.at, part.path);
  }
  for (const [key, item] of pairs) {
    const bound: Binding[] =
      part.names.length === 2 ? [[part.names[0], key], [part.names[1], item]] : [[part.names[0], item]];
    emit(part.body, values, [...scope, ...bound], out);
  }
}

function hasType(node: ValueNode, name: string): boolean {
  return node.kind === name || (name === "integer" && node.kind === "number");
}

function isListed(node: ValueNode, options: ValueNode): boolean {
  if (node.kind === "object" || node.kind === "array") return false;
  return options.items.some((option) => option.kind === node.kind && option.text === node.text);
}

function check(node: ValueNode, schema: ValueNode, pointer: string, errors: string[][]): void {
  const keywords = schema.members;
  const type = keywords.get("type");
  if (type !== undefined && !hasType(node, type.text)) errors.push([pointer, "type", node.layer]);
  const options = keywords.get("enum");
  if (options !== undefined && !isListed(node, options)) errors.push([pointer, "enum", node.layer]);
  if (node.kind === "number") {
    const minimum = keywords.get("minimum");
    if (minimum !== undefined && Number(node.text) < Number(minimum.text)) errors.push([pointer, "minimum", node.layer]);
    const maximum = keywords.get("maximum");
    if (maximum !== undefined && Number(node.text) > Number(maximum.text)) errors.push([pointer, "maximum", node.layer]);
  }
  if (node.kind === "object") {
    const properties = keywords.get("properties")?.members ?? new Map<string, ValueNode>();
    for (const key of keywords.get("required")?.items ?? []) {
      if (!node.members.has(key.text)) errors.push([`${pointer}/${key.text}`, "required", ""]);
    }
    const closed = keywords.get("additionalProperties")?.text === "false";
    for (const [key, child] of node.members) {
      const sub = properties.get(key);
      if (sub !== undefined) check(child, sub, `${pointer}/${key}`, errors);
      else if (closed) errors.push([`${pointer}/${key}`, "additionalProperties", child.layer]);
    }
  }
  const items = keywords.get("items");
  if (node.kind === "array" && items !== undefined) {
    node.items.forEach((child, index) => check(child, items, `${pointer}/${index}`, errors));
  }
}

function compareText(a: string, b: string): number {
  return a < b ? -1 : a > b ? 1 : 0;
}

export class ValuesRenderer {
  private readonly layers = new Map<string, ValueNode>();
  private schema = new ValueNode("object");

  // Level 1
  setLayer(name: string, rows: string[][]): boolean {
    const isNew = !this.layers.has(name);
    this.layers.set(name, decode(rows));
    return isNew;
  }

  merged(): string[][] {
    const rows: string[][] = [];
    walk(this.merge(), "", (pointer, node) => rows.push([pointer, node.kind, node.text]));
    return rows;
  }

  // Level 2 and 3
  render(template: string): string[] {
    const values = this.merge();
    const errors = this.errors(values);
    if (errors.length > 0) return ["error", "invalid_values", "", String(errors.length)];
    try {
      const out: string[] = [];
      emit(parse(template), values, [], out);
      return ["ok", out.join("")];
    } catch (error) {
      if (!(error instanceof TemplateError)) throw error;
      return ["error", error.code, lineAndColumn(template, error.position), error.detail];
    }
  }

  // Level 4
  setSchema(rows: string[][]): void {
    this.schema = decode(rows);
  }

  validate(): string[][] {
    return this.errors(this.merge());
  }

  provenance(): string[][] {
    const rows: string[][] = [];
    walk(this.merge(), "", (pointer, node) => rows.push([pointer, node.layer]));
    return rows;
  }

  private merge(): ValueNode {
    const root = new ValueNode("object");
    for (const [name, layer] of this.layers) mergeInto(root, layer, name);
    return root;
  }

  private errors(values: ValueNode): string[][] {
    const errors: string[][] = [];
    check(values, this.schema, "", errors);
    return errors.sort((a, b) => compareText(a[0], b[0]) || compareText(a[1], b[1]));
  }
}
