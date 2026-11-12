use std::collections::{BTreeSet, HashMap, HashSet};

/// One address space: a page table from page to frame, an optional TLB, and, once demand paging
/// is on, a frame table with the state each replacement policy needs. The standard library has
/// no ordered map with a cheap "move to the end", so the TLB and the policies keep a stamp from a
/// counter that grows with every translation: the stamp of a TLB entry's last use, and the stamps
/// of each page's load and last use. Evicting scans for the smallest stamp, which is cheap for at
/// most 64 entries or frames. Every translation is one reference in a history, which the working
/// set reads.
pub struct VirtualMemory {
    size: i64,
    shift: u32,
    table: HashMap<i64, i64>,
    fault_count: i32,
    tlb: Option<HashMap<i64, (i64, u64)>>,
    tlb_entries: usize,
    hits: i32,
    misses: i32,
    frames: usize,
    policy: String,
    owner: Vec<i64>,
    loaded_at: HashMap<i64, u64>,
    used_at: HashMap<i64, u64>,
    use_bit: Vec<bool>,
    hand: usize,
    now: u64,
    history: Vec<i64>,
}

impl VirtualMemory {
    pub fn new(page_size: i32) -> Self {
        VirtualMemory {
            size: page_size as i64,
            shift: page_size.trailing_zeros(),
            table: HashMap::new(),
            fault_count: 0,
            tlb: None,
            tlb_entries: 0,
            hits: 0,
            misses: 0,
            frames: 0,
            policy: String::new(),
            owner: Vec::new(),
            loaded_at: HashMap::new(),
            used_at: HashMap::new(),
            use_bit: Vec::new(),
            hand: 0,
            now: 0,
            history: Vec::new(),
        }
    }

    // Level 1
    pub fn split(&mut self, address: i64) -> Vec<i64> {
        vec![address >> self.shift, address & (self.size - 1)]
    }

    pub fn map_page(&mut self, page: i64, frame: i64) -> bool {
        let new = self.table.insert(page, frame).is_none();
        self.invalidate(page);
        new
    }

    pub fn unmap_page(&mut self, page: i64) -> bool {
        if self.table.remove(&page).is_none() {
            return false;
        }
        self.invalidate(page);
        true
    }

    pub fn translate(&mut self, address: i64) -> i64 {
        let page = address >> self.shift;
        self.history.push(page);
        match self.frame_of(page) {
            Some(frame) => frame * self.size + (address & (self.size - 1)),
            None => -1,
        }
    }

    pub fn faults(&mut self) -> i32 {
        self.fault_count
    }

    // Level 2
    pub fn enable_tlb(&mut self, entries: i32) {
        self.tlb = Some(HashMap::new());
        self.tlb_entries = entries as usize;
        self.hits = 0;
        self.misses = 0;
    }

    pub fn flush_tlb(&mut self) {
        if let Some(tlb) = &mut self.tlb {
            tlb.clear();
        }
    }

    pub fn tlb_hits(&mut self) -> i32 {
        self.hits
    }

    pub fn tlb_misses(&mut self) -> i32 {
        self.misses
    }

    // Level 3
    pub fn use_frames(&mut self, count: i32, policy: String) {
        self.frames = count as usize;
        self.policy = policy;
        self.table.clear();
        self.flush_tlb();
        self.fault_count = 0;
        self.hits = 0;
        self.misses = 0;
        self.owner = vec![0; self.frames];
        self.use_bit = vec![false; self.frames];
        self.loaded_at.clear();
        self.used_at.clear();
        self.hand = 0;
        self.history.clear();
    }

    pub fn resident(&mut self) -> Vec<i64> {
        let mut pages: Vec<i64> = self.table.keys().copied().collect();
        pages.sort_unstable();
        pages
    }

    // Level 4
    pub fn walk(&mut self, address: i64, entry_bytes: i32) -> Vec<i64> {
        let per_table = self.size / entry_bytes as i64;
        let page = address >> self.shift;
        vec![page / per_table, page % per_table, address & (self.size - 1)]
    }

    pub fn table_bytes(&mut self, address_bits: i32, entry_bytes: i32) -> Vec<i64> {
        let pages = 1_i64 << (address_bits as u32 - self.shift);
        let entry = entry_bytes as i64;
        let per_table = self.size / entry;
        let directory = pages / per_table * entry;
        let tables: HashSet<i64> = self.table.keys().map(|page| page / per_table).collect();
        vec![pages * entry, directory + tables.len() as i64 * self.size]
    }

    pub fn working_set(&mut self, window: i32) -> Vec<i64> {
        let from = self.history.len().saturating_sub(window as usize);
        let pages: BTreeSet<i64> = self.history[from..].iter().copied().collect();
        pages.into_iter().collect()
    }

    pub fn thrashing(&mut self, window: i32) -> bool {
        self.frames > 0 && self.working_set(window).len() > self.frames
    }

    // Translation
    fn frame_of(&mut self, page: i64) -> Option<i64> {
        self.now += 1;
        let now = self.now;
        if let Some(tlb) = &mut self.tlb {
            if let Some(entry) = tlb.get_mut(&page) {
                entry.1 = now;
                let frame = entry.0;
                self.hits += 1;
                self.touch(page);
                return Some(frame);
            }
            self.misses += 1;
        }
        let frame = match self.table.get(&page) {
            Some(&frame) => frame,
            None => {
                self.fault_count += 1;
                if self.frames == 0 {
                    return None;
                }
                self.load(page)
            }
        };
        self.touch(page);
        let capacity = self.tlb_entries;
        if let Some(tlb) = &mut self.tlb {
            if tlb.len() == capacity {
                let oldest = tlb.iter().min_by_key(|(_, entry)| entry.1).map(|(&p, _)| p);
                if let Some(oldest) = oldest {
                    tlb.remove(&oldest);
                }
            }
            tlb.insert(page, (frame, now));
        }
        Some(frame)
    }

    fn invalidate(&mut self, page: i64) {
        if let Some(tlb) = &mut self.tlb {
            tlb.remove(&page);
        }
    }

    fn touch(&mut self, page: i64) {
        if self.frames == 0 {
            return;
        }
        self.used_at.insert(page, self.now);
        let frame = self.table[&page] as usize;
        self.use_bit[frame] = true;
    }

    fn load(&mut self, page: i64) -> i64 {
        let frame = if self.table.len() < self.frames {
            self.table.len()
        } else {
            let frame = self.victim_frame();
            let victim = self.owner[frame];
            self.table.remove(&victim);
            self.loaded_at.remove(&victim);
            self.used_at.remove(&victim);
            self.invalidate(victim);
            frame
        };
        self.table.insert(page, frame as i64);
        self.owner[frame] = page;
        self.loaded_at.insert(page, self.now);
        frame as i64
    }

    fn victim_frame(&mut self) -> usize {
        match self.policy.as_str() {
            "fifo" => self.oldest(&self.loaded_at),
            "lru" => self.oldest(&self.used_at),
            _ => {
                while self.use_bit[self.hand] {
                    self.use_bit[self.hand] = false;
                    self.hand = (self.hand + 1) % self.frames;
                }
                let frame = self.hand;
                self.hand = (self.hand + 1) % self.frames;
                frame
            }
        }
    }

    /// The frame whose page has the smallest stamp.
    fn oldest(&self, stamp: &HashMap<i64, u64>) -> usize {
        (0..self.frames).min_by_key(|&f| stamp[&self.owner[f]]).unwrap()
    }
}
