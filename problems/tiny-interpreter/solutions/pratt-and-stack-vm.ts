const KEYWORDS = new Set(["let", "in", "fn", "if", "then", "else"]);
const TWO_CHAR_SYMBOLS = new Set(["==", "!=", "<=", ">=", "=>"]);
const ONE_CHAR_SYMBOLS = new Set([..."()+-*/%^<>=,"]);
const INT_MIN = -2147483648;
const INT_MAX = 2147483647;

// Binding power of each binary operator; `^` groups to the right.
const BINARY = new Map<string, number>([
  ["==", 1], ["!=", 1], ["<", 1], ["<=", 1], [">", 1], [">=", 1],
  ["+", 2], ["-", 2],
  ["*", 3], ["/", 3], ["%", 3],
  ["^", 5],
]);
const PREFIX_MINUS = 4;
const CALL = 6;
const LOWEST = 0;
const OPCODES = new Map<string, string>([
  ["+", "ADD"], ["-", "SUB"], ["*", "MUL"], ["/", "DIV"], ["%", "MOD"], ["^", "POW"],
  ["==", "EQ"], ["!=", "NE"], ["<", "LT"], ["<=", "LE"], [">", "GT"], [">=", "GE"],
]);
const OPERATORS = new Map<string, string>([...OPCODES].map(([operator, opcode]) => [opcode, operator]));

type Position = [number, number];

class LangError extends Error {
  readonly code: string;
  readonly position: Position;

  constructor(code: string, position: Position) {
    super(code);
    this.code = code;
    this.position = position;
  }

  text(): string {
    return `error ${this.code} ${this.position[0]}:${this.position[1]}`;
  }
}

type Token = { kind: string; text: string; position: Position };

function tokenText(token: Token): string {
  const where = `${token.position[0]}:${token.position[1]}`;
  return token.kind === "end" ? `end ${where}` : `${token.kind} ${token.text} ${where}`;
}

// ------------------------------------------------------------------------------ level 1: tokens
const isDigit = (char: string): boolean => char >= "0" && char <= "9";
const isLetter = (char: string): boolean => (char >= "a" && char <= "z") || (char >= "A" && char <= "Z") || char === "_";

function tokenize(source: string): Token[] {
  const tokens: Token[] = [];
  let index = 0;
  let line = 1;
  let column = 1;
  const advance = (count: number): void => {
    index += count;
    column += count;
  };
  while (index < source.length) {
    const char = source[index];
    const here: Position = [line, column];
    if (char === "\n") {
      index++;
      line++;
      column = 1;
    } else if (char === " " || char === "\t") {
      advance(1);
    } else if (char === "#") {
      while (index < source.length && source[index] !== "\n") {
        advance(1);
      }
    } else if (isDigit(char)) {
      let end = index;
      while (end < source.length && isDigit(source[end])) {
        end++;
      }
      const digits = source.slice(index, end);
      if ((digits.length > 1 && digits[0] === "0") || digits.length > 10 || Number(digits) > INT_MAX) {
        throw new LangError("bad-number", here);
      }
      tokens.push({ kind: "number", text: digits, position: here });
      advance(end - index);
    } else if (isLetter(char)) {
      let end = index;
      while (end < source.length && (isLetter(source[end]) || isDigit(source[end]))) {
        end++;
      }
      const word = source.slice(index, end);
      tokens.push({ kind: KEYWORDS.has(word) ? "keyword" : "name", text: word, position: here });
      advance(end - index);
    } else if (TWO_CHAR_SYMBOLS.has(source.slice(index, index + 2))) {
      tokens.push({ kind: "symbol", text: source.slice(index, index + 2), position: here });
      advance(2);
    } else if (ONE_CHAR_SYMBOLS.has(char)) {
      tokens.push({ kind: "symbol", text: char, position: here });
      advance(1);
    } else {
      throw new LangError("bad-char", here);
    }
  }
  tokens.push({ kind: "end", text: "", position: [line, column] });
  return tokens;
}

// ------------------------------------------------------------------------------ level 2: syntax tree
type Node =
  | { tag: "number"; position: Position; value: number }
  | { tag: "name"; position: Position; name: string }
  | { tag: "negate"; position: Position; operand: Node }
  | { tag: "binary"; position: Position; operator: string; left: Node; right: Node }
  | { tag: "call"; position: Position; callee: Node; args: Node[] }
  | { tag: "let"; position: Position; name: string; value: Node; body: Node }
  | { tag: "if"; position: Position; condition: Node; then: Node; otherwise: Node }
  | FunctionNode;

type FunctionNode = {
  tag: "fn";
  position: Position;
  name: string | null;
  params: string[];
  body: Node;
  block: number;
};

// A Pratt parser: each token knows how it starts an expression (prefix) and how it continues one
// (infix), and `expression(minimum)` extends the left side while the next operator binds tighter.
class Parser {
  private readonly tokens: Token[];
  private index = 0;
  private functions = 0;

  constructor(tokens: Token[]) {
    this.tokens = tokens;
  }

  program(): Node {
    const node = this.expression(LOWEST);
    this.expect("end");
    return node;
  }

  private peek(): Token {
    return this.tokens[this.index];
  }

  private take(): Token {
    return this.tokens[this.index++];
  }

  private peekSymbol(text: string): boolean {
    const token = this.peek();
    return token.kind === "symbol" && token.text === text;
  }

  private expect(kind: string, text?: string): Token {
    const token = this.peek();
    if (token.kind !== kind || (text !== undefined && token.text !== text)) {
      throw new LangError("unexpected-token", token.position);
    }
    return this.take();
  }

  private expression(minimum: number): Node {
    let left = this.prefix();
    for (;;) {
      const token = this.peek();
      if (token.kind !== "symbol") {
        return left;
      }
      const power = BINARY.get(token.text);
      if (token.text === "(" && CALL > minimum) {
        left = this.call(left);
      } else if (power !== undefined && power > minimum) {
        this.take();
        const right = this.expression(token.text === "^" ? power - 1 : power);
        left = { tag: "binary", position: token.position, operator: token.text, left, right };
      } else {
        return left;
      }
    }
  }

  private prefix(): Node {
    const token = this.take();
    if (token.kind === "number") {
      return { tag: "number", position: token.position, value: Number(token.text) };
    }
    if (token.kind === "name") {
      return { tag: "name", position: token.position, name: token.text };
    }
    if (token.kind === "symbol" && token.text === "-") {
      return { tag: "negate", position: token.position, operand: this.expression(PREFIX_MINUS) };
    }
    if (token.kind === "symbol" && token.text === "(") {
      const inner = this.expression(LOWEST);
      this.expect("symbol", ")");
      return inner;
    }
    if (token.kind === "keyword" && token.text === "let") {
      const name = this.expect("name").text;
      this.expect("symbol", "=");
      const value = this.expression(LOWEST);
      this.expect("keyword", "in");
      return { tag: "let", position: token.position, name, value, body: this.expression(LOWEST) };
    }
    if (token.kind === "keyword" && token.text === "if") {
      const condition = this.expression(LOWEST);
      this.expect("keyword", "then");
      const then = this.expression(LOWEST);
      this.expect("keyword", "else");
      return { tag: "if", position: token.position, condition, then, otherwise: this.expression(LOWEST) };
    }
    if (token.kind === "keyword" && token.text === "fn") {
      return this.function(token);
    }
    throw new LangError("unexpected-token", token.position);
  }

  private function(keyword: Token): FunctionNode {
    const block = ++this.functions;
    const name = this.peek().kind === "name" ? this.take().text : null;
    this.expect("symbol", "(");
    const params: string[] = [];
    if (!this.peekSymbol(")")) {
      for (;;) {
        const param = this.expect("name");
        if (params.includes(param.text)) {
          throw new LangError("duplicate-param", param.position);
        }
        params.push(param.text);
        if (!this.peekSymbol(",")) {
          break;
        }
        this.take();
      }
    }
    this.expect("symbol", ")");
    this.expect("symbol", "=>");
    return { tag: "fn", position: keyword.position, name, params, body: this.expression(LOWEST), block };
  }

  private call(callee: Node): Node {
    const paren = this.take();
    const args: Node[] = [];
    if (!this.peekSymbol(")")) {
      args.push(this.expression(LOWEST));
      while (this.peekSymbol(",")) {
        this.take();
        args.push(this.expression(LOWEST));
      }
    }
    this.expect("symbol", ")");
    return { tag: "call", position: paren.position, callee, args };
  }
}

function parse(source: string): Node {
  return new Parser(tokenize(source)).program();
}

function head(node: FunctionNode): string {
  const named = node.name === null ? "fn " : `fn ${node.name} `;
  return `${named}(${node.params.join(" ")})`;
}

function show(node: Node): string {
  switch (node.tag) {
    case "number":
      return String(node.value);
    case "name":
      return node.name;
    case "negate":
      return `(neg ${show(node.operand)})`;
    case "binary":
      return `(${node.operator} ${show(node.left)} ${show(node.right)})`;
    case "call":
      return `(${["call", show(node.callee), ...node.args.map(show)].join(" ")})`;
    case "let":
      return `(let ${node.name} ${show(node.value)} ${show(node.body)})`;
    case "if":
      return `(if ${show(node.condition)} ${show(node.then)} ${show(node.otherwise)})`;
    case "fn":
      return `(${head(node)} ${show(node.body)})`;
  }
}

// ------------------------------------------------------------------------------ level 3: evaluation
// One level of names; lookups walk outwards to the enclosing levels.
class Scope {
  readonly parent: Scope | null;
  readonly names: Map<string, Value>;

  constructor(parent: Scope | null, names: Map<string, Value>) {
    this.parent = parent;
    this.names = names;
  }

  lookup(name: string, position: Position): Value {
    for (let scope: Scope | null = this; scope !== null; scope = scope.parent) {
      const value = scope.names.get(name);
      if (value !== undefined) {
        return value;
      }
    }
    throw new LangError("unbound", position);
  }
}

class Closure {
  readonly name: string | null;
  readonly params: string[];
  readonly scope: Scope;
  readonly body: Node | null;
  readonly block: number;

  constructor(name: string | null, params: string[], scope: Scope, body: Node | null, block: number) {
    this.name = name;
    this.params = params;
    this.scope = scope;
    this.body = body;
    this.block = block;
  }

  callScope(args: Value[]): Scope {
    const names = new Map<string, Value>();
    if (this.name !== null) {
      names.set(this.name, this);
    }
    this.params.forEach((param, index) => names.set(param, args[index]));
    return new Scope(this.scope, names);
  }
}

type Value = number | Closure;

function valueText(value: Value): string {
  if (value instanceof Closure) {
    return value.name === null ? "<fn>" : `<fn ${value.name}>`;
  }
  return String(value);
}

// Every intermediate result is an exact integer: a product of two values stays below 2^62, and
// whatever leaves the 32-bit range is rejected before it is used again.
function checked(value: number, position: Position): number {
  if (value < INT_MIN || value > INT_MAX) {
    throw new LangError("overflow", position);
  }
  return value;
}

function power(base: number, exponent: number, position: Position): number {
  if ((base === 0 || base === 1) && exponent > 0) {
    return base;
  }
  if (base === -1) {
    return exponent % 2 === 1 ? -1 : 1;
  }
  let result = 1;
  for (let step = 0; step < exponent; step++) {
    result = checked(result * base, position);
  }
  return result;
}

function applyBinary(operator: string, left: Value, right: Value, position: Position): number {
  if (typeof left !== "number" || typeof right !== "number") {
    throw new LangError("type", position);
  }
  if ((operator === "/" || operator === "%") && right === 0) {
    throw new LangError("div-zero", position);
  }
  if (operator === "^" && right < 0) {
    throw new LangError("negative-exponent", position);
  }
  switch (operator) {
    case "+":
      return checked(left + right, position);
    case "-":
      return checked(left - right, position);
    case "*":
      return checked(left * right, position);
    case "/":
      return checked(Math.trunc(left / right), position);
    case "%":
      return (left % right) + 0;
    case "^":
      return power(left, right, position);
    case "==":
      return left === right ? 1 : 0;
    case "!=":
      return left !== right ? 1 : 0;
    case "<":
      return left < right ? 1 : 0;
    case "<=":
      return left <= right ? 1 : 0;
    case ">":
      return left > right ? 1 : 0;
    default:
      return left >= right ? 1 : 0;
  }
}

function negate(value: Value, position: Position): number {
  if (typeof value !== "number") {
    throw new LangError("type", position);
  }
  return checked(0 - value, position);
}

function checkCall(callee: Value, count: number, depth: number, maxDepth: number, position: Position): Closure {
  if (!(callee instanceof Closure)) {
    throw new LangError("not-callable", position);
  }
  if (count !== callee.params.length) {
    throw new LangError("arity", position);
  }
  if (depth >= maxDepth) {
    throw new LangError("depth", position);
  }
  return callee;
}

function truth(value: Value, position: Position): boolean {
  if (typeof value !== "number") {
    throw new LangError("type", position);
  }
  return value !== 0;
}

function walk(node: Node, scope: Scope, depth: number, maxDepth: number): Value {
  switch (node.tag) {
    case "number":
      return node.value;
    case "name":
      return scope.lookup(node.name, node.position);
    case "negate":
      return negate(walk(node.operand, scope, depth, maxDepth), node.position);
    case "binary": {
      const left = walk(node.left, scope, depth, maxDepth);
      const right = walk(node.right, scope, depth, maxDepth);
      return applyBinary(node.operator, left, right, node.position);
    }
    case "if": {
      const chosen = truth(walk(node.condition, scope, depth, maxDepth), node.position) ? node.then : node.otherwise;
      return walk(chosen, scope, depth, maxDepth);
    }
    case "let": {
      const bound = walk(node.value, scope, depth, maxDepth);
      return walk(node.body, new Scope(scope, new Map([[node.name, bound]])), depth, maxDepth);
    }
    case "fn":
      return new Closure(node.name, node.params, scope, node.body, node.block);
    case "call": {
      const callee = walk(node.callee, scope, depth, maxDepth);
      const values = node.args.map((arg) => walk(arg, scope, depth, maxDepth));
      const closure = checkCall(callee, values.length, depth, maxDepth, node.position);
      return walk(closure.body as Node, closure.callScope(values), depth + 1, maxDepth);
    }
  }
}

// ------------------------------------------------------------------------------ level 4: bytecode
type Instruction = { opcode: string; operand: number | string | null; position: Position | null };

function instructionText(instruction: Instruction): string {
  const parts = [instruction.opcode];
  if (instruction.operand !== null) {
    parts.push(String(instruction.operand));
  }
  if (instruction.position !== null) {
    parts.push(`${instruction.position[0]}:${instruction.position[1]}`);
  }
  return parts.join(" ");
}

type Block = { header: string; name: string | null; params: string[]; code: Instruction[] };

class Compiler {
  private readonly blocks = new Map<number, Block>();

  program(node: Node): Block[] {
    this.blocks.set(0, { header: "main", name: null, params: [], code: [] });
    this.emitBlock(0, node);
    return [...this.blocks.keys()].sort((a, b) => a - b).map((key) => this.blocks.get(key) as Block);
  }

  private emitBlock(number: number, body: Node): void {
    const code = (this.blocks.get(number) as Block).code;
    this.emit(body, code);
    code.push({ opcode: "RETURN", operand: null, position: null });
  }

  private emit(node: Node, code: Instruction[]): void {
    switch (node.tag) {
      case "number":
        code.push({ opcode: "PUSH", operand: node.value, position: null });
        return;
      case "name":
        code.push({ opcode: "LOAD", operand: node.name, position: node.position });
        return;
      case "negate":
        this.emit(node.operand, code);
        code.push({ opcode: "NEG", operand: null, position: node.position });
        return;
      case "binary":
        this.emit(node.left, code);
        this.emit(node.right, code);
        code.push({ opcode: OPCODES.get(node.operator) as string, operand: null, position: node.position });
        return;
      case "if": {
        this.emit(node.condition, code);
        const toElse: Instruction = { opcode: "JUMP_IF_ZERO", operand: null, position: node.position };
        code.push(toElse);
        this.emit(node.then, code);
        const toEnd: Instruction = { opcode: "JUMP", operand: null, position: null };
        code.push(toEnd);
        toElse.operand = code.length;
        this.emit(node.otherwise, code);
        toEnd.operand = code.length;
        return;
      }
      case "let":
        this.emit(node.value, code);
        code.push({ opcode: "BIND", operand: node.name, position: null });
        this.emit(node.body, code);
        code.push({ opcode: "UNBIND", operand: null, position: null });
        return;
      case "fn":
        this.blocks.set(node.block, { header: head(node), name: node.name, params: node.params, code: [] });
        this.emitBlock(node.block, node.body);
        code.push({ opcode: "CLOSURE", operand: node.block, position: null });
        return;
      case "call":
        this.emit(node.callee, code);
        for (const arg of node.args) {
          this.emit(arg, code);
        }
        code.push({ opcode: "CALL", operand: node.args.length, position: node.position });
        return;
    }
  }
}

type Frame = { block: Block; scope: Scope; ip: number };

// A stack machine: one value stack shared by all frames, and a frame per active call. The loop
// never recurses, so the depth limit is the only bound on calls.
function execute(blocks: Block[], maxDepth: number): Value {
  const stack: Value[] = [];
  const frames: Frame[] = [{ block: blocks[0], scope: new Scope(null, new Map()), ip: 0 }];
  for (;;) {
    const frame = frames[frames.length - 1];
    const instruction = frame.block.code[frame.ip++];
    const position = instruction.position as Position;
    const operator = OPERATORS.get(instruction.opcode);
    if (operator !== undefined) {
      const right = stack.pop() as Value;
      const left = stack.pop() as Value;
      stack.push(applyBinary(operator, left, right, position));
      continue;
    }
    switch (instruction.opcode) {
      case "PUSH":
        stack.push(instruction.operand as number);
        break;
      case "LOAD":
        stack.push(frame.scope.lookup(instruction.operand as string, position));
        break;
      case "NEG":
        stack.push(negate(stack.pop() as Value, position));
        break;
      case "JUMP_IF_ZERO":
        if (!truth(stack.pop() as Value, position)) {
          frame.ip = instruction.operand as number;
        }
        break;
      case "JUMP":
        frame.ip = instruction.operand as number;
        break;
      case "BIND":
        frame.scope = new Scope(frame.scope, new Map([[instruction.operand as string, stack.pop() as Value]]));
        break;
      case "UNBIND":
        frame.scope = frame.scope.parent as Scope;
        break;
      case "CLOSURE": {
        const number = instruction.operand as number;
        const block = blocks[number];
        stack.push(new Closure(block.name, block.params, frame.scope, null, number));
        break;
      }
      case "CALL": {
        const args = stack.splice(stack.length - (instruction.operand as number));
        const callee = stack.pop() as Value;
        const closure = checkCall(callee, args.length, frames.length - 1, maxDepth, position);
        frames.push({ block: blocks[closure.block], scope: closure.callScope(args), ip: 0 });
        break;
      }
      case "RETURN":
        frames.pop();
        if (frames.length === 0) {
          return stack.pop() as Value;
        }
        break;
    }
  }
}

function listing(blocks: Block[]): string[] {
  const lines: string[] = [];
  blocks.forEach((block, number) => {
    lines.push(`block ${number} ${block.header}`);
    block.code.forEach((instruction, index) => lines.push(`${index} ${instructionText(instruction)}`));
  });
  return lines;
}

function guarded<T>(work: () => T, onError: (error: LangError) => T): T {
  try {
    return work();
  } catch (error) {
    if (error instanceof LangError) {
      return onError(error);
    }
    throw error;
  }
}

export class Interpreter {
  private readonly maxDepth: number;

  constructor(maxDepth: number) {
    this.maxDepth = maxDepth;
  }

  // Level 1
  tokenize(source: string): string[] {
    return guarded(() => tokenize(source).map(tokenText), (error) => [error.text()]);
  }

  // Level 2
  parse(source: string): string {
    return guarded(() => show(parse(source)), (error) => error.text());
  }

  // Level 3
  evaluate(source: string): string {
    return guarded(
      () => valueText(walk(parse(source), new Scope(null, new Map()), 0, this.maxDepth)),
      (error) => error.text(),
    );
  }

  // Level 4
  bytecode(source: string): string[] {
    return guarded(() => listing(new Compiler().program(parse(source))), (error) => [error.text()]);
  }

  run(source: string): string {
    return guarded(
      () => valueText(execute(new Compiler().program(parse(source)), this.maxDepth)),
      (error) => error.text(),
    );
  }
}
