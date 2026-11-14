package values_templating

import (
	"regexp"
	"sort"
	"strconv"
	"strings"
)

// Layers are kept as given and merged on demand, oldest first, with the rules of RFC 7396. Every
// node of the merged tree remembers the layer that set it. A template is parsed in one
// left-to-right pass into a tree of text, substitutions, conditionals and loops, and rendered with
// a stack of loop bindings that shadow the values.

var (
	keyPattern   = regexp.MustCompile(`^[A-Za-z_][A-Za-z0-9_]*$`)
	indexPattern = regexp.MustCompile(`^(0|[1-9][0-9]*)$`)
	pathPattern  = regexp.MustCompile(`^(?:[A-Za-z_][A-Za-z0-9_]*|0|[1-9][0-9]*)(?:\.(?:[A-Za-z_][A-Za-z0-9_]*|0|[1-9][0-9]*))*$`)
	blockWords   = map[string]bool{"if": true, "else": true, "end": true, "for": true}
	reserved     = map[string]bool{"if": true, "else": true, "end": true, "for": true, "in": true}
)

type node struct {
	kind, text, layer string
	members           map[string]*node
	items             []*node
}

func newNode(kind, text, layer string) *node {
	return &node{kind: kind, text: text, layer: layer, members: map[string]*node{}}
}

func (n *node) copyAs(layer string) *node {
	twin := newNode(n.kind, n.text, layer)
	for key, child := range n.members {
		twin.members[key] = child.copyAs(layer)
	}
	for _, child := range n.items {
		twin.items = append(twin.items, child.copyAs(layer))
	}
	return twin
}

func (n *node) sortedKeys() []string {
	keys := make([]string, 0, len(n.members))
	for key := range n.members {
		keys = append(keys, key)
	}
	sort.Strings(keys)
	return keys
}

type templateError struct {
	code     string
	position int
	detail   string
}

func (e *templateError) Error() string { return e.code }

type token struct{ kind, value string }

// tag is a classified tag: kind is text, out, if, else, end or for.
type tag struct {
	kind, text, path string
	fallback         *string
	names            []string
}

type segment struct {
	text                string
	tag                 *tag
	at                  int
	trimLeft, trimRight bool
}

// part is a parsed piece of a template: text, out, if (first and second branch) or for (first
// is the body).
type part struct {
	kind, text, path string
	fallback         *string
	names            []string
	at               int
	first, second    []*part
}

type binding struct {
	name  string
	value *node
}

type ValuesRenderer struct {
	names  []string
	layers map[string]*node
	schema *node
}

func NewValuesRenderer() *ValuesRenderer {
	return &ValuesRenderer{layers: map[string]*node{}, schema: newNode("object", "", "")}
}

// Level 1

func (v *ValuesRenderer) SetLayer(name string, rows [][]string) bool {
	_, known := v.layers[name]
	if !known {
		v.names = append(v.names, name)
	}
	v.layers[name] = decode(rows)
	return !known
}

func (v *ValuesRenderer) Merged() [][]string {
	rows := [][]string{}
	walk(v.merge(), "", func(pointer string, n *node) { rows = append(rows, []string{pointer, n.kind, n.text}) })
	return rows
}

// Level 2 and 3

func (v *ValuesRenderer) Render(template string) []string {
	values := v.merge()
	if errors := v.errors(values); len(errors) > 0 {
		return []string{"error", "invalid_values", "", strconv.Itoa(len(errors))}
	}
	parts, err := parse(template)
	var out strings.Builder
	if err == nil {
		err = emit(parts, values, nil, &out)
	}
	if err != nil {
		return []string{"error", err.code, lineAndColumn(template, err.position), err.detail}
	}
	return []string{"ok", out.String()}
}

// Level 4

func (v *ValuesRenderer) SetSchema(rows [][]string) {
	v.schema = decode(rows)
}

func (v *ValuesRenderer) Validate() [][]string {
	return v.errors(v.merge())
}

func (v *ValuesRenderer) Provenance() [][]string {
	rows := [][]string{}
	walk(v.merge(), "", func(pointer string, n *node) { rows = append(rows, []string{pointer, n.layer}) })
	return rows
}

// Merging

func (v *ValuesRenderer) merge() *node {
	root := newNode("object", "", "")
	for _, name := range v.names {
		mergeInto(root, v.layers[name], name)
	}
	return root
}

func decode(rows [][]string) *node {
	root := newNode("object", "", "")
	for _, row := range rows {
		segments := strings.Split(row[0], "/")[1:]
		parent := root
		for _, segment := range segments[:len(segments)-1] {
			if parent.kind == "object" {
				parent = parent.members[segment]
			} else {
				index, _ := strconv.Atoi(segment)
				parent = parent.items[index]
			}
		}
		child := newNode(row[1], row[2], "")
		if parent.kind == "object" {
			parent.members[segments[len(segments)-1]] = child
		} else {
			parent.items = append(parent.items, child)
		}
	}
	return root
}

func walk(n *node, pointer string, visit func(string, *node)) {
	if n.kind == "object" {
		for _, key := range n.sortedKeys() {
			child := n.members[key]
			visit(pointer+"/"+key, child)
			walk(child, pointer+"/"+key, visit)
		}
	} else if n.kind == "array" {
		for index, child := range n.items {
			here := pointer + "/" + strconv.Itoa(index)
			visit(here, child)
			walk(child, here, visit)
		}
	}
}

func mergeInto(target, patch *node, layer string) {
	for key, value := range patch.members {
		switch value.kind {
		case "null":
			delete(target.members, key)
		case "object":
			current, ok := target.members[key]
			if !ok || current.kind != "object" {
				current = newNode("object", "", layer)
				target.members[key] = current
			}
			mergeInto(current, value, layer)
		default:
			target.members[key] = value.copyAs(layer)
		}
	}
}

// Parsing

func isWordChar(c byte) bool {
	return c >= 'a' && c <= 'z' || c >= 'A' && c <= 'Z' || c >= '0' && c <= '9' || c == '_' || c == '.'
}

func tokenize(body string, position int) ([]token, *templateError) {
	bad := &templateError{code: "bad_expression", position: position}
	var tokens []token
	i := 0
	for i < len(body) {
		c := body[i]
		switch {
		case c == ' ':
			i++
		case c == '|' || c == ',':
			tokens = append(tokens, token{"punct", string(c)})
			i++
		case c == '"':
			var text strings.Builder
			i++
			for {
				if i >= len(body) {
					return nil, bad
				}
				d := body[i]
				if d == '"' {
					break
				}
				if d == '\\' {
					if i+1 >= len(body) || (body[i+1] != '"' && body[i+1] != '\\') {
						return nil, bad
					}
					text.WriteByte(body[i+1])
					i += 2
				} else {
					text.WriteByte(d)
					i++
				}
			}
			tokens = append(tokens, token{"string", text.String()})
			i++
		case isWordChar(c):
			start := i
			for i < len(body) && isWordChar(body[i]) {
				i++
			}
			tokens = append(tokens, token{"word", body[start:i]})
		default:
			return nil, bad
		}
	}
	return tokens, nil
}

func classify(tokens []token, position int) (*tag, *templateError) {
	kinds := make([]string, len(tokens))
	words := make([]string, len(tokens))
	for i, t := range tokens {
		kinds[i], words[i] = t.kind, t.value
	}
	shape := strings.Join(kinds, " ")
	if len(tokens) > 0 && kinds[0] == "word" && blockWords[words[0]] {
		return classifyBlock(shape, words, position)
	}
	switch {
	case shape == "string":
		return &tag{kind: "text", text: words[0]}, nil
	case shape == "word" && pathPattern.MatchString(words[0]):
		return &tag{kind: "out", path: words[0]}, nil
	case shape == "word punct word string" && pathPattern.MatchString(words[0]) && words[1] == "|" && words[2] == "default":
		fallback := words[3]
		return &tag{kind: "out", path: words[0], fallback: &fallback}, nil
	}
	return nil, &templateError{code: "bad_expression", position: position}
}

func classifyBlock(shape string, words []string, position int) (*tag, *templateError) {
	head := words[0]
	if (head == "else" || head == "end") && len(words) == 1 {
		return &tag{kind: head}, nil
	}
	if head == "if" && shape == "word word" && pathPattern.MatchString(words[1]) {
		return &tag{kind: "if", path: words[1]}, nil
	}
	if head == "for" {
		var names []string
		if shape == "word word word word" && words[2] == "in" {
			names = []string{words[1]}
		} else if shape == "word word punct word word word" && words[2] == "," && words[4] == "in" {
			names = []string{words[1], words[3]}
		}
		valid := len(names) > 0
		for _, name := range names {
			valid = valid && keyPattern.MatchString(name) && !reserved[name]
		}
		if len(names) == 2 && names[0] == names[1] {
			valid = false
		}
		if path := words[len(words)-1]; valid && pathPattern.MatchString(path) {
			return &tag{kind: "for", path: path, names: names}, nil
		}
	}
	return nil, &templateError{code: "bad_expression", position: position}
}

type open struct {
	isIf    bool
	at      int
	hasElse bool
}

func parse(template string) ([]*part, *templateError) {
	var segments []segment
	var stack []*open
	i := 0
	for {
		start := strings.Index(template[i:], "{{")
		if start < 0 {
			segments = append(segments, segment{text: template[i:]})
			break
		}
		start += i
		segments = append(segments, segment{text: template[i:start]})
		end := strings.Index(template[start+2:], "}}")
		if end < 0 {
			return nil, &templateError{code: "unclosed_tag", position: start}
		}
		end += start + 2
		body := template[start+2 : end]
		trimLeft := strings.HasPrefix(body, "-")
		if trimLeft {
			body = body[1:]
		}
		trimRight := strings.HasSuffix(body, "-")
		if trimRight {
			body = body[:len(body)-1]
		}
		tokens, err := tokenize(strings.Trim(body, " "), start)
		if err != nil {
			return nil, err
		}
		t, err := classify(tokens, start)
		if err != nil {
			return nil, err
		}
		switch t.kind {
		case "if", "for":
			stack = append(stack, &open{isIf: t.kind == "if", at: start})
		case "else":
			if len(stack) == 0 || !stack[len(stack)-1].isIf || stack[len(stack)-1].hasElse {
				return nil, &templateError{code: "unexpected_tag", position: start}
			}
			stack[len(stack)-1].hasElse = true
		case "end":
			if len(stack) == 0 {
				return nil, &templateError{code: "unexpected_tag", position: start}
			}
			stack = stack[:len(stack)-1]
		}
		segments = append(segments, segment{tag: t, at: start, trimLeft: trimLeft, trimRight: trimRight})
		i = end + 2
	}
	if len(stack) > 0 {
		return nil, &templateError{code: "unclosed_block", position: stack[len(stack)-1].at}
	}
	for k, s := range segments {
		if s.tag == nil {
			continue
		}
		if s.trimLeft {
			segments[k-1].text = strings.TrimRight(segments[k-1].text, " \n")
		}
		if s.trimRight {
			segments[k+1].text = strings.TrimLeft(segments[k+1].text, " \n")
		}
	}
	return build(segments), nil
}

func build(segments []segment) []*part {
	root := &part{kind: "root"}
	blocks := []*part{root}
	inElse := []bool{false}
	add := func(p *part) {
		top := blocks[len(blocks)-1]
		if inElse[len(inElse)-1] {
			top.second = append(top.second, p)
		} else {
			top.first = append(top.first, p)
		}
	}
	for _, s := range segments {
		if s.tag == nil {
			if s.text != "" {
				add(&part{kind: "text", text: s.text})
			}
			continue
		}
		switch s.tag.kind {
		case "if", "for":
			block := &part{kind: s.tag.kind, path: s.tag.path, names: s.tag.names, at: s.at}
			add(block)
			blocks = append(blocks, block)
			inElse = append(inElse, false)
		case "else":
			inElse[len(inElse)-1] = true
		case "end":
			blocks = blocks[:len(blocks)-1]
			inElse = inElse[:len(inElse)-1]
		case "text":
			add(&part{kind: "text", text: s.tag.text})
		default:
			add(&part{kind: "out", path: s.tag.path, fallback: s.tag.fallback, at: s.at})
		}
	}
	return root.first
}

func lineAndColumn(template string, position int) string {
	before := template[:position]
	line := strings.Count(before, "\n") + 1
	column := position - (strings.LastIndex(before, "\n") + 1) + 1
	return strconv.Itoa(line) + ":" + strconv.Itoa(column)
}

// Rendering

func emit(parts []*part, values *node, scope []binding, out *strings.Builder) *templateError {
	for _, p := range parts {
		switch p.kind {
		case "text":
			out.WriteString(p.text)
		case "out":
			found := lookup(p.path, values, scope)
			switch {
			case found == nil && p.fallback == nil:
				return &templateError{"missing_value", p.at, p.path}
			case found == nil:
				out.WriteString(*p.fallback)
			case found.kind == "object" || found.kind == "array":
				return &templateError{"not_scalar", p.at, p.path}
			default:
				out.WriteString(found.text)
			}
		case "if":
			branch := p.second
			if truthy(lookup(p.path, values, scope)) {
				branch = p.first
			}
			if err := emit(branch, values, scope, out); err != nil {
				return err
			}
		default:
			if err := loop(p, values, scope, out); err != nil {
				return err
			}
		}
	}
	return nil
}

func loop(p *part, values *node, scope []binding, out *strings.Builder) *templateError {
	found := lookup(p.path, values, scope)
	if found == nil {
		return &templateError{"missing_value", p.at, p.path}
	}
	var keys, items []*node
	switch found.kind {
	case "array":
		for index, item := range found.items {
			keys = append(keys, newNode("number", strconv.Itoa(index), ""))
			items = append(items, item)
		}
	case "object":
		for _, key := range found.sortedKeys() {
			keys = append(keys, newNode("string", key, ""))
			items = append(items, found.members[key])
		}
	default:
		return &templateError{"not_iterable", p.at, p.path}
	}
	for index := range items {
		inner := append(append([]binding{}, scope...), binding{p.names[0], items[index]})
		if len(p.names) == 2 {
			inner[len(inner)-1] = binding{p.names[0], keys[index]}
			inner = append(inner, binding{p.names[1], items[index]})
		}
		if err := emit(p.first, values, inner, out); err != nil {
			return err
		}
	}
	return nil
}

func lookup(path string, values *node, scope []binding) *node {
	segments := strings.Split(path, ".")
	current := values
	for i := len(scope) - 1; i >= 0; i-- {
		if scope[i].name == segments[0] {
			current, segments = scope[i].value, segments[1:]
			break
		}
	}
	for _, s := range segments {
		switch {
		case current.kind == "object":
			next, ok := current.members[s]
			if !ok {
				return nil
			}
			current = next
		case current.kind == "array" && indexPattern.MatchString(s):
			index, err := strconv.Atoi(s)
			if err != nil || index >= len(current.items) {
				return nil
			}
			current = current.items[index]
		default:
			return nil
		}
	}
	if current.kind == "null" {
		return nil
	}
	return current
}

func truthy(n *node) bool {
	if n == nil {
		return false
	}
	switch n.kind {
	case "boolean":
		return n.text == "true"
	case "string":
		return n.text != ""
	case "number":
		return n.text != "0"
	case "object":
		return len(n.members) > 0
	default:
		return len(n.items) > 0
	}
}

// Validation

func (v *ValuesRenderer) errors(values *node) [][]string {
	errors := [][]string{}
	check(values, v.schema, "", &errors)
	sort.Slice(errors, func(i, j int) bool {
		if errors[i][0] != errors[j][0] {
			return errors[i][0] < errors[j][0]
		}
		return errors[i][1] < errors[j][1]
	})
	return errors
}

func hasType(n *node, name string) bool {
	return n.kind == name || (name == "integer" && n.kind == "number")
}

func isListed(n, options *node) bool {
	if n.kind == "object" || n.kind == "array" {
		return false
	}
	for _, option := range options.items {
		if option.kind == n.kind && option.text == n.text {
			return true
		}
	}
	return false
}

func check(n, schema *node, pointer string, errors *[][]string) {
	keywords := schema.members
	fail := func(where, keyword, layer string) { *errors = append(*errors, []string{where, keyword, layer}) }
	if t, ok := keywords["type"]; ok && !hasType(n, t.text) {
		fail(pointer, "type", n.layer)
	}
	if options, ok := keywords["enum"]; ok && !isListed(n, options) {
		fail(pointer, "enum", n.layer)
	}
	if n.kind == "number" {
		value, _ := strconv.ParseInt(n.text, 10, 64)
		if minimum, ok := keywords["minimum"]; ok {
			if bound, _ := strconv.ParseInt(minimum.text, 10, 64); value < bound {
				fail(pointer, "minimum", n.layer)
			}
		}
		if maximum, ok := keywords["maximum"]; ok {
			if bound, _ := strconv.ParseInt(maximum.text, 10, 64); value > bound {
				fail(pointer, "maximum", n.layer)
			}
		}
	}
	if n.kind == "object" {
		properties := map[string]*node{}
		if p, ok := keywords["properties"]; ok {
			properties = p.members
		}
		if required, ok := keywords["required"]; ok {
			for _, key := range required.items {
				if _, present := n.members[key.text]; !present {
					fail(pointer+"/"+key.text, "required", "")
				}
			}
		}
		additional, ok := keywords["additionalProperties"]
		closed := ok && additional.text == "false"
		for key, child := range n.members {
			if sub, listed := properties[key]; listed {
				check(child, sub, pointer+"/"+key, errors)
			} else if closed {
				fail(pointer+"/"+key, "additionalProperties", child.layer)
			}
		}
	}
	if items, ok := keywords["items"]; ok && n.kind == "array" {
		for index, child := range n.items {
			check(child, items, pointer+"/"+strconv.Itoa(index), errors)
		}
	}
}
