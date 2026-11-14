struct DisjointSet {
    parent: Vec<usize>,
    rank: Vec<u32>,
}

impl DisjointSet {
    fn new(count: usize) -> Self {
        DisjointSet {
            parent: (0..count).collect(),
            rank: vec![0; count],
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

    fn union(&mut self, a: usize, b: usize) {
        let (mut root_a, mut root_b) = (self.find(a), self.find(b));
        if root_a == root_b {
            return;
        }
        if self.rank[root_a] < self.rank[root_b] {
            std::mem::swap(&mut root_a, &mut root_b);
        }
        self.parent[root_b] = root_a;
        if self.rank[root_a] == self.rank[root_b] {
            self.rank[root_a] += 1;
        }
    }
}

#[allow(clippy::ptr_arg)] // the signature is fixed: the board is changed in place
pub fn solve(board: &mut Vec<Vec<char>>) {
    let rows = board.len();
    let cols = board[0].len();
    let edge = rows * cols; // a virtual node that every 'O' on the edge joins
    let mut set = DisjointSet::new(rows * cols + 1);
    for r in 0..rows {
        for c in 0..cols {
            if board[r][c] != 'O' {
                continue;
            }
            let cell = r * cols + c;
            if r == 0 || r == rows - 1 || c == 0 || c == cols - 1 {
                set.union(cell, edge);
            }
            if c + 1 < cols && board[r][c + 1] == 'O' {
                set.union(cell, cell + 1);
            }
            if r + 1 < rows && board[r + 1][c] == 'O' {
                set.union(cell, cell + cols);
            }
        }
    }
    let edge_root = set.find(edge);
    for (r, row) in board.iter_mut().enumerate() {
        for (c, cell) in row.iter_mut().enumerate() {
            if *cell == 'O' && set.find(r * cols + c) != edge_root {
                *cell = 'X';
            }
        }
    }
}
