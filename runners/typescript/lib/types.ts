// The signature type DSL (docs/specs/problem-format.md#type-dsl), as far as the runner needs it.
// Arrays and lists are both JavaScript arrays here, so `int[]` and `list<int>` parse alike.

export type Scalar = "int" | "long" | "double" | "bool" | "string" | "char";
export type NodeKind = "ListNode" | "TreeNode" | "GraphNode";

export type TypeSpec =
  | { readonly kind: "scalar"; readonly scalar: Scalar; readonly text: string }
  | { readonly kind: "node"; readonly node: NodeKind; readonly text: string }
  | {
      readonly kind: "array";
      readonly element: TypeSpec;
      readonly text: string;
    }
  | { readonly kind: "void"; readonly text: string };

const SCALARS: readonly string[] = [
  "int",
  "long",
  "double",
  "bool",
  "string",
  "char",
];
const NODE_KINDS: readonly string[] = ["ListNode", "TreeNode", "GraphNode"];
const ARRAY_SUFFIX = "[]";
const LIST_PREFIX = "list<";
const LIST_SUFFIX = ">";
const VOID = "void";

export class UnknownTypeError extends Error {}

export function parseType(text: string): TypeSpec {
  if (text === VOID) {
    return { kind: "void", text };
  }
  if (text.endsWith(ARRAY_SUFFIX)) {
    return {
      kind: "array",
      element: parseType(text.slice(0, -ARRAY_SUFFIX.length)),
      text,
    };
  }
  if (text.startsWith(LIST_PREFIX) && text.endsWith(LIST_SUFFIX)) {
    const element = text.slice(LIST_PREFIX.length, -LIST_SUFFIX.length);
    return { kind: "array", element: parseType(element), text };
  }
  if (isScalar(text)) {
    return { kind: "scalar", scalar: text, text };
  }
  if (isNodeKind(text)) {
    return { kind: "node", node: text, text };
  }
  throw new UnknownTypeError(`unknown type "${text}"`);
}

function isScalar(text: string): text is Scalar {
  return SCALARS.includes(text);
}

function isNodeKind(text: string): text is NodeKind {
  return NODE_KINDS.includes(text);
}
