package line_diff_and_merge

import (
	"fmt"
	"regexp"
	"slices"
	"strconv"
)

const (
	keep      = ' '
	remove    = '-'
	add       = '+'
	ours      = "<<<<<<< ours"
	baseMark  = "||||||| base"
	separator = "======="
	theirs    = ">>>>>>> theirs"
)

var header = regexp.MustCompile(`^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@$`)

type step struct {
	kind byte
	line string
}

type hunk struct {
	start int
	old   []string
	fresh []string
}

type LineDiff struct {
	last []string
}

func NewLineDiff() *LineDiff {
	return &LineDiff{last: []string{}}
}

// Level 1
func (d *LineDiff) Lcs(before []string, after []string) []string {
	kept := []string{}
	for _, s := range script(before, after) {
		if s.kind == keep {
			kept = append(kept, s.line)
		}
	}
	return kept
}

func (d *LineDiff) Diff(before []string, after []string) []string {
	lines := []string{}
	for _, s := range script(before, after) {
		lines = append(lines, string(s.kind)+s.line)
	}
	return lines
}

// Level 2
func (d *LineDiff) Unified(before []string, after []string, context int) []string {
	steps := script(before, after)
	changed := []int{}
	for index, s := range steps {
		if s.kind != keep {
			changed = append(changed, index)
		}
	}
	lines := []string{}
	if len(changed) == 0 {
		return lines
	}
	groups := [][2]int{}
	first, previous := changed[0], changed[0]
	for _, index := range changed[1:] {
		if index-previous-1 > 2*context {
			groups = append(groups, [2]int{first, previous})
			first = index
		}
		previous = index
	}
	groups = append(groups, [2]int{first, previous})
	for _, group := range groups {
		start := max(0, group[0]-context)
		end := min(len(steps), group[1]+context+1)
		prior, inside := steps[:start], steps[start:end]
		oldRange := rangeText(count(prior, add), count(inside, add))
		newRange := rangeText(count(prior, remove), count(inside, remove))
		lines = append(lines, fmt.Sprintf("@@ -%s +%s @@", oldRange, newRange))
		for _, s := range inside {
			lines = append(lines, string(s.kind)+s.line)
		}
	}
	return lines
}

// Level 3
func (d *LineDiff) ApplyPatch(lines []string, patch []string, maxOffset int) []string {
	result := slices.Clone(lines)
	statuses := []string{}
	added, shift, floor := 0, 0, 0
	for _, h := range parseHunks(patch) {
		base := h.start + added
		found := findHunk(result, h.old, base+shift, floor, maxOffset)
		if found < 0 {
			statuses = append(statuses, "rejected")
			continue
		}
		result = slices.Concat(result[:found], h.fresh, result[found+len(h.old):])
		shift = found - base
		added += len(h.fresh) - len(h.old)
		floor = found + len(h.fresh)
		statuses = append(statuses, fmt.Sprintf("applied %d", shift))
	}
	d.last = result
	return statuses
}

func (d *LineDiff) Patched() []string {
	return slices.Clone(d.last)
}

// Level 4
func (d *LineDiff) Merge(base []string, oursLines []string, theirsLines []string) []string {
	toOurs := keptAt(base, oursLines)
	toTheirs := keptAt(base, theirsLines)
	merged := []string{}
	o, a, b := 0, 0, 0
	for index, line := range base {
		j, inOurs := toOurs[index]
		k, inTheirs := toTheirs[index]
		if inOurs && inTheirs {
			merged = append(merged, resolve(base[o:index], oursLines[a:j], theirsLines[b:k])...)
			merged = append(merged, line)
			o, a, b = index+1, j+1, k+1
		}
	}
	return append(merged, resolve(base[o:], oursLines[a:], theirsLines[b:])...)
}

// script is the diff with the most kept lines that, read from the top, keeps rather than removes
// and removes rather than adds wherever both stay optimal.
func script(before []string, after []string) []step {
	n, m := len(before), len(after)
	// longest[i][j]: the length of a longest common subsequence of before[i:] and after[j:].
	longest := make([][]int, n+1)
	for i := range longest {
		longest[i] = make([]int, m+1)
	}
	for i := n - 1; i >= 0; i-- {
		for j := m - 1; j >= 0; j-- {
			if before[i] == after[j] {
				longest[i][j] = longest[i+1][j+1] + 1
			} else {
				longest[i][j] = max(longest[i+1][j], longest[i][j+1])
			}
		}
	}
	steps := []step{}
	i, j := 0, 0
	for i < n || j < m {
		switch {
		case i < n && j < m && before[i] == after[j]:
			steps = append(steps, step{keep, before[i]})
			i, j = i+1, j+1
		case i < n && (j == m || longest[i+1][j] >= longest[i][j+1]):
			steps = append(steps, step{remove, before[i]})
			i++
		default:
			steps = append(steps, step{add, after[j]})
			j++
		}
	}
	return steps
}

// count is the number of steps that are not of the skipped kind.
func count(steps []step, skipped byte) int {
	total := 0
	for _, s := range steps {
		if s.kind != skipped {
			total++
		}
	}
	return total
}

func rangeText(linesBefore int, size int) string {
	switch size {
	case 0:
		return fmt.Sprintf("%d,0", linesBefore)
	case 1:
		return strconv.Itoa(linesBefore + 1)
	default:
		return fmt.Sprintf("%d,%d", linesBefore+1, size)
	}
}

// parseHunks reads each hunk: the index where its old lines start, its old lines and its new lines.
func parseHunks(patch []string) []*hunk {
	hunks := []*hunk{}
	for _, line := range patch {
		if match := header.FindStringSubmatch(line); match != nil {
			oldStart, _ := strconv.Atoi(match[1])
			oldCount := 1
			if match[2] != "" {
				oldCount, _ = strconv.Atoi(match[2])
			}
			start := oldStart
			if oldCount > 0 {
				start = oldStart - 1
			}
			hunks = append(hunks, &hunk{start: start, old: []string{}, fresh: []string{}})
			continue
		}
		if line == "" {
			continue
		}
		current := hunks[len(hunks)-1]
		text := line[1:]
		if line[0] != add {
			current.old = append(current.old, text)
		}
		if line[0] != remove {
			current.fresh = append(current.fresh, text)
		}
	}
	return hunks
}

// findHunk is the nearest position to expected where old matches, the earlier one first, or -1.
func findHunk(result []string, old []string, expected int, floor int, maxOffset int) int {
	for distance := 0; distance <= maxOffset; distance++ {
		for _, position := range []int{expected - distance, expected + distance} {
			fits := floor <= position && position+len(old) <= len(result)
			if fits && slices.Equal(result[position:position+len(old)], old) {
				return position
			}
		}
	}
	return -1
}

// keptAt maps each line of base that the diff to other keeps to the index it keeps it at.
func keptAt(base []string, other []string) map[int]int {
	kept := map[int]int{}
	i, j := 0, 0
	for _, s := range script(base, other) {
		if s.kind == keep {
			kept[i] = j
		}
		if s.kind != add {
			i++
		}
		if s.kind != remove {
			j++
		}
	}
	return kept
}

func resolve(base []string, oursChunk []string, theirsChunk []string) []string {
	switch {
	case slices.Equal(oursChunk, theirsChunk):
		return oursChunk
	case slices.Equal(oursChunk, base):
		return theirsChunk
	case slices.Equal(theirsChunk, base):
		return oursChunk
	}
	conflict := []string{ours}
	conflict = append(conflict, oursChunk...)
	conflict = append(conflict, baseMark)
	conflict = append(conflict, base...)
	conflict = append(conflict, separator)
	conflict = append(conflict, theirsChunk...)
	return append(conflict, theirs)
}
