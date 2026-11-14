package snapshot_array

// write is one call to Set: the position, the value and the snapshot id current at the time.
type write struct {
	index, value, snapID int
}

type SnapshotArray struct {
	log   []write
	snaps int
}

func NewSnapshotArray(length int) *SnapshotArray {
	return &SnapshotArray{}
}

func (a *SnapshotArray) Set(index int, value int) {
	a.log = append(a.log, write{index, value, a.snaps})
}

func (a *SnapshotArray) Snap() int {
	a.snaps++
	return a.snaps - 1
}

func (a *SnapshotArray) Get(index int, snapId int) int {
	// The newest write to index that happened before snapshot snapId was taken.
	for i := len(a.log) - 1; i >= 0; i-- {
		if w := a.log[i]; w.index == index && w.snapID <= snapId {
			return w.value
		}
	}
	return 0
}
