from __future__ import annotations

import re

KEY = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
INDEX = re.compile(r"0|[1-9][0-9]*")
SEGMENT = r"(?:[A-Za-z_][A-Za-z0-9_]*|0|[1-9][0-9]*)"
PATH = re.compile(rf"{SEGMENT}(?:\.{SEGMENT})*")
WORD_CHARS = frozenset("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.")
BLOCK_WORDS = frozenset({"if", "else", "end", "for"})
RESERVED = frozenset({"if", "else", "end", "for", "in"})


class Node:
    """One JSON value: an object (members), an array (items) or a scalar (kind and text). `layer`
    names the layer that set it, for provenance."""

    __slots__ = ("items", "kind", "layer", "members", "text")

    def __init__(self, kind: str, text: str = "", layer: str = "") -> None:
        self.kind = kind
        self.text = text
        self.members: dict[str, Node] = {}
        self.items: list[Node] = []
        self.layer = layer

    def copy(self, layer: str) -> Node:
        twin = Node(self.kind, self.text, layer)
        twin.members = {key: child.copy(layer) for key, child in self.members.items()}
        twin.items = [child.copy(layer) for child in self.items]
        return twin


class TemplateError(Exception):
    def __init__(self, code: str, position: int, detail: str = "") -> None:
        super().__init__(code)
        self.code = code
        self.position = position
        self.detail = detail


def decode(rows: list[list[str]]) -> Node:
    """Builds the tree from rows listed parent first; the root is an implicit object."""
    root = Node("object")
    for pointer, kind, text in rows:
        *parents, last = pointer.split("/")[1:]
        parent = root
        for segment in parents:
            parent = parent.members[segment] if parent.kind == "object" else parent.items[int(segment)]
        node = Node(kind, text)
        if parent.kind == "object":
            parent.members[last] = node
        else:
            parent.items.append(node)
    return root


def walk(node: Node, pointer: str, visit) -> None:
    """Visits every node below `node` in canonical order: keys ascending, items by index."""
    if node.kind == "object":
        for key in sorted(node.members):
            child = node.members[key]
            visit(f"{pointer}/{key}", child)
            walk(child, f"{pointer}/{key}", visit)
    elif node.kind == "array":
        for index, child in enumerate(node.items):
            visit(f"{pointer}/{index}", child)
            walk(child, f"{pointer}/{index}", visit)


def merge_into(target: Node, patch: Node, layer: str) -> None:
    """RFC 7396 merge of one object into another: null removes, an object merges key by key,
    anything else replaces. A new object belongs to the layer that created it."""
    for key, value in patch.members.items():
        if value.kind == "null":
            target.members.pop(key, None)
        elif value.kind == "object":
            current = target.members.get(key)
            if current is None or current.kind != "object":
                current = Node("object", "", layer)
                target.members[key] = current
            merge_into(current, value, layer)
        else:
            target.members[key] = value.copy(layer)


def is_path(word: str) -> bool:
    return PATH.fullmatch(word) is not None


def is_key(segment: str) -> bool:
    return KEY.fullmatch(segment) is not None


def is_index(segment: str) -> bool:
    return INDEX.fullmatch(segment) is not None


def tokenize(body: str, position: int) -> list[tuple[str, str]]:
    """Splits a tag body into ("word", w), ("string", s) and ("punct", "|" or ",") tokens."""
    tokens: list[tuple[str, str]] = []
    i = 0
    while i < len(body):
        c = body[i]
        if c == " ":
            i += 1
        elif c in "|,":
            tokens.append(("punct", c))
            i += 1
        elif c == '"':
            text, i = read_string(body, i + 1, position)
            tokens.append(("string", text))
        elif c in WORD_CHARS:
            start = i
            while i < len(body) and body[i] in WORD_CHARS:
                i += 1
            tokens.append(("word", body[start:i]))
        else:
            raise TemplateError("bad_expression", position)
    return tokens


def read_string(body: str, i: int, position: int) -> tuple[str, int]:
    out: list[str] = []
    while i < len(body):
        c = body[i]
        if c == '"':
            return "".join(out), i + 1
        if c == "\\":
            if i + 1 < len(body) and body[i + 1] in '"\\':
                out.append(body[i + 1])
                i += 2
                continue
            raise TemplateError("bad_expression", position)
        out.append(c)
        i += 1
    raise TemplateError("bad_expression", position)


def classify(tokens: list[tuple[str, str]], position: int) -> tuple:
    """The meaning of a tag: ("text", s), ("out", path, default or None), ("if", path),
    ("else",), ("end",) or ("for", names, path)."""
    kinds = [kind for kind, _ in tokens]
    words = [value for _, value in tokens]
    if kinds and kinds[0] == "word" and words[0] in BLOCK_WORDS:
        return classify_block(kinds, words, position)
    if kinds == ["string"]:
        return ("text", words[0])
    if kinds == ["word"] and is_path(words[0]):
        return ("out", words[0], None)
    is_default = kinds == ["word", "punct", "word", "string"] and words[1:3] == ["|", "default"]
    if is_default and is_path(words[0]):
        return ("out", words[0], words[3])
    raise TemplateError("bad_expression", position)


def classify_block(kinds: list[str], words: list[str], position: int) -> tuple:
    head = words[0]
    if head in ("else", "end") and len(words) == 1:
        return (head,)
    if head == "if" and kinds == ["word", "word"] and is_path(words[1]):
        return ("if", words[1])
    if head == "for":
        if kinds == ["word"] * 4 and words[2] == "in":
            names = [words[1]]
        elif kinds == ["word", "word", "punct", "word", "word", "word"] and words[2] == ",":
            names = [words[1], words[3]] if words[4] == "in" else []
        else:
            names = []
        valid = all(is_key(name) and name not in RESERVED for name in names)
        if names and valid and len(set(names)) == len(names) and is_path(words[-1]):
            return ("for", names, words[-1])
    raise TemplateError("bad_expression", position)


def parse(template: str) -> list:
    """Scans the template once, left to right, stopping at the first problem, and returns the
    tree: a list of strings and tags, where if and for tags hold their own lists."""
    segments: list = []
    stack: list[tuple] = []
    i = 0
    while True:
        start = template.find("{{", i)
        if start < 0:
            segments.append(template[i:])
            break
        segments.append(template[i:start])
        end = template.find("}}", start + 2)
        if end < 0:
            raise TemplateError("unclosed_tag", start)
        body = template[start + 2 : end]
        trim_left = body.startswith("-")
        if trim_left:
            body = body[1:]
        trim_right = body.endswith("-")
        if trim_right:
            body = body[:-1]
        tag = classify(tokenize(body.strip(" "), start), start)
        if tag[0] in ("if", "for"):
            stack.append((tag[0], start, False))
        elif tag[0] == "else":
            if not stack or stack[-1][0] != "if" or stack[-1][2]:
                raise TemplateError("unexpected_tag", start)
            stack[-1] = ("if", stack[-1][1], True)
        elif tag[0] == "end":
            if not stack:
                raise TemplateError("unexpected_tag", start)
            stack.pop()
        segments.append((tag, start, trim_left, trim_right))
        i = end + 2
    if stack:
        raise TemplateError("unclosed_block", stack[-1][1])
    for index, segment in enumerate(segments):
        if isinstance(segment, tuple):
            if segment[2]:
                segments[index - 1] = segments[index - 1].rstrip(" \n")
            if segment[3]:
                segments[index + 1] = segments[index + 1].lstrip(" \n")
    return build(segments)


def build(segments: list) -> list:
    """Nests the flat segments: an if holds a then-list and an else-list, a for its body."""
    root: list = []
    stack: list[tuple[dict, list]] = []
    current = root
    for segment in segments:
        if isinstance(segment, str):
            if segment:
                current.append(segment)
            continue
        tag, position = segment[0], segment[1]
        if tag[0] == "if":
            node = {"kind": "if", "path": tag[1], "then": [], "else": [], "at": position}
            current.append(node)
            stack.append((node, current))
            current = node["then"]
        elif tag[0] == "for":
            node = {"kind": "for", "names": tag[1], "path": tag[2], "body": [], "at": position}
            current.append(node)
            stack.append((node, current))
            current = node["body"]
        elif tag[0] == "else":
            current = stack[-1][0]["else"]
        elif tag[0] == "end":
            current = stack.pop()[1]
        elif tag[0] == "text":
            current.append(tag[1])
        else:
            current.append({"kind": "out", "path": tag[1], "default": tag[2], "at": position})
    return root


def line_and_column(template: str, position: int) -> str:
    line = template.count("\n", 0, position) + 1
    column = position - (template.rfind("\n", 0, position) + 1) + 1
    return f"{line}:{column}"


class ValuesRenderer:
    """Layers are kept as given and merged on demand, oldest first, with the rules of RFC 7396.
    Every node of the merged tree remembers the layer that set it. A template is parsed in one
    left-to-right pass into a tree of text, substitutions, conditionals and loops, and rendered
    with a stack of loop bindings that shadow the values."""

    def __init__(self) -> None:
        self._layers: dict[str, Node] = {}
        self._schema: Node = Node("object")

    # Level 1
    def set_layer(self, name: str, rows: list[list[str]]) -> bool:
        is_new = name not in self._layers
        self._layers[name] = decode(rows)
        return is_new

    def merged(self) -> list[list[str]]:
        rows: list[list[str]] = []
        walk(self._merge(), "", lambda pointer, node: rows.append([pointer, node.kind, node.text]))
        return rows

    # Level 2 and 3
    def render(self, template: str) -> list[str]:
        values = self._merge()
        errors = self._errors(values)
        if errors:
            return ["error", "invalid_values", "", str(len(errors))]
        try:
            out: list[str] = []
            self._emit(parse(template), values, [], out)
            return ["ok", "".join(out)]
        except TemplateError as error:
            return ["error", error.code, line_and_column(template, error.position), error.detail]

    # Level 4
    def set_schema(self, rows: list[list[str]]) -> None:
        self._schema = decode(rows)

    def validate(self) -> list[list[str]]:
        return self._errors(self._merge())

    def provenance(self) -> list[list[str]]:
        rows: list[list[str]] = []
        walk(self._merge(), "", lambda pointer, node: rows.append([pointer, node.layer]))
        return rows

    # Merging
    def _merge(self) -> Node:
        root = Node("object")
        for name, layer in self._layers.items():
            merge_into(root, layer, name)
        return root

    # Rendering
    def _emit(self, nodes: list, values: Node, scope: list[tuple[str, Node]], out: list[str]) -> None:
        for node in nodes:
            if isinstance(node, str):
                out.append(node)
            elif node["kind"] == "out":
                found = self._lookup(node["path"], values, scope)
                if found is None:
                    if node["default"] is None:
                        raise TemplateError("missing_value", node["at"], node["path"])
                    out.append(node["default"])
                elif found.kind in ("object", "array"):
                    raise TemplateError("not_scalar", node["at"], node["path"])
                else:
                    out.append(found.text)
            elif node["kind"] == "if":
                found = self._lookup(node["path"], values, scope)
                branch = node["then"] if truthy(found) else node["else"]
                self._emit(branch, values, scope, out)
            else:
                self._loop(node, values, scope, out)

    def _loop(self, node: dict, values: Node, scope: list[tuple[str, Node]], out: list[str]) -> None:
        found = self._lookup(node["path"], values, scope)
        if found is None:
            raise TemplateError("missing_value", node["at"], node["path"])
        if found.kind == "array":
            pairs = [(Node("number", str(i)), item) for i, item in enumerate(found.items)]
        elif found.kind == "object":
            pairs = [(Node("string", key), found.members[key]) for key in sorted(found.members)]
        else:
            raise TemplateError("not_iterable", node["at"], node["path"])
        names = node["names"]
        for key, item in pairs:
            bound = [(names[0], key), (names[1], item)] if len(names) == 2 else [(names[0], item)]
            self._emit(node["body"], values, scope + bound, out)

    @staticmethod
    def _lookup(path: str, values: Node, scope: list[tuple[str, Node]]) -> Node | None:
        segments = path.split(".")
        current: Node | None = values
        for name, bound in reversed(scope):
            if name == segments[0]:
                current, segments = bound, segments[1:]
                break
        for segment in segments:
            if current is None:
                return None
            if current.kind == "object":
                current = current.members.get(segment)
            elif current.kind == "array" and is_index(segment) and int(segment) < len(current.items):
                current = current.items[int(segment)]
            else:
                return None
        return None if current is None or current.kind == "null" else current

    # Validation
    def _errors(self, values: Node) -> list[list[str]]:
        errors: list[list[str]] = []
        check(values, self._schema, "", errors)
        return sorted(errors, key=lambda error: (error[0], error[1]))


def truthy(node: Node | None) -> bool:
    if node is None:
        return False
    if node.kind == "boolean":
        return node.text == "true"
    if node.kind == "string":
        return node.text != ""
    if node.kind == "number":
        return node.text != "0"
    return bool(node.members) if node.kind == "object" else bool(node.items)


def has_type(node: Node, name: str) -> bool:
    return node.kind == name or (name == "integer" and node.kind == "number")


def is_listed(node: Node, options: Node) -> bool:
    if node.kind in ("object", "array"):
        return False
    return any(node.kind == option.kind and node.text == option.text for option in options.items)


def check(node: Node, schema: Node, pointer: str, errors: list[list[str]]) -> None:
    """Applies the keywords of one schema object at one instance location, then recurses into
    the members and items the schema describes."""
    keywords = schema.members
    if "type" in keywords and not has_type(node, keywords["type"].text):
        errors.append([pointer, "type", node.layer])
    if "enum" in keywords and not is_listed(node, keywords["enum"]):
        errors.append([pointer, "enum", node.layer])
    if node.kind == "number":
        if "minimum" in keywords and int(node.text) < int(keywords["minimum"].text):
            errors.append([pointer, "minimum", node.layer])
        if "maximum" in keywords and int(node.text) > int(keywords["maximum"].text):
            errors.append([pointer, "maximum", node.layer])
    if node.kind == "object":
        properties = keywords["properties"].members if "properties" in keywords else {}
        if "required" in keywords:
            for key in keywords["required"].items:
                if key.text not in node.members:
                    errors.append([f"{pointer}/{key.text}", "required", ""])
        additional = keywords.get("additionalProperties")
        closed = additional is not None and additional.text == "false"
        for key, child in node.members.items():
            if key in properties:
                check(child, properties[key], f"{pointer}/{key}", errors)
            elif closed:
                errors.append([f"{pointer}/{key}", "additionalProperties", child.layer])
    if node.kind == "array" and "items" in keywords:
        for index, child in enumerate(node.items):
            check(child, keywords["items"], f"{pointer}/{index}", errors)
