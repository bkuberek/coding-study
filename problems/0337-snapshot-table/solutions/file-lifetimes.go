package snapshot_table

import (
	"math"
	"sort"
	"strconv"
)

const never = math.MaxInt

type dataFile struct {
	path      string
	partition string
	rows      string
	added     int
	removed   int
}

func (f *dataFile) liveAt(snapshot int) bool {
	return f.added <= snapshot && snapshot < f.removed
}

type snapshot struct {
	id        int
	parent    int
	timestamp int64
	operation string
	added     []*dataFile
	removed   []*dataFile
}

// SnapshotTable numbers snapshots 1, 2, 3 in commit order, and history is a single line, so a data
// file is live in one interval of snapshots: from the one that added it up to, not including, the
// one that removed it. Each file keeps that interval, each snapshot keeps the files it added and
// removed, and every question is a filter over the files or a walk over the snapshots.
type SnapshotTable struct {
	files         map[string]*dataFile
	snapshots     []*snapshot
	firstRetained int
}

func NewSnapshotTable() *SnapshotTable {
	return &SnapshotTable{files: map[string]*dataFile{}, firstRetained: 1}
}

// Level 1
func (t *SnapshotTable) Append(files [][]string, timestamp int64) int {
	if len(files) == 0 || !t.fresh(files) {
		return -1
	}
	return t.commitChange(files, nil, timestamp, "")
}

func (t *SnapshotTable) CurrentSnapshot() int {
	return len(t.snapshots)
}

func (t *SnapshotTable) Scan() []string {
	return t.ScanAt(t.CurrentSnapshot())
}

func (t *SnapshotTable) Manifest(snapshotID int) [][]string {
	entries := [][]string{}
	if !t.retained(snapshotID) {
		return entries
	}
	for _, file := range t.files {
		var status string
		switch {
		case file.liveAt(snapshotID) && file.added == snapshotID:
			status = "added"
		case file.liveAt(snapshotID):
			status = "existing"
		case file.removed == snapshotID:
			status = "deleted"
		default:
			continue
		}
		entries = append(entries, []string{file.path, file.partition, file.rows, status})
	}
	sort.Slice(entries, func(a, b int) bool { return entries[a][0] < entries[b][0] })
	return entries
}

// Level 2
func (t *SnapshotTable) DeleteFiles(paths []string, timestamp int64) int {
	if len(paths) == 0 || !t.removable(paths, t.CurrentSnapshot()) {
		return -1
	}
	return t.commitChange(nil, paths, timestamp, "")
}

func (t *SnapshotTable) Overwrite(partition string, files [][]string, timestamp int64) int {
	for _, file := range files {
		if file[1] != partition {
			return -1
		}
	}
	if !t.fresh(files) {
		return -1
	}
	current := t.CurrentSnapshot()
	old := []string{}
	for _, file := range t.files {
		if file.partition == partition && file.liveAt(current) {
			old = append(old, file.path)
		}
	}
	if len(old) == 0 && len(files) == 0 {
		return -1
	}
	return t.commitChange(files, old, timestamp, "")
}

func (t *SnapshotTable) ScanAt(snapshotID int) []string {
	paths := []string{}
	if !t.retained(snapshotID) {
		return paths
	}
	for path, file := range t.files {
		if file.liveAt(snapshotID) {
			paths = append(paths, path)
		}
	}
	sort.Strings(paths)
	return paths
}

func (t *SnapshotTable) SnapshotAsOf(timestamp int64) int {
	found := 0
	for _, s := range t.snapshots {
		if s.timestamp <= timestamp {
			found = s.id
		}
	}
	if found < t.firstRetained {
		return 0
	}
	return found
}

func (t *SnapshotTable) History() [][]string {
	entries := [][]string{}
	for _, s := range t.snapshots[t.firstRetained-1:] {
		entries = append(entries, []string{
			strconv.Itoa(s.id),
			strconv.Itoa(s.parent),
			strconv.FormatInt(s.timestamp, 10),
			s.operation,
			strconv.Itoa(len(s.added)),
			strconv.Itoa(len(s.removed)),
		})
	}
	return entries
}

// Level 3
func (t *SnapshotTable) Commit(base int, adds [][]string, removes []string, timestamp int64) []string {
	current := t.CurrentSnapshot()
	baseOK := (base == 0 && t.firstRetained == 1) || t.retained(base)
	if !baseOK || (len(adds) == 0 && len(removes) == 0) || !t.fresh(adds) || !t.removable(removes, base) {
		return []string{"invalid", ""}
	}
	removing := map[string]bool{}
	partitions := map[string]bool{}
	for _, path := range removes {
		removing[path] = true
		partitions[t.files[path].partition] = true
	}
	for _, s := range t.snapshots[base:current] {
		conflict := false
		for _, file := range s.removed {
			conflict = conflict || removing[file.path]
		}
		if s.operation != "replace" {
			for _, file := range s.added {
				conflict = conflict || partitions[file.partition]
			}
		}
		if conflict {
			return []string{"conflict", strconv.Itoa(s.id)}
		}
	}
	outcome := "rebased"
	if base == current {
		outcome = "committed"
	}
	return []string{outcome, strconv.Itoa(t.commitChange(adds, removes, timestamp, ""))}
}

// Level 4
func (t *SnapshotTable) ExpireSnapshots(olderThan int64, retainLast int) []string {
	oldFirst := t.firstRetained
	lastCandidate := t.CurrentSnapshot() - retainLast
	for t.firstRetained <= lastCandidate && t.snapshots[t.firstRetained-1].timestamp < olderThan {
		t.firstRetained++
	}
	freed := []string{}
	for path, file := range t.files {
		if oldFirst < file.removed && file.removed <= t.firstRetained {
			freed = append(freed, path)
		}
	}
	sort.Strings(freed)
	return freed
}

func (t *SnapshotTable) Compact(partition string, maxFileRows int, timestamp int64) int {
	current := t.CurrentSnapshot()
	small := []string{}
	var rows int64
	for path, file := range t.files {
		fileRows, _ := strconv.ParseInt(file.rows, 10, 64)
		if file.partition == partition && file.liveAt(current) && fileRows < int64(maxFileRows) {
			small = append(small, path)
			rows += fileRows
		}
	}
	if len(small) < 2 {
		return -1
	}
	sort.Strings(small)
	path := partition + "/compacted-" + strconv.Itoa(current+1)
	added := [][]string{{path, partition, strconv.FormatInt(rows, 10)}}
	return t.commitChange(added, small, timestamp, "replace")
}

// Helpers
func (t *SnapshotTable) retained(snapshotID int) bool {
	return t.firstRetained <= snapshotID && snapshotID <= t.CurrentSnapshot()
}

func (t *SnapshotTable) fresh(adds [][]string) bool {
	seen := map[string]bool{}
	for _, file := range adds {
		if _, used := t.files[file[0]]; used || seen[file[0]] {
			return false
		}
		seen[file[0]] = true
	}
	return true
}

func (t *SnapshotTable) removable(paths []string, snapshotID int) bool {
	seen := map[string]bool{}
	for _, path := range paths {
		file, known := t.files[path]
		if seen[path] || !known || !file.liveAt(snapshotID) {
			return false
		}
		seen[path] = true
	}
	return true
}

func (t *SnapshotTable) commitChange(adds [][]string, removes []string, timestamp int64, operation string) int {
	parent := t.CurrentSnapshot()
	id := parent + 1
	if operation == "" {
		switch {
		case len(adds) > 0 && len(removes) > 0:
			operation = "overwrite"
		case len(adds) > 0:
			operation = "append"
		default:
			operation = "delete"
		}
	}
	s := &snapshot{id: id, parent: parent, timestamp: timestamp, operation: operation}
	for _, path := range removes {
		file := t.files[path]
		file.removed = id
		s.removed = append(s.removed, file)
	}
	for _, add := range adds {
		file := &dataFile{path: add[0], partition: add[1], rows: add[2], added: id, removed: never}
		t.files[file.path] = file
		s.added = append(s.added, file)
	}
	t.snapshots = append(t.snapshots, s)
	return id
}
