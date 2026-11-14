package architecture_checker

import (
	"slices"
	"strconv"
	"strings"
)

const sep = "\x00"

type pair struct{ from, to string }

type contract struct {
	pairs      []pair
	direct     bool
	ignores    map[pair]bool
	exceptions map[pair]string
}

type walk struct {
	order  []string
	parent map[string]string
}

type violation struct {
	key   []string
	chain []string
}

// ArchitectureChecker keeps the imports as written. The first question after a change resolves
// every import to the longest declared module that is the import or a dotted prefix of it, and
// keeps one sorted list of targets per module, so every walk visits neighbours in name order.
//
// A breadth-first walk from a sorted list of starts, over sorted neighbours, reaches each module
// first along the shortest chain that is smallest in name order, so one walk per source name
// answers every pair of a contract that starts there. Cycles are the strongly connected
// components, found with two depth-first passes over the graph and its reverse.
type ArchitectureChecker struct {
	imports   map[string][]string
	graph     map[string][]string
	contracts map[string]*contract
	version   []int
	baseline  map[string][]string
}

func NewArchitectureChecker() *ArchitectureChecker {
	return &ArchitectureChecker{
		imports:   map[string][]string{},
		contracts: map[string]*contract{},
		version:   []int{},
		baseline:  map[string][]string{},
	}
}

// Level 1
func (c *ArchitectureChecker) AddModule(name string, imports []string) bool {
	_, known := c.imports[name]
	c.imports[name] = slices.Clone(imports)
	c.graph = nil
	return !known
}

func (c *ArchitectureChecker) UnknownImports() [][]string {
	rows := map[string][]string{}
	for module, list := range c.imports {
		for _, text := range list {
			if _, ok := c.resolve(text); !ok {
				rows[module+sep+text] = []string{module, text}
			}
		}
	}
	return sortedRows(rows)
}

func (c *ArchitectureChecker) Dependencies(name string) []string {
	edges := c.edges()
	found := map[string]bool{}
	for _, module := range c.members(name) {
		for _, target := range edges[module] {
			if !inside(target, name) {
				found[target] = true
			}
		}
	}
	return sortedKeys(found)
}

func (c *ArchitectureChecker) TransitiveDependencies(name string) []string {
	w := c.walk(c.members(name), nil)
	depth := map[string]int{}
	reached := []string{}
	for _, module := range w.order {
		if above, ok := w.parent[module]; ok && above != "" {
			depth[module] = depth[above] + 1
		}
		if !inside(module, name) {
			reached = append(reached, module)
		}
	}
	slices.SortFunc(reached, func(a, b string) int {
		if depth[a] != depth[b] {
			return depth[a] - depth[b]
		}
		return strings.Compare(a, b)
	})
	return reached
}

// Level 2
func (c *ArchitectureChecker) Cycles(depth int) [][]string {
	adjacency := map[string]map[string]bool{}
	for module, targets := range c.edges() {
		group := groupOf(module, depth)
		if adjacency[group] == nil {
			adjacency[group] = map[string]bool{}
		}
		for _, target := range targets {
			if other := groupOf(target, depth); other != group {
				adjacency[group][other] = true
			}
		}
	}
	found := [][]string{}
	for _, part := range components(adjacency) {
		if len(part) > 1 {
			slices.Sort(part)
			found = append(found, part)
		}
	}
	slices.SortFunc(found, compareRows)
	return found
}

func (c *ArchitectureChecker) CycleChain(name string) []string {
	if _, ok := c.imports[name]; !ok {
		return []string{}
	}
	edges := c.edges()
	w := c.walk([]string{name}, nil)
	for _, module := range w.order {
		if slices.Contains(edges[module], name) {
			return append(chainOf(module, w.parent), name)
		}
	}
	return []string{}
}

// Level 3
func (c *ArchitectureChecker) AddLayers(name string, layers []string) bool {
	pairs := []pair{}
	for low := range layers {
		for high := 0; high < low; high++ {
			pairs = append(pairs, pair{layers[low], layers[high]})
		}
	}
	return c.addContract(name, pairs)
}

func (c *ArchitectureChecker) AddForbidden(name string, source string, target string) bool {
	return c.addContract(name, []pair{{source, target}})
}

func (c *ArchitectureChecker) AddIndependence(name string, names []string) bool {
	pairs := []pair{}
	for _, first := range names {
		for _, second := range names {
			if first != second {
				pairs = append(pairs, pair{first, second})
			}
		}
	}
	return c.addContract(name, pairs)
}

func (c *ArchitectureChecker) Check() [][]string {
	rows := [][]string{}
	for _, v := range c.violations() {
		rows = append(rows, append(slices.Clone(v.key), v.chain...))
	}
	return rows
}

// Level 4
func (c *ArchitectureChecker) Ignore(name string, importer string, imported string) bool {
	rules, ok := c.contracts[name]
	key := pair{importer, imported}
	if !ok || rules.ignores[key] {
		return false
	}
	rules.ignores[key] = true
	return true
}

func (c *ArchitectureChecker) Allow(name string, importer string, imported string, until string) bool {
	rules, ok := c.contracts[name]
	if !ok {
		return false
	}
	key := pair{importer, imported}
	if old, had := rules.exceptions[key]; had && slices.Compare(versionKey(old), versionKey(until)) == 0 {
		return false
	}
	rules.exceptions[key] = until
	return true
}

func (c *ArchitectureChecker) SetVersion(version string) [][]string {
	c.version = versionKey(version)
	rows := map[string][]string{}
	for name, rules := range c.contracts {
		for key, until := range rules.exceptions {
			if slices.Compare(versionKey(until), c.version) <= 0 {
				row := []string{name, key.from, key.to, until}
				rows[strings.Join(row, sep)] = row
			}
		}
	}
	return sortedRows(rows)
}

func (c *ArchitectureChecker) SetMode(name string, mode string) bool {
	rules, ok := c.contracts[name]
	direct := mode == "direct"
	if !ok || rules.direct == direct {
		return false
	}
	rules.direct = direct
	return true
}

func (c *ArchitectureChecker) SetBaseline(entries [][]string) int {
	c.baseline = map[string][]string{}
	for _, entry := range entries {
		key := slices.Clone(entry[:3])
		c.baseline[strings.Join(key, sep)] = key
	}
	return len(c.baseline)
}

func (c *ArchitectureChecker) Ratchet() [][]string {
	broken := map[string]bool{}
	rows := [][]string{}
	for _, v := range c.violations() {
		key := strings.Join(v.key, sep)
		broken[key] = true
		if _, known := c.baseline[key]; !known {
			row := append([]string{"new"}, v.key...)
			rows = append(rows, append(row, v.chain...))
		}
	}
	fixed := map[string][]string{}
	for key, entry := range c.baseline {
		if !broken[key] {
			fixed[key] = entry
		}
	}
	for _, entry := range sortedRows(fixed) {
		delete(c.baseline, strings.Join(entry, sep))
		rows = append(rows, append([]string{"fixed"}, entry...))
	}
	return rows
}

// Helpers
func (c *ArchitectureChecker) resolve(text string) (string, bool) {
	name := text
	for {
		if _, ok := c.imports[name]; ok {
			return name, true
		}
		cut := strings.LastIndexByte(name, '.')
		if cut < 0 {
			return "", false
		}
		name = name[:cut]
	}
}

func (c *ArchitectureChecker) edges() map[string][]string {
	if c.graph == nil {
		c.graph = map[string][]string{}
		for module, list := range c.imports {
			targets := map[string]bool{}
			for _, text := range list {
				if target, ok := c.resolve(text); ok && target != module {
					targets[target] = true
				}
			}
			c.graph[module] = sortedKeys(targets)
		}
	}
	return c.graph
}

func (c *ArchitectureChecker) members(name string) []string {
	found := []string{}
	for module := range c.imports {
		if inside(module, name) {
			found = append(found, module)
		}
	}
	slices.Sort(found)
	return found
}

// walk goes breadth-first from the sorted starts over sorted neighbours. The order slice is also
// the queue, and a start's parent is the empty string, which is never a module name.
func (c *ArchitectureChecker) walk(starts []string, rules *contract) walk {
	edges := c.edges()
	parent := map[string]string{}
	for _, start := range starts {
		parent[start] = ""
	}
	order := slices.Clone(starts)
	for head := 0; head < len(order); head++ {
		module := order[head]
		for _, target := range edges[module] {
			if _, seen := parent[target]; !seen && !c.skipped(rules, module, target) {
				parent[target] = module
				order = append(order, target)
			}
		}
	}
	return walk{order, parent}
}

func (c *ArchitectureChecker) addContract(name string, pairs []pair) bool {
	if _, taken := c.contracts[name]; taken {
		return false
	}
	c.contracts[name] = &contract{pairs: pairs, ignores: map[pair]bool{}, exceptions: map[pair]string{}}
	return true
}

func (c *ArchitectureChecker) skipped(rules *contract, importer, imported string) bool {
	if rules == nil {
		return false
	}
	for rule := range rules.ignores {
		if inside(importer, rule.from) && inside(imported, rule.to) {
			return true
		}
	}
	for rule, until := range rules.exceptions {
		live := slices.Compare(c.version, versionKey(until)) < 0
		if live && inside(importer, rule.from) && inside(imported, rule.to) {
			return true
		}
	}
	return false
}

func (c *ArchitectureChecker) violations() []violation {
	found := []violation{}
	names := make([]string, 0, len(c.contracts))
	for name := range c.contracts {
		names = append(names, name)
	}
	slices.Sort(names)
	for _, name := range names {
		rules := c.contracts[name]
		sources := map[string]bool{}
		for _, p := range rules.pairs {
			sources[p.from] = true
		}
		for _, source := range sortedKeys(sources) {
			targets := []string{}
			for _, p := range rules.pairs {
				if p.from == source {
					targets = append(targets, p.to)
				}
			}
			for target, chain := range c.chains(rules, source, targets) {
				found = append(found, violation{[]string{name, source, target}, chain})
			}
		}
	}
	slices.SortFunc(found, func(a, b violation) int { return slices.Compare(a.key, b.key) })
	return found
}

func (c *ArchitectureChecker) chains(rules *contract, source string, targets []string) map[string][]string {
	starts := c.members(source)
	found := map[string][]string{}
	if rules.direct {
		for _, target := range targets {
			if hit := c.firstImport(rules, starts, target); hit != nil {
				found[target] = hit
			}
		}
		return found
	}
	w := c.walk(starts, rules)
	for _, target := range targets {
		for _, module := range w.order {
			if inside(module, target) {
				found[target] = chainOf(module, w.parent)
				break
			}
		}
	}
	return found
}

// firstImport scans sorted starts and their sorted targets, so the first import found is the
// smallest.
func (c *ArchitectureChecker) firstImport(rules *contract, starts []string, target string) []string {
	edges := c.edges()
	for _, module := range starts {
		for _, other := range edges[module] {
			if inside(other, target) && !c.skipped(rules, module, other) {
				return []string{module, other}
			}
		}
	}
	return nil
}

func inside(module, name string) bool {
	return module == name || strings.HasPrefix(module, name+".")
}

func groupOf(module string, depth int) string {
	if depth == 0 {
		return module
	}
	parts := strings.Split(module, ".")
	return strings.Join(parts[:min(depth, len(parts))], ".")
}

func chainOf(module string, parent map[string]string) []string {
	chain := []string{}
	for step := module; step != ""; step = parent[step] {
		chain = append(chain, step)
	}
	slices.Reverse(chain)
	return chain
}

func versionKey(text string) []int {
	parts := []int{}
	for _, part := range strings.Split(text, ".") {
		number, _ := strconv.Atoi(part)
		parts = append(parts, number)
	}
	for len(parts) > 0 && parts[len(parts)-1] == 0 {
		parts = parts[:len(parts)-1]
	}
	return parts
}

func sortedKeys(set map[string]bool) []string {
	keys := make([]string, 0, len(set))
	for key := range set {
		keys = append(keys, key)
	}
	slices.Sort(keys)
	return keys
}

func sortedRows(rows map[string][]string) [][]string {
	sorted := make([][]string, 0, len(rows))
	for _, row := range rows {
		sorted = append(sorted, row)
	}
	slices.SortFunc(sorted, compareRows)
	return sorted
}

// compareRows compares two rows element by element; a row that starts a longer one comes first.
func compareRows(a, b []string) int {
	return slices.Compare(a, b)
}

// components runs two depth-first passes: finishing order on the graph, then components on its
// reverse.
func components(adjacency map[string]map[string]bool) [][]string {
	nodes := make([]string, 0, len(adjacency))
	for node := range adjacency {
		nodes = append(nodes, node)
	}
	slices.Sort(nodes)
	forward := map[string][]string{}
	reverse := map[string][]string{}
	for _, node := range nodes {
		forward[node] = sortedKeys(adjacency[node])
	}
	for _, node := range nodes {
		for _, target := range forward[node] {
			reverse[target] = append(reverse[target], node)
		}
	}
	type frame struct {
		node  string
		index int
	}
	finished := []string{}
	seen := map[string]bool{}
	for _, root := range nodes {
		if seen[root] {
			continue
		}
		seen[root] = true
		stack := []frame{{root, 0}}
		for len(stack) > 0 {
			top := &stack[len(stack)-1]
			targets := forward[top.node]
			if top.index < len(targets) {
				target := targets[top.index]
				top.index++
				if !seen[target] {
					seen[target] = true
					stack = append(stack, frame{target, 0})
				}
			} else {
				finished = append(finished, top.node)
				stack = stack[:len(stack)-1]
			}
		}
	}
	assigned := map[string]bool{}
	parts := [][]string{}
	for i := len(finished) - 1; i >= 0; i-- {
		root := finished[i]
		if assigned[root] {
			continue
		}
		assigned[root] = true
		part := []string{}
		stack := []string{root}
		for len(stack) > 0 {
			node := stack[len(stack)-1]
			stack = stack[:len(stack)-1]
			part = append(part, node)
			for _, source := range reverse[node] {
				if !assigned[source] {
					assigned[source] = true
					stack = append(stack, source)
				}
			}
		}
		parts = append(parts, part)
	}
	return parts
}
