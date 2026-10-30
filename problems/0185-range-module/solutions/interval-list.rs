pub struct RangeModule {
    // Disjoint, non-touching half-open intervals (start, end), sorted by start.
    intervals: Vec<(i32, i32)>,
}

impl RangeModule {
    pub fn new() -> Self {
        RangeModule {
            intervals: Vec::new(),
        }
    }

    pub fn add_range(&mut self, left: i32, right: i32) {
        let (mut left, mut right) = (left, right);
        let mut merged = Vec::with_capacity(self.intervals.len() + 1);
        let mut placed = false;
        for &(start, end) in &self.intervals {
            if end < left {
                merged.push((start, end));
            } else if right < start {
                if !placed {
                    merged.push((left, right));
                    placed = true;
                }
                merged.push((start, end));
            } else {
                // Overlapping or touching: absorb it into the new interval.
                left = left.min(start);
                right = right.max(end);
            }
        }
        if !placed {
            merged.push((left, right));
        }
        self.intervals = merged;
    }

    pub fn query_range(&mut self, left: i32, right: i32) -> bool {
        // Stored intervals never touch, so a covered range lies inside a single one.
        self.intervals
            .iter()
            .any(|&(start, end)| start <= left && right <= end)
    }

    pub fn remove_range(&mut self, left: i32, right: i32) {
        let mut kept = Vec::with_capacity(self.intervals.len() + 1);
        for &(start, end) in &self.intervals {
            if end <= left || right <= start {
                kept.push((start, end));
                continue;
            }
            if start < left {
                kept.push((start, left));
            }
            if right < end {
                kept.push((right, end));
            }
        }
        self.intervals = kept;
    }
}
