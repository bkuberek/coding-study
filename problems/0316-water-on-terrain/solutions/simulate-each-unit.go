package water_on_terrain

import "strings"

const (
	stay  = -1
	spill = -2
)

// Terrain keeps water as a depth per column; a column's level is its height plus its water.
//
// One unit of water is one walk: try to the left, then to the right, one column at a time and
// never uphill, and note where the final flat stretch of the walk begins. The walk either reaches
// an edge (the unit falls off), ends lower than it began (the unit settles at the start of the
// final flat stretch) or ends where it began (this direction does nothing).
type Terrain struct {
	heights      []int
	depths       []int
	spilledUnits int
}

func NewTerrain(heights []int) *Terrain {
	return &Terrain{heights: append([]int(nil), heights...), depths: make([]int, len(heights))}
}

// Level 1
func (t *Terrain) Render() []string {
	return t.picture(0, len(t.heights)-1)
}

func (t *Terrain) Tallest() int {
	best := 0
	for _, height := range t.heights {
		if height > best {
			best = height
		}
	}
	return best
}

// Level 2
func (t *Terrain) Pour(column int) []int {
	t.drop(column)
	return t.Water()
}

func (t *Terrain) Water() []int {
	return append([]int{}, t.depths...)
}

func (t *Terrain) Spilled() int {
	return t.spilledUnits
}

// Level 3
func (t *Terrain) PourMany(column int, units int) []int {
	for unit := 0; unit < units; unit++ {
		t.drop(column)
	}
	return t.Water()
}

// Level 4
func (t *Terrain) RenderWindow(first int, last int) []string {
	return t.picture(first, last)
}

func (t *Terrain) level(column int) int {
	return t.heights[column] + t.depths[column]
}

func (t *Terrain) drop(column int) {
	for _, step := range []int{-1, 1} {
		landing := t.walk(column, step)
		if landing == spill {
			t.spilledUnits++
			return
		}
		if landing != stay {
			t.depths[landing]++
			return
		}
	}
	t.depths[column]++
}

func (t *Terrain) walk(column int, step int) int {
	at, flatStart := column, column
	for {
		ahead := at + step
		if ahead < 0 || ahead >= len(t.heights) {
			return spill
		}
		if t.level(ahead) > t.level(at) {
			break
		}
		if t.level(ahead) < t.level(at) {
			flatStart = ahead
		}
		at = ahead
	}
	if t.level(flatStart) < t.level(column) {
		return flatStart
	}
	return stay
}

func (t *Terrain) picture(first int, last int) []string {
	top := 0
	for column := range t.heights {
		if t.level(column) > top {
			top = t.level(column)
		}
	}
	rows := []string{}
	for row := top; row >= 1; row-- {
		var cells strings.Builder
		for column := first; column <= last; column++ {
			switch {
			case t.heights[column] >= row:
				cells.WriteByte('#')
			case t.level(column) >= row:
				cells.WriteByte('~')
			default:
				cells.WriteByte('.')
			}
		}
		rows = append(rows, cells.String())
	}
	return rows
}
