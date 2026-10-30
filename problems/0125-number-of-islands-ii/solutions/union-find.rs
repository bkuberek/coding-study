const STEPS: [(isize, isize); 4] = [(1, 0), (-1, 0), (0, 1), (0, -1)];

struct DisjointSet {
    parent: Vec<usize>,
    size: Vec<usize>, // size[r]: number of cells in the tree rooted at r
}

impl DisjointSet {
    fn new(count: usize) -> Self {
        DisjointSet {
            parent: (0..count).collect(),
            size: vec![1; count],
        }
    }

    fn find(&mut self, mut x: usize) -> usize {
        let mut root = x;
        while self.parent[root] != root {
            root = self.parent[root];
        }
        while self.parent[x] != root {
            // path compression: point the whole path at the root
            let next = self.parent[x];
            self.parent[x] = root;
            x = next;
        }
        root
    }

    /// Merges the groups of `a` and `b` and reports whether they were separate.
    fn union(&mut self, a: usize, b: usize) -> bool {
        let (mut root_a, mut root_b) = (self.find(a), self.find(b));
        if root_a == root_b {
            return false;
        }
        if self.size[root_a] < self.size[root_b] {
            std::mem::swap(&mut root_a, &mut root_b);
        }
        self.parent[root_b] = root_a; // union by size: the smaller tree goes under the larger
        self.size[root_a] += self.size[root_b];
        true
    }
}

pub fn num_islands2(m: i32, n: i32, positions: Vec<Vec<i32>>) -> Vec<i32> {
    let (m, n) = (m as usize, n as usize);
    let mut set = DisjointSet::new(m * n); // cell r * n + c
    let mut land = vec![false; m * n];

    let mut islands = 0;
    let mut counts = Vec::with_capacity(positions.len());
    for position in &positions {
        let (r, c) = (position[0] as usize, position[1] as usize);
        let cell = r * n + c;
        if !land[cell] {
            land[cell] = true;
            islands += 1; // a new island, until it merges with its neighbors
            for (step_row, step_col) in STEPS {
                let (Some(nr), Some(nc)) = (
                    r.checked_add_signed(step_row),
                    c.checked_add_signed(step_col),
                ) else {
                    continue;
                };
                if nr < m && nc < n && land[nr * n + nc] && set.union(nr * n + nc, cell) {
                    islands -= 1;
                }
            }
        }
        counts.push(islands);
    }
    counts
}
