package manifest_policy

import (
	"sort"
	"strconv"
	"strings"
	"time"
)

// Manifests are kept as trees by id, rules as data in the order they were added. A check expands
// each rule's pointer pattern over each manifest and tests the concrete pointers; a service's port
// rule looks up the workloads its selector picks. Exceptions, severities, modes and fixes are
// applied on top of the same list of violations.

var severityRank = map[string]int{"critical": 0, "high": 1, "medium": 2, "low": 3}

type node struct {
	kind, text string
	members    map[string]*node
	items      []*node
}

type rule struct {
	check, kind, pointer string
	tags                 []string
	severity, mode, fix  string
}

type key struct{ ruleID, manifestID string }

type allowance struct {
	reason  string
	expires time.Time
}

type violation struct{ manifestID, ruleID, pointer string }

type PolicyChecker struct {
	manifests  map[string]*node
	ruleIDs    []string
	rules      map[string]*rule
	allowances map[key]allowance
}

func NewPolicyChecker() *PolicyChecker {
	return &PolicyChecker{manifests: map[string]*node{}, rules: map[string]*rule{}, allowances: map[key]allowance{}}
}

// Level 1

func (p *PolicyChecker) AddManifest(rows [][]string) bool {
	root := decode(rows)
	id := textOf(root, "/kind") + "/" + textOf(root, "/name")
	_, known := p.manifests[id]
	p.manifests[id] = root
	return !known
}

func (p *PolicyChecker) RequireField(ruleId string, kind string, pointer string) bool {
	return p.define(ruleId, "field", kind, pointer, nil)
}

func (p *PolicyChecker) ForbidTags(ruleId string, kind string, pointer string, tags []string) bool {
	return p.define(ruleId, "tags", kind, pointer, tags)
}

func (p *PolicyChecker) Check() [][]string {
	rows := [][]string{}
	for _, v := range p.violations() {
		rows = append(rows, []string{v.manifestID, v.ruleID, v.pointer})
	}
	return rows
}

// Level 2

func (p *PolicyChecker) RequirePortTargets(ruleId string) bool {
	return p.define(ruleId, "ports", "service", "", nil)
}

// Level 3

func (p *PolicyChecker) Allow(ruleId string, manifestId string, reason string, expires time.Time) bool {
	k := key{ruleId, manifestId}
	_, known := p.allowances[k]
	p.allowances[k] = allowance{reason, expires}
	return !known
}

func (p *PolicyChecker) CheckOn(today time.Time) [][]string {
	rows := [][]string{}
	for _, v := range p.violations() {
		if a, ok := p.active(v.ruleID, v.manifestID, today); ok {
			rows = append(rows, []string{v.manifestID, v.ruleID, v.pointer, "excepted", a.reason})
		} else {
			rows = append(rows, []string{v.manifestID, v.ruleID, v.pointer, "violation", ""})
		}
	}
	var expired []key
	for k, a := range p.allowances {
		if today.After(a.expires) {
			expired = append(expired, k)
		}
	}
	sort.Slice(expired, func(i, j int) bool {
		if expired[i].manifestID != expired[j].manifestID {
			return expired[i].manifestID < expired[j].manifestID
		}
		return expired[i].ruleID < expired[j].ruleID
	})
	for _, k := range expired {
		date := p.allowances[k].expires.Format("2006-01-02")
		rows = append(rows, []string{k.manifestID, k.ruleID, "", "expired", date})
	}
	return rows
}

// Level 4

func (p *PolicyChecker) Configure(ruleId string, severity string, mode string, fix string) bool {
	r, ok := p.rules[ruleId]
	if !ok {
		return false
	}
	r.severity, r.mode, r.fix = severity, mode, fix
	return true
}

func (p *PolicyChecker) Findings(today time.Time) [][]string {
	rows := [][]string{}
	for _, v := range p.violations() {
		if _, ok := p.active(v.ruleID, v.manifestID, today); ok {
			continue
		}
		r := p.rules[v.ruleID]
		op, value := fixFor(r, p.manifests[v.manifestID], v.pointer)
		rows = append(rows, []string{v.manifestID, v.ruleID, v.pointer, r.severity, r.mode, op, value})
	}
	sort.SliceStable(rows, func(i, j int) bool { return severityRank[rows[i][3]] < severityRank[rows[j][3]] })
	return rows
}

func (p *PolicyChecker) Decide(today time.Time) [][]string {
	counts := map[string][2]int{}
	for id := range p.manifests {
		counts[id] = [2]int{}
	}
	for _, row := range p.Findings(today) {
		count := counts[row[0]]
		if row[4] == "deny" {
			count[0]++
		} else {
			count[1]++
		}
		counts[row[0]] = count
	}
	rows := [][]string{}
	for _, id := range sortedKeys(p.manifests) {
		count := counts[id]
		decision := "admit"
		if count[0] > 0 {
			decision = "reject"
		}
		rows = append(rows, []string{id, decision, strconv.Itoa(count[0]), strconv.Itoa(count[1])})
	}
	return rows
}

// Rules

func (p *PolicyChecker) define(ruleID, check, kind, pointer string, tags []string) bool {
	r, known := p.rules[ruleID]
	if !known {
		r = &rule{severity: "medium", mode: "deny"}
		p.rules[ruleID] = r
		p.ruleIDs = append(p.ruleIDs, ruleID)
	}
	r.check, r.kind, r.pointer, r.tags = check, kind, pointer, append([]string{}, tags...)
	return !known
}

func (p *PolicyChecker) violations() []violation {
	var found []violation
	for _, manifestID := range sortedKeys(p.manifests) {
		root := p.manifests[manifestID]
		kind := textOf(root, "/kind")
		for _, ruleID := range p.ruleIDs {
			r := p.rules[ruleID]
			if r.kind != "*" && r.kind != kind {
				continue
			}
			for _, pointer := range p.broken(r, root) {
				found = append(found, violation{manifestID, ruleID, pointer})
			}
		}
	}
	return found
}

func (p *PolicyChecker) broken(r *rule, root *node) []string {
	if r.check == "ports" {
		return p.unservedPorts(root)
	}
	var broken []string
	for _, pointer := range expand(root, r.pointer) {
		n := resolve(root, pointer)
		if r.check == "field" {
			if n == nil || n.kind == "null" || (n.kind == "string" && n.text == "") {
				broken = append(broken, pointer)
			}
		} else if n != nil && n.kind == "string" && !strings.Contains(n.text, "@") {
			_, tag, hasTag := tagSplit(n.text)
			if !hasTag || contains(r.tags, tag) {
				broken = append(broken, pointer)
			}
		}
	}
	return broken
}

func (p *PolicyChecker) unservedPorts(service *node) []string {
	selector := resolve(service, "/selector")
	if selector == nil || selector.kind != "object" || len(selector.members) == 0 {
		return []string{"/selector"}
	}
	var served []map[string]bool
	for _, root := range p.manifests {
		if textOf(root, "/kind") != "workload" || !selects(selector, root) {
			continue
		}
		names := map[string]bool{}
		for _, pointer := range expand(root, "/containers/*/ports/*/name") {
			if n := resolve(root, pointer); n != nil && n.kind == "string" {
				names[n.text] = true
			}
		}
		served = append(served, names)
	}
	if len(served) == 0 {
		return []string{"/selector"}
	}
	var broken []string
	for _, pointer := range expand(service, "/ports/*") {
		target := resolve(service, pointer+"/target")
		if target == nil || target.kind != "string" {
			continue
		}
		for _, names := range served {
			if !names[target.text] {
				broken = append(broken, pointer+"/target")
				break
			}
		}
	}
	return broken
}

func selects(selector, workload *node) bool {
	for k, value := range selector.members {
		label := resolve(workload, "/labels/"+k)
		if value.kind != "string" || label == nil || label.kind != "string" || label.text != value.text {
			return false
		}
	}
	return true
}

func (p *PolicyChecker) active(ruleID, manifestID string, today time.Time) (allowance, bool) {
	a, ok := p.allowances[key{ruleID, manifestID}]
	if !ok || today.After(a.expires) {
		return allowance{}, false
	}
	return a, true
}

func fixFor(r *rule, root *node, pointer string) (string, string) {
	if r.fix == "" || r.check == "ports" {
		return "", ""
	}
	n := resolve(root, pointer)
	if r.check == "tags" {
		repository, _, _ := tagSplit(n.text)
		return "replace", repository + ":" + r.fix
	}
	if n != nil {
		return "replace", r.fix
	}
	parent := resolve(root, pointer[:strings.LastIndex(pointer, "/")])
	if parent != nil && parent.kind == "object" {
		return "add", r.fix
	}
	return "", ""
}

// Documents

func decode(rows [][]string) *node {
	root := &node{kind: "object", members: map[string]*node{}}
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
		child := &node{kind: row[1], text: row[2], members: map[string]*node{}}
		if parent.kind == "object" {
			parent.members[segments[len(segments)-1]] = child
		} else {
			parent.items = append(parent.items, child)
		}
	}
	return root
}

func resolve(root *node, pointer string) *node {
	n := root
	if pointer == "" {
		return n
	}
	for _, segment := range strings.Split(pointer, "/")[1:] {
		switch n.kind {
		case "object":
			next, ok := n.members[segment]
			if !ok {
				return nil
			}
			n = next
		case "array":
			index, err := strconv.Atoi(segment)
			if err != nil || index < 0 || index >= len(n.items) || segment[0] == '+' || segment[0] == '-' {
				return nil
			}
			n = n.items[index]
		default:
			return nil
		}
	}
	return n
}

func expand(root *node, pattern string) []string {
	pointers := []string{""}
	for _, segment := range strings.Split(pattern, "/")[1:] {
		var next []string
		for _, pointer := range pointers {
			if segment != "*" {
				next = append(next, pointer+"/"+segment)
				continue
			}
			if n := resolve(root, pointer); n != nil && n.kind == "array" {
				for index := range n.items {
					next = append(next, pointer+"/"+strconv.Itoa(index))
				}
			}
		}
		pointers = next
	}
	return pointers
}

// tagSplit returns the repository and the tag of an image reference, and whether it has a tag.
func tagSplit(image string) (string, string, bool) {
	colon := strings.LastIndex(image, ":")
	if colon > strings.LastIndex(image, "/") {
		return image[:colon], image[colon+1:], true
	}
	return image, "", false
}

func textOf(root *node, pointer string) string {
	if n := resolve(root, pointer); n != nil && n.kind == "string" {
		return n.text
	}
	return ""
}

func contains(list []string, item string) bool {
	for _, value := range list {
		if value == item {
			return true
		}
	}
	return false
}

func sortedKeys(manifests map[string]*node) []string {
	keys := make([]string, 0, len(manifests))
	for id := range manifests {
		keys = append(keys, id)
	}
	sort.Strings(keys)
	return keys
}
