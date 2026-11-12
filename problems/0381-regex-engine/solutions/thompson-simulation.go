package regex_engine

import (
	"fmt"
	"strconv"
	"strings"
)

// node is a tree node: kind is lit, any, empty, class, cat, alt, star, plus or opt.
type node struct {
	kind    string
	ch      byte
	negated bool
	items   [][2]byte
	parts   []*node
}

func (n *node) showClass() string {
	parts := make([]string, len(n.items))
	for i, item := range n.items {
		if item[0] == item[1] {
			parts[i] = fmt.Sprintf("'%c'", item[0])
		} else {
			parts[i] = fmt.Sprintf("'%c'-'%c'", item[0], item[1])
		}
	}
	head := "class("
	if n.negated {
		head = "notclass("
	}
	return head + strings.Join(parts, ",") + ")"
}

func (n *node) show() string {
	switch n.kind {
	case "lit":
		return fmt.Sprintf("'%c'", n.ch)
	case "any", "empty":
		return n.kind
	case "class":
		return n.showClass()
	}
	parts := make([]string, len(n.parts))
	for i, part := range n.parts {
		parts[i] = part.show()
	}
	return n.kind + "(" + strings.Join(parts, ",") + ")"
}

func (n *node) matches(c byte) bool {
	inside := false
	for _, item := range n.items {
		if item[0] <= c && c <= item[1] {
			inside = true
		}
	}
	return inside != n.negated
}

type patternError struct {
	code     string
	position int
}

var repeats = map[byte]string{'*': "star", '+': "plus", '?': "opt"}

// parser is a recursive descent; a pattern has at most 100 characters, so the recursion stays
// shallow. The first error found stops it.
type parser struct {
	text string
	pos  int
	err  *patternError
}

func (p *parser) peek() (byte, bool) {
	if p.pos < len(p.text) {
		return p.text[p.pos], true
	}
	return 0, false
}

func (p *parser) fail(code string, position int) *node {
	if p.err == nil {
		p.err = &patternError{code, position}
	}
	return nil
}

func (p *parser) parse() *node {
	root := p.alternation()
	if p.err == nil && p.pos < len(p.text) {
		return p.fail("unmatched-paren", p.pos)
	}
	return root
}

func (p *parser) alternation() *node {
	branches := []*node{p.sequence()}
	for p.err == nil {
		c, ok := p.peek()
		if !ok || c != '|' {
			break
		}
		p.pos++
		branches = append(branches, p.sequence())
	}
	if len(branches) == 1 {
		return branches[0]
	}
	return &node{kind: "alt", parts: branches}
}

func (p *parser) sequence() *node {
	var items []*node
	for p.err == nil {
		c, ok := p.peek()
		if !ok || c == '|' || c == ')' {
			break
		}
		items = append(items, p.repetition())
	}
	switch len(items) {
	case 0:
		return &node{kind: "empty"}
	case 1:
		return items[0]
	}
	return &node{kind: "cat", parts: items}
}

func (p *parser) repetition() *node {
	if c, _ := p.peek(); repeats[c] != "" {
		return p.fail("nothing-to-repeat", p.pos)
	}
	result := p.atom()
	for p.err == nil {
		c, ok := p.peek()
		if !ok || repeats[c] == "" {
			break
		}
		result = &node{kind: repeats[c], parts: []*node{result}}
		p.pos++
	}
	return result
}

func (p *parser) atom() *node {
	start := p.pos
	c := p.text[p.pos]
	p.pos++
	switch c {
	case '(':
		inner := p.alternation()
		if p.err != nil {
			return nil
		}
		if next, ok := p.peek(); !ok || next != ')' {
			return p.fail("unclosed-group", start)
		}
		p.pos++
		return inner
	case '.':
		return &node{kind: "any"}
	case '[':
		return p.charClass(start)
	}
	return &node{kind: "lit", ch: c}
}

func (p *parser) charClass(start int) *node {
	negated := false
	if c, ok := p.peek(); ok && c == '^' {
		negated = true
		p.pos++
	}
	var items [][2]byte
	for {
		c, ok := p.peek()
		if !ok {
			return p.fail("unclosed-class", start)
		}
		if c == ']' {
			if len(items) == 0 {
				return p.fail("empty-class", start)
			}
			p.pos++
			return &node{kind: "class", negated: negated, items: items}
		}
		lowAt := p.pos
		low := c
		p.pos++
		next, ok := p.peek()
		if ok && next == '-' && p.pos+1 < len(p.text) && p.text[p.pos+1] != ']' {
			high := p.text[p.pos+1]
			if high < low {
				return p.fail("bad-range", lowAt)
			}
			p.pos += 2
			items = append(items, [2]byte{low, high})
		} else {
			items = append(items, [2]byte{low, low})
		}
	}
}

// automaton holds parallel slices: the kind of each state, the node labelling a char or class
// state, and its arrows.
type automaton struct {
	kind       []string
	label      []*node
	outs       [][]int
	finalState int
}

type hole struct{ state, index int }

func (a *automaton) add(kind string, label *node, arrows int) int {
	a.kind = append(a.kind, kind)
	a.label = append(a.label, label)
	out := make([]int, arrows)
	for i := range out {
		out[i] = -1
	}
	a.outs = append(a.outs, out)
	return len(a.kind) - 1
}

func (a *automaton) patch(holes []hole, target int) {
	for _, h := range holes {
		a.outs[h.state][h.index] = target
	}
}

func (a *automaton) fragment(n *node) (int, []hole) {
	switch n.kind {
	case "lit", "any", "empty", "class":
		kind := n.kind
		if kind == "lit" {
			kind = "char"
		}
		state := a.add(kind, n, 1)
		return state, []hole{{state, 0}}
	case "cat":
		start, holes := a.fragment(n.parts[0])
		for _, part := range n.parts[1:] {
			next, nextHoles := a.fragment(part)
			a.patch(holes, next)
			holes = nextHoles
		}
		return start, holes
	case "alt":
		split := a.add("split", nil, len(n.parts))
		var holes []hole
		for i, part := range n.parts {
			side, sideHoles := a.fragment(part)
			a.outs[split][i] = side
			holes = append(holes, sideHoles...)
		}
		return split, holes
	}
	inner, innerHoles := a.fragment(n.parts[0])
	split := a.add("split", nil, 2)
	a.outs[split][0] = inner
	switch n.kind {
	case "star":
		a.patch(innerHoles, split)
		return split, []hole{{split, 1}}
	case "plus":
		a.patch(innerHoles, split)
		return inner, []hole{{split, 1}}
	}
	return split, append(innerHoles, hole{split, 1})
}

// newAutomaton builds the fragments, adds the match state and renumbers breadth first from the
// start state: the start is 0, and each arrow's unseen target is next.
func newAutomaton(root *node) *automaton {
	a := &automaton{}
	start, holes := a.fragment(root)
	a.patch(holes, a.add("match", nil, 0))
	number := make([]int, len(a.kind))
	for i := range number {
		number[i] = -1
	}
	number[start] = 0
	order := []int{start}
	for i := 0; i < len(order); i++ {
		for _, target := range a.outs[order[i]] {
			if number[target] < 0 {
				number[target] = len(order)
				order = append(order, target)
			}
		}
	}
	b := &automaton{}
	for _, state := range order {
		out := make([]int, len(a.outs[state]))
		for j, target := range a.outs[state] {
			out[j] = number[target]
		}
		b.kind = append(b.kind, a.kind[state])
		b.label = append(b.label, a.label[state])
		b.outs = append(b.outs, out)
		if a.kind[state] == "match" {
			b.finalState = len(b.kind) - 1
		}
	}
	return b
}

func (a *automaton) line(state int) string {
	head := strconv.Itoa(state) + ": "
	switch a.kind[state] {
	case "char":
		head += fmt.Sprintf("char '%c'", a.label[state].ch)
	case "class":
		head += a.label[state].showClass()
	default:
		head += a.kind[state]
	}
	if len(a.outs[state]) == 0 {
		return head
	}
	targets := make([]string, len(a.outs[state]))
	for i, target := range a.outs[state] {
		targets[i] = strconv.Itoa(target)
	}
	return head + " -> " + strings.Join(targets, ", ")
}

func (a *automaton) accepts(state int, c byte) bool {
	switch a.kind[state] {
	case "char":
		return a.label[state].ch == c
	case "any":
		return true
	case "class":
		return a.label[state].matches(c)
	}
	return false
}

// closure returns every state reachable from the sources through split and empty arrows,
// sources included.
func (a *automaton) closure(sources []int) []int {
	seen := make([]bool, len(a.kind))
	var reached []int
	stack := make([]int, 0, len(sources))
	for i := len(sources) - 1; i >= 0; i-- {
		stack = append(stack, sources[i])
	}
	for len(stack) > 0 {
		state := stack[len(stack)-1]
		stack = stack[:len(stack)-1]
		if seen[state] {
			continue
		}
		seen[state] = true
		reached = append(reached, state)
		if a.kind[state] == "split" || a.kind[state] == "empty" {
			for i := len(a.outs[state]) - 1; i >= 0; i-- {
				stack = append(stack, a.outs[state][i])
			}
		}
	}
	return reached
}

func (a *automaton) run(text string) (bool, int) {
	current := a.closure([]int{0})
	steps := len(current)
	for i := 0; i < len(text); i++ {
		var targets []int
		for _, state := range current {
			if a.accepts(state, text[i]) {
				targets = append(targets, a.outs[state][0])
			}
		}
		current = a.closure(targets)
		steps += len(current)
		if len(current) == 0 {
			return false, steps
		}
	}
	for _, state := range current {
		if state == a.finalState {
			return true, steps
		}
	}
	return false, steps
}

type thread struct{ state, start int }

// leftmostLongest makes one pass: each live state carries the earliest start that reaches it, and
// the live list stays ordered by start. After a match, later starts are dropped and the scan goes
// on while a state with that start or an earlier one is alive.
func (a *automaton) leftmostLongest(text string) []int {
	found := false
	best := []int{-1, -1}
	var live []thread
	for position := 0; position <= len(text); position++ {
		if !found {
			have := make([]bool, len(a.kind))
			for _, t := range live {
				have[t.state] = true
			}
			for _, state := range a.closure([]int{0}) {
				if !have[state] {
					live = append(live, thread{state, position})
				}
			}
		}
		for _, t := range live {
			if t.state == a.finalState && (!found || t.start <= best[0]) {
				found = true
				best = []int{t.start, position}
			}
		}
		if found {
			kept := live[:0]
			for _, t := range live {
				if t.start <= best[0] {
					kept = append(kept, t)
				}
			}
			live = kept
		}
		if position == len(text) || len(live) == 0 {
			break
		}
		seen := make([]bool, len(a.kind))
		var moved []thread
		for _, t := range live {
			if !a.accepts(t.state, text[position]) {
				continue
			}
			for _, reached := range a.closure([]int{a.outs[t.state][0]}) {
				if !seen[reached] {
					seen[reached] = true
					moved = append(moved, thread{reached, t.start})
				}
			}
		}
		live = moved
	}
	return best
}

// RegexEngine parses with recursive descent, builds the automaton by Thompson's construction and
// matches by running every live state in step with the text, so it never backtracks. Compiled
// automata are cached by pattern.
type RegexEngine struct {
	automata map[string]*automaton
}

func NewRegexEngine() *RegexEngine {
	return &RegexEngine{automata: map[string]*automaton{}}
}

func (r *RegexEngine) automaton(pattern string) *automaton {
	if a, ok := r.automata[pattern]; ok {
		return a
	}
	p := &parser{text: pattern}
	a := newAutomaton(p.parse())
	r.automata[pattern] = a
	return a
}

// Level 1
func (r *RegexEngine) Parse(pattern string) string {
	p := &parser{text: pattern}
	root := p.parse()
	if p.err != nil {
		return fmt.Sprintf("error: %s at %d", p.err.code, p.err.position)
	}
	return root.show()
}

// Level 2
func (r *RegexEngine) Nfa(pattern string) []string {
	a := r.automaton(pattern)
	lines := make([]string, len(a.kind))
	for state := range a.kind {
		lines[state] = a.line(state)
	}
	return lines
}

// Level 3
func (r *RegexEngine) FullMatch(pattern string, text string) bool {
	matched, _ := r.automaton(pattern).run(text)
	return matched
}

func (r *RegexEngine) CountSteps(pattern string, text string) int {
	_, steps := r.automaton(pattern).run(text)
	return steps
}

// Level 4
func (r *RegexEngine) Search(pattern string, text string) []int {
	return r.automaton(pattern).leftmostLongest(text)
}
