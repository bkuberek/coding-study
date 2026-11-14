package snapshot_array

import "sort"

// change is the value a position took in the snapshot period snapID.
type change struct {
	snapID, value int
}

type SnapshotArray struct {
	// history[i] holds the changes of position i with strictly increasing snap ids.
	history [][]change
	snaps   int
}

func NewSnapshotArray(length int) *SnapshotArray {
	return &SnapshotArray{history: make([][]change, length)}
}

func (a *SnapshotArray) Set(index int, value int) {
	entries := a.history[index]
	if last := len(entries) - 1; last >= 0 && entries[last].snapID == a.snaps {
		entries[last].value = value
		return
	}
	a.history[index] = append(entries, change{a.snaps, value})
}

func (a *SnapshotArray) Snap() int {
	a.snaps++
	return a.snaps - 1
}

func (a *SnapshotArray) Get(index int, snapId int) int {
	entries := a.history[index]
	position := sort.Search(len(entries), func(i int) bool { return entries[i].snapID > snapId })
	if position == 0 {
		return 0
	}
	return entries[position-1].value
}
