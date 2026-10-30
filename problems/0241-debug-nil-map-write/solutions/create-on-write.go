package debug_nil_map_write

// PageViews counts views by page, then by visitor: visits[page][visitor].
type PageViews struct {
	visits map[string]map[string]int
}

func NewPageViews() *PageViews {
	return &PageViews{visits: make(map[string]map[string]int)}
}

func (p *PageViews) Record(page string, visitor string) {
	p.visitorsOf(page)[visitor]++
}

func (p *PageViews) Views(page string) int {
	total := 0
	for _, count := range p.visits[page] {
		total += count
	}
	return total
}

func (p *PageViews) UniqueVisitors(page string) int {
	return len(p.visits[page])
}

// Merge adds the views of source to target, for a page that moved to a new address.
func (p *PageViews) Merge(source string, target string) {
	from, ok := p.visits[source]
	if !ok || source == target {
		return
	}
	into := p.visitorsOf(target)
	for visitor, count := range from {
		into[visitor] += count
	}
	delete(p.visits, source)
}

// visitorsOf returns the visitor counts of page for writing, creating them on first use. A
// missing key reads as a nil map, which is fine to read and panics on the first write.
func (p *PageViews) visitorsOf(page string) map[string]int {
	byVisitor, ok := p.visits[page]
	if !ok {
		byVisitor = make(map[string]int)
		p.visits[page] = byVisitor
	}
	return byVisitor
}
