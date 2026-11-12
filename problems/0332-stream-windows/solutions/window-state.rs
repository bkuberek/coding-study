use std::collections::HashMap;

/// A window is (start, key), so sorting windows orders them by start and then key.
type Window = (i32, i32);
type Groups = HashMap<Window, (i32, i32)>;

fn bump(groups: &mut Groups, window: Window, value: i32) {
    let totals = groups.entry(window).or_insert((0, 0));
    totals.0 += 1;
    totals.1 += value;
}

fn row(window: Window, size: i32, count: i32, sum: i32) -> Vec<i32> {
    vec![window.1, window.0, window.0 + size, count, sum]
}

fn rows(groups: &Groups, size: i32) -> Vec<Vec<i32>> {
    let mut windows: Vec<&Window> = groups.keys().collect();
    windows.sort();
    windows
        .into_iter()
        .map(|w| row(*w, size, groups[w].0, groups[w].1))
        .collect()
}

/// Every event is kept in a log, so the batch views of levels 1 and 2 can group the whole stream
/// in any way they are asked.
///
/// The stream of levels 3 and 4 keeps a map from (start, key) to a running count and sum for the
/// windows not yet emitted, and a second map for the windows already emitted that can still be
/// corrected. After each event the watermark moves, the open windows it has passed are emitted
/// in order, and the corrected windows it has left behind are forgotten.
pub struct StreamWindows {
    events: Vec<(i32, i32, i32)>,
    size: i32,
    lateness: i32,
    grace: i32,
    mark: i32,
    open: Groups,
    closed: Groups,
    out: Vec<Vec<i32>>,
    side: Vec<Vec<i32>>,
    emitted: i32,
    updated: i32,
}

impl StreamWindows {
    pub fn new() -> Self {
        StreamWindows {
            events: Vec::new(),
            size: 0,
            lateness: 0,
            grace: 0,
            mark: 0,
            open: HashMap::new(),
            closed: HashMap::new(),
            out: Vec::new(),
            side: Vec::new(),
            emitted: 0,
            updated: 0,
        }
    }

    // Level 1
    pub fn add(&mut self, key: i32, time: i32, value: i32) {
        self.events.push((key, time, value));
        if self.size > 0 {
            self.stream(key, time, value);
        }
    }

    pub fn tumbling(&mut self, size: i32) -> Vec<Vec<i32>> {
        let mut groups = Groups::new();
        for &(key, time, value) in &self.events {
            bump(&mut groups, (time - time % size, key), value);
        }
        rows(&groups, size)
    }

    // Level 2
    pub fn hopping(&mut self, size: i32, slide: i32) -> Vec<Vec<i32>> {
        let mut groups = Groups::new();
        for &(key, time, value) in &self.events {
            let mut start = time - time % slide;
            while start > time - size {
                bump(&mut groups, (start, key), value);
                start -= slide;
            }
        }
        rows(&groups, size)
    }

    pub fn sessions(&mut self, gap: i32) -> Vec<Vec<i32>> {
        let mut by_key: HashMap<i32, Vec<(i32, i32)>> = HashMap::new();
        for &(key, time, value) in &self.events {
            by_key.entry(key).or_default().push((time, value));
        }
        let mut sessions: Vec<Vec<i32>> = Vec::new();
        for (key, mut list) in by_key {
            list.sort();
            let mut current: Option<usize> = None;
            for (time, value) in list {
                match current {
                    Some(i) if time < sessions[i][2] => {
                        let session = &mut sessions[i];
                        session[2] = time + gap;
                        session[3] += 1;
                        session[4] += value;
                    }
                    _ => {
                        sessions.push(vec![key, time, time + gap, 1, value]);
                        current = Some(sessions.len() - 1);
                    }
                }
            }
        }
        sessions.sort_by_key(|s| (s[1], s[0]));
        sessions
    }

    // Level 3
    pub fn configure(&mut self, size: i32, lateness: i32) {
        self.size = size;
        self.lateness = lateness;
    }

    pub fn watermark(&mut self) -> i32 {
        self.mark
    }

    pub fn pending(&mut self) -> Vec<Vec<i32>> {
        rows(&self.open, self.size)
    }

    pub fn poll(&mut self) -> Vec<Vec<i32>> {
        std::mem::take(&mut self.out)
    }

    // Level 4
    pub fn allow_updates(&mut self, grace: i32) {
        self.grace = grace;
    }

    pub fn dropped(&mut self) -> Vec<Vec<i32>> {
        self.side.clone()
    }

    pub fn stats(&mut self) -> Vec<i32> {
        vec![self.emitted, self.updated, self.side.len() as i32]
    }

    // The stream
    fn stream(&mut self, key: i32, time: i32, value: i32) {
        let start = time - time % self.size;
        let end = start + self.size;
        if end > self.mark {
            bump(&mut self.open, (start, key), value);
        } else if self.mark < end + self.grace {
            self.correct((start, key), value);
        } else {
            self.side.push(vec![key, time, value]);
        }
        self.advance(time - self.lateness);
    }

    fn correct(&mut self, window: Window, value: i32) {
        let size = self.size;
        match self.closed.get_mut(&window) {
            None => {
                self.closed.insert(window, (1, value));
                self.emitted += 1;
                self.out.push(row(window, size, 1, value));
            }
            Some(old) => {
                self.out.push(row(window, size, -old.0, -old.1));
                old.0 += 1;
                old.1 += value;
                self.updated += 1;
                self.out.push(row(window, size, old.0, old.1));
            }
        }
    }

    fn advance(&mut self, candidate: i32) {
        if candidate <= self.mark {
            return;
        }
        self.mark = candidate;
        let (size, mark, grace) = (self.size, self.mark, self.grace);
        let mut due: Vec<Window> = self
            .open
            .keys()
            .filter(|w| w.0 + size <= mark)
            .copied()
            .collect();
        due.sort();
        for window in due {
            if let Some(totals) = self.open.remove(&window) {
                self.out.push(row(window, size, totals.0, totals.1));
                self.closed.insert(window, totals);
                self.emitted += 1;
            }
        }
        self.closed.retain(|w, _| w.0 + size + grace > mark);
    }
}
