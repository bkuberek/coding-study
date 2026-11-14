struct DisjointSet {
    parent: Vec<usize>,
    size: Vec<i32>,
}

impl DisjointSet {
    fn new(count: usize) -> Self {
        DisjointSet {
            parent: (0..count).collect(),
            size: vec![1; count],
        }
    }

    fn find(&mut self, mut cell: usize) -> usize {
        let mut root = cell;
        while self.parent[root] != root {
            root = self.parent[root];
        }
        while self.parent[cell] != root {
            let next = self.parent[cell];
            self.parent[cell] = root;
            cell = next;
        }
        root
    }

    /// Merges the groups of `a` and `b` and returns the size of the merged group.
    fn union(&mut self, a: usize, b: usize) -> i32 {
        let (mut root_a, mut root_b) = (self.find(a), self.find(b));
        if root_a != root_b {
            if self.size[root_a] < self.size[root_b] {
                std::mem::swap(&mut root_a, &mut root_b);
            }
            self.parent[root_b] = root_a;
            self.size[root_a] += self.size[root_b];
        }
        self.size[root_a]
    }
}

pub fn max_area_of_island(grid: Vec<Vec<i32>>) -> i32 {
    let rows = grid.len();
    let cols = grid[0].len();
    let mut set = DisjointSet::new(rows * cols);
    let mut best = 0;
    for row in 0..rows {
        for col in 0..cols {
            if grid[row][col] != 1 {
                continue;
            }
            let cell = row * cols + col;
            best = best.max(1);
            if col + 1 < cols && grid[row][col + 1] == 1 {
                best = best.max(set.union(cell, cell + 1));
            }
            if row + 1 < rows && grid[row + 1][col] == 1 {
                best = best.max(set.union(cell, cell + cols));
            }
        }
    }
    best
}
