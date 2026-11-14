package lineage_graph

import (
	"sort"
	"strings"
)

var usages = map[string]bool{"identity": true, "transform": true, "aggregate": true, "filter": true}
var maskable = map[string]bool{"transform": true, "aggregate": true}

type edge struct {
	source  string
	target  string
	usage   string
	masking bool
}

func everyEdge(*edge) bool        { return true }
func identityOnly(e *edge) bool   { return e.usage == "identity" }
func carriesValue(e *edge) bool   { return e.usage != "filter" && !e.masking }
func datasetOf(column string) string {
	dataset, _, _ := strings.Cut(column, ".")
	return dataset
}

// isName checks a dataset or column name: 1 to 20 characters from a-z, 0-9 and _.
func isName(text string) bool {
	if len(text) < 1 || len(text) > 20 {
		return false
	}
	for _, ch := range text {
		if !((ch >= 'a' && ch <= 'z') || (ch >= '0' && ch <= '9') || ch == '_') {
			return false
		}
	}
	return true
}

func isColumnRef(text string) bool {
	dataset, column, found := strings.Cut(text, ".")
	return found && isName(dataset) && isName(column)
}

func lessRows(a, b []string) bool {
	for at := 0; at < len(a) && at < len(b); at++ {
		if a[at] != b[at] {
			return a[at] < b[at]
		}
	}
	return len(a) < len(b)
}

func contains(list []string, value string) bool {
	for _, item := range list {
		if item == value {
			return true
		}
	}
	return false
}

// LineageGraph names columns dataset.column, and each lineage edge points from an input column to
// the column computed from it. Two adjacency maps, forward and backward, answer every walk: a
// breadth-first search gives distances for the ordered queries, a filter on the edge's usage
// restricts a walk to the edges a change or a label travels along, and Kosaraju's two passes group
// the columns that sit on a cycle.
type LineageGraph struct {
	columns   map[string][]string
	edges     []*edge
	forward   map[string][]*edge
	backward  map[string][]*edge
	labels    map[string]map[string]bool
	published map[string]bool
}

func NewLineageGraph() *LineageGraph {
	return &LineageGraph{
		columns:   map[string][]string{},
		forward:   map[string][]*edge{},
		backward:  map[string][]*edge{},
		labels:    map[string]map[string]bool{},
		published: map[string]bool{},
	}
}

// Level 1
func (g *LineageGraph) AddDataset(name string, columns []string, edges [][]string) bool {
	if _, taken := g.columns[name]; taken || !isName(name) {
		return false
	}
	seen := map[string]bool{}
	for _, column := range columns {
		if seen[column] || !isName(column) {
			return false
		}
		seen[column] = true
	}
	pairs := map[[2]string]bool{}
	parsed := []*edge{}
	for _, spec := range edges {
		if len(spec) < 3 || len(spec) > 4 || !seen[spec[0]] || !isColumnRef(spec[1]) {
			return false
		}
		usage, masking := spec[2], len(spec) == 4
		if !usages[usage] || (masking && (spec[3] != "masking" || !maskable[usage])) {
			return false
		}
		pair := [2]string{spec[0], spec[1]}
		if pairs[pair] {
			return false
		}
		pairs[pair] = true
		parsed = append(parsed, &edge{source: spec[1], target: name + "." + spec[0], usage: usage, masking: masking})
	}
	g.columns[name] = append([]string{}, columns...)
	for _, e := range parsed {
		g.edges = append(g.edges, e)
		g.forward[e.source] = append(g.forward[e.source], e)
		g.backward[e.target] = append(g.backward[e.target], e)
	}
	return true
}

func (g *LineageGraph) Validate() [][]string {
	issues := [][]string{}
	for _, e := range g.edges {
		dataset, column, _ := strings.Cut(e.source, ".")
		declared, known := g.columns[dataset]
		if !known {
			issues = append(issues, []string{"unknown-dataset", e.target, e.source})
		} else if !contains(declared, column) {
			issues = append(issues, []string{"unknown-column", e.target, e.source})
		}
	}
	for _, group := range g.cycles() {
		issues = append(issues, append([]string{"cycle"}, group...))
	}
	sort.Slice(issues, func(a, b int) bool { return lessRows(issues[a], issues[b]) })
	return issues
}

func (g *LineageGraph) InputsOf(column string) []string {
	inputs := []string{}
	for _, e := range g.backward[column] {
		inputs = append(inputs, e.source)
	}
	sort.Strings(inputs)
	return inputs
}

// Level 2
func (g *LineageGraph) Upstream(column string) []string {
	return byDistance(g.walk(column, false, everyEdge))
}

func (g *LineageGraph) Downstream(column string) []string {
	return byDistance(g.walk(column, true, everyEdge))
}

// Level 3
func (g *LineageGraph) Impact(column string, change string) [][]string {
	reached := g.affected(column, change)
	rows := [][]string{}
	for _, name := range byDistance(reached) {
		use := "derived"
		if reached[name] == 1 {
			use = "direct"
		}
		rows = append(rows, []string{name, use})
	}
	return rows
}

func (g *LineageGraph) IsBreaking(column string, change string) bool {
	if change != "retype" {
		return len(g.affected(column, change)) > 0
	}
	for name := range g.typed(column) {
		for _, e := range g.forward[name] {
			if e.usage != "identity" {
				return true
			}
		}
	}
	return false
}

func (g *LineageGraph) ImpactedDatasets(column string, change string) []string {
	unique := map[string]bool{}
	for name := range g.affected(column, change) {
		unique[datasetOf(name)] = true
	}
	return sortedKeys(unique)
}

// Level 4
func (g *LineageGraph) Tag(column string, label string) bool {
	if !g.declared(column) || g.labels[column][label] {
		return false
	}
	if g.labels[column] == nil {
		g.labels[column] = map[string]bool{}
	}
	g.labels[column][label] = true
	return true
}

func (g *LineageGraph) TagsOf(column string) []string {
	sources := g.walk(column, false, carriesValue)
	sources[column] = 0
	found := map[string]bool{}
	for name := range sources {
		for label := range g.labels[name] {
			found[label] = true
		}
	}
	return sortedKeys(found)
}

func (g *LineageGraph) Publish(dataset string) bool {
	if _, known := g.columns[dataset]; !known || g.published[dataset] {
		return false
	}
	g.published[dataset] = true
	return true
}

func (g *LineageGraph) Exposures(label string) [][]string {
	found := [][]string{}
	for source, given := range g.labels {
		if !given[label] {
			continue
		}
		reached := g.walk(source, true, carriesValue)
		reached[source] = 0
		for name := range reached {
			if g.published[datasetOf(name)] {
				found = append(found, []string{name, source})
			}
		}
	}
	sort.Slice(found, func(a, b int) bool { return lessRows(found[a], found[b]) })
	return found
}

// Helpers
func (g *LineageGraph) declared(column string) bool {
	if !isColumnRef(column) {
		return false
	}
	dataset, name, _ := strings.Cut(column, ".")
	return contains(g.columns[dataset], name)
}

type queued struct {
	node  string
	steps int
}

// walk gives breadth-first distances from start along the kept edges; start is in the answer
// only when an edge leads back to it.
func (g *LineageGraph) walk(start string, ahead bool, keep func(*edge) bool) map[string]int {
	distance := map[string]int{}
	queue := []queued{{start, 0}}
	adjacency := g.backward
	if ahead {
		adjacency = g.forward
	}
	for head := 0; head < len(queue); head++ {
		current := queue[head]
		for _, e := range adjacency[current.node] {
			next := e.source
			if ahead {
				next = e.target
			}
			if _, done := distance[next]; keep(e) && !done {
				distance[next] = current.steps + 1
				queue = append(queue, queued{next, current.steps + 1})
			}
		}
	}
	return distance
}

func (g *LineageGraph) typed(column string) map[string]int {
	typed := g.walk(column, true, identityOnly)
	typed[column] = 0
	return typed
}

func (g *LineageGraph) affected(column string, change string) map[string]int {
	if change == "drop" {
		return g.walk(column, true, everyEdge)
	}
	affected := map[string]int{}
	if change == "rename" {
		for _, e := range g.forward[column] {
			affected[e.target] = 1
		}
		return affected
	}
	for name, steps := range g.typed(column) {
		for _, e := range g.forward[name] {
			if known, seen := affected[e.target]; !seen || steps+1 < known {
				affected[e.target] = steps + 1
			}
		}
	}
	return affected
}

func byDistance(distance map[string]int) []string {
	names := make([]string, 0, len(distance))
	for name := range distance {
		names = append(names, name)
	}
	sort.Slice(names, func(a, b int) bool {
		if distance[names[a]] != distance[names[b]] {
			return distance[names[a]] < distance[names[b]]
		}
		return names[a] < names[b]
	})
	return names
}

func sortedKeys(set map[string]bool) []string {
	keys := make([]string, 0, len(set))
	for key := range set {
		keys = append(keys, key)
	}
	sort.Strings(keys)
	return keys
}

type frame struct {
	node string
	at   int
}

// cycles gives the strongly connected groups that hold a cycle, by Kosaraju's two passes.
func (g *LineageGraph) cycles() [][]string {
	nodeSet := map[string]bool{}
	selfLoops := map[string]bool{}
	for _, e := range g.edges {
		nodeSet[e.source] = true
		nodeSet[e.target] = true
		if e.source == e.target {
			selfLoops[e.source] = true
		}
	}
	finished := []string{}
	seen := map[string]bool{}
	for _, root := range sortedKeys(nodeSet) {
		if seen[root] {
			continue
		}
		seen[root] = true
		stack := []frame{{root, 0}}
		for len(stack) > 0 {
			top := &stack[len(stack)-1]
			out := g.forward[top.node]
			if top.at == len(out) {
				finished = append(finished, top.node)
				stack = stack[:len(stack)-1]
				continue
			}
			next := out[top.at].target
			top.at++
			if !seen[next] {
				seen[next] = true
				stack = append(stack, frame{next, 0})
			}
		}
	}
	grouped := map[string]bool{}
	groups := [][]string{}
	for at := len(finished) - 1; at >= 0; at-- {
		root := finished[at]
		if grouped[root] {
			continue
		}
		grouped[root] = true
		members := []string{root}
		pending := []string{root}
		for len(pending) > 0 {
			node := pending[len(pending)-1]
			pending = pending[:len(pending)-1]
			for _, e := range g.backward[node] {
				if !grouped[e.source] {
					grouped[e.source] = true
					members = append(members, e.source)
					pending = append(pending, e.source)
				}
			}
		}
		if len(members) > 1 || selfLoops[root] {
			sort.Strings(members)
			groups = append(groups, members)
		}
	}
	return groups
}
