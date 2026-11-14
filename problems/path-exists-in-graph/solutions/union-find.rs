struct DisjointSet {
    parent: Vec<usize>,
    size: Vec<usize>,
}

impl DisjointSet {
    fn new(count: usize) -> Self {
        DisjointSet {
            parent: (0..count).collect(),
            size: vec![1; count],
        }
    }

    fn find(&mut self, mut node: usize) -> usize {
        // Path halving: point every other node on the way up at its grandparent.
        while self.parent[node] != node {
            self.parent[node] = self.parent[self.parent[node]];
            node = self.parent[node];
        }
        node
    }

    fn union(&mut self, a: usize, b: usize) {
        let (mut root_a, mut root_b) = (self.find(a), self.find(b));
        if root_a == root_b {
            return;
        }
        if self.size[root_a] < self.size[root_b] {
            std::mem::swap(&mut root_a, &mut root_b);
        }
        self.parent[root_b] = root_a;
        self.size[root_a] += self.size[root_b];
    }
}

pub fn has_path(n: i32, edges: Vec<Vec<i32>>, source: i32, target: i32) -> bool {
    let mut sets = DisjointSet::new(n as usize);
    for edge in &edges {
        sets.union(edge[0] as usize, edge[1] as usize);
    }
    sets.find(source as usize) == sets.find(target as usize)
}
