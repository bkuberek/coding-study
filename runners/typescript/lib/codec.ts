// JSON encodings of the type DSL (docs/specs/problem-format.md#type-mapping and
// #serialization-of-linked-structures). Inputs are trusted (the CLI validates content); outputs
// come from user code, so every encoder checks the value and throws InvalidOutput with a reason.
// Node objects are duck-typed: any object with the right fields is accepted.

import { GraphNode, ListNode, TreeNode } from "../support.ts";
import type { NodeKind, Scalar, TypeSpec } from "./types.ts";

export const MAX_LIST_NODES = 100_000;
const INT_MIN = -(2 ** 31);
const INT_MAX = 2 ** 31 - 1;
const QUOTED_STRING_LIMIT = 40;

/** A return value that cannot be serialized as the declared type. */
export class InvalidOutput extends Error {}

/** A case input that does not fit its declared type (a content error, not a user error). */
export class InvalidInput extends Error {}

type NodeObject = Record<string, unknown>;

interface ScalarRule {
  readonly accepts: (value: unknown) => boolean;
  readonly expected: string;
}

const SCALAR_RULES: Readonly<Record<Scalar, ScalarRule>> = {
  int: { accepts: isInt, expected: "an int (32-bit integer)" },
  long: {
    accepts: Number.isSafeInteger,
    expected: "a long (integer of magnitude at most 2^53-1)",
  },
  double: {
    accepts: (value) => typeof value === "number" && Number.isFinite(value),
    expected: "a finite double",
  },
  bool: { accepts: (value) => typeof value === "boolean", expected: "a bool" },
  string: {
    accepts: (value) => typeof value === "string",
    expected: "a string",
  },
  char: {
    accepts: (value) => typeof value === "string" && value.length === 1,
    expected: "a char (string of length 1)",
  },
};

const NODE_FIELDS: Readonly<Record<NodeKind, readonly string[]>> = {
  ListNode: ["next"],
  TreeNode: ["left", "right"],
  GraphNode: ["neighbors"],
};

export function decode(json: unknown, spec: TypeSpec): unknown {
  switch (spec.kind) {
    case "array":
      return requireInputArray(json, spec).map((element) =>
        decode(element, spec.element),
      );
    case "node":
      return NODE_DECODERS[spec.node](json);
    default:
      return json;
  }
}

export function encode(value: unknown, spec: TypeSpec, path = ""): unknown {
  switch (spec.kind) {
    case "scalar":
      return encodeScalar(value, spec.scalar, path);
    case "array":
      return encodeArray(value, spec, path);
    case "node":
      return NODE_ENCODERS[spec.node](value, path);
    case "void":
      return null;
  }
}

/** The `as: value` modifier: the node's `val`, or null. */
export function encodeNodeValue(
  value: unknown,
  typeText: string,
): number | null {
  const node = nullableNode(value, typeText, "");
  return node === null ? null : nodeVal(node, "");
}

/**
 * Every node object reachable from `value`, each once, in traversal order: `next` order for
 * lists, level order for trees, breadth-first `neighbors` order for graphs, and element order
 * for arrays of nodes. Defines `ref_of` and `as: index` positions and `no_alias_with` checks.
 */
export function traverse(value: unknown, spec: TypeSpec): readonly object[] {
  const visited = new Set<object>();
  collect(value, spec, visited);
  return [...visited];
}

const NODE_DECODERS: Readonly<Record<NodeKind, (json: unknown) => unknown>> = {
  ListNode: decodeListNode,
  TreeNode: decodeTreeNode,
  GraphNode: decodeGraphNode,
};

const NODE_ENCODERS: Readonly<
  Record<NodeKind, (value: unknown, path: string) => unknown>
> = {
  ListNode: encodeListNode,
  TreeNode: encodeTreeNode,
  GraphNode: encodeGraphNode,
};

function decodeListNode(json: unknown): ListNode | null {
  const cyclic =
    !Array.isArray(json) && typeof json === "object" && json !== null;
  const encoding = cyclic
    ? (json as { values: unknown; cycle_at: unknown })
    : { values: json, cycle_at: -1 };
  const values = requireInputArray(encoding.values, "ListNode");
  const nodes = values.map((value) => new ListNode(value as number));
  nodes.forEach((node, index) => {
    node.next = nodes[index + 1] ?? null;
  });
  const cycleAt = encoding.cycle_at as number;
  const tail = nodes.at(-1);
  if (tail !== undefined && cycleAt >= 0) {
    tail.next = nodes[cycleAt] ?? null;
  }
  return nodes[0] ?? null;
}

function decodeTreeNode(json: unknown): TreeNode | null {
  const values = requireInputArray(json, "TreeNode");
  const root = treeChild(values[0]);
  if (root === null) {
    return null;
  }
  const parents = [root];
  let next = 1;
  for (let index = 0; index < parents.length && next < values.length; index++) {
    const parent = parents[index] as TreeNode;
    parent.left = treeChild(values[next++]);
    parent.right = next < values.length ? treeChild(values[next++]) : null;
    for (const child of [parent.left, parent.right]) {
      if (child !== null) {
        parents.push(child);
      }
    }
  }
  return root;
}

function treeChild(value: unknown): TreeNode | null {
  return value === null || value === undefined
    ? null
    : new TreeNode(value as number);
}

function decodeGraphNode(json: unknown): GraphNode | null {
  const adjacency = requireInputArray(json, "GraphNode").map((row) =>
    requireInputArray(row, "GraphNode"),
  );
  const nodes = adjacency.map((_, index) => new GraphNode(index + 1));
  adjacency.forEach((neighbors, index) => {
    (nodes[index] as GraphNode).neighbors = neighbors.map((value) =>
      graphNode(nodes, value),
    );
  });
  return nodes[0] ?? null;
}

function graphNode(nodes: readonly GraphNode[], value: unknown): GraphNode {
  const node = nodes[(value as number) - 1];
  if (node === undefined) {
    throw new InvalidInput(
      `GraphNode neighbor ${String(value)} is not between 1 and ${nodes.length}`,
    );
  }
  return node;
}

function requireInputArray(
  json: unknown,
  spec: TypeSpec | NodeKind,
): readonly unknown[] {
  if (!Array.isArray(json)) {
    const type = typeof spec === "string" ? spec : spec.text;
    throw new InvalidInput(
      `expected a JSON array for ${type}, got ${describe(json)}`,
    );
  }
  return json;
}

function encodeScalar(value: unknown, scalar: Scalar, path: string): unknown {
  const rule = SCALAR_RULES[scalar];
  if (!rule.accepts(value)) {
    fail(`expected ${rule.expected}, got ${describe(value)}`, path);
  }
  return value;
}

function encodeArray(
  value: unknown,
  spec: TypeSpec & { kind: "array" },
  path: string,
): unknown[] {
  if (!Array.isArray(value)) {
    fail(`expected ${spec.text} (an array), got ${describe(value)}`, path);
  }
  const encoded: unknown[] = [];
  for (let index = 0; index < value.length; index++) {
    encoded.push(encode(value[index], spec.element, `${path}[${index}]`));
  }
  return encoded;
}

function encodeListNode(value: unknown, path: string): number[] {
  const values: number[] = [];
  for (
    let node = nullableNode(value, "ListNode", path);
    node !== null;
    node = link(node, "next", "ListNode", path)
  ) {
    if (values.length === MAX_LIST_NODES) {
      fail("list too long or cyclic", path);
    }
    values.push(nodeVal(node, path));
  }
  return values;
}

function encodeTreeNode(value: unknown, path: string): (number | null)[] {
  const root = nullableNode(value, "TreeNode", path);
  const queue: (NodeObject | null)[] = [root];
  const seen = new Set<object>(root === null ? [] : [root]);
  const values: (number | null)[] = [];
  for (let index = 0; index < queue.length; index++) {
    const node = queue[index] ?? null;
    if (node === null) {
      values.push(null);
      continue;
    }
    values.push(nodeVal(node, path));
    for (const child of [
      link(node, "left", "TreeNode", path),
      link(node, "right", "TreeNode", path),
    ]) {
      if (child !== null && seen.has(child)) {
        fail("tree has a cycle or a node with two parents", path);
      }
      if (child !== null) {
        seen.add(child);
      }
      queue.push(child);
    }
  }
  while (values.at(-1) === null) {
    values.pop();
  }
  return values;
}

function encodeGraphNode(value: unknown, path: string): number[][] {
  const start = nullableNode(value, "GraphNode", path);
  if (start === null) {
    return [];
  }
  const reachable = [start];
  const seen = new Set<object>(reachable);
  for (let index = 0; index < reachable.length; index++) {
    for (const neighbor of neighbors(reachable[index] as NodeObject, path)) {
      if (!seen.has(neighbor)) {
        seen.add(neighbor);
        reachable.push(neighbor);
      }
    }
  }
  const byVal = graphNodesByVal(reachable, path);
  return byVal.map((node) =>
    neighbors(node, path).map((neighbor) => neighbor["val"] as number),
  );
}

function graphNodesByVal(
  nodes: readonly NodeObject[],
  path: string,
): NodeObject[] {
  const byVal = new Array<NodeObject | undefined>(nodes.length).fill(undefined);
  for (const node of nodes) {
    const val = nodeVal(node, path);
    if (val < 1 || val > nodes.length || byVal[val - 1] !== undefined) {
      fail(
        `graph node vals must be exactly 1..${nodes.length} (one per reachable node), found ${val}`,
        path,
      );
    }
    byVal[val - 1] = node;
  }
  return byVal as NodeObject[];
}

function neighbors(node: NodeObject, path: string): NodeObject[] {
  const linked = node["neighbors"] ?? [];
  if (!Array.isArray(linked)) {
    fail(
      `expected GraphNode.neighbors to be an array, got ${describe(linked)}`,
      path,
    );
  }
  return linked.map((neighbor: unknown) => {
    if (!isObject(neighbor)) {
      fail(
        `expected a GraphNode in neighbors, got ${describe(neighbor)}`,
        path,
      );
    }
    return neighbor;
  });
}

function nullableNode(
  value: unknown,
  typeText: string,
  path: string,
): NodeObject | null {
  if (value === null) {
    return null;
  }
  if (!isObject(value)) {
    fail(`expected ${typeText} or null, got ${describe(value)}`, path);
  }
  return value;
}

/** A node's `next`, `left` or `right`; a missing field counts as null. */
function link(
  node: NodeObject,
  field: string,
  typeText: string,
  path: string,
): NodeObject | null {
  const linked = node[field];
  return linked === undefined ? null : nullableNode(linked, typeText, path);
}

function nodeVal(node: NodeObject, path: string): number {
  const val = node["val"];
  if (!isInt(val)) {
    fail(`expected node val to be an int, got ${describe(val)}`, path);
  }
  return val;
}

function collect(value: unknown, spec: TypeSpec, visited: Set<object>): void {
  if (spec.kind === "array" && Array.isArray(value)) {
    value.forEach((element: unknown) =>
      collect(element, spec.element, visited),
    );
  }
  if (spec.kind === "node" && isObject(value)) {
    collectNodes(value, NODE_FIELDS[spec.node], visited);
  }
}

function collectNodes(
  start: NodeObject,
  fields: readonly string[],
  visited: Set<object>,
): void {
  const queue = visited.has(start) ? [] : [start];
  queue.forEach((node) => visited.add(node));
  for (let index = 0; index < queue.length; index++) {
    for (const linked of linkedNodes(queue[index] as NodeObject, fields)) {
      if (!visited.has(linked)) {
        visited.add(linked);
        queue.push(linked);
      }
    }
  }
}

function linkedNodes(
  node: NodeObject,
  fields: readonly string[],
): NodeObject[] {
  return fields.flatMap((field) => {
    const linked = node[field];
    const candidates: unknown[] = Array.isArray(linked) ? linked : [linked];
    return candidates.filter(isObject);
  });
}

function isObject(value: unknown): value is NodeObject {
  return typeof value === "object" && value !== null;
}

function isInt(value: unknown): value is number {
  return (
    Number.isInteger(value) &&
    (value as number) >= INT_MIN &&
    (value as number) <= INT_MAX
  );
}

function fail(reason: string, path: string): never {
  throw new InvalidOutput(path === "" ? reason : `${reason} at ${path}`);
}

/** A short description of a value for messages, e.g. `1.5`, `"abc"`, `undefined`, `Promise`. */
export function describe(value: unknown): string {
  switch (typeof value) {
    case "string":
      return JSON.stringify(
        value.length > QUOTED_STRING_LIMIT
          ? `${value.slice(0, QUOTED_STRING_LIMIT)}...`
          : value,
      );
    case "number":
    case "boolean":
    case "undefined":
      return String(value);
    case "bigint":
      return `${value}n (a bigint)`;
    case "function":
      return "a function";
    case "symbol":
      return "a symbol";
    default:
      return describeObject(value as object | null);
  }
}

function describeObject(value: object | null): string {
  if (value === null) {
    return "null";
  }
  if (Array.isArray(value)) {
    return "an array";
  }
  const name = value.constructor?.name;
  return name === undefined || name === "Object" ? "an object" : `a ${name}`;
}
