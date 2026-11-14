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
        let mut root = node;
        while self.parent[root] != root {
            root = self.parent[root];
        }
        while self.parent[node] != root {
            let next = self.parent[node];
            self.parent[node] = root;
            node = next;
        }
        root
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

pub fn is_bipartite(graph: Vec<Vec<i32>>) -> bool {
    let mut set = DisjointSet::new(graph.len());
    // All neighbors of a node must share a team, so they go into one group.
    for neighbors in &graph {
        for &neighbor in neighbors.iter().skip(1) {
            set.union(neighbors[0] as usize, neighbor as usize);
        }
    }
    // A split exists exactly when no edge has both ends in one group.
    for (node, neighbors) in graph.iter().enumerate() {
        for &neighbor in neighbors {
            if set.find(node) == set.find(neighbor as usize) {
                return false;
            }
        }
    }
    true
}
