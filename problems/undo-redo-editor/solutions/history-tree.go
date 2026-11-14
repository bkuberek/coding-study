package undo_redo_editor

import "strings"

const (
	groupGapMs = 1000
	root       = 0
)

// step is one recorded edit, kept as a command that can be applied and reverted: at position,
// removed was replaced by inserted. The step is also the history state it leads to.
type step struct {
	number       int
	parent       *step
	position     int
	removed      string
	inserted     string
	children     []*step
	currentChild *step
}

func (s *step) apply(text string) string {
	return text[:s.position] + s.inserted + text[s.position+len(s.removed):]
}

func (s *step) revert(text string) string {
	return text[:s.position] + s.removed + text[s.position+len(s.inserted):]
}

// ancestors lists this step and every step above it, up to the root.
func (s *step) ancestors() []*step {
	var chain []*step
	for current := s; current != nil; current = current.parent {
		chain = append(chain, current)
	}
	return chain
}

type Editor struct {
	content     string
	steps       []*step
	current     *step
	checkpoints map[string]string
	groupOpen   bool
	lastTypedAt int64
}

func NewEditor(initial string) *Editor {
	first := &step{number: root}
	return &Editor{
		content:     initial,
		steps:       []*step{first},
		current:     first,
		checkpoints: map[string]string{},
	}
}

// Level 1
func (e *Editor) Insert(position int, text string) {
	e.groupOpen = false
	e.record(min(position, len(e.content)), "", text)
}

func (e *Editor) Erase(position int, count int) {
	e.groupOpen = false
	start := min(position, len(e.content))
	end := min(len(e.content), start+count)
	e.record(start, e.content[start:end], "")
}

func (e *Editor) Undo() bool {
	e.groupOpen = false
	if e.current.parent == nil {
		return false
	}
	e.content = e.current.revert(e.content)
	e.current = e.current.parent
	return true
}

func (e *Editor) Redo() bool {
	e.groupOpen = false
	child := e.current.currentChild
	if child == nil {
		return false
	}
	e.content = child.apply(e.content)
	e.current = child
	return true
}

func (e *Editor) Text() string {
	return e.content
}

// Level 2
func (e *Editor) TypeText(timestamp int64, position int, text string) {
	at := min(position, len(e.content))
	if e.joinsGroup(timestamp, at) {
		e.content = e.content[:at] + text + e.content[at:]
		e.current.inserted += text
	} else {
		e.record(at, "", text)
	}
	e.groupOpen = true
	e.lastTypedAt = timestamp
}

func (e *Editor) joinsGroup(timestamp int64, position int) bool {
	group := e.current
	return e.groupOpen &&
		position == group.position+len(group.inserted) &&
		timestamp-e.lastTypedAt <= groupGapMs &&
		!strings.HasSuffix(group.inserted, " ")
}

// Level 3
func (e *Editor) Checkpoint(name string) {
	e.groupOpen = false
	e.checkpoints[name] = e.content
}

func (e *Editor) Restore(name string) bool {
	e.groupOpen = false
	saved, ok := e.checkpoints[name]
	if !ok {
		return false
	}
	e.record(0, e.content, saved)
	return true
}

// Level 4
func (e *Editor) State() int {
	return e.current.number
}

func (e *Editor) Branches() []int {
	numbers := make([]int, 0, len(e.current.children))
	for _, child := range e.current.children {
		numbers = append(numbers, child.number)
	}
	return numbers
}

func (e *Editor) Jump(state int) bool {
	e.groupOpen = false
	if state < 0 || state >= len(e.steps) {
		return false
	}
	target := e.steps[state]
	pathDown := target.ancestors()
	onTargetPath := make(map[*step]int, len(pathDown))
	for index, s := range pathDown {
		onTargetPath[s] = index
	}
	common, found := onTargetPath[e.current]
	for !found {
		e.content = e.current.revert(e.content)
		e.current = e.current.parent
		common, found = onTargetPath[e.current]
	}
	for index := common - 1; index >= 0; index-- {
		e.content = pathDown[index].apply(e.content)
	}
	for index := 1; index < len(pathDown); index++ {
		pathDown[index].currentChild = pathDown[index-1]
	}
	e.current = target
	return true
}

// record records one step, unless it would leave the text as it is.
func (e *Editor) record(position int, removed string, inserted string) {
	if removed == inserted {
		return
	}
	s := &step{number: len(e.steps), parent: e.current, position: position, removed: removed, inserted: inserted}
	e.steps = append(e.steps, s)
	e.current.children = append(e.current.children, s)
	e.current.currentChild = s
	e.content = s.apply(e.content)
	e.current = s
}
