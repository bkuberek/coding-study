from dataclasses import dataclass, field

KEYWORDS = {"let", "in", "fn", "if", "then", "else"}
TWO_CHAR_SYMBOLS = {"==", "!=", "<=", ">=", "=>"}
ONE_CHAR_SYMBOLS = set("()+-*/%^<>=,")
INT_MIN, INT_MAX = -(2**31), 2**31 - 1

# Binding power of each binary operator, and whether it groups to the right.
BINARY = {
    "==": 1, "!=": 1, "<": 1, "<=": 1, ">": 1, ">=": 1,
    "+": 2, "-": 2,
    "*": 3, "/": 3, "%": 3,
    "^": 5,
}
RIGHT_ASSOCIATIVE = {"^"}
PREFIX_MINUS = 4
CALL = 6
LOWEST = 0
OPCODES = {
    "+": "ADD", "-": "SUB", "*": "MUL", "/": "DIV", "%": "MOD", "^": "POW",
    "==": "EQ", "!=": "NE", "<": "LT", "<=": "LE", ">": "GT", ">=": "GE",
}


class LangError(Exception):
    def __init__(self, code: str, position: tuple[int, int]) -> None:
        super().__init__(code)
        self.code = code
        self.position = position

    def __str__(self) -> str:
        return f"error {self.code} {self.position[0]}:{self.position[1]}"


@dataclass
class Token:
    kind: str
    text: str
    position: tuple[int, int]

    def __str__(self) -> str:
        where = f"{self.position[0]}:{self.position[1]}"
        return f"end {where}" if self.kind == "end" else f"{self.kind} {self.text} {where}"


# ---------------------------------------------------------------------------- level 1: tokens
def tokenize(source: str) -> list[Token]:
    tokens: list[Token] = []
    index, line, column = 0, 1, 1

    def advance(count: int) -> None:
        nonlocal index, column
        index += count
        column += count

    while index < len(source):
        char = source[index]
        here = (line, column)
        if char == "\n":
            index, line, column = index + 1, line + 1, 1
        elif char in " \t":
            advance(1)
        elif char == "#":
            while index < len(source) and source[index] != "\n":
                advance(1)
        elif char.isascii() and char.isdigit():
            end = index
            while end < len(source) and source[end].isascii() and source[end].isdigit():
                end += 1
            digits = source[index:end]
            if (len(digits) > 1 and digits[0] == "0") or int(digits) > INT_MAX:
                raise LangError("bad-number", here)
            tokens.append(Token("number", digits, here))
            advance(end - index)
        elif char.isascii() and (char.isalpha() or char == "_"):
            end = index
            while end < len(source) and source[end].isascii() and (source[end].isalnum() or source[end] == "_"):
                end += 1
            word = source[index:end]
            tokens.append(Token("keyword" if word in KEYWORDS else "name", word, here))
            advance(end - index)
        elif source[index : index + 2] in TWO_CHAR_SYMBOLS:
            tokens.append(Token("symbol", source[index : index + 2], here))
            advance(2)
        elif char in ONE_CHAR_SYMBOLS:
            tokens.append(Token("symbol", char, here))
            advance(1)
        else:
            raise LangError("bad-char", here)
    tokens.append(Token("end", "", (line, column)))
    return tokens


# ---------------------------------------------------------------------------- level 2: syntax tree
@dataclass
class Node:
    position: tuple[int, int]


@dataclass
class Number(Node):
    value: int


@dataclass
class Name(Node):
    name: str


@dataclass
class Negate(Node):
    operand: Node


@dataclass
class Binary(Node):
    operator: str
    left: Node
    right: Node


@dataclass
class Call(Node):
    callee: Node
    arguments: list[Node]


@dataclass
class Let(Node):
    name: str
    value: Node
    body: Node


@dataclass
class If(Node):
    condition: Node
    then: Node
    otherwise: Node


@dataclass
class Function(Node):
    name: str | None
    params: list[str]
    body: Node
    block: int = 0


class Parser:
    """A Pratt parser: each token knows how it starts an expression (prefix) and how it
    continues one (infix), and `expression(minimum)` keeps extending the left side while the
    next operator binds tighter than `minimum`."""

    def __init__(self, tokens: list[Token]) -> None:
        self.tokens = tokens
        self.index = 0
        self.functions = 0

    def peek(self) -> Token:
        return self.tokens[self.index]

    def take(self) -> Token:
        token = self.tokens[self.index]
        self.index += 1
        return token

    def expect(self, kind: str, text: str | None = None) -> Token:
        token = self.peek()
        if token.kind != kind or (text is not None and token.text != text):
            raise LangError("unexpected-token", token.position)
        return self.take()

    def program(self) -> Node:
        node = self.expression(LOWEST)
        self.expect("end")
        return node

    def expression(self, minimum: int) -> Node:
        left = self.prefix()
        while True:
            token = self.peek()
            if token.kind != "symbol":
                return left
            if token.text == "(" and CALL > minimum:
                left = self.call(left)
            elif token.text in BINARY and BINARY[token.text] > minimum:
                self.take()
                power = BINARY[token.text]
                right = self.expression(power - 1 if token.text in RIGHT_ASSOCIATIVE else power)
                left = Binary(token.position, token.text, left, right)
            else:
                return left

    def prefix(self) -> Node:
        token = self.take()
        if token.kind == "number":
            return Number(token.position, int(token.text))
        if token.kind == "name":
            return Name(token.position, token.text)
        if token.kind == "symbol" and token.text == "-":
            return Negate(token.position, self.expression(PREFIX_MINUS))
        if token.kind == "symbol" and token.text == "(":
            inner = self.expression(LOWEST)
            self.expect("symbol", ")")
            return inner
        if token.kind == "keyword" and token.text == "let":
            name = self.expect("name").text
            self.expect("symbol", "=")
            value = self.expression(LOWEST)
            self.expect("keyword", "in")
            return Let(token.position, name, value, self.expression(LOWEST))
        if token.kind == "keyword" and token.text == "if":
            condition = self.expression(LOWEST)
            self.expect("keyword", "then")
            then = self.expression(LOWEST)
            self.expect("keyword", "else")
            return If(token.position, condition, then, self.expression(LOWEST))
        if token.kind == "keyword" and token.text == "fn":
            return self.function(token)
        raise LangError("unexpected-token", token.position)

    def function(self, keyword: Token) -> Function:
        self.functions += 1
        block = self.functions
        name = self.take().text if self.peek().kind == "name" else None
        self.expect("symbol", "(")
        params: list[str] = []
        if not (self.peek().kind == "symbol" and self.peek().text == ")"):
            while True:
                param = self.expect("name")
                if param.text in params:
                    raise LangError("duplicate-param", param.position)
                params.append(param.text)
                if not (self.peek().kind == "symbol" and self.peek().text == ","):
                    break
                self.take()
        self.expect("symbol", ")")
        self.expect("symbol", "=>")
        return Function(keyword.position, name, params, self.expression(LOWEST), block)

    def call(self, callee: Node) -> Call:
        paren = self.take()
        arguments: list[Node] = []
        if not (self.peek().kind == "symbol" and self.peek().text == ")"):
            arguments.append(self.expression(LOWEST))
            while self.peek().kind == "symbol" and self.peek().text == ",":
                self.take()
                arguments.append(self.expression(LOWEST))
        self.expect("symbol", ")")
        return Call(paren.position, callee, arguments)


def parse(source: str) -> Node:
    return Parser(tokenize(source)).program()


def head(node: Function) -> str:
    named = f"fn {node.name} " if node.name else "fn "
    return named + "(" + " ".join(node.params) + ")"


def show(node: Node) -> str:
    match node:
        case Number(value=value):
            return str(value)
        case Name(name=name):
            return name
        case Negate(operand=operand):
            return f"(neg {show(operand)})"
        case Binary(operator=operator, left=left, right=right):
            return f"({operator} {show(left)} {show(right)})"
        case Call(callee=callee, arguments=arguments):
            return "(" + " ".join(["call", show(callee), *map(show, arguments)]) + ")"
        case Let(name=name, value=value, body=body):
            return f"(let {name} {show(value)} {show(body)})"
        case If(condition=condition, then=then, otherwise=otherwise):
            return f"(if {show(condition)} {show(then)} {show(otherwise)})"
        case Function(body=body):
            return f"({head(node)} {show(body)})"
    raise TypeError(node)


# ---------------------------------------------------------------------------- level 3: evaluation
class Scope:
    """One level of names; lookups walk outwards to the enclosing levels."""

    def __init__(self, parent: "Scope | None", names: dict[str, object]) -> None:
        self.parent = parent
        self.names = names

    def lookup(self, name: str, position: tuple[int, int]) -> object:
        scope: "Scope | None" = self
        while scope is not None:
            if name in scope.names:
                return scope.names[name]
            scope = scope.parent
        raise LangError("unbound", position)


@dataclass(eq=False)
class Closure:
    name: str | None
    params: list[str]
    scope: Scope
    body: Node | None = None
    block: int = 0

    def __str__(self) -> str:
        return f"<fn {self.name}>" if self.name else "<fn>"

    def call_scope(self, arguments: list[object]) -> Scope:
        own = {self.name: self} if self.name else {}
        return Scope(self.scope, own | dict(zip(self.params, arguments, strict=True)))


def checked(value: int, position: tuple[int, int]) -> int:
    if not INT_MIN <= value <= INT_MAX:
        raise LangError("overflow", position)
    return value


def power(base: int, exponent: int, position: tuple[int, int]) -> int:
    if base in (0, 1) and exponent > 0:
        return base
    if base == -1:
        return -1 if exponent % 2 else 1
    result = 1
    for _ in range(exponent):
        result = checked(result * base, position)
    return result


def apply_binary(operator: str, left: object, right: object, position: tuple[int, int]) -> int:
    if not isinstance(left, int) or not isinstance(right, int):
        raise LangError("type", position)
    if operator in ("/", "%") and right == 0:
        raise LangError("div-zero", position)
    if operator == "^" and right < 0:
        raise LangError("negative-exponent", position)
    if operator in ("/", "%"):
        quotient = abs(left) // abs(right) * (1 if (left < 0) == (right < 0) else -1)
        return checked(quotient, position) if operator == "/" else left - right * quotient
    if operator == "^":
        return power(left, right, position)
    arithmetic = {"+": left + right, "-": left - right, "*": left * right}
    if operator in arithmetic:
        return checked(arithmetic[operator], position)
    comparison = {
        "==": left == right, "!=": left != right, "<": left < right,
        "<=": left <= right, ">": left > right, ">=": left >= right,
    }
    return int(comparison[operator])


def negate(value: object, position: tuple[int, int]) -> int:
    if not isinstance(value, int):
        raise LangError("type", position)
    return checked(-value, position)


def check_call(callee: object, count: int, depth: int, max_depth: int, position: tuple[int, int]) -> Closure:
    if not isinstance(callee, Closure):
        raise LangError("not-callable", position)
    if count != len(callee.params):
        raise LangError("arity", position)
    if depth >= max_depth:
        raise LangError("depth", position)
    return callee


def truth(value: object, position: tuple[int, int]) -> bool:
    if not isinstance(value, int):
        raise LangError("type", position)
    return value != 0


class TreeWalker:
    def __init__(self, max_depth: int) -> None:
        self.max_depth = max_depth

    def run(self, node: Node, scope: Scope, depth: int) -> object:
        match node:
            case Number(value=value):
                return value
            case Name(name=name):
                return scope.lookup(name, node.position)
            case Negate(operand=operand):
                return negate(self.run(operand, scope, depth), node.position)
            case Binary(operator=operator, left=left, right=right):
                first = self.run(left, scope, depth)
                second = self.run(right, scope, depth)
                return apply_binary(operator, first, second, node.position)
            case If(condition=condition, then=then, otherwise=otherwise):
                chosen = then if truth(self.run(condition, scope, depth), node.position) else otherwise
                return self.run(chosen, scope, depth)
            case Let(name=name, value=value, body=body):
                bound = self.run(value, scope, depth)
                return self.run(body, Scope(scope, {name: bound}), depth)
            case Function(name=name, params=params, body=body):
                return Closure(name, params, scope, body=body)
            case Call(callee=callee, arguments=arguments):
                function = self.run(callee, scope, depth)
                values = [self.run(argument, scope, depth) for argument in arguments]
                closure = check_call(function, len(values), depth, self.max_depth, node.position)
                return self.run(closure.body, closure.call_scope(values), depth + 1)
        raise TypeError(node)


# ---------------------------------------------------------------------------- level 4: bytecode
@dataclass
class Instruction:
    opcode: str
    operand: int | str | None = None
    position: tuple[int, int] | None = None

    def __str__(self) -> str:
        parts = [self.opcode]
        if self.operand is not None:
            parts.append(str(self.operand))
        if self.position is not None:
            parts.append(f"{self.position[0]}:{self.position[1]}")
        return " ".join(parts)


@dataclass
class Block:
    header: str
    name: str | None
    params: list[str]
    code: list[Instruction] = field(default_factory=list)


class Compiler:
    def __init__(self) -> None:
        self.blocks: dict[int, Block] = {}

    def program(self, node: Node) -> list[Block]:
        self.blocks[0] = Block("main", None, [])
        self.emit_block(0, node)
        return [self.blocks[number] for number in sorted(self.blocks)]

    def emit_block(self, number: int, body: Node) -> None:
        code = self.blocks[number].code
        self.emit(body, code)
        code.append(Instruction("RETURN"))

    def emit(self, node: Node, code: list[Instruction]) -> None:
        match node:
            case Number(value=value):
                code.append(Instruction("PUSH", value))
            case Name(name=name):
                code.append(Instruction("LOAD", name, node.position))
            case Negate(operand=operand):
                self.emit(operand, code)
                code.append(Instruction("NEG", None, node.position))
            case Binary(operator=operator, left=left, right=right):
                self.emit(left, code)
                self.emit(right, code)
                code.append(Instruction(OPCODES[operator], None, node.position))
            case If(condition=condition, then=then, otherwise=otherwise):
                self.emit(condition, code)
                to_else = Instruction("JUMP_IF_ZERO", None, node.position)
                code.append(to_else)
                self.emit(then, code)
                to_end = Instruction("JUMP")
                code.append(to_end)
                to_else.operand = len(code)
                self.emit(otherwise, code)
                to_end.operand = len(code)
            case Let(name=name, value=value, body=body):
                self.emit(value, code)
                code.append(Instruction("BIND", name))
                self.emit(body, code)
                code.append(Instruction("UNBIND"))
            case Function(name=name, params=params, body=body, block=block):
                self.blocks[block] = Block(head(node), name, params)
                self.emit_block(block, body)
                code.append(Instruction("CLOSURE", block))
            case Call(callee=callee, arguments=arguments):
                self.emit(callee, code)
                for argument in arguments:
                    self.emit(argument, code)
                code.append(Instruction("CALL", len(arguments), node.position))


@dataclass
class Frame:
    block: Block
    scope: Scope
    ip: int = 0


class Machine:
    """A stack machine: one value stack shared by all frames, and a frame per active call. The
    loop never recurses, so the depth limit is the only bound on calls."""

    def __init__(self, blocks: list[Block], max_depth: int) -> None:
        self.blocks = blocks
        self.max_depth = max_depth

    def run(self) -> object:
        stack: list[object] = []
        frames = [Frame(self.blocks[0], Scope(None, {}))]
        while True:
            frame = frames[-1]
            instruction = frame.block.code[frame.ip]
            frame.ip += 1
            opcode, operand, position = instruction.opcode, instruction.operand, instruction.position
            if opcode == "PUSH":
                stack.append(operand)
            elif opcode == "LOAD":
                stack.append(frame.scope.lookup(operand, position))
            elif opcode == "NEG":
                stack.append(negate(stack.pop(), position))
            elif opcode in BINARY_OPCODES:
                right = stack.pop()
                left = stack.pop()
                stack.append(apply_binary(BINARY_OPCODES[opcode], left, right, position))
            elif opcode == "JUMP_IF_ZERO":
                if not truth(stack.pop(), position):
                    frame.ip = operand
            elif opcode == "JUMP":
                frame.ip = operand
            elif opcode == "BIND":
                frame.scope = Scope(frame.scope, {operand: stack.pop()})
            elif opcode == "UNBIND":
                frame.scope = frame.scope.parent
            elif opcode == "CLOSURE":
                block = self.blocks[operand]
                stack.append(Closure(block.name, block.params, frame.scope, block=operand))
            elif opcode == "CALL":
                arguments = stack[len(stack) - operand :]
                del stack[len(stack) - operand :]
                callee = stack.pop()
                closure = check_call(callee, len(arguments), len(frames) - 1, self.max_depth, position)
                frames.append(Frame(self.blocks[closure.block], closure.call_scope(arguments)))
            elif opcode == "RETURN":
                frames.pop()
                if not frames:
                    return stack.pop()


BINARY_OPCODES = {opcode: operator for operator, opcode in OPCODES.items()}


def listing(blocks: list[Block]) -> list[str]:
    lines = []
    for number, block in enumerate(blocks):
        lines.append(f"block {number} {block.header}")
        lines.extend(f"{index} {instruction}" for index, instruction in enumerate(block.code))
    return lines


def compile_program(source: str) -> list[Block]:
    return Compiler().program(parse(source))


class Interpreter:
    def __init__(self, max_depth: int) -> None:
        self._max_depth = max_depth

    # Level 1
    def tokenize(self, source: str) -> list[str]:
        try:
            return [str(token) for token in tokenize(source)]
        except LangError as error:
            return [str(error)]

    # Level 2
    def parse(self, source: str) -> str:
        try:
            return show(parse(source))
        except LangError as error:
            return str(error)

    # Level 3
    def evaluate(self, source: str) -> str:
        try:
            return str(TreeWalker(self._max_depth).run(parse(source), Scope(None, {}), 0))
        except LangError as error:
            return str(error)

    # Level 4
    def bytecode(self, source: str) -> list[str]:
        try:
            return listing(compile_program(source))
        except LangError as error:
            return [str(error)]

    def run(self, source: str) -> str:
        try:
            return str(Machine(compile_program(source), self._max_depth).run())
        except LangError as error:
            return str(error)
