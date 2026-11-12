"""tiny-interpreter promises that its hidden cases catch the classic mistakes of building a
language: symbols read one character at a time, positions counted from 0, numbers that are too big
or start with 0, operators grouped or bound the wrong way, a `let` body that stops too early,
dynamic instead of lexical scope, checks done in the wrong order, division that floors, missing
overflow checks, an off-by-one depth limit, and bytecode with the wrong block numbers, jump targets
or positions. These tests replay every case against a model of the language written from the
statement, and against that model with one mistake planted at a time, which some hidden case must
fail.

The model is built differently from the reference: a regular-expression scanner, a recursive descent
parser with one function per precedence level, environments copied as dictionaries, and a machine
that executes the text of the listing itself, so `run` also proves that the listing is complete."""

import json
import math
import re
import sys
from collections.abc import Callable, Mapping, Sequence
from typing import Any

import pytest

from tests.helpers import CATALOG_PROBLEMS

PROBLEM = CATALOG_PROBLEMS / "0364-tiny-interpreter"
CASES: Sequence[Mapping[str, Any]] = json.loads(
    (PROBLEM / "tests.json").read_text(encoding="utf-8")
)["cases"]
HIDDEN_CASES = [case for case in CASES if not case.get("visible", False)]
LOW, HIGH = -(2**31), 2**31 - 1
KEYWORDS = ("let", "in", "fn", "if", "then", "else")
SYMBOLS = ("==", "!=", "<=", ">=", "=>", "(", ")", ",", "+", "-", "*", "/", "%", "^", "<", ">", "=")
OPCODE = {
    "+": "ADD",
    "-": "SUB",
    "*": "MUL",
    "/": "DIV",
    "%": "MOD",
    "^": "POW",
    "==": "EQ",
    "!=": "NE",
    "<": "LT",
    "<=": "LE",
    ">": "GT",
    ">=": "GE",
}
OPERATOR = {opcode: operator for operator, opcode in OPCODE.items()}
STEP_BUDGET = 3_000_000  # far above what any case needs; a broken jump loops forever otherwise

Tree = tuple  # ("num", value, pos) and so on, the position last


class LangError(Exception):
    def __init__(self, code: str, pos: tuple[int, int]) -> None:
        super().__init__(f"error {code} {pos[0]}:{pos[1]}")


class Fn:
    def __init__(self, name: str | None, params: list[str], body: Any, env: dict, block: int = 0):
        self.name, self.params, self.body, self.env, self.block = name, params, body, env, block

    def text(self) -> str:
        return f"<fn {self.name}>" if self.name else "<fn>"


class Model:
    def __init__(self, max_depth: int) -> None:
        self.max_depth = max_depth

    # ------------------------------------------------------------ level 1
    def symbols(self) -> tuple[str, ...]:
        return SYMBOLS

    def first_column(self) -> int:
        return 1

    def width(self, char: str) -> int:
        return 1

    def blank(self) -> str:
        return " \t"

    def word_pattern(self) -> str:
        return r"[A-Za-z_][A-Za-z0-9_]*"

    def number_is_fine(self, digits: str) -> bool:
        return (digits == "0" or not digits.startswith("0")) and int(digits) <= HIGH

    def word_kind(self, word: str) -> str:
        return "keyword" if word in KEYWORDS else "name"

    def scan(self, source: str) -> list[tuple[str, str, tuple[int, int]]]:
        found = []
        at, line, column = 0, 1, self.first_column()
        symbol = "|".join(re.escape(s) for s in self.symbols())
        while at < len(source):
            pos = (line, column)
            if source[at] == "\n":
                at, line, column = at + 1, line + 1, self.first_column()
                continue
            match = (
                re.compile(f"[{self.blank()}]").match(source, at)
                or re.compile("#[^\n]*").match(source, at)
                or re.compile("[0-9]+").match(source, at)
                or re.compile(self.word_pattern()).match(source, at)
                or re.compile(symbol).match(source, at)
            )
            if match is None:
                raise LangError("bad-char", pos)
            text = match.group()
            if text[0].isdigit():
                if not self.number_is_fine(text):
                    raise LangError("bad-number", pos)
                found.append(("number", text, pos))
            elif text[0].isalpha() or text[0] == "_":
                found.append((self.word_kind(text), text, pos))
            elif text[0] in "(),+-*/%^<>=!":
                found.append(("symbol", text, pos))
            at = match.end()
            column += sum(self.width(char) for char in text)
        found.append(("end", "", self.end_position(source, line, column)))
        return found

    def end_position(self, source: str, line: int, column: int) -> tuple[int, int]:
        return (line, column)

    def tokenize(self, source: str) -> list[str]:
        try:
            return [
                f"{kind} {text} {p[0]}:{p[1]}" if kind != "end" else f"end {p[0]}:{p[1]}"
                for kind, text, p in self.scan(source)
            ]
        except LangError as failure:
            return [str(failure)]

    # ------------------------------------------------------------ level 2
    def tree(self, source: str) -> Tree:
        self.tokens = self.scan(source)
        self.at = 0
        self.fns = 0
        node = self.expr()
        self.want("end")
        return node

    def peek(self) -> tuple[str, str, tuple[int, int]]:
        return self.tokens[self.at]

    def is_symbol(self, *texts: str) -> bool:
        kind, text, _ = self.peek()
        return kind == "symbol" and text in texts

    def fail_here(self) -> LangError:
        return LangError("unexpected-token", self.peek()[2])

    def want(self, kind: str, text: str | None = None) -> tuple[str, str, tuple[int, int]]:
        token = self.peek()
        if token[0] != kind or (text is not None and token[1] != text):
            raise self.fail_here()
        self.at += 1
        return token

    def chain(self, operators: tuple[str, ...], operand: Callable[[], Tree]) -> Tree:
        left = operand()
        while self.is_symbol(*operators):
            _, op, pos = self.want("symbol")
            left = ("bin", op, left, operand(), pos)
        return left

    def expr(self) -> Tree:
        return self.chain(("==", "!=", "<", "<=", ">", ">="), self.sum)

    def sum(self) -> Tree:
        return self.chain(("+", "-"), self.product)

    def product(self) -> Tree:
        return self.chain(("*", "/", "%"), self.unary)

    def unary(self) -> Tree:
        if self.is_symbol("-"):
            pos = self.want("symbol")[2]
            return ("neg", self.unary(), pos)
        return self.power()

    def power(self) -> Tree:
        base = self.postfix()
        if self.is_symbol("^"):
            pos = self.want("symbol")[2]
            return ("bin", "^", base, self.unary(), pos)
        return base

    def postfix(self) -> Tree:
        node = self.primary()
        while self.is_symbol("("):
            pos = self.want("symbol")[2]
            args = []
            if not self.is_symbol(")"):
                args.append(self.expr())
                while self.is_symbol(","):
                    self.at += 1
                    args.append(self.expr())
            self.want("symbol", ")")
            node = ("call", node, args, pos)
        return node

    def tail(self) -> Tree:
        """The expression after the last keyword or `=>` of `let`, `if` and `fn`."""
        return self.expr()

    def primary(self) -> Tree:
        kind, text, pos = self.peek()
        self.at += 1
        if kind == "number":
            return ("num", int(text), pos)
        if kind == "name":
            return ("name", text, pos)
        if (kind, text) == ("symbol", "("):
            inner = self.expr()
            self.want("symbol", ")")
            return inner
        if (kind, text) == ("keyword", "let"):
            name = self.want("name")[1]
            self.want("symbol", "=")
            value = self.expr()
            self.want("keyword", "in")
            return ("let", name, value, self.tail(), pos)
        if (kind, text) == ("keyword", "if"):
            test = self.expr()
            self.want("keyword", "then")
            yes = self.expr()
            self.want("keyword", "else")
            return ("if", test, yes, self.tail(), pos)
        if (kind, text) == ("keyword", "fn"):
            self.fns += 1
            block = self.fns
            name = self.want("name")[1] if self.peek()[0] == "name" else None
            self.want("symbol", "(")
            params: list[str] = []
            while not self.is_symbol(")"):
                if params:
                    self.want("symbol", ",")
                param = self.want("name")
                self.check_param(params, param)
                params.append(param[1])
            self.at += 1
            self.want("symbol", "=>")
            return ("fn", name, params, self.tail(), block, pos)
        self.at -= 1
        raise self.fail_here()

    def check_param(self, params: list[str], param: tuple[str, str, tuple[int, int]]) -> None:
        if param[1] in params:
            raise LangError("duplicate-param", param[2])

    def show(self, node: Tree) -> str:
        tag = node[0]
        if tag in ("num", "name"):
            return str(node[1])
        if tag == "neg":
            return f"(neg {self.show(node[1])})"
        if tag == "bin":
            return f"({node[1]} {self.show(node[2])} {self.show(node[3])})"
        if tag == "call":
            return "(" + " ".join(["call", self.show(node[1]), *map(self.show, node[2])]) + ")"
        if tag == "let":
            return f"(let {node[1]} {self.show(node[2])} {self.show(node[3])})"
        if tag == "if":
            return f"(if {self.show(node[1])} {self.show(node[2])} {self.show(node[3])})"
        return f"({self.head(node)} {self.show(node[3])})"

    def head(self, node: Tree) -> str:
        _, name, params, *_ = node
        return " ".join(["fn", *([name] if name else []), "(" + " ".join(params) + ")"])

    def parse(self, source: str) -> str:
        try:
            return self.show(self.tree(source))
        except LangError as failure:
            return str(failure)

    # ------------------------------------------------------------ level 3
    def fits(self, value: int, pos: tuple[int, int]) -> int:
        if not LOW <= value <= HIGH:
            raise LangError("overflow", pos)
        return value

    def divide(self, a: int, b: int) -> int:
        return int(a / b)

    def remainder(self, a: int, b: int) -> int:
        return int(math.fmod(a, b))

    def raise_to(self, a: int, b: int, pos: tuple[int, int]) -> int:
        if b < 0:
            raise LangError("negative-exponent", pos)
        if abs(a) >= 2 and b > 62:
            raise LangError("overflow", pos)
        return self.fits(a**b, pos)

    def binary(self, op: str, a: Any, b: Any, pos: tuple[int, int]) -> int:
        if isinstance(a, Fn) or isinstance(b, Fn):
            raise LangError("type", pos)
        if op in "/%" and b == 0:
            raise LangError("div-zero", pos)
        if op == "^":
            return self.raise_to(a, b, pos)
        if op == "/":
            return self.fits(self.divide(a, b), pos)
        if op == "%":
            return self.remainder(a, b)
        if op in ("+", "-", "*"):
            return self.fits({"+": a + b, "-": a - b, "*": a * b}[op], pos)
        holds = {"==": a == b, "!=": a != b, "<": a < b, "<=": a <= b, ">": a > b, ">=": a >= b}
        return 1 if holds[op] else 0

    def minus(self, value: Any, pos: tuple[int, int]) -> int:
        if isinstance(value, Fn):
            raise LangError("type", pos)
        return self.fits(-value, pos)

    def chooses_then(self, value: Any, pos: tuple[int, int]) -> bool:
        if isinstance(value, Fn):
            raise LangError("type", pos)
        return value != 0

    def enter(
        self, fn: Any, args: list[Any], depth: int, pos: tuple[int, int], caller: dict
    ) -> dict:
        """Checks a call and returns the names its body sees."""
        if not isinstance(fn, Fn):
            raise LangError("not-callable", pos)
        if len(args) != len(fn.params):
            raise LangError("arity", pos)
        if depth >= self.max_depth:
            raise LangError("depth", pos)
        own = {fn.name: fn} if fn.name else {}
        return {**fn.env, **own, **dict(zip(fn.params, args, strict=True))}

    def let_scope(self, env: dict, name: str) -> dict:
        return env

    def closure(self, node: Tree, env: dict) -> Fn:
        return Fn(node[1], node[2], node[3], env, node[4])

    def value(self, node: Tree, env: dict, depth: int) -> Any:
        tag = node[0]
        if tag == "num":
            return node[1]
        if tag == "name":
            if node[1] not in env:
                raise LangError("unbound", node[2])
            return env[node[1]]
        if tag == "neg":
            return self.minus(self.value(node[1], env, depth), node[2])
        if tag == "bin":
            return self.operands(node, env, depth)
        if tag == "if":
            test = self.value(node[1], env, depth)
            branch = node[2] if self.chooses_then(test, node[4]) else node[3]
            return self.value(branch, env, depth)
        if tag == "let":
            bound = self.value(node[2], self.let_scope(env, node[1]), depth)
            return self.value(node[3], {**env, node[1]: bound}, depth)
        if tag == "fn":
            return self.closure(node, env)
        return self.calling(node, env, depth)

    def operands(self, node: Tree, env: dict, depth: int) -> int:
        _, op, left, right, pos = node
        a = self.value(left, env, depth)
        b = self.value(right, env, depth)
        return self.binary(op, a, b, pos)

    def calling(self, node: Tree, env: dict, depth: int) -> Any:
        _, callee, arguments, pos = node
        fn = self.value(callee, env, depth)
        args = [self.value(argument, env, depth) for argument in arguments]
        scope = self.enter(fn, args, depth, pos, env)
        return self.value(fn.body, scope, depth + 1)

    def evaluate(self, source: str) -> str:
        try:
            result = self.value(self.tree(source), {}, 0)
        except LangError as failure:
            return str(failure)
        return result.text() if isinstance(result, Fn) else str(result)

    # ------------------------------------------------------------ level 4
    def blocks_in_order(self, root: Tree) -> list[Tree]:
        """Every `fn` node, in the order of its keyword in the source."""
        found: list[Tree] = []

        def visit(node: Any) -> None:
            if isinstance(node, tuple) and node and node[0] == "fn":
                found.append(node)
            if isinstance(node, (tuple, list)):
                for part in node:
                    visit(part)

        visit(root)
        return found

    def where(self, pos: tuple[int, int]) -> str:
        return f"{pos[0]}:{pos[1]}"

    def emit(self, node: Tree, out: list[str]) -> None:
        tag = node[0]
        if tag == "num":
            out.append(f"PUSH {node[1]}")
        elif tag == "name":
            out.append(f"LOAD {node[1]} {self.where(node[2])}")
        elif tag == "neg":
            self.emit(node[1], out)
            out.append(f"NEG {self.where(node[2])}")
        elif tag == "bin":
            self.emit(node[2], out)
            self.emit(node[3], out)
            out.append(f"{OPCODE[node[1]]} {self.where(node[4])}")
        elif tag == "let":
            self.emit(node[2], out)
            out.append(f"BIND {node[1]}")
            self.emit(node[3], out)
            out.append("UNBIND")
        elif tag == "if":
            self.emit(node[1], out)
            jump_else = len(out)
            out.append("")
            self.emit(node[2], out)
            jump_end = len(out)
            out.append("")
            self.emit(node[3], out)
            out[jump_else] = (
                f"JUMP_IF_ZERO {self.target(jump_else, jump_end + 1)} {self.where(node[4])}"
            )
            out[jump_end] = f"JUMP {self.target(jump_end, len(out))}"
        elif tag == "fn":
            out.append(f"CLOSURE {self.number[id(node)]}")
        else:
            self.emit(node[1], out)
            for argument in node[2]:
                self.emit(argument, out)
            out.append(f"CALL {self.argument_count(node)} {self.where(node[3])}")

    def target(self, here: int, index: int) -> int:
        return index

    def argument_count(self, node: Tree) -> int:
        return len(node[2])

    def bytecode(self, source: str) -> list[str]:
        try:
            root = self.tree(source)
        except LangError as failure:
            return [str(failure)]
        fns = self.blocks_in_order(root)
        self.number = {id(node): self.block_number(k, len(fns)) for k, node in enumerate(fns)}
        listing: list[str] = []
        for number, (header, body) in sorted(
            [(0, ("main", root))] + [(self.number[id(n)], (self.head(n), n[3])) for n in fns]
        ):
            code: list[str] = []
            self.emit(body, code)
            code.append("RETURN")
            listing.append(f"block {number} {header}")
            listing += [f"{index} {line}" for index, line in enumerate(code)]
        return listing

    def block_number(self, index: int, count: int) -> int:
        return index + 1

    def run(self, source: str) -> str:
        """Executes the listing text: each block's lines are split into words."""
        listing = self.bytecode(source)
        if listing[0].startswith("error"):
            return listing[0]
        blocks: dict[int, dict[str, Any]] = {}
        current: dict[str, Any] = {"code": []}
        for line in listing:
            words = line.split()
            if words[0] == "block":
                head = words[2:]
                named = len(head) > 1 and not head[1].startswith("(")
                params = " ".join(head[2 if named else 1 :]).strip("()").split()
                current = blocks[int(words[1])] = {
                    "name": head[1] if named else None,
                    "params": params,
                    "code": [],
                }
            else:
                current["code"].append(words[1:])
        try:
            result = self.machine(blocks)
        except LangError as failure:
            return str(failure)
        return result.text() if isinstance(result, Fn) else str(result)

    def calls_in_progress(self, frames: list[Any]) -> int:
        return len(frames) - 1

    def machine(self, blocks: dict[int, dict[str, Any]]) -> Any:
        stack: list[Any] = []
        frames = [[0, 0, [{}]]]  # block, next instruction, scopes from the outside in

        def pos(words: list[str]) -> tuple[int, int]:
            line, column = words[-1].split(":")
            return (int(line), int(column))

        for _ in range(STEP_BUDGET):
            frame = frames[-1]
            words = blocks[frame[0]]["code"][frame[1]]
            frame[1] += 1
            names = {k: v for scope in frame[2] for k, v in scope.items()}
            op = words[0]
            if op == "PUSH":
                stack.append(int(words[1]))
            elif op == "LOAD":
                if words[1] not in names:
                    raise LangError("unbound", pos(words))
                stack.append(names[words[1]])
            elif op == "NEG":
                stack.append(self.minus(stack.pop(), pos(words)))
            elif op in OPERATOR:
                b, a = stack.pop(), stack.pop()
                stack.append(self.binary(OPERATOR[op], a, b, pos(words)))
            elif op == "JUMP_IF_ZERO":
                if not self.chooses_then(stack.pop(), pos(words)):
                    frame[1] = int(words[1])
            elif op == "JUMP":
                frame[1] = int(words[1])
            elif op == "BIND":
                frame[2] = [*frame[2], {words[1]: stack.pop()}]
            elif op == "UNBIND":
                frame[2] = frame[2][:-1]
            elif op == "CLOSURE":
                block = blocks[int(words[1])]
                stack.append(Fn(block["name"], block["params"], None, names, int(words[1])))
            elif op == "CALL":
                count = int(words[1])
                args = stack[len(stack) - count :]
                del stack[len(stack) - count :]
                fn = stack.pop()
                scope = self.enter(fn, args, self.calls_in_progress(frames), pos(words), names)
                frames.append([fn.block, 0, [scope]])
            elif op == "RETURN":
                frames.pop()
                if not frames:
                    return stack.pop()
        raise RuntimeError("the machine ran out of steps")


# ------------------------------------------------------------------ level 1 mistakes
class OneCharacterSymbolsFirst(Model):
    """Tries `>` before `>=`, so two-character symbols split."""

    def symbols(self) -> tuple[str, ...]:
        return tuple(sorted(SYMBOLS, key=len))


class ColumnsFromZero(Model):
    """Counts columns from 0."""

    def first_column(self) -> int:
        return 0


class TabIsFourColumns(Model):
    """Counts a tab as four columns."""

    def width(self, char: str) -> int:
        return 4 if char == "\t" else 1


class EndStaysOnTheLastLine(Model):
    """Puts the end token just after the last token, ignoring the newlines after it."""

    def scan(self, source: str) -> list[tuple[str, str, tuple[int, int]]]:
        found = super().scan(source)
        if len(found) > 1:
            _, text, (row, col) = found[-2]
            found[-1] = ("end", "", (row, col + len(text)))
        return found


class LeadingZerosAllowed(Model):
    """Accepts a number that starts with 0."""

    def number_is_fine(self, digits: str) -> bool:
        return int(digits) <= HIGH


class NumbersWithoutALimit(Model):
    """Accepts a number above 2147483647."""

    def number_is_fine(self, digits: str) -> bool:
        return digits == "0" or not digits.startswith("0")


class KeywordFoundInsideAName(Model):
    """Reads a keyword at the start of a longer name: `letter` is `let` then `ter`."""

    def word_pattern(self) -> str:
        return "|".join(KEYWORDS) + r"|[A-Za-z_][A-Za-z0-9_]*"


class AnyLetterStartsAName(Model):
    """Accepts letters outside ASCII in names."""

    def word_pattern(self) -> str:
        return r"[^\W\d][\w]*"


class CarriageReturnIsWhitespace(Model):
    """Skips a carriage return as whitespace."""

    def blank(self) -> str:
        return " \t\r"


# ------------------------------------------------------------------ level 2 mistakes
class PowerGroupsFromTheLeft(Model):
    """Groups `^` from the left."""

    def power(self) -> Tree:
        base = self.postfix()
        while self.is_symbol("^"):
            pos = self.want("symbol")[2]
            base = ("bin", "^", base, self.postfix(), pos)
        return base


class MinusBindsTighterThanPower(Model):
    """Reads `-2 ^ 2` as `(-2) ^ 2`."""

    def unary(self) -> Tree:
        node = self.signed()
        if self.is_symbol("^"):
            caret = self.want("symbol")[2]
            return ("bin", "^", node, self.unary(), caret)
        return node

    def signed(self) -> Tree:
        if self.is_symbol("-"):
            pos = self.want("symbol")[2]
            return ("neg", self.signed(), pos)
        return self.postfix()


class MinusBindsLooserThanTimes(Model):
    """Reads `-x * y` as `-(x * y)`."""

    def product(self) -> Tree:
        if self.is_symbol("-"):
            pos = self.want("symbol")[2]
            return ("neg", self.product(), pos)
        return self.chain(("*", "/", "%"), self.unary)


class ComparisonsBindTighterThanSums(Model):
    """Puts the comparisons above `+` and `-`."""

    def expr(self) -> Tree:
        return self.chain(("+", "-"), self.compared)

    def compared(self) -> Tree:
        return self.chain(("==", "!=", "<", "<=", ">", ">="), self.product)


class TailStopsAtTheFirstOperator(Model):
    """Parses the body of `let`, `if` and `fn` as a single operand."""

    def tail(self) -> Tree:
        return self.unary()


class DuplicateParametersAllowed(Model):
    """Accepts a parameter name twice."""

    def check_param(self, params: list[str], param: tuple[str, str, tuple[int, int]]) -> None:
        return None


class ErrorAtThePreviousToken(Model):
    """Reports an unexpected token at the token before it."""

    def fail_here(self) -> LangError:
        return LangError("unexpected-token", self.tokens[max(0, self.at - 1)][2])


class CallAppliesToTheNegation(Model):
    """Reads `-f(2)` as `(-f)(2)`."""

    def unary(self) -> Tree:
        if self.is_symbol("-"):
            pos = self.want("symbol")[2]
            node: Tree = ("neg", self.unary_operand(), pos)
            while self.is_symbol("("):
                paren = self.want("symbol")[2]
                args = [] if self.is_symbol(")") else [self.expr()]
                while self.is_symbol(","):
                    self.at += 1
                    args.append(self.expr())
                self.want("symbol", ")")
                node = ("call", node, args, paren)
            return node
        return self.power()

    def unary_operand(self) -> Tree:
        if self.is_symbol("-"):
            return self.unary()
        return self.primary()


class TrailingTokensIgnored(Model):
    """Stops after the first complete expression."""

    def tree(self, source: str) -> Tree:
        self.tokens = self.scan(source)
        self.at = 0
        self.fns = 0
        return self.expr()


# ------------------------------------------------------------------ level 3 mistakes
class DynamicScope(Model):
    """Looks up a function's free names where it is called."""

    def enter(
        self, fn: Any, args: list[Any], depth: int, pos: tuple[int, int], caller: dict
    ) -> dict:
        super().enter(fn, args, depth, pos, caller)
        own = {fn.name: fn} if fn.name else {}
        return {**caller, **own, **dict(zip(fn.params, args, strict=True))}


class LetSeesItsOwnName(Model):
    """Computes a `let` value with its own name already hiding the outer one."""

    def let_scope(self, env: dict, name: str) -> dict:
        return {k: v for k, v in env.items() if k != name}


class DivisionFloors(Model):
    """Rounds a quotient down and gives the remainder the sign of the right operand."""

    def divide(self, a: int, b: int) -> int:
        return a // b

    def remainder(self, a: int, b: int) -> int:
        return a % b


class NoOverflowCheck(Model):
    """Lets results leave the range of values."""

    def fits(self, value: int, pos: tuple[int, int]) -> int:
        return value


class TypeCheckedBeforeTheRightOperand(Model):
    """Rejects a function on the left before computing the right operand."""

    def operands(self, node: Tree, env: dict, depth: int) -> int:
        _, op, left, right, pos = node
        a = self.value(left, env, depth)
        if isinstance(a, Fn):
            raise LangError("type", pos)
        return self.binary(op, a, self.value(right, env, depth), pos)


class DivisionByZeroBeforeTheType(Model):
    """Checks for a zero divisor before checking the operand types."""

    def binary(self, op: str, a: Any, b: Any, pos: tuple[int, int]) -> int:
        if op in "/%" and b == 0:
            raise LangError("div-zero", pos)
        return super().binary(op, a, b, pos)


class DepthAllowsOneMore(Model):
    """Fails only when more than `maxDepth` calls are in progress."""

    def enter(
        self, fn: Any, args: list[Any], depth: int, pos: tuple[int, int], caller: dict
    ) -> dict:
        return super().enter(fn, args, depth - 1, pos, caller)


class DepthStopsOneEarly(Model):
    """Counts the call being made as already in progress."""

    def enter(
        self, fn: Any, args: list[Any], depth: int, pos: tuple[int, int], caller: dict
    ) -> dict:
        return super().enter(fn, args, depth + 1, pos, caller)


class ChecksBeforeTheArguments(Model):
    """Checks the callee and the argument count before computing the arguments."""

    def calling(self, node: Tree, env: dict, depth: int) -> Any:
        _, callee, arguments, pos = node
        fn = self.value(callee, env, depth)
        if not isinstance(fn, Fn):
            raise LangError("not-callable", pos)
        if len(arguments) != len(fn.params):
            raise LangError("arity", pos)
        return super().calling(node, env, depth)


class DepthCheckedBeforeArity(Model):
    """Checks the depth before the argument count."""

    def enter(
        self, fn: Any, args: list[Any], depth: int, pos: tuple[int, int], caller: dict
    ) -> dict:
        if isinstance(fn, Fn) and depth >= self.max_depth:
            raise LangError("depth", pos)
        return super().enter(fn, args, depth, pos, caller)


class ArgumentsBeforeTheCallee(Model):
    """Computes the arguments before the function."""

    def calling(self, node: Tree, env: dict, depth: int) -> Any:
        _, callee, arguments, pos = node
        args = [self.value(argument, env, depth) for argument in arguments]
        fn = self.value(callee, env, depth)
        scope = self.enter(fn, args, depth, pos, env)
        return self.value(fn.body, scope, depth + 1)


class FunctionConditionIsTrue(Model):
    """Treats a function as a true condition."""

    def chooses_then(self, value: Any, pos: tuple[int, int]) -> bool:
        return isinstance(value, Fn) or value != 0


class FunctionNameVisibleOutside(Model):
    """Lets a named function's name leak into the `let` around it."""

    def let_scope(self, env: dict, name: str) -> dict:
        return env

    def value(self, node: Tree, env: dict, depth: int) -> Any:
        if node[0] == "let" and node[2][0] == "fn" and node[2][1]:
            bound = self.value(node[2], env, depth)
            return self.value(node[3], {**env, node[2][1]: bound, node[1]: bound}, depth)
        return super().value(node, env, depth)


class FunctionNameHidesAParameter(Model):
    """Binds the parameters first and the function's name over them."""

    def enter(
        self, fn: Any, args: list[Any], depth: int, pos: tuple[int, int], caller: dict
    ) -> dict:
        scope = super().enter(fn, args, depth, pos, caller)
        return {**scope, fn.name: fn} if fn.name else scope


class NegativeExponentGivesZero(Model):
    """Answers 0 for a negative exponent."""

    def raise_to(self, a: int, b: int, pos: tuple[int, int]) -> int:
        return 0 if b < 0 else super().raise_to(a, b, pos)


class RemainderOverflowsForMinusOne(Model):
    """Computes the quotient first, so `-2147483648 % -1` overflows."""

    def binary(self, op: str, a: Any, b: Any, pos: tuple[int, int]) -> int:
        if op == "%" and a == LOW and b == -1:
            raise LangError("overflow", pos)
        return super().binary(op, a, b, pos)


# ------------------------------------------------------------------ level 4 mistakes
class InnerBlocksNumberedFirst(Model):
    """Numbers each block after the blocks of the functions inside it."""

    def blocks_in_order(self, root: Tree) -> list[Tree]:
        found: list[Tree] = []

        def visit(node: Any) -> None:
            if isinstance(node, (tuple, list)):
                for part in node:
                    visit(part)
            if isinstance(node, tuple) and node and node[0] == "fn":
                found.append(node)

        visit(root)
        return found


class JumpTargetsRelative(Model):
    """Writes jump targets as distances from the jump."""

    def target(self, here: int, index: int) -> int:
        return index - here


class ElseStartsOneEarly(Model):
    """Points `JUMP_IF_ZERO` at the `JUMP` that ends the `then` branch."""

    def emit(self, node: Tree, out: list[str]) -> None:
        start = len(out)
        super().emit(node, out)
        if node[0] == "if":
            for index in range(start, len(out)):
                if out[index].startswith("JUMP_IF_ZERO"):
                    op, target, position = out[index].split()
                    out[index] = f"{op} {int(target) - 1} {position}"
                    break


class PositionOnEveryInstruction(Model):
    """Adds a position to `PUSH` too."""

    def emit(self, node: Tree, out: list[str]) -> None:
        if node[0] == "num":
            out.append(f"PUSH {node[1]} {self.where(node[2])}")
        else:
            super().emit(node, out)


class CallCountsTheFunction(Model):
    """Counts the function among the values `CALL` pops."""

    def argument_count(self, node: Tree) -> int:
        return len(node[2]) + 1


class MachineCountsTheProgramAsACall(Model):
    """Counts the program's own frame among the calls in progress."""

    def calls_in_progress(self, frames: list[Any]) -> int:
        return len(frames)


MISTAKES: Sequence[type[Model]] = Model.__subclasses__()


def outputs(model_type: type[Model], case: Mapping[str, Any]) -> list[Any]:
    """The output of every op of the case, `None` for the constructor."""
    model = model_type(*case["args"][0])
    calls = zip(case["ops"][1:], case["args"][1:], strict=True)
    return [None, *(getattr(model, op)(*arguments) for op, arguments in calls)]


def passes(model_type: type[Model], case: Mapping[str, Any]) -> bool:
    try:
        return outputs(model_type, case) == case["expected"]
    except (IndexError, KeyError, ValueError, TypeError, AttributeError, RuntimeError):
        return False


@pytest.fixture(autouse=True)
def deep_enough_for_the_model():
    """The model recurses once per nested expression and per call in progress, up to 100 deep."""
    limit = sys.getrecursionlimit()
    sys.setrecursionlimit(max(limit, 20_000))
    yield
    sys.setrecursionlimit(limit)


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
def test_the_model_of_the_statement_gives_every_expected_output(case):
    assert outputs(Model, case) == case["expected"]


@pytest.mark.parametrize("mistake", MISTAKES, ids=[mistake.__name__ for mistake in MISTAKES])
def test_a_hidden_case_catches_each_classic_mistake(mistake):
    assert not all(passes(mistake, case) for case in HIDDEN_CASES), mistake.__doc__


def test_every_level_has_two_visible_and_two_hidden_cases():
    for level in (1, 2, 3, 4):
        at_level = [case for case in CASES if case["level"] == level]
        assert sum(bool(case.get("visible")) for case in at_level) >= 2
        assert sum(not case.get("visible") for case in at_level) >= 2


def test_run_and_evaluate_agree_on_every_program_of_the_cases():
    for case in CASES:
        model = Model(case["args"][0][0])
        for op, arguments in zip(case["ops"], case["args"], strict=True):
            if op in ("evaluate", "run", "bytecode"):
                assert model.run(*arguments) == model.evaluate(*arguments), arguments
