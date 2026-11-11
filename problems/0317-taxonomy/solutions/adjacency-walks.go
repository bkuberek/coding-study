package taxonomy

import (
	"sort"
	"strings"
)

type set map[string]bool

// Taxonomy keeps, for every concept, the set of its parents and the set of its children.
// Questions about ancestors, descendants, cycles and expansion are breadth-first walks over those
// sets, so nothing recurses and a chain of 10^5 concepts is as safe as a flat list. Retired
// concepts keep their id and their labels; a table of replacements sends them to a live concept,
// and every method that takes an id first follows that table.
type Taxonomy struct {
	label map[string]string
	up    map[string]set
	down  map[string]set
	alts  map[string][]string
	index map[string]set
	gone  map[string]string
	same  map[string]set
}

func NewTaxonomy() *Taxonomy {
	return &Taxonomy{
		label: map[string]string{},
		up:    map[string]set{},
		down:  map[string]set{},
		alts:  map[string][]string{},
		index: map[string]set{},
		gone:  map[string]string{},
		same:  map[string]set{},
	}
}

// Level 1
func (t *Taxonomy) AddConcept(concept string, label string, parents []string) string {
	if _, taken := t.label[concept]; taken {
		return "duplicate"
	}
	for _, parent := range parents {
		if parent == concept {
			return "cycle"
		}
	}
	for _, parent := range parents {
		if _, known := t.label[parent]; !known {
			return "unknown-broader"
		}
	}
	resolved := set{}
	for _, parent := range parents {
		resolved[t.follow(parent)] = true
	}
	for parent := range resolved {
		if schemeOf(parent) != schemeOf(concept) {
			return "cross-scheme"
		}
	}
	t.label[concept] = label
	t.up[concept] = resolved
	t.down[concept] = set{}
	t.alts[concept] = []string{}
	t.same[concept] = set{}
	for parent := range resolved {
		t.down[parent][concept] = true
	}
	t.indexLabel(concept, label)
	return "ok"
}

func (t *Taxonomy) AddBroader(narrower string, broader string) string {
	child, parent := t.follow(narrower), t.follow(broader)
	if !t.has(child) || !t.has(parent) {
		return "unknown-concept"
	}
	if schemeOf(child) != schemeOf(parent) {
		return "cross-scheme"
	}
	if child == parent || reach(parent, t.up)[child] {
		return "cycle"
	}
	t.up[child][parent] = true
	t.down[parent][child] = true
	return "ok"
}

func (t *Taxonomy) PrefLabel(concept string) string {
	return t.label[t.follow(concept)]
}

func (t *Taxonomy) Broader(concept string) []string {
	return sortedKeys(t.up[t.follow(concept)])
}

func (t *Taxonomy) Narrower(concept string) []string {
	return sortedKeys(t.down[t.follow(concept)])
}

func (t *Taxonomy) Ancestors(concept string) []string {
	return nearestFirst(t.follow(concept), t.up)
}

func (t *Taxonomy) Descendants(concept string) []string {
	return nearestFirst(t.follow(concept), t.down)
}

func (t *Taxonomy) Roots() []string {
	found := []string{}
	for concept, parents := range t.up {
		if _, retired := t.gone[concept]; !retired && len(parents) == 0 {
			found = append(found, concept)
		}
	}
	sort.Strings(found)
	return found
}

// Level 2
func (t *Taxonomy) LowestCommonAncestors(first string, second string) []string {
	a, b := t.follow(first), t.follow(second)
	if !t.has(a) || !t.has(b) {
		return []string{}
	}
	aboveB := reach(b, t.up)
	common := set{}
	for concept := range reach(a, t.up) {
		if aboveB[concept] {
			common[concept] = true
		}
	}
	lowest := []string{}
	for concept := range common {
		covered := false
		for kid := range t.down[concept] {
			if common[kid] {
				covered = true
				break
			}
		}
		if !covered {
			lowest = append(lowest, concept)
		}
	}
	sort.Strings(lowest)
	return lowest
}

// Level 3
func (t *Taxonomy) AddAltLabel(concept string, label string) string {
	id := t.follow(concept)
	if !t.has(id) {
		return "unknown-concept"
	}
	key := normalize(label)
	if key == "" {
		return "empty-label"
	}
	if normalize(t.label[id]) == key {
		return "duplicate"
	}
	for _, text := range t.alts[id] {
		if normalize(text) == key {
			return "duplicate"
		}
	}
	t.alts[id] = append(t.alts[id], label)
	t.indexLabel(id, label)
	return "ok"
}

func (t *Taxonomy) AltLabels(concept string) []string {
	return append([]string{}, t.alts[t.follow(concept)]...)
}

func (t *Taxonomy) FindByLabel(label string) []string {
	return sortedKeys(t.matching(label))
}

func (t *Taxonomy) Expand(labels []string) []string {
	seen := set{}
	queue := []string{}
	for _, label := range labels {
		for concept := range t.matching(label) {
			if !seen[concept] {
				seen[concept] = true
				queue = append(queue, concept)
			}
		}
	}
	for next := 0; next < len(queue); next++ {
		for kid := range t.down[queue[next]] {
			if !seen[kid] {
				seen[kid] = true
				queue = append(queue, kid)
			}
		}
	}
	return sortedKeys(seen)
}

// Level 4
func (t *Taxonomy) Rename(concept string, label string) string {
	id := t.follow(concept)
	if !t.has(id) {
		return "unknown-concept"
	}
	old, key := t.label[id], normalize(label)
	kept := []string{}
	for _, text := range t.alts[id] {
		if normalize(text) != key {
			kept = append(kept, text)
		}
	}
	if oldKey := normalize(old); oldKey != "" && oldKey != key {
		kept = append(kept, old)
	}
	t.alts[id] = kept
	t.label[id] = label
	t.indexLabel(id, label)
	return "ok"
}

func (t *Taxonomy) RemoveBroader(narrower string, broader string) string {
	child, parent := t.follow(narrower), t.follow(broader)
	if !t.has(child) || !t.has(parent) {
		return "unknown-concept"
	}
	if !t.up[child][parent] {
		return "no-link"
	}
	delete(t.up[child], parent)
	delete(t.down[parent], child)
	return "ok"
}

func (t *Taxonomy) Deprecate(concept string, replacement string) string {
	if !t.has(concept) || !t.has(replacement) {
		return "unknown-concept"
	}
	if _, retired := t.gone[concept]; retired {
		return "deprecated"
	}
	target := t.follow(replacement)
	if target == concept {
		return "same-concept"
	}
	if schemeOf(target) != schemeOf(concept) {
		return "cross-scheme"
	}
	if len(t.down[concept]) > 0 {
		return "has-narrower"
	}
	for parent := range t.up[concept] {
		delete(t.down[parent], concept)
	}
	t.up[concept] = set{}
	for partner := range t.same[concept] {
		delete(t.same[partner], concept)
		t.same[partner][target] = true
		t.same[target][partner] = true
	}
	t.same[concept] = set{}
	t.gone[concept] = target
	return "ok"
}

func (t *Taxonomy) Resolve(concept string) string {
	id := t.follow(concept)
	if t.has(id) {
		return id
	}
	return ""
}

func (t *Taxonomy) AddExactMatch(first string, second string) string {
	a, b := t.follow(first), t.follow(second)
	if !t.has(a) || !t.has(b) {
		return "unknown-concept"
	}
	if schemeOf(a) == schemeOf(b) {
		return "same-scheme"
	}
	t.same[a][b] = true
	t.same[b][a] = true
	return "ok"
}

func (t *Taxonomy) Translate(concepts []string, scheme string) []string {
	found := set{}
	for _, concept := range t.known(concepts) {
		for _, target := range t.targets(concept, scheme) {
			found[target] = true
		}
	}
	return sortedKeys(found)
}

func (t *Taxonomy) Unmapped(concepts []string, scheme string) []string {
	found := []string{}
	for _, concept := range t.known(concepts) {
		if len(t.targets(concept, scheme)) == 0 {
			found = append(found, concept)
		}
	}
	return found
}

// Helpers
func (t *Taxonomy) has(concept string) bool {
	_, known := t.label[concept]
	return known
}

func schemeOf(concept string) string {
	if colon := strings.IndexByte(concept, ':'); colon >= 0 {
		return concept[:colon]
	}
	return ""
}

// normalize trims the spaces at both ends, turns each run of spaces into one and lower-cases A to Z.
func normalize(label string) string {
	parts := []string{}
	for _, part := range strings.Split(label, " ") {
		if part != "" {
			parts = append(parts, part)
		}
	}
	return strings.ToLower(strings.Join(parts, " "))
}

func sortedKeys(items set) []string {
	keys := make([]string, 0, len(items))
	for key := range items {
		keys = append(keys, key)
	}
	sort.Strings(keys)
	return keys
}

func (t *Taxonomy) follow(concept string) string {
	current := concept
	for {
		next, retired := t.gone[current]
		if !retired {
			break
		}
		current = next
	}
	if current != concept {
		t.gone[concept] = current
	}
	return current
}

func (t *Taxonomy) known(concepts []string) []string {
	resolved := set{}
	for _, concept := range concepts {
		if id := t.follow(concept); t.has(id) {
			resolved[id] = true
		}
	}
	return sortedKeys(resolved)
}

func (t *Taxonomy) targets(concept string, scheme string) []string {
	if schemeOf(concept) == scheme {
		return []string{concept}
	}
	found := []string{}
	for partner := range t.same[concept] {
		if schemeOf(partner) == scheme {
			found = append(found, partner)
		}
	}
	return found
}

func (t *Taxonomy) indexLabel(concept string, label string) {
	key := normalize(label)
	if key == "" {
		return
	}
	if t.index[key] == nil {
		t.index[key] = set{}
	}
	t.index[key][concept] = true
}

func (t *Taxonomy) matching(label string) set {
	found := set{}
	key := normalize(label)
	if key == "" {
		return found
	}
	for concept := range t.index[key] {
		found[t.follow(concept)] = true
	}
	return found
}

// reach is the concept itself and everything above (or below) it.
func reach(start string, edges map[string]set) set {
	seen := set{start: true}
	queue := []string{start}
	for next := 0; next < len(queue); next++ {
		for neighbour := range edges[queue[next]] {
			if !seen[neighbour] {
				seen[neighbour] = true
				queue = append(queue, neighbour)
			}
		}
	}
	return seen
}

func nearestFirst(start string, edges map[string]set) []string {
	found := []string{}
	if _, known := edges[start]; !known {
		return found
	}
	seen := set{start: true}
	level := []string{start}
	for len(level) > 0 {
		following := set{}
		for _, current := range level {
			for neighbour := range edges[current] {
				if !seen[neighbour] {
					following[neighbour] = true
				}
			}
		}
		for concept := range following {
			seen[concept] = true
		}
		level = sortedKeys(following)
		found = append(found, level...)
	}
	return found
}
