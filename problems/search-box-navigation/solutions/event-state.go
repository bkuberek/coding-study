package search_box_navigation

import "strings"

const (
	arrowDown = "ArrowDown"
	arrowUp   = "ArrowUp"
	enter     = "Enter"
	nothing   = -1
	noRequest = 0
)

// SearchBox keeps the list empty exactly when nothing is highlighted: show keeps the two in step.
type SearchBox struct {
	names          []string
	loweredNames   []string
	shown          []string
	highlight      int
	text           string
	requestsSent   int
	awaitedRequest int
	selected       []string
}

func NewSearchBox(names []string) *SearchBox {
	lowered := make([]string, len(names))
	for index, name := range names {
		lowered[index] = strings.ToLower(name)
	}
	return &SearchBox{
		names:          append([]string(nil), names...),
		loweredNames:   lowered,
		shown:          []string{},
		highlight:      nothing,
		awaitedRequest: noRequest,
		selected:       []string{},
	}
}

// Level 1
func (b *SearchBox) Keydown(timestamp int64, key string) {
	switch key {
	case arrowDown:
		b.move(1)
	case arrowUp:
		b.move(-1)
	case enter:
		b.selectHighlighted()
	}
}

// Keyup changes nothing: every action happens when the key goes down.
func (b *SearchBox) Keyup(timestamp int64, key string) {}

func (b *SearchBox) ResultsArrived(timestamp int64, items []string) {
	b.show(items)
}

func (b *SearchBox) Results(timestamp int64) []string {
	return append([]string{}, b.shown...)
}

func (b *SearchBox) Highlighted(timestamp int64) int {
	return b.highlight
}

func (b *SearchBox) HighlightedText(timestamp int64) string {
	if b.highlight == nothing {
		return ""
	}
	return b.shown[b.highlight]
}

// Level 2
func (b *SearchBox) Search(timestamp int64, query string) {
	needle := strings.ToLower(strings.TrimSpace(query))
	matches := []string{}
	if needle != "" {
		for index, lowered := range b.loweredNames {
			if strings.Contains(lowered, needle) {
				matches = append(matches, b.names[index])
			}
		}
	}
	b.show(matches)
}

// Level 3
func (b *SearchBox) InputChanged(timestamp int64, text string) int {
	b.text = text
	if strings.TrimSpace(text) == "" {
		b.stopAwaiting()
		return nothing
	}
	b.requestsSent++
	b.awaitedRequest = b.requestsSent
	return b.requestsSent
}

func (b *SearchBox) ResponseArrived(timestamp int64, requestId int, items []string) {
	if requestId == b.awaitedRequest {
		b.show(items)
	}
}

func (b *SearchBox) InputText(timestamp int64) string {
	return b.text
}

// Level 4
func (b *SearchBox) Selections(timestamp int64) []string {
	return append([]string{}, b.selected...)
}

// move adds count before taking the remainder, since Go's % keeps the sign of the dividend.
func (b *SearchBox) move(step int) {
	count := len(b.shown)
	if count > 0 {
		b.highlight = (b.highlight + step + count) % count
	}
}

func (b *SearchBox) selectHighlighted() {
	if b.highlight == nothing {
		return
	}
	choice := b.shown[b.highlight]
	b.selected = append(b.selected, choice)
	b.text = choice
	b.stopAwaiting()
}

// stopAwaiting handles an input that changed without a request: no response sent so far may be
// shown, and the list closes.
func (b *SearchBox) stopAwaiting() {
	b.awaitedRequest = noRequest
	b.show([]string{})
}

func (b *SearchBox) show(items []string) {
	b.shown = append([]string{}, items...)
	if len(items) == 0 {
		b.highlight = nothing
	} else {
		b.highlight = 0
	}
}
