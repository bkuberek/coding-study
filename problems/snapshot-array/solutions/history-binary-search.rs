pub struct SnapshotArray {
    /// `history[i]` holds `(snap id, value)` pairs of position `i` with strictly increasing ids.
    history: Vec<Vec<(i32, i32)>>,
    snaps: i32,
}

impl SnapshotArray {
    pub fn new(length: i32) -> Self {
        SnapshotArray {
            history: vec![Vec::new(); length as usize],
            snaps: 0,
        }
    }

    pub fn set(&mut self, index: i32, value: i32) {
        let entries = &mut self.history[index as usize];
        match entries.last_mut() {
            Some(last) if last.0 == self.snaps => last.1 = value,
            _ => entries.push((self.snaps, value)),
        }
    }

    pub fn snap(&mut self) -> i32 {
        self.snaps += 1;
        self.snaps - 1
    }

    pub fn get(&mut self, index: i32, snap_id: i32) -> i32 {
        let entries = &self.history[index as usize];
        let position = entries.partition_point(|&(id, _)| id <= snap_id);
        position.checked_sub(1).map_or(0, |last| entries[last].1)
    }
}
