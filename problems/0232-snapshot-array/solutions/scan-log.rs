/// One call to `set`: the position, the value and the snapshot id current at the time.
struct Write {
    index: i32,
    value: i32,
    snap_id: i32,
}

pub struct SnapshotArray {
    log: Vec<Write>,
    snaps: i32,
}

impl SnapshotArray {
    pub fn new(length: i32) -> Self {
        SnapshotArray {
            log: Vec::new(),
            snaps: 0,
        }
    }

    pub fn set(&mut self, index: i32, value: i32) {
        self.log.push(Write {
            index,
            value,
            snap_id: self.snaps,
        });
    }

    pub fn snap(&mut self) -> i32 {
        self.snaps += 1;
        self.snaps - 1
    }

    pub fn get(&mut self, index: i32, snap_id: i32) -> i32 {
        // The newest write to `index` that happened before snapshot `snap_id` was taken.
        self.log
            .iter()
            .rev()
            .find(|write| write.index == index && write.snap_id <= snap_id)
            .map_or(0, |write| write.value)
    }
}
