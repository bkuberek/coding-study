const LAND: char = '1';

/// A disjoint set over the cells, with union by size and path compression.
struct DisjointSet {
    parent: Vec<usize>,
    size: Vec<usize>,
}

impl DisjointSet {
    fn new(cells: usize) -> Self {
        DisjointSet {
            parent: (0..cells).collect(),
            size: vec![1; cells],
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

    /// Joins the sets of `a` and `b`; returns whether they were different sets.
    fn union(&mut self, a: usize, b: usize) -> bool {
        let (mut root_a, mut root_b) = (self.find(a), self.find(b));
        if root_a == root_b {
            return false;
        }
        if self.size[root_a] < self.size[root_b] {
            std::mem::swap(&mut root_a, &mut root_b);
        }
        self.parent[root_b] = root_a;
        self.size[root_a] += self.size[root_b];
        true
    }
}

pub fn num_islands(grid: Vec<Vec<char>>) -> i32 {
    let (rows, cols) = (grid.len(), grid[0].len());
    let mut cells = DisjointSet::new(rows * cols);
    let mut islands = 0;
    for row in 0..rows {
        for col in 0..cols {
            if grid[row][col] != LAND {
                continue;
            }
            islands += 1;
            let cell = row * cols + col;
            // Looking right and down is enough: the left and upper neighbors already looked here.
            if col + 1 < cols && grid[row][col + 1] == LAND && cells.union(cell, cell + 1) {
                islands -= 1;
            }
            if row + 1 < rows && grid[row + 1][col] == LAND && cells.union(cell, cell + cols) {
                islands -= 1;
            }
        }
    }
    islands
}
