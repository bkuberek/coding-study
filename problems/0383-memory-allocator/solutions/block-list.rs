const HEADER: i32 = 8;
const ALIGN: i32 = 8;
const MIN_BLOCK: i32 = 16;
const POLICIES: [&str; 3] = ["first-fit", "next-fit", "best-fit"];

#[derive(Clone, Copy)]
struct Block {
    start: i32,
    size: i32,
    used: bool,
    requested: i32,
}

impl Block {
    fn vacant(start: i32, size: i32) -> Self {
        Block { start, size, used: false, requested: 0 }
    }
}

/// The heap is a vector of blocks in address order, each with its start, its size (header
/// included) and whether it is in use. Allocating splits a free block; freeing marks it free and,
/// with coalescing or in the buddy system, merges it with its free neighbors. Next fit keeps a
/// rover: the address where its next search starts.
pub struct MemoryAllocator {
    heap_size: i32,
    blocks: Vec<Block>,
    coalescing: bool,
    policy: String,
    started: bool,
    rover: i32,
}

impl MemoryAllocator {
    pub fn new(heap_size: i32) -> Self {
        MemoryAllocator {
            heap_size,
            blocks: vec![Block::vacant(0, heap_size)],
            coalescing: false,
            policy: "first-fit".to_string(),
            started: false,
            rover: 0,
        }
    }

    // --- helpers
    fn position(&self, start: i32) -> Option<usize> {
        self.blocks.iter().position(|block| block.start == start)
    }

    fn block_size(&self, size: i32) -> i32 {
        if self.policy == "buddy" {
            let mut block = MIN_BLOCK;
            while block < size + HEADER {
                block *= 2;
            }
            return block;
        }
        HEADER + (size + ALIGN - 1) / ALIGN * ALIGN
    }

    /// The position of the free block the policy picks, if any.
    fn choose(&self, need: i32) -> Option<usize> {
        let fits: Vec<usize> = (0..self.blocks.len())
            .filter(|&i| !self.blocks[i].used && self.blocks[i].size >= need)
            .collect();
        let first = *fits.first()?;
        match self.policy.as_str() {
            "next-fit" => {
                let here = self.position(self.rover).unwrap_or(0);
                Some(fits.iter().copied().find(|&i| i >= here).unwrap_or(first))
            }
            // min_by_key keeps the first of equal sizes, which is the lowest address.
            "best-fit" | "buddy" => fits.iter().copied().min_by_key(|&i| self.blocks[i].size),
            _ => Some(first),
        }
    }

    fn split(&mut self, position: usize, keep: i32) {
        let block = self.blocks[position];
        self.blocks.insert(position + 1, Block::vacant(block.start + keep, block.size - keep));
        self.blocks[position].size = keep;
    }

    fn merge_with_next(&mut self, position: usize) {
        let following = self.blocks.remove(position + 1);
        self.blocks[position].size += following.size;
        if self.rover == following.start {
            self.rover = self.blocks[position].start;
        }
    }

    fn free_buddies(&mut self, mut position: usize) {
        while self.blocks[position].size < self.heap_size {
            let block = self.blocks[position];
            let other = match self.position(block.start ^ block.size) {
                Some(other) if !self.blocks[other].used && self.blocks[other].size == block.size => {
                    other
                }
                _ => return,
            };
            position = position.min(other);
            self.merge_with_next(position);
        }
    }

    // Level 1
    pub fn allocate(&mut self, size: i32) -> i32 {
        self.started = true;
        let need = self.block_size(size);
        let Some(position) = self.choose(need) else {
            return -1;
        };
        if self.policy == "buddy" {
            while self.blocks[position].size > need {
                let half = self.blocks[position].size / 2;
                self.split(position, half);
            }
        } else if self.blocks[position].size - need >= MIN_BLOCK {
            self.split(position, need);
        }
        let block = &mut self.blocks[position];
        block.used = true;
        block.requested = size;
        let (start, end) = (block.start, block.start + block.size);
        self.rover = end % self.heap_size;
        start + HEADER
    }

    pub fn free(&mut self, address: i32) -> String {
        let position = match self.position(address - HEADER) {
            Some(position) if self.blocks[position].used => position,
            _ => return "invalid".to_string(),
        };
        self.blocks[position].used = false;
        if self.policy == "buddy" {
            self.free_buddies(position);
        } else if self.coalescing {
            if position + 1 < self.blocks.len() && !self.blocks[position + 1].used {
                self.merge_with_next(position);
            }
            if position > 0 && !self.blocks[position - 1].used {
                self.merge_with_next(position - 1);
            }
        }
        "ok".to_string()
    }

    pub fn heap_map(&mut self) -> Vec<String> {
        self.blocks
            .iter()
            .map(|b| format!("{} {} {}", b.start, b.size, if b.used { "used" } else { "free" }))
            .collect()
    }

    // Level 2
    pub fn set_coalescing(&mut self, enabled: bool) -> String {
        if self.started {
            return "too-late".to_string();
        }
        self.coalescing = enabled;
        "ok".to_string()
    }

    pub fn free_report(&mut self) -> Vec<i32> {
        let sizes: Vec<i32> = self.blocks.iter().filter(|b| !b.used).map(|b| b.size).collect();
        let total: i32 = sizes.iter().sum();
        let largest = sizes.iter().copied().max().unwrap_or(0);
        let fragmentation = if total == 0 { 0 } else { 100 * (total - largest) / total };
        vec![sizes.len() as i32, total, largest, fragmentation]
    }

    // Level 3
    pub fn set_policy(&mut self, policy: String) -> String {
        if !POLICIES.contains(&policy.as_str()) && policy != "buddy" {
            return "unknown-policy".to_string();
        }
        if self.started {
            return "too-late".to_string();
        }
        if policy == "buddy" && (self.heap_size & (self.heap_size - 1)) != 0 {
            return "bad-size".to_string();
        }
        self.policy = policy;
        "ok".to_string()
    }

    pub fn compare(&mut self, trace: Vec<i32>) -> Vec<Vec<i32>> {
        POLICIES
            .iter()
            .map(|&name| {
                let mut heap = MemoryAllocator::new(self.heap_size);
                heap.set_coalescing(self.coalescing);
                heap.set_policy(name.to_string());
                let mut addresses: Vec<i32> = Vec::new();
                let mut failed = 0;
                for &step in &trace {
                    if step > 0 {
                        let address = heap.allocate(step);
                        addresses.push(address);
                        if address < 0 {
                            failed += 1;
                        }
                    } else {
                        let address = addresses[(-step - 1) as usize];
                        if address >= 0 {
                            heap.free(address);
                        }
                    }
                }
                let mut row = vec![failed];
                row.extend(heap.free_report());
                row
            })
            .collect()
    }

    // Level 4
    pub fn wasted(&mut self) -> i32 {
        self.blocks.iter().filter(|b| b.used).map(|b| b.size - HEADER - b.requested).sum()
    }
}
