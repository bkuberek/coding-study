package query_planner

import (
	"fmt"
	"strings"
)

var keywords = map[string]bool{"SELECT": true, "FROM": true, "JOIN": true, "ON": true, "WHERE": true, "AND": true}

const randomRead = 4

type column struct{ table, name string }

func (c column) String() string { return c.table + "." + c.name }

type condition struct {
	col   column
	op    string
	value string
}

func (c condition) String() string { return c.col.String() + " " + c.op + " " + c.value }

func isLetter(c byte) bool { return (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || c == '_' }

func isDigit(c byte) bool { return c >= '0' && c <= '9' }

func tokenize(sql string) ([]string, bool) {
	var tokens []string
	for i := 0; i < len(sql); {
		c := sql[i]
		switch {
		case c == ' ':
			i++
		case isLetter(c):
			j := i + 1
			for j < len(sql) && (isLetter(sql[j]) || isDigit(sql[j])) {
				j++
			}
			tokens = append(tokens, sql[i:j])
			i = j
		case isDigit(c) || (c == '-' && i+1 < len(sql) && isDigit(sql[i+1])):
			j := i + 1
			for j < len(sql) && isDigit(sql[j]) {
				j++
			}
			digits := j - i
			if c == '-' {
				digits--
			}
			if digits > 9 {
				return nil, false
			}
			tokens = append(tokens, sql[i:j])
			i = j
		case strings.IndexByte("*,.=<>", c) >= 0:
			tokens = append(tokens, string(c))
			i++
		default:
			return nil, false
		}
	}
	return tokens, true
}

// query holds SELECT ... FROM t [JOIN u ON a.x = b.y]... [WHERE c op n [AND ...]], as written.
// A parser method that finds a token out of place sets bad and returns zero values.
type query struct {
	selected   []column
	star       bool
	tables     []string
	joins      [][2]column
	conditions []condition
	tokens     []string
	pos        int
	bad        bool
}

func (q *query) peek() string {
	if q.pos < len(q.tokens) {
		return q.tokens[q.pos]
	}
	return ""
}

func (q *query) expect(token string) {
	if q.peek() != token {
		q.bad = true
		return
	}
	q.pos++
}

func (q *query) name() string {
	token := q.peek()
	if token == "" || !isLetter(token[0]) || keywords[token] {
		q.bad = true
		return ""
	}
	q.pos++
	return token
}

func (q *query) column() column {
	table := q.name()
	q.expect(".")
	return column{table, q.name()}
}

func (q *query) condition() condition {
	col := q.column()
	op := q.peek()
	if op != "=" && op != "<" && op != ">" {
		q.bad = true
		return condition{}
	}
	q.pos++
	value := q.peek()
	if value == "" || !(isDigit(value[0]) || value[0] == '-') {
		q.bad = true
		return condition{}
	}
	q.pos++
	return condition{col, op, value}
}

// parseQuery returns nil for a syntax error.
func parseQuery(sql string) *query {
	tokens, ok := tokenize(sql)
	if !ok {
		return nil
	}
	q := &query{tokens: tokens}
	q.expect("SELECT")
	if q.peek() == "*" {
		q.star = true
		q.pos++
	} else {
		q.selected = append(q.selected, q.column())
		for !q.bad && q.peek() == "," {
			q.pos++
			q.selected = append(q.selected, q.column())
		}
	}
	q.expect("FROM")
	q.tables = append(q.tables, q.name())
	for !q.bad && q.peek() == "JOIN" {
		q.pos++
		q.tables = append(q.tables, q.name())
		q.expect("ON")
		left := q.column()
		q.expect("=")
		q.joins = append(q.joins, [2]column{left, q.column()})
	}
	if !q.bad && q.peek() == "WHERE" {
		q.pos++
		q.conditions = append(q.conditions, q.condition())
		for !q.bad && q.peek() == "AND" {
			q.pos++
			q.conditions = append(q.conditions, q.condition())
		}
	}
	if q.bad || q.pos != len(q.tokens) {
		return nil
	}
	return q
}

func (q *query) columnRefs() []column {
	refs := append([]column{}, q.selected...)
	for _, join := range q.joins {
		refs = append(refs, join[0], join[1])
	}
	for _, c := range q.conditions {
		refs = append(refs, c.col)
	}
	return refs
}

// rounded is numerator / denominator rounded half up, and at least 1.
func rounded(numerator, denominator int64) int64 {
	value := (2*numerator + denominator) / (2 * denominator)
	if value < 1 {
		return 1
	}
	return value
}

type edge struct {
	left, right             int
	leftColumn, rightColumn column
}

type stat struct {
	rows     int64
	distinct []int64
}

// plan is one checked query: tables in written order (a table is its position, a set of tables a
// bit mask), the conditions of each table, and one edge per join, written with the earlier table
// first.
type plan struct {
	planner *QueryPlanner
	q       *query
	tables  []string
	where   [][]condition
	edges   []edge
}

func contains(list []string, value string) bool {
	for _, item := range list {
		if item == value {
			return true
		}
	}
	return false
}

func indexOf(list []string, value string) int {
	for i, item := range list {
		if item == value {
			return i
		}
	}
	return -1
}

// newPlan returns the plan, or the error line's detail.
func (p *QueryPlanner) newPlan(sql string, needStats bool) (*plan, string) {
	q := parseQuery(sql)
	if q == nil {
		return nil, "syntax"
	}
	var seen []string
	for _, table := range q.tables {
		if _, ok := p.columns[table]; !ok {
			return nil, "unknown-table " + table
		}
		if contains(seen, table) {
			return nil, "duplicate-table " + table
		}
		seen = append(seen, table)
	}
	for _, ref := range q.columnRefs() {
		if !contains(seen, ref.table) || !contains(p.columns[ref.table], ref.name) {
			return nil, "unknown-column " + ref.String()
		}
	}
	pl := &plan{planner: p, q: q, tables: q.tables}
	for index, join := range q.joins {
		table := q.tables[index+1]
		earlier := q.tables[:index+1]
		left, right := join[0], join[1]
		if left.table == table && contains(earlier, right.table) {
			left, right = right, left
		} else if !(right.table == table && contains(earlier, left.table)) {
			return nil, "bad-join " + table
		}
		pl.edges = append(pl.edges, edge{indexOf(q.tables, left.table), index + 1, left, right})
	}
	if needStats {
		for _, table := range q.tables {
			if _, ok := p.stats[table]; !ok {
				return nil, "no-stats " + table
			}
		}
	}
	for _, table := range q.tables {
		var own []condition
		for _, c := range q.conditions {
			if c.col.table == table {
				own = append(own, c)
			}
		}
		pl.where = append(pl.where, own)
	}
	return pl, ""
}

func (pl *plan) head() string {
	if pl.q.star {
		return "project *"
	}
	names := make([]string, len(pl.q.selected))
	for i, c := range pl.q.selected {
		names[i] = c.String()
	}
	return "project " + strings.Join(names, ", ")
}

// --- estimates

func (pl *plan) distinct(c column) int64 {
	return pl.planner.stats[c.table].distinct[indexOf(pl.planner.columns[c.table], c.name)]
}

func (pl *plan) divisor(c condition) int64 {
	if c.op == "=" {
		return pl.distinct(c.col)
	}
	return 3
}

func (pl *plan) base(table int) int64 { return pl.planner.stats[pl.tables[table]].rows }

// out is the rows of a table after its conditions.
func (pl *plan) out(table int) int64 {
	if len(pl.where[table]) == 0 {
		return pl.base(table)
	}
	divisor := int64(1)
	for _, c := range pl.where[table] {
		divisor *= pl.divisor(c)
	}
	return rounded(pl.base(table), divisor)
}

func (pl *plan) rows(mask int) int64 {
	numerator := int64(1)
	for t := range pl.tables {
		if mask&(1<<t) != 0 {
			numerator *= pl.out(t)
		}
	}
	denominator := int64(1)
	for _, e := range pl.edges {
		if mask&(1<<e.left) != 0 && mask&(1<<e.right) != 0 {
			denominator *= max(pl.distinct(e.leftColumn), pl.distinct(e.rightColumn))
		}
	}
	return rounded(numerator, denominator)
}

// edgeInto is the edge between a table and a set it joins, written with the set's column first.
func (pl *plan) edgeInto(mask, table int) (column, column, bool) {
	for _, e := range pl.edges {
		if e.right == table && mask&(1<<e.left) != 0 {
			return e.leftColumn, e.rightColumn, true
		}
		if e.left == table && mask&(1<<e.right) != 0 {
			return e.rightColumn, e.leftColumn, true
		}
	}
	return column{}, column{}, false
}

// --- level 4 access paths and join methods

// access is the cheapest way to read a table: its cost, and the position of the condition an
// index serves, or -1 for a full scan. Ties keep the full scan, then the condition written first.
func (pl *plan) access(table int) (int64, int) {
	cost, used := pl.base(table), -1
	indexed := pl.planner.indexes[pl.tables[table]]
	for position, c := range pl.where[table] {
		if c.op == "=" && indexed[c.col.name] {
			candidate := randomRead * rounded(pl.base(table), pl.distinct(c.col))
			if candidate < cost {
				cost, used = candidate, position
			}
		}
	}
	return cost, used
}

func (pl *plan) joinStep(leftRows int64, table int) (string, int64) {
	innerCost, _ := pl.access(table)
	nested := leftRows * innerCost
	hashed := innerCost + pl.out(table) + leftRows
	if nested <= hashed {
		return "nested loop", nested
	}
	return "hash join", hashed
}

// --- printing

func (pl *plan) tableLines(table, depth, mode int) []string {
	pad := strings.Repeat("  ", depth)
	name := pl.tables[table]
	conditions := pl.where[table]
	var scan string
	switch {
	case mode == 1:
		scan = "scan " + name
	case mode < 4:
		scan = fmt.Sprintf("scan %s (rows=%d)", name, pl.base(table))
	default:
		cost, used := pl.access(table)
		if used < 0 {
			scan = fmt.Sprintf("full scan %s (rows=%d cost=%d)", name, pl.base(table), cost)
		} else {
			c := conditions[used]
			matched := rounded(pl.base(table), pl.distinct(c.col))
			scan = fmt.Sprintf("index scan %s (rows=%d cost=%d)", c, matched, cost)
			rest := append([]condition{}, conditions[:used]...)
			conditions = append(rest, conditions[used+1:]...)
		}
	}
	if len(conditions) == 0 {
		return []string{pad + scan}
	}
	shown := make([]string, len(conditions))
	for i, c := range conditions {
		shown[i] = c.String()
	}
	filter := "filter " + strings.Join(shown, " AND ")
	if mode > 1 {
		filter += fmt.Sprintf(" (rows=%d)", pl.out(table))
	}
	return []string{pad + filter, pad + "  " + scan}
}

// lines prints the plan joining the tables in this order, left-deep, under its project line. Mode
// 1 prints no numbers, 2 the rows, 3 the rows and the cost, 4 the access paths and the join
// methods.
func (pl *plan) lines(order []int, mode int) []string {
	depth := len(order)
	var steps []string
	joined := 1 << order[0]
	cost := int64(0)
	if mode == 4 {
		cost, _ = pl.access(order[0])
	}
	for _, table := range order[1:] {
		leftColumn, rightColumn, _ := pl.edgeInto(joined, table)
		name := "join"
		if mode == 4 {
			method, step := pl.joinStep(pl.rows(joined), table)
			name = method
			cost += step
		}
		joined |= 1 << table
		if mode == 3 {
			cost += pl.rows(joined)
		}
		text := fmt.Sprintf("%s %s = %s", name, leftColumn, rightColumn)
		if mode == 2 {
			text += fmt.Sprintf(" (rows=%d)", pl.rows(joined))
		} else if mode > 2 {
			text += fmt.Sprintf(" (rows=%d cost=%d)", pl.rows(joined), cost)
		}
		steps = append(steps, text)
	}
	// Pre-order: the last join on top, each join's left input below it, then the first table; the
	// table joined at step k is the right input of that join, at depth n - k + 1.
	result := []string{pl.head()}
	for level := range steps {
		result = append(result, strings.Repeat("  ", level+1)+steps[len(steps)-1-level])
	}
	result = append(result, pl.tableLines(order[0], depth, mode)...)
	for k := 1; k < len(order); k++ {
		result = append(result, pl.tableLines(order[k], depth-k+1, mode)...)
	}
	return result
}

type best struct {
	cost  int64
	order []int
}

func (pl *plan) before(a, b best) bool {
	if a.cost != b.cost {
		return a.cost < b.cost
	}
	for i := range a.order {
		x, y := pl.tables[a.order[i]], pl.tables[b.order[i]]
		if x != y {
			return x < y
		}
	}
	return false
}

// bestOrder is dynamic programming over subsets: the cheapest left-deep order of every connected
// set, built from the cheapest order of the set without its last table. Ties go to the order whose
// list of table names comes first.
func (pl *plan) bestOrder(mode int) []int {
	count := len(pl.tables)
	found := make([]*best, 1<<count)
	for t := 0; t < count; t++ {
		cost := int64(0)
		if mode == 4 {
			cost, _ = pl.access(t)
		}
		found[1<<t] = &best{cost, []int{t}}
	}
	for size := 2; size <= count; size++ {
		for mask := 1; mask < 1<<count; mask++ {
			known := found[mask]
			if known == nil || len(known.order) != size-1 {
				continue
			}
			for t := 0; t < count; t++ {
				if _, _, linked := pl.edgeInto(mask, t); mask&(1<<t) != 0 || !linked {
					continue
				}
				grown := mask | 1<<t
				step := pl.rows(grown)
				if mode == 4 {
					_, step = pl.joinStep(pl.rows(mask), t)
				}
				order := append(append([]int{}, known.order...), t)
				candidate := best{known.cost + step, order}
				if found[grown] == nil || pl.before(candidate, *found[grown]) {
					found[grown] = &candidate
				}
			}
		}
	}
	return found[1<<count-1].order
}

// QueryPlanner parses a small SQL subset, checks it against the catalog, and plans it: written
// order with filters pushed to the scans, row estimates from table statistics, the cheapest
// left-deep join order by dynamic programming over subsets of tables, then access paths and join
// methods.
type QueryPlanner struct {
	columns map[string][]string
	stats   map[string]stat
	indexes map[string]map[string]bool
}

func NewQueryPlanner() *QueryPlanner {
	return &QueryPlanner{
		columns: map[string][]string{},
		stats:   map[string]stat{},
		indexes: map[string]map[string]bool{},
	}
}

func (p *QueryPlanner) plan(sql string, needStats bool, mode int) []string {
	pl, failure := p.newPlan(sql, needStats)
	if pl == nil {
		return []string{"error: " + failure}
	}
	var order []int
	if mode >= 3 {
		order = pl.bestOrder(mode)
	} else {
		for t := range pl.tables {
			order = append(order, t)
		}
	}
	return pl.lines(order, mode)
}

// Level 1
func (p *QueryPlanner) AddTable(table string, columns []string) string {
	if _, ok := p.columns[table]; ok {
		return "duplicate"
	}
	p.columns[table] = append([]string{}, columns...)
	return "ok"
}

func (p *QueryPlanner) LogicalPlan(sql string) []string {
	return p.plan(sql, false, 1)
}

// Level 2
func (p *QueryPlanner) Analyze(table string, rows int64, distinct []int64) string {
	columns, ok := p.columns[table]
	if !ok {
		return "unknown-table"
	}
	if len(distinct) != len(columns) || rows < 1 {
		return "bad-stats"
	}
	for _, count := range distinct {
		if count < 1 || count > rows {
			return "bad-stats"
		}
	}
	p.stats[table] = stat{rows, append([]int64{}, distinct...)}
	return "ok"
}

func (p *QueryPlanner) Estimate(sql string) []string {
	return p.plan(sql, true, 2)
}

// Level 3
func (p *QueryPlanner) Optimize(sql string) []string {
	return p.plan(sql, true, 3)
}

// Level 4
func (p *QueryPlanner) AddIndex(table string, column string) string {
	columns, ok := p.columns[table]
	if !ok {
		return "unknown-table"
	}
	if !contains(columns, column) {
		return "unknown-column"
	}
	if p.indexes[table] == nil {
		p.indexes[table] = map[string]bool{}
	}
	if p.indexes[table][column] {
		return "duplicate"
	}
	p.indexes[table][column] = true
	return "ok"
}

func (p *QueryPlanner) Explain(sql string) []string {
	return p.plan(sql, true, 4)
}
