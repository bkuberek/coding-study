package cdc_apply

import (
	"slices"
	"sort"
)

const (
	ok      = "ok"
	skipped = "skipped"
	never   = -1
)

type stagedChange struct {
	op  string
	row []string
}

// pending is a transaction's view of one key: its new row, or a mark that it was deleted.
type pending struct {
	row     []string
	deleted bool
}

// ReplicaTable holds the table in a map from key to row. A second map holds each key's version,
// the position at which its last change became visible, and keeps it when the row is deleted:
// that tombstone is what stops an old insert from bringing a deleted row back.
//
// A change is skipped when its position is not after the key's version, or not after the
// snapshot the table started from. A transaction's changes wait in a buffer until its commit,
// then run into an overlay, a small map of the rows they change, which is written into the table
// only when every change worked.
type ReplicaTable struct {
	names         []string
	table         map[string][]string
	versions      map[string]int
	floor         int
	schemaVersion int
	staged        map[string][]stagedChange
}

func NewReplicaTable(columns []string) *ReplicaTable {
	return &ReplicaTable{
		names:    append([]string{}, columns...),
		table:    map[string][]string{},
		versions: map[string]int{},
		staged:   map[string][]stagedChange{},
	}
}

// Level 1
func (r *ReplicaTable) Apply(op string, row []string) string {
	_, present := r.table[row[0]]
	code := r.check(present, op, row)
	if code == ok {
		if op == "delete" {
			delete(r.table, row[0])
		} else {
			r.table[row[0]] = append([]string{}, row...)
		}
	}
	return code
}

func (r *ReplicaTable) Rows() [][]string {
	keys := make([]string, 0, len(r.table))
	for key := range r.table {
		keys = append(keys, key)
	}
	sort.Strings(keys)
	rows := [][]string{}
	for _, key := range keys {
		rows = append(rows, append([]string{}, r.table[key]...))
	}
	return rows
}

// Level 2
func (r *ReplicaTable) ApplyAt(lsn int, op string, row []string) string {
	key := row[0]
	if lsn <= r.floor || lsn <= r.Version(key) {
		return skipped
	}
	code := r.Apply(op, row)
	if code == ok {
		r.versions[key] = lsn
	}
	return code
}

func (r *ReplicaTable) Version(key string) int {
	if v, found := r.versions[key]; found {
		return v
	}
	return never
}

// Level 3
func (r *ReplicaTable) LoadSnapshot(lsn int, snapshot [][]string) {
	r.table = map[string][]string{}
	r.versions = map[string]int{}
	for _, row := range snapshot {
		r.table[row[0]] = append([]string{}, row...)
		r.versions[row[0]] = lsn
	}
	r.floor = lsn
}

func (r *ReplicaTable) Stage(tx string, op string, row []string) {
	r.staged[tx] = append(r.staged[tx], stagedChange{op, append([]string{}, row...)})
}

func (r *ReplicaTable) Commit(lsn int, tx string) string {
	changes := r.staged[tx]
	delete(r.staged, tx)
	if lsn <= r.floor {
		return skipped
	}
	overlay := map[string]pending{}
	var order []string
	for _, c := range changes {
		key := c.row[0]
		if lsn <= r.Version(key) {
			continue
		}
		var present bool
		if p, found := overlay[key]; found {
			present = !p.deleted
		} else {
			_, present = r.table[key]
			order = append(order, key)
		}
		code := r.check(present, c.op, c.row)
		if code != ok {
			return code
		}
		overlay[key] = pending{row: c.row, deleted: c.op == "delete"}
	}
	if len(order) == 0 {
		return skipped
	}
	for _, key := range order {
		if p := overlay[key]; p.deleted {
			delete(r.table, key)
		} else {
			r.table[key] = p.row
		}
		r.versions[key] = lsn
	}
	return ok
}

func (r *ReplicaTable) Rollback(tx string) {
	delete(r.staged, tx)
}

// Level 4
func (r *ReplicaTable) AlterAt(lsn int, change []string) string {
	if lsn <= r.floor || lsn <= r.schemaVersion {
		return skipped
	}
	code := r.alter(change)
	if code == ok {
		r.schemaVersion = lsn
	}
	return code
}

func (r *ReplicaTable) Columns() []string {
	return append([]string{}, r.names...)
}

func (r *ReplicaTable) Compare(sourceColumns []string, sourceRows [][]string) [][]string {
	report := [][]string{}
	all := sortedUnion(r.names, sourceColumns)
	for _, name := range all {
		inMine, inTheirs := slices.Contains(r.names, name), slices.Contains(sourceColumns, name)
		if !inMine {
			report = append(report, []string{"missing-column", name})
		} else if !inTheirs {
			report = append(report, []string{"extra-column", name})
		}
	}
	var common []string
	for _, name := range all {
		if slices.Contains(r.names, name) && slices.Contains(sourceColumns, name) {
			common = append(common, name)
		}
	}
	source := map[string][]string{}
	var sourceKeys []string
	for _, row := range sourceRows {
		source[row[0]] = row
		sourceKeys = append(sourceKeys, row[0])
	}
	var tableKeys []string
	for key := range r.table {
		tableKeys = append(tableKeys, key)
	}
	for _, key := range sortedUnion(tableKeys, sourceKeys) {
		here, inMine := r.table[key]
		there, inTheirs := source[key]
		switch {
		case !inMine:
			report = append(report, []string{"missing-row", key})
		case !inTheirs:
			report = append(report, []string{"extra-row", key})
		default:
			for _, name := range common {
				a := here[slices.Index(r.names, name)]
				b := there[slices.Index(sourceColumns, name)]
				if a != b {
					report = append(report, []string{"value-differs", key, name, a, b})
				}
			}
		}
	}
	return report
}

// Changes
func (r *ReplicaTable) check(present bool, op string, row []string) string {
	if op != "delete" && len(row) != len(r.names) {
		return "column-count"
	}
	if op == "insert" {
		if present {
			return "duplicate-key"
		}
		return ok
	}
	if present {
		return ok
	}
	return "unknown-key"
}

func (r *ReplicaTable) alter(change []string) string {
	kind, name := change[0], change[1]
	if kind == "add" {
		if slices.Contains(r.names, name) {
			return "duplicate-column"
		}
		r.names = append(r.names, name)
		for key, row := range r.table {
			r.table[key] = append(row, change[2])
		}
		return ok
	}
	index := slices.Index(r.names, name)
	if index < 0 {
		return "unknown-column"
	}
	if kind == "drop" {
		if index == 0 {
			return "key-column"
		}
		r.names = slices.Delete(r.names, index, index+1)
		for key, row := range r.table {
			r.table[key] = slices.Delete(row, index, index+1)
		}
		return ok
	}
	if slices.Contains(r.names, change[2]) {
		return "duplicate-column"
	}
	r.names[index] = change[2]
	return ok
}

func sortedUnion(a, b []string) []string {
	seen := map[string]bool{}
	var out []string
	for _, s := range append(append([]string{}, a...), b...) {
		if !seen[s] {
			seen[s] = true
			out = append(out, s)
		}
	}
	sort.Strings(out)
	return out
}
