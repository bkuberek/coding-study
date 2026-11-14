use std::collections::{BTreeMap, HashMap};
use std::fmt;
use std::rc::Rc;

const KEYWORDS: [&str; 6] = ["let", "in", "fn", "if", "then", "else"];
const TWO_CHAR_SYMBOLS: [&str; 5] = ["==", "!=", "<=", ">=", "=>"];
const ONE_CHAR_SYMBOLS: &str = "()+-*/%^<>=,";
const PREFIX_MINUS: u8 = 4;
const CALL: u8 = 6;
const LOWEST: u8 = 0;

/// Binding power of each binary operator; `^` groups to the right.
fn binding_power(operator: &str) -> Option<u8> {
    match operator {
        "==" | "!=" | "<" | "<=" | ">" | ">=" => Some(1),
        "+" | "-" => Some(2),
        "*" | "/" | "%" => Some(3),
        "^" => Some(5),
        _ => None,
    }
}

const OPCODES: [(&str, &str); 12] = [
    ("+", "ADD"), ("-", "SUB"), ("*", "MUL"), ("/", "DIV"), ("%", "MOD"), ("^", "POW"),
    ("==", "EQ"), ("!=", "NE"), ("<", "LT"), ("<=", "LE"), (">", "GT"), (">=", "GE"),
];

fn opcode_of(operator: &str) -> &'static str {
    OPCODES.iter().find(|(op, _)| *op == operator).map(|(_, code)| *code).unwrap_or("?")
}

fn operator_of(opcode: &str) -> Option<&'static str> {
    OPCODES.iter().find(|(_, code)| *code == opcode).map(|(op, _)| *op)
}

#[derive(Clone, Copy, Debug)]
struct Position(usize, usize);

impl fmt::Display for Position {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}:{}", self.0, self.1)
    }
}

#[derive(Debug)]
struct LangError {
    code: &'static str,
    position: Position,
}

impl fmt::Display for LangError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "error {} {}", self.code, self.position)
    }
}

type Outcome<T> = Result<T, LangError>;

fn fail<T>(code: &'static str, position: Position) -> Outcome<T> {
    Err(LangError { code, position })
}

struct Token {
    kind: &'static str,
    text: String,
    position: Position,
}

impl Token {
    fn describe(&self) -> String {
        if self.kind == "end" {
            format!("end {}", self.position)
        } else {
            format!("{} {} {}", self.kind, self.text, self.position)
        }
    }
}

// ------------------------------------------------------------------------------ level 1: tokens
fn is_letter(c: u8) -> bool {
    c.is_ascii_alphabetic() || c == b'_'
}

/// Works on bytes: every character that can be part of a token is ASCII, a character outside
/// ASCII is an error at its first byte, and one inside a comment is skipped up to the newline.
fn scan(source: &str) -> Outcome<Vec<Token>> {
    let bytes = source.as_bytes();
    let mut tokens = Vec::new();
    let (mut index, mut line, mut column) = (0, 1, 1);
    while index < bytes.len() {
        let c = bytes[index];
        let here = Position(line, column);
        let length = match c {
            b'\n' => {
                index += 1;
                line += 1;
                column = 1;
                continue;
            }
            b' ' | b'\t' => 1,
            b'#' => bytes[index..].iter().position(|&b| b == b'\n').unwrap_or(bytes.len() - index),
            b'0'..=b'9' => {
                let end = index + bytes[index..].iter().take_while(|b| b.is_ascii_digit()).count();
                let digits = &source[index..end];
                let fits = digits.parse::<i64>().map(|value| value <= i32::MAX as i64).unwrap_or(false);
                if (digits.len() > 1 && digits.starts_with('0')) || !fits {
                    return fail("bad-number", here);
                }
                tokens.push(Token { kind: "number", text: digits.to_string(), position: here });
                end - index
            }
            _ if is_letter(c) => {
                let end = index + bytes[index..].iter().take_while(|&&b| is_letter(b) || b.is_ascii_digit()).count();
                let word = &source[index..end];
                let kind = if KEYWORDS.contains(&word) { "keyword" } else { "name" };
                tokens.push(Token { kind, text: word.to_string(), position: here });
                end - index
            }
            _ if index + 2 <= bytes.len() && TWO_CHAR_SYMBOLS.iter().any(|s| s.as_bytes() == &bytes[index..index + 2]) => {
                tokens.push(Token { kind: "symbol", text: source[index..index + 2].to_string(), position: here });
                2
            }
            _ if ONE_CHAR_SYMBOLS.as_bytes().contains(&c) => {
                tokens.push(Token { kind: "symbol", text: (c as char).to_string(), position: here });
                1
            }
            _ => return fail("bad-char", here),
        };
        index += length;
        column += length;
    }
    tokens.push(Token { kind: "end", text: String::new(), position: Position(line, column) });
    Ok(tokens)
}

// ------------------------------------------------------------------------------ level 2: syntax tree
enum Node {
    Num(i64),
    Name(Position, String),
    Negate(Position, Box<Node>),
    Binary(Position, &'static str, Box<Node>, Box<Node>),
    Call(Position, Box<Node>, Vec<Node>),
    Let(String, Box<Node>, Box<Node>),
    If(Position, Box<Node>, Box<Node>, Box<Node>),
    Fn(Rc<Function>),
}

struct Function {
    name: Option<String>,
    params: Vec<String>,
    body: Node,
    block: usize,
}

/// A Pratt parser: each token knows how it starts an expression (prefix) and how it continues
/// one (infix), and `expression(minimum)` extends the left side while the next operator binds
/// tighter.
struct Parser {
    tokens: Vec<Token>,
    index: usize,
    functions: usize,
}

impl Parser {
    fn peek(&self) -> &Token {
        &self.tokens[self.index]
    }

    fn take(&mut self) -> &Token {
        self.index += 1;
        &self.tokens[self.index - 1]
    }

    fn peek_symbol(&self, text: &str) -> bool {
        self.peek().kind == "symbol" && self.peek().text == text
    }

    fn expect(&mut self, kind: &str, text: Option<&str>) -> Outcome<(String, Position)> {
        let token = self.peek();
        if token.kind != kind || text.is_some_and(|wanted| token.text != wanted) {
            return fail("unexpected-token", token.position);
        }
        let token = self.take();
        Ok((token.text.clone(), token.position))
    }

    fn program(&mut self) -> Outcome<Node> {
        let node = self.expression(LOWEST)?;
        self.expect("end", None)?;
        Ok(node)
    }

    fn expression(&mut self, minimum: u8) -> Outcome<Node> {
        let mut left = self.prefix()?;
        loop {
            let token = self.peek();
            if token.kind != "symbol" {
                return Ok(left);
            }
            let position = token.position;
            if token.text == "(" && CALL > minimum {
                left = self.call(left)?;
                continue;
            }
            let operator = match OPCODES.iter().find(|(op, _)| *op == token.text) {
                Some((op, _)) => *op,
                None => return Ok(left),
            };
            let power = binding_power(operator).unwrap_or(0);
            if power <= minimum {
                return Ok(left);
            }
            self.take();
            let right = self.expression(if operator == "^" { power - 1 } else { power })?;
            left = Node::Binary(position, operator, Box::new(left), Box::new(right));
        }
    }

    fn prefix(&mut self) -> Outcome<Node> {
        let token = self.take();
        let (kind, text, position) = (token.kind, token.text.clone(), token.position);
        match (kind, text.as_str()) {
            ("number", digits) => Ok(Node::Num(digits.parse().unwrap_or(0))),
            ("name", name) => Ok(Node::Name(position, name.to_string())),
            ("symbol", "-") => Ok(Node::Negate(position, Box::new(self.expression(PREFIX_MINUS)?))),
            ("symbol", "(") => {
                let inner = self.expression(LOWEST)?;
                self.expect("symbol", Some(")"))?;
                Ok(inner)
            }
            ("keyword", "let") => {
                let (name, _) = self.expect("name", None)?;
                self.expect("symbol", Some("="))?;
                let value = self.expression(LOWEST)?;
                self.expect("keyword", Some("in"))?;
                let body = self.expression(LOWEST)?;
                Ok(Node::Let(name, Box::new(value), Box::new(body)))
            }
            ("keyword", "if") => {
                let condition = self.expression(LOWEST)?;
                self.expect("keyword", Some("then"))?;
                let then = self.expression(LOWEST)?;
                self.expect("keyword", Some("else"))?;
                let otherwise = self.expression(LOWEST)?;
                Ok(Node::If(position, Box::new(condition), Box::new(then), Box::new(otherwise)))
            }
            ("keyword", "fn") => self.function(),
            _ => fail("unexpected-token", position),
        }
    }

    fn function(&mut self) -> Outcome<Node> {
        self.functions += 1;
        let block = self.functions;
        let name = if self.peek().kind == "name" { Some(self.take().text.clone()) } else { None };
        self.expect("symbol", Some("("))?;
        let mut params: Vec<String> = Vec::new();
        if !self.peek_symbol(")") {
            loop {
                let (param, at) = self.expect("name", None)?;
                if params.contains(&param) {
                    return fail("duplicate-param", at);
                }
                params.push(param);
                if !self.peek_symbol(",") {
                    break;
                }
                self.take();
            }
        }
        self.expect("symbol", Some(")"))?;
        self.expect("symbol", Some("=>"))?;
        let body = self.expression(LOWEST)?;
        Ok(Node::Fn(Rc::new(Function { name, params, body, block })))
    }

    fn call(&mut self, callee: Node) -> Outcome<Node> {
        let position = self.take().position;
        let mut args = Vec::new();
        if !self.peek_symbol(")") {
            args.push(self.expression(LOWEST)?);
            while self.peek_symbol(",") {
                self.take();
                args.push(self.expression(LOWEST)?);
            }
        }
        self.expect("symbol", Some(")"))?;
        Ok(Node::Call(position, Box::new(callee), args))
    }
}

fn parse_program(source: &str) -> Outcome<Node> {
    Parser { tokens: scan(source)?, index: 0, functions: 0 }.program()
}

fn head(function: &Function) -> String {
    let named = match &function.name {
        Some(name) => format!("fn {} ", name),
        None => "fn ".to_string(),
    };
    format!("{}({})", named, function.params.join(" "))
}

fn show(node: &Node) -> String {
    match node {
        Node::Num(value) => value.to_string(),
        Node::Name(_, name) => name.clone(),
        Node::Negate(_, operand) => format!("(neg {})", show(operand)),
        Node::Binary(_, operator, left, right) => format!("({} {} {})", operator, show(left), show(right)),
        Node::Call(_, callee, args) => {
            let mut parts = vec!["call".to_string(), show(callee)];
            parts.extend(args.iter().map(show));
            format!("({})", parts.join(" "))
        }
        Node::Let(name, value, body) => format!("(let {} {} {})", name, show(value), show(body)),
        Node::If(_, condition, then, otherwise) => format!("(if {} {} {})", show(condition), show(then), show(otherwise)),
        Node::Fn(function) => format!("({} {})", head(function), show(&function.body)),
    }
}

// ------------------------------------------------------------------------------ level 3: evaluation
#[derive(Clone)]
enum Value {
    Int(i64),
    Fn(Rc<Closure>),
}

impl fmt::Display for Value {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Value::Int(number) => write!(f, "{}", number),
            Value::Fn(closure) => match &closure.name {
                Some(name) => write!(f, "<fn {}>", name),
                None => write!(f, "<fn>"),
            },
        }
    }
}

/// One level of names; lookups walk outwards to the enclosing levels.
struct Scope {
    parent: Option<Rc<Scope>>,
    names: HashMap<String, Value>,
}

impl Scope {
    fn lookup(scope: &Rc<Scope>, name: &str, position: Position) -> Outcome<Value> {
        let mut current = Some(scope);
        while let Some(level) = current {
            if let Some(found) = level.names.get(name) {
                return Ok(found.clone());
            }
            current = level.parent.as_ref();
        }
        fail("unbound", position)
    }
}

struct Closure {
    name: Option<String>,
    params: Vec<String>,
    scope: Rc<Scope>,
    function: Option<Rc<Function>>,
    block: usize,
}

fn call_scope(closure: &Rc<Closure>, args: Vec<Value>) -> Rc<Scope> {
    let mut names = HashMap::new();
    if let Some(name) = &closure.name {
        names.insert(name.clone(), Value::Fn(Rc::clone(closure)));
    }
    for (param, arg) in closure.params.iter().zip(args) {
        names.insert(param.clone(), arg);
    }
    Rc::new(Scope { parent: Some(Rc::clone(&closure.scope)), names })
}

fn checked(value: i64, position: Position) -> Outcome<i64> {
    if value < i32::MIN as i64 || value > i32::MAX as i64 {
        return fail("overflow", position);
    }
    Ok(value)
}

fn power(base: i64, exponent: i64, position: Position) -> Outcome<i64> {
    if (base == 0 || base == 1) && exponent > 0 {
        return Ok(base);
    }
    if base == -1 {
        return Ok(if exponent % 2 == 1 { -1 } else { 1 });
    }
    let mut result = 1;
    for _ in 0..exponent {
        result = checked(result * base, position)?;
    }
    Ok(result)
}

fn apply_binary(operator: &str, left: &Value, right: &Value, position: Position) -> Outcome<Value> {
    let (&Value::Int(a), &Value::Int(b)) = (left, right) else {
        return fail("type", position);
    };
    if (operator == "/" || operator == "%") && b == 0 {
        return fail("div-zero", position);
    }
    if operator == "^" && b < 0 {
        return fail("negative-exponent", position);
    }
    let result = match operator {
        "+" => checked(a + b, position)?,
        "-" => checked(a - b, position)?,
        "*" => checked(a * b, position)?,
        "/" => checked(a / b, position)?,
        "%" => a % b,
        "^" => power(a, b, position)?,
        "==" => (a == b) as i64,
        "!=" => (a != b) as i64,
        "<" => (a < b) as i64,
        "<=" => (a <= b) as i64,
        ">" => (a > b) as i64,
        _ => (a >= b) as i64,
    };
    Ok(Value::Int(result))
}

fn negate(value: &Value, position: Position) -> Outcome<Value> {
    match value {
        Value::Int(number) => Ok(Value::Int(checked(-number, position)?)),
        Value::Fn(_) => fail("type", position),
    }
}

fn check_call(callee: &Value, count: usize, depth: usize, max_depth: usize, position: Position) -> Outcome<Rc<Closure>> {
    let Value::Fn(closure) = callee else {
        return fail("not-callable", position);
    };
    if count != closure.params.len() {
        return fail("arity", position);
    }
    if depth >= max_depth {
        return fail("depth", position);
    }
    Ok(Rc::clone(closure))
}

fn truth(value: &Value, position: Position) -> Outcome<bool> {
    match value {
        Value::Int(number) => Ok(*number != 0),
        Value::Fn(_) => fail("type", position),
    }
}

struct TreeWalker {
    max_depth: usize,
}

impl TreeWalker {
    fn run(&self, node: &Node, scope: &Rc<Scope>, depth: usize) -> Outcome<Value> {
        match node {
            Node::Num(value) => Ok(Value::Int(*value)),
            Node::Name(position, name) => Scope::lookup(scope, name, *position),
            Node::Negate(position, operand) => negate(&self.run(operand, scope, depth)?, *position),
            Node::Binary(position, operator, left, right) => {
                let first = self.run(left, scope, depth)?;
                let second = self.run(right, scope, depth)?;
                apply_binary(operator, &first, &second, *position)
            }
            Node::If(position, condition, then, otherwise) => {
                let chosen = if truth(&self.run(condition, scope, depth)?, *position)? { then } else { otherwise };
                self.run(chosen, scope, depth)
            }
            Node::Let(name, value, body) => {
                let bound = self.run(value, scope, depth)?;
                let inner = Rc::new(Scope { parent: Some(Rc::clone(scope)), names: HashMap::from([(name.clone(), bound)]) });
                self.run(body, &inner, depth)
            }
            Node::Fn(function) => Ok(Value::Fn(Rc::new(Closure {
                name: function.name.clone(),
                params: function.params.clone(),
                scope: Rc::clone(scope),
                function: Some(Rc::clone(function)),
                block: function.block,
            }))),
            Node::Call(position, callee, args) => {
                let function = self.run(callee, scope, depth)?;
                let mut values = Vec::with_capacity(args.len());
                for arg in args {
                    values.push(self.run(arg, scope, depth)?);
                }
                let closure = check_call(&function, values.len(), depth, self.max_depth, *position)?;
                let body = Rc::clone(closure.function.as_ref().expect("a tree-walker closure has its body"));
                self.run(&body.body, &call_scope(&closure, values), depth + 1)
            }
        }
    }
}

// ------------------------------------------------------------------------------ level 4: bytecode
enum Operand {
    None,
    Int(i64),
    Name(String),
}

struct Instruction {
    opcode: &'static str,
    operand: Operand,
    position: Option<Position>,
}

impl Instruction {
    fn new(opcode: &'static str, operand: Operand, position: Option<Position>) -> Self {
        Instruction { opcode, operand, position }
    }

    fn describe(&self) -> String {
        let mut parts = vec![self.opcode.to_string()];
        match &self.operand {
            Operand::None => {}
            Operand::Int(number) => parts.push(number.to_string()),
            Operand::Name(name) => parts.push(name.clone()),
        }
        if let Some(position) = self.position {
            parts.push(position.to_string());
        }
        parts.join(" ")
    }

    fn number(&self) -> usize {
        match self.operand {
            Operand::Int(number) => number as usize,
            _ => 0,
        }
    }

    fn name(&self) -> &str {
        match &self.operand {
            Operand::Name(name) => name,
            _ => "",
        }
    }
}

struct Block {
    header: String,
    name: Option<String>,
    params: Vec<String>,
    code: Vec<Instruction>,
}

struct Compiler {
    blocks: BTreeMap<usize, Block>,
}

impl Compiler {
    fn program(node: &Node) -> Vec<Block> {
        let mut compiler = Compiler { blocks: BTreeMap::new() };
        let main = Block { header: "main".to_string(), name: None, params: Vec::new(), code: Vec::new() };
        compiler.blocks.insert(0, main);
        compiler.emit_block(0, node);
        compiler.blocks.into_values().collect()
    }

    fn emit_block(&mut self, number: usize, body: &Node) {
        let mut code = Vec::new();
        self.emit(body, &mut code);
        code.push(Instruction::new("RETURN", Operand::None, None));
        if let Some(block) = self.blocks.get_mut(&number) {
            block.code = code;
        }
    }

    fn emit(&mut self, node: &Node, code: &mut Vec<Instruction>) {
        match node {
            Node::Num(value) => code.push(Instruction::new("PUSH", Operand::Int(*value), None)),
            Node::Name(position, name) => code.push(Instruction::new("LOAD", Operand::Name(name.clone()), Some(*position))),
            Node::Negate(position, operand) => {
                self.emit(operand, code);
                code.push(Instruction::new("NEG", Operand::None, Some(*position)));
            }
            Node::Binary(position, operator, left, right) => {
                self.emit(left, code);
                self.emit(right, code);
                code.push(Instruction::new(opcode_of(operator), Operand::None, Some(*position)));
            }
            Node::If(position, condition, then, otherwise) => {
                self.emit(condition, code);
                let to_else = code.len();
                code.push(Instruction::new("JUMP_IF_ZERO", Operand::None, Some(*position)));
                self.emit(then, code);
                let to_end = code.len();
                code.push(Instruction::new("JUMP", Operand::None, None));
                code[to_else].operand = Operand::Int(code.len() as i64);
                self.emit(otherwise, code);
                code[to_end].operand = Operand::Int(code.len() as i64);
            }
            Node::Let(name, value, body) => {
                self.emit(value, code);
                code.push(Instruction::new("BIND", Operand::Name(name.clone()), None));
                self.emit(body, code);
                code.push(Instruction::new("UNBIND", Operand::None, None));
            }
            Node::Fn(function) => {
                let block = Block {
                    header: head(function),
                    name: function.name.clone(),
                    params: function.params.clone(),
                    code: Vec::new(),
                };
                self.blocks.insert(function.block, block);
                self.emit_block(function.block, &function.body);
                code.push(Instruction::new("CLOSURE", Operand::Int(function.block as i64), None));
            }
            Node::Call(position, callee, args) => {
                self.emit(callee, code);
                for arg in args {
                    self.emit(arg, code);
                }
                code.push(Instruction::new("CALL", Operand::Int(args.len() as i64), Some(*position)));
            }
        }
    }
}

struct Frame {
    block: usize,
    scope: Rc<Scope>,
    ip: usize,
}

/// A stack machine: one value stack shared by all frames, and a frame per active call. The loop
/// never recurses, so the depth limit is the only bound on calls.
fn execute(blocks: &[Block], max_depth: usize) -> Outcome<Value> {
    let mut stack: Vec<Value> = Vec::new();
    let empty = Rc::new(Scope { parent: None, names: HashMap::new() });
    let mut frames = vec![Frame { block: 0, scope: empty, ip: 0 }];
    loop {
        let frame = frames.last_mut().expect("the program's frame runs until it returns");
        let instruction = &blocks[frame.block].code[frame.ip];
        frame.ip += 1;
        let position = instruction.position.unwrap_or(Position(0, 0));
        let mut pop = || stack.pop().expect("the compiler balances the stack");
        if let Some(operator) = operator_of(instruction.opcode) {
            let right = pop();
            let left = pop();
            let result = apply_binary(operator, &left, &right, position)?;
            stack.push(result);
            continue;
        }
        match instruction.opcode {
            "PUSH" => stack.push(Value::Int(instruction.number() as i64)),
            "LOAD" => {
                let found = Scope::lookup(&frame.scope, instruction.name(), position)?;
                stack.push(found);
            }
            "NEG" => {
                let operand = pop();
                stack.push(negate(&operand, position)?);
            }
            "JUMP_IF_ZERO" => {
                if !truth(&pop(), position)? {
                    frame.ip = instruction.number();
                }
            }
            "JUMP" => frame.ip = instruction.number(),
            "BIND" => {
                let bound = pop();
                let names = HashMap::from([(instruction.name().to_string(), bound)]);
                frame.scope = Rc::new(Scope { parent: Some(Rc::clone(&frame.scope)), names });
            }
            "UNBIND" => {
                let parent = frame.scope.parent.clone().expect("UNBIND follows a BIND");
                frame.scope = parent;
            }
            "CLOSURE" => {
                let number = instruction.number();
                let block = &blocks[number];
                stack.push(Value::Fn(Rc::new(Closure {
                    name: block.name.clone(),
                    params: block.params.clone(),
                    scope: Rc::clone(&frame.scope),
                    function: None,
                    block: number,
                })));
            }
            "CALL" => {
                let count = instruction.number();
                let args = stack.split_off(stack.len() - count);
                let callee = stack.pop().expect("the callee sits below its arguments");
                let depth = frames.len() - 1;
                let closure = check_call(&callee, count, depth, max_depth, position)?;
                frames.push(Frame { block: closure.block, scope: call_scope(&closure, args), ip: 0 });
            }
            _ => {
                frames.pop();
                if frames.is_empty() {
                    return Ok(stack.pop().expect("a block leaves its value"));
                }
            }
        }
    }
}

fn listing(blocks: &[Block]) -> Vec<String> {
    let mut lines = Vec::new();
    for (number, block) in blocks.iter().enumerate() {
        lines.push(format!("block {} {}", number, block.header));
        for (index, instruction) in block.code.iter().enumerate() {
            lines.push(format!("{} {}", index, instruction.describe()));
        }
    }
    lines
}

pub struct Interpreter {
    max_depth: usize,
}

impl Interpreter {
    pub fn new(max_depth: i32) -> Self {
        Interpreter { max_depth: max_depth.max(0) as usize }
    }

    // Level 1
    pub fn tokenize(&mut self, source: String) -> Vec<String> {
        match scan(&source) {
            Ok(tokens) => tokens.iter().map(Token::describe).collect(),
            Err(error) => vec![error.to_string()],
        }
    }

    // Level 2
    pub fn parse(&mut self, source: String) -> String {
        match parse_program(&source) {
            Ok(node) => show(&node),
            Err(error) => error.to_string(),
        }
    }

    // Level 3
    pub fn evaluate(&mut self, source: String) -> String {
        let walker = TreeWalker { max_depth: self.max_depth };
        let empty = Rc::new(Scope { parent: None, names: HashMap::new() });
        match parse_program(&source).and_then(|node| walker.run(&node, &empty, 0)) {
            Ok(value) => value.to_string(),
            Err(error) => error.to_string(),
        }
    }

    // Level 4
    pub fn bytecode(&mut self, source: String) -> Vec<String> {
        match parse_program(&source) {
            Ok(node) => listing(&Compiler::program(&node)),
            Err(error) => vec![error.to_string()],
        }
    }

    pub fn run(&mut self, source: String) -> String {
        match parse_program(&source).and_then(|node| execute(&Compiler::program(&node), self.max_depth)) {
            Ok(value) => value.to_string(),
            Err(error) => error.to_string(),
        }
    }
}
