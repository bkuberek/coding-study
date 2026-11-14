package org_chart_outline

import (
	"sort"
	"strings"
)

// OrgChart indexes the rows once by id, then answers every question with a walk over the index.
// Nothing here recurses: the outline and the subtree sizes use an explicit stack and a
// breadth-first order, so a chain of 10^5 managers is as safe as a flat one.
type OrgChart struct {
	ids       []string
	parents   map[string]string
	names     map[string]string
	kids      map[string][]string
	orphanIDs []string
	tops      []string
	attached  map[string]bool
	sizes     map[string]int
	cycleList [][]string
}

func NewOrgChart() *OrgChart {
	chart := &OrgChart{}
	chart.Load(nil)
	return chart
}

// Level 1
func (o *OrgChart) Load(rows [][]string) {
	o.ids = make([]string, 0, len(rows))
	o.parents = make(map[string]string, len(rows))
	o.names = make(map[string]string, len(rows))
	o.kids = make(map[string][]string)
	for _, row := range rows {
		o.ids = append(o.ids, row[0])
		o.parents[row[0]] = row[1]
		o.names[row[0]] = row[2]
	}
	for _, id := range o.ids {
		o.kids[o.parents[id]] = append(o.kids[o.parents[id]], id)
	}
	o.orphanIDs = []string{}
	o.tops = []string{}
	isOrphan := map[string]bool{}
	for _, id := range o.ids {
		parent := o.parents[id]
		if _, known := o.names[parent]; parent != "" && !known {
			o.orphanIDs = append(o.orphanIDs, id)
			isOrphan[id] = true
		}
	}
	for _, id := range o.ids {
		if o.parents[id] == "" || isOrphan[id] {
			o.tops = append(o.tops, id)
		}
	}
	order := append([]string(nil), o.tops...)
	o.attached = make(map[string]bool, len(order))
	for _, top := range order {
		o.attached[top] = true
	}
	for next := 0; next < len(order); next++ {
		for _, kid := range o.kids[order[next]] {
			o.attached[kid] = true
			order = append(order, kid)
		}
	}
	o.sizes = make(map[string]int, len(order))
	for _, id := range order {
		o.sizes[id] = 1
	}
	for at := len(order) - 1; at >= 0; at-- {
		parent := o.parents[order[at]]
		if _, inTree := o.sizes[parent]; inTree {
			o.sizes[parent] += o.sizes[order[at]]
		}
	}
	o.cycleList = o.findCycles()
}

func (o *OrgChart) Roots() []string {
	return append([]string{}, o.kids[""]...)
}

func (o *OrgChart) NameOf(employee string) string {
	return o.names[employee]
}

func (o *OrgChart) Children(employee string) []string {
	if _, known := o.names[employee]; !known {
		return []string{}
	}
	return append([]string{}, o.kids[employee]...)
}

// Level 2
func (o *OrgChart) Orphans() []string {
	return append([]string{}, o.orphanIDs...)
}

func (o *OrgChart) Cycles() [][]string {
	copied := make([][]string, 0, len(o.cycleList))
	for _, cycle := range o.cycleList {
		copied = append(copied, append([]string{}, cycle...))
	}
	return copied
}

// Level 3
func (o *OrgChart) Chain(employee string) []string {
	path := []string{}
	if !o.attached[employee] {
		return path
	}
	path = append(path, employee)
	parent := o.parents[employee]
	for {
		if _, known := o.names[parent]; !known {
			break
		}
		path = append(path, parent)
		parent = o.parents[parent]
	}
	return path
}

func (o *OrgChart) LowestCommonManager(first string, second string) string {
	aboveSecond := map[string]bool{}
	for _, manager := range o.Chain(second) {
		aboveSecond[manager] = true
	}
	for _, manager := range o.Chain(first) {
		if aboveSecond[manager] {
			return manager
		}
	}
	return ""
}

// Level 4
func (o *OrgChart) SubtreeSize(employee string) int {
	return o.sizes[employee]
}

type outlineEntry struct {
	id    string
	depth int
}

func (o *OrgChart) Outline(order string) []string {
	lines := []string{}
	stack := []outlineEntry{}
	sortedTops := o.sorted(o.tops, order)
	for at := len(sortedTops) - 1; at >= 0; at-- {
		stack = append(stack, outlineEntry{sortedTops[at], 0})
	}
	for len(stack) > 0 {
		current := stack[len(stack)-1]
		stack = stack[:len(stack)-1]
		lines = append(lines, strings.Repeat("  ", current.depth)+o.names[current.id]+" ("+current.id+")")
		below := o.sorted(o.kids[current.id], order)
		for at := len(below) - 1; at >= 0; at-- {
			stack = append(stack, outlineEntry{below[at], current.depth + 1})
		}
	}
	return lines
}

func (o *OrgChart) sorted(members []string, order string) []string {
	copied := append([]string{}, members...)
	switch order {
	case "name":
		sort.Slice(copied, func(a, b int) bool {
			x, y := copied[a], copied[b]
			if o.names[x] != o.names[y] {
				return o.names[x] < o.names[y]
			}
			return x < y
		})
	case "size":
		sort.Slice(copied, func(a, b int) bool {
			x, y := copied[a], copied[b]
			if o.sizes[x] != o.sizes[y] {
				return o.sizes[x] > o.sizes[y]
			}
			if o.names[x] != o.names[y] {
				return o.names[x] < o.names[y]
			}
			return x < y
		})
	}
	return copied
}

func (o *OrgChart) findCycles() [][]string {
	position := make(map[string]int, len(o.ids))
	for index, id := range o.ids {
		position[id] = index
	}
	seen := make(map[string]bool, len(o.ids))
	for id := range o.attached {
		seen[id] = true
	}
	found := [][]string{}
	for _, start := range o.ids {
		walk := []string{}
		current := start
		for !seen[current] {
			seen[current] = true
			walk = append(walk, current)
			current = o.parents[current]
		}
		at := -1
		for index, member := range walk {
			if member == current {
				at = index
				break
			}
		}
		if at < 0 {
			continue
		}
		cycle := walk[at:]
		first := 0
		for k := 1; k < len(cycle); k++ {
			if position[cycle[k]] < position[cycle[first]] {
				first = k
			}
		}
		turned := append(append([]string{}, cycle[first:]...), cycle[:first]...)
		found = append(found, turned)
	}
	sort.Slice(found, func(a, b int) bool { return position[found[a][0]] < position[found[b][0]] })
	return found
}
