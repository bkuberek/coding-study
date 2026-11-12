package tiny_interpreter

import (
	"fmt"
	"math"
	"slices"
	"strconv"
	"strings"
)

var keywords = map[string]bool{"let": true, "in": true, "fn": true, "if": true, "then": true, "else": true}
var twoCharSymbols = map[string]bool{"==": true, "!=": true, "<=": true, ">=": true, "=>": true}

const oneCharSymbols = "()+-*/%^<>=,"

// binary is the binding power of each binary operator; ^ groups to the right.
var binary = map[string]int{
	"==": 1, "!=": 1, "<": 1, "<=": 1, ">": 1, ">=": 1,
	"+": 2, "-": 2,
	"*": 3, "/": 3, "%": 3,
	"^": 5,
}

const (
	prefixMinus = 4
	callPower   = 6
	lowest      = 0
)

var opcodes = map[string]string{
	"+": "ADD", "-": "SUB", "*": "MUL", "/": "DIV", "%": "MOD", "^": "POW",
	"==": "EQ", "!=": "NE", "<": "LT", "<=": "LE", ">": "GT", ">=": "GE",
}
var operators = map[string]string{}

func init() {
	for operator, opcode := range opcodes {
		operators[opcode] = operator
	}
}

type position struct{ line, column int }

func (p position) String() string { return fmt.Sprintf("%d:%d", p.line, p.column) }

// langError travels as a panic from where a problem is found to the public method, which
// recovers it and turns it into the result text.
type langError struct {
	code  string
	where position
}

func fail(code string, where position) { panic(&langError{code, where}) }

func guard(onError func(text string)) {
	if recovered := recover(); recovered != nil {
		err, ok := recovered.(*langError)
		if !ok {
			panic(recovered)
		}
		onError(fmt.Sprintf("error %s %s", err.code, err.where))
	}
}

type token struct {
	kind, text string
	where      position
}

func (t token) describe() string {
	if t.kind == "end" {
		return "end " + t.where.String()
	}
	return t.kind + " " + t.text + " " + t.where.String()
}

// ------------------------------------------------------------------------------ level 1: tokens
func isDigit(c byte) bool  { return c >= '0' && c <= '9' }
func isLetter(c byte) bool { return (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || c == '_' }

// scan works on bytes: every character that can be part of a token is ASCII, a character outside
// ASCII is an error at its first byte, and one inside a comment is skipped up to the newline.
func scan(source string) []token {
	tokens := []token{}
	index, line, column := 0, 1, 1
	for index < len(source) {
		c := source[index]
		here := position{line, column}
		length := 0
		switch {
		case c == '\n':
			index, line, column = index+1, line+1, 1
			continue
		case c == ' ' || c == '\t':
			length = 1
		case c == '#':
			end := strings.IndexByte(source[index:], '\n')
			if end < 0 {
				end = len(source) - index
			}
			length = end
		case isDigit(c):
			end := index
			for end < len(source) && isDigit(source[end]) {
				end++
			}
			digits := source[index:end]
			value, err := strconv.ParseInt(digits, 10, 64)
			if (len(digits) > 1 && digits[0] == '0') || err != nil || value > math.MaxInt32 {
				fail("bad-number", here)
			}
			tokens = append(tokens, token{"number", digits, here})
			length = end - index
		case isLetter(c):
			end := index
			for end < len(source) && (isLetter(source[end]) || isDigit(source[end])) {
				end++
			}
			word := source[index:end]
			kind := "name"
			if keywords[word] {
				kind = "keyword"
			}
			tokens = append(tokens, token{kind, word, here})
			length = end - index
		case index+2 <= len(source) && twoCharSymbols[source[index:index+2]]:
			tokens = append(tokens, token{"symbol", source[index : index+2], here})
			length = 2
		case strings.IndexByte(oneCharSymbols, c) >= 0:
			tokens = append(tokens, token{"symbol", string(c), here})
			length = 1
		default:
			fail("bad-char", here)
		}
		index += length
		column += length
	}
	return append(tokens, token{"end", "", position{line, column}})
}

// ------------------------------------------------------------------------------ level 2: syntax tree
type node interface{ at() position }

type (
	numNode struct {
		where position
		value int
	}
	nameNode struct {
		where position
		name  string
	}
	negateNode struct {
		where   position
		operand node
	}
	binaryNode struct {
		where       position
		operator    string
		left, right node
	}
	callNode struct {
		where  position
		callee node
		args   []node
	}
	letNode struct {
		where       position
		name        string
		value, body node
	}
	ifNode struct {
		where                      position
		condition, then, otherwise node
	}
	fnNode struct {
		where  position
		name   string // empty for an anonymous function
		params []string
		body   node
		block  int
	}
)

func (n *numNode) at() position    { return n.where }
func (n *nameNode) at() position   { return n.where }
func (n *negateNode) at() position { return n.where }
func (n *binaryNode) at() position { return n.where }
func (n *callNode) at() position   { return n.where }
func (n *letNode) at() position    { return n.where }
func (n *ifNode) at() position     { return n.where }
func (n *fnNode) at() position     { return n.where }

// parser is a Pratt parser: each token knows how it starts an expression (prefix) and how it
// continues one (infix), and expression(minimum) extends the left side while the next operator
// binds tighter.
type parser struct {
	tokens    []token
	index     int
	functions int
}

func (p *parser) peek() token { return p.tokens[p.index] }

func (p *parser) take() token {
	t := p.tokens[p.index]
	p.index++
	return t
}

func (p *parser) peekSymbol(text string) bool {
	t := p.peek()
	return t.kind == "symbol" && t.text == text
}

func (p *parser) expect(kind, text string) token {
	t := p.peek()
	if t.kind != kind || (text != "" && t.text != text) {
		fail("unexpected-token", t.where)
	}
	return p.take()
}

func (p *parser) program() node {
	n := p.expression(lowest)
	p.expect("end", "")
	return n
}

func (p *parser) expression(minimum int) node {
	left := p.prefix()
	for {
		t := p.peek()
		if t.kind != "symbol" {
			return left
		}
		power, isBinary := binary[t.text]
		switch {
		case t.text == "(" && callPower > minimum:
			left = p.call(left)
		case isBinary && power > minimum:
			p.take()
			next := power
			if t.text == "^" {
				next = power - 1
			}
			left = &binaryNode{t.where, t.text, left, p.expression(next)}
		default:
			return left
		}
	}
}

func (p *parser) prefix() node {
	t := p.take()
	switch {
	case t.kind == "number":
		value, _ := strconv.Atoi(t.text)
		return &numNode{t.where, value}
	case t.kind == "name":
		return &nameNode{t.where, t.text}
	case t.kind == "symbol" && t.text == "-":
		return &negateNode{t.where, p.expression(prefixMinus)}
	case t.kind == "symbol" && t.text == "(":
		inner := p.expression(lowest)
		p.expect("symbol", ")")
		return inner
	case t.kind == "keyword" && t.text == "let":
		name := p.expect("name", "").text
		p.expect("symbol", "=")
		value := p.expression(lowest)
		p.expect("keyword", "in")
		return &letNode{t.where, name, value, p.expression(lowest)}
	case t.kind == "keyword" && t.text == "if":
		condition := p.expression(lowest)
		p.expect("keyword", "then")
		then := p.expression(lowest)
		p.expect("keyword", "else")
		return &ifNode{t.where, condition, then, p.expression(lowest)}
	case t.kind == "keyword" && t.text == "fn":
		return p.function(t)
	}
	fail("unexpected-token", t.where)
	return nil
}

func (p *parser) function(keyword token) node {
	p.functions++
	block := p.functions
	name := ""
	if p.peek().kind == "name" {
		name = p.take().text
	}
	p.expect("symbol", "(")
	params := []string{}
	if !p.peekSymbol(")") {
		for {
			param := p.expect("name", "")
			if slices.Contains(params, param.text) {
				fail("duplicate-param", param.where)
			}
			params = append(params, param.text)
			if !p.peekSymbol(",") {
				break
			}
			p.take()
		}
	}
	p.expect("symbol", ")")
	p.expect("symbol", "=>")
	return &fnNode{keyword.where, name, params, p.expression(lowest), block}
}

func (p *parser) call(callee node) node {
	paren := p.take()
	args := []node{}
	if !p.peekSymbol(")") {
		args = append(args, p.expression(lowest))
		for p.peekSymbol(",") {
			p.take()
			args = append(args, p.expression(lowest))
		}
	}
	p.expect("symbol", ")")
	return &callNode{paren.where, callee, args}
}

func parseProgram(source string) node {
	p := &parser{tokens: scan(source)}
	return p.program()
}

func head(fn *fnNode) string {
	named := "fn "
	if fn.name != "" {
		named = "fn " + fn.name + " "
	}
	return named + "(" + strings.Join(fn.params, " ") + ")"
}

func show(n node) string {
	switch n := n.(type) {
	case *numNode:
		return strconv.Itoa(n.value)
	case *nameNode:
		return n.name
	case *negateNode:
		return "(neg " + show(n.operand) + ")"
	case *binaryNode:
		return "(" + n.operator + " " + show(n.left) + " " + show(n.right) + ")"
	case *callNode:
		parts := []string{"call", show(n.callee)}
		for _, arg := range n.args {
			parts = append(parts, show(arg))
		}
		return "(" + strings.Join(parts, " ") + ")"
	case *letNode:
		return "(let " + n.name + " " + show(n.value) + " " + show(n.body) + ")"
	case *ifNode:
		return "(if " + show(n.condition) + " " + show(n.then) + " " + show(n.otherwise) + ")"
	case *fnNode:
		return "(" + head(n) + " " + show(n.body) + ")"
	}
	panic("unknown node")
}

// ------------------------------------------------------------------------------ level 3: evaluation
// A value is an int or a *closure.
type value any

// scope is one level of names; lookups walk outwards to the enclosing levels.
type scope struct {
	parent *scope
	names  map[string]value
}

func (s *scope) lookup(name string, where position) value {
	for current := s; current != nil; current = current.parent {
		if found, ok := current.names[name]; ok {
			return found
		}
	}
	fail("unbound", where)
	return nil
}

type closure struct {
	name   string
	params []string
	scope  *scope
	body   node
	block  int
}

func (c *closure) callScope(args []value) *scope {
	names := map[string]value{}
	if c.name != "" {
		names[c.name] = c
	}
	for index, param := range c.params {
		names[param] = args[index]
	}
	return &scope{c.scope, names}
}

func valueText(v value) string {
	if c, ok := v.(*closure); ok {
		if c.name == "" {
			return "<fn>"
		}
		return "<fn " + c.name + ">"
	}
	return strconv.Itoa(v.(int))
}

func checked(result int64, where position) int {
	if result < math.MinInt32 || result > math.MaxInt32 {
		fail("overflow", where)
	}
	return int(result)
}

func power(base, exponent int, where position) int {
	if (base == 0 || base == 1) && exponent > 0 {
		return base
	}
	if base == -1 {
		if exponent%2 == 1 {
			return -1
		}
		return 1
	}
	result := 1
	for step := 0; step < exponent; step++ {
		result = checked(int64(result)*int64(base), where)
	}
	return result
}

func applyBinary(operator string, left, right value, where position) int {
	a, leftIsInt := left.(int)
	b, rightIsInt := right.(int)
	if !leftIsInt || !rightIsInt {
		fail("type", where)
	}
	if (operator == "/" || operator == "%") && b == 0 {
		fail("div-zero", where)
	}
	if operator == "^" && b < 0 {
		fail("negative-exponent", where)
	}
	x, y := int64(a), int64(b)
	switch operator {
	case "+":
		return checked(x+y, where)
	case "-":
		return checked(x-y, where)
	case "*":
		return checked(x*y, where)
	case "/":
		return checked(x/y, where)
	case "%":
		return int(x % y)
	case "^":
		return power(a, b, where)
	}
	holds := map[string]bool{"==": x == y, "!=": x != y, "<": x < y, "<=": x <= y, ">": x > y, ">=": x >= y}
	if holds[operator] {
		return 1
	}
	return 0
}

func negate(v value, where position) int {
	number, ok := v.(int)
	if !ok {
		fail("type", where)
	}
	return checked(-int64(number), where)
}

func checkCall(callee value, count, depth, maxDepth int, where position) *closure {
	c, ok := callee.(*closure)
	if !ok {
		fail("not-callable", where)
	}
	if count != len(c.params) {
		fail("arity", where)
	}
	if depth >= maxDepth {
		fail("depth", where)
	}
	return c
}

func truth(v value, where position) bool {
	number, ok := v.(int)
	if !ok {
		fail("type", where)
	}
	return number != 0
}

func walk(n node, s *scope, depth, maxDepth int) value {
	switch n := n.(type) {
	case *numNode:
		return n.value
	case *nameNode:
		return s.lookup(n.name, n.where)
	case *negateNode:
		return negate(walk(n.operand, s, depth, maxDepth), n.where)
	case *binaryNode:
		left := walk(n.left, s, depth, maxDepth)
		right := walk(n.right, s, depth, maxDepth)
		return applyBinary(n.operator, left, right, n.where)
	case *ifNode:
		if truth(walk(n.condition, s, depth, maxDepth), n.where) {
			return walk(n.then, s, depth, maxDepth)
		}
		return walk(n.otherwise, s, depth, maxDepth)
	case *letNode:
		bound := walk(n.value, s, depth, maxDepth)
		return walk(n.body, &scope{s, map[string]value{n.name: bound}}, depth, maxDepth)
	case *fnNode:
		return &closure{n.name, n.params, s, n.body, n.block}
	case *callNode:
		callee := walk(n.callee, s, depth, maxDepth)
		args := make([]value, 0, len(n.args))
		for _, arg := range n.args {
			args = append(args, walk(arg, s, depth, maxDepth))
		}
		c := checkCall(callee, len(args), depth, maxDepth, n.where)
		return walk(c.body, c.callScope(args), depth+1, maxDepth)
	}
	panic("unknown node")
}

// ------------------------------------------------------------------------------ level 4: bytecode
type instruction struct {
	opcode  string
	operand any // an int, a string, or nil
	where   *position
}

func (i *instruction) describe() string {
	parts := []string{i.opcode}
	if i.operand != nil {
		parts = append(parts, fmt.Sprint(i.operand))
	}
	if i.where != nil {
		parts = append(parts, i.where.String())
	}
	return strings.Join(parts, " ")
}

type block struct {
	header string
	name   string
	params []string
	code   []*instruction
}

type compiler struct{ blocks map[int]*block }

func (c *compiler) program(n node) []*block {
	c.blocks = map[int]*block{0: {header: "main"}}
	c.emitBlock(0, n)
	ordered := make([]*block, len(c.blocks))
	for number, b := range c.blocks {
		ordered[number] = b
	}
	return ordered
}

func (c *compiler) emitBlock(number int, body node) {
	b := c.blocks[number]
	c.emit(body, b)
	b.code = append(b.code, &instruction{opcode: "RETURN"})
}

func (c *compiler) emit(n node, b *block) {
	at := func() *position { where := n.at(); return &where }
	switch n := n.(type) {
	case *numNode:
		b.code = append(b.code, &instruction{opcode: "PUSH", operand: n.value})
	case *nameNode:
		b.code = append(b.code, &instruction{"LOAD", n.name, at()})
	case *negateNode:
		c.emit(n.operand, b)
		b.code = append(b.code, &instruction{"NEG", nil, at()})
	case *binaryNode:
		c.emit(n.left, b)
		c.emit(n.right, b)
		b.code = append(b.code, &instruction{opcodes[n.operator], nil, at()})
	case *ifNode:
		c.emit(n.condition, b)
		toElse := &instruction{"JUMP_IF_ZERO", nil, at()}
		b.code = append(b.code, toElse)
		c.emit(n.then, b)
		toEnd := &instruction{opcode: "JUMP"}
		b.code = append(b.code, toEnd)
		toElse.operand = len(b.code)
		c.emit(n.otherwise, b)
		toEnd.operand = len(b.code)
	case *letNode:
		c.emit(n.value, b)
		b.code = append(b.code, &instruction{opcode: "BIND", operand: n.name})
		c.emit(n.body, b)
		b.code = append(b.code, &instruction{opcode: "UNBIND"})
	case *fnNode:
		c.blocks[n.block] = &block{header: head(n), name: n.name, params: n.params}
		c.emitBlock(n.block, n.body)
		b.code = append(b.code, &instruction{opcode: "CLOSURE", operand: n.block})
	case *callNode:
		c.emit(n.callee, b)
		for _, arg := range n.args {
			c.emit(arg, b)
		}
		b.code = append(b.code, &instruction{"CALL", len(n.args), at()})
	}
}

type frame struct {
	code  []*instruction
	scope *scope
	ip    int
}

// execute is a stack machine: one value stack shared by all frames, and a frame per active call.
// The loop never recurses, so the depth limit is the only bound on calls.
func execute(blocks []*block, maxDepth int) value {
	stack := []value{}
	pop := func() value {
		top := stack[len(stack)-1]
		stack = stack[:len(stack)-1]
		return top
	}
	frames := []*frame{{code: blocks[0].code, scope: &scope{nil, map[string]value{}}}}
	for {
		f := frames[len(frames)-1]
		in := f.code[f.ip]
		f.ip++
		var where position
		if in.where != nil {
			where = *in.where
		}
		if operator, ok := operators[in.opcode]; ok {
			right := pop()
			left := pop()
			stack = append(stack, applyBinary(operator, left, right, where))
			continue
		}
		switch in.opcode {
		case "PUSH":
			stack = append(stack, in.operand.(int))
		case "LOAD":
			stack = append(stack, f.scope.lookup(in.operand.(string), where))
		case "NEG":
			stack = append(stack, negate(pop(), where))
		case "JUMP_IF_ZERO":
			if !truth(pop(), where) {
				f.ip = in.operand.(int)
			}
		case "JUMP":
			f.ip = in.operand.(int)
		case "BIND":
			f.scope = &scope{f.scope, map[string]value{in.operand.(string): pop()}}
		case "UNBIND":
			f.scope = f.scope.parent
		case "CLOSURE":
			number := in.operand.(int)
			b := blocks[number]
			stack = append(stack, &closure{b.name, b.params, f.scope, nil, number})
		case "CALL":
			count := in.operand.(int)
			args := slices.Clone(stack[len(stack)-count:])
			stack = stack[:len(stack)-count]
			c := checkCall(pop(), count, len(frames)-1, maxDepth, where)
			frames = append(frames, &frame{code: blocks[c.block].code, scope: c.callScope(args)})
		case "RETURN":
			frames = frames[:len(frames)-1]
			if len(frames) == 0 {
				return pop()
			}
		}
	}
}

func listing(blocks []*block) []string {
	lines := []string{}
	for number, b := range blocks {
		lines = append(lines, fmt.Sprintf("block %d %s", number, b.header))
		for index, in := range b.code {
			lines = append(lines, fmt.Sprintf("%d %s", index, in.describe()))
		}
	}
	return lines
}

type Interpreter struct {
	maxDepth int
}

func NewInterpreter(maxDepth int) *Interpreter {
	return &Interpreter{maxDepth: maxDepth}
}

// Level 1
func (it *Interpreter) Tokenize(source string) (result []string) {
	defer guard(func(text string) { result = []string{text} })
	for _, t := range scan(source) {
		result = append(result, t.describe())
	}
	return result
}

// Level 2
func (it *Interpreter) Parse(source string) (result string) {
	defer guard(func(text string) { result = text })
	return show(parseProgram(source))
}

// Level 3
func (it *Interpreter) Evaluate(source string) (result string) {
	defer guard(func(text string) { result = text })
	return valueText(walk(parseProgram(source), &scope{nil, map[string]value{}}, 0, it.maxDepth))
}

// Level 4
func (it *Interpreter) Bytecode(source string) (result []string) {
	defer guard(func(text string) { result = []string{text} })
	c := &compiler{}
	return listing(c.program(parseProgram(source)))
}

func (it *Interpreter) Run(source string) (result string) {
	defer guard(func(text string) { result = text })
	c := &compiler{}
	return valueText(execute(c.program(parseProgram(source)), it.maxDepth))
}
