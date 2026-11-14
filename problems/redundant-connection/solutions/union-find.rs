fn find(parent: &mut [usize], mut x: usize) -> usize {
    let mut root = x;
    while parent[root] != root {
        root = parent[root];
    }
    while parent[x] != root {
        // path compression: point the whole path at the root
        let next = parent[x];
        parent[x] = root;
        x = next;
    }
    root
}

pub fn find_redundant_connection(edges: Vec<Vec<i32>>) -> Vec<i32> {
    let mut parent: Vec<usize> = (0..=edges.len()).collect();
    let mut size = vec![1; edges.len() + 1]; // size[r]: number of nodes in the tree rooted at r
    for edge in &edges {
        let mut root_a = find(&mut parent, edge[0] as usize);
        let mut root_b = find(&mut parent, edge[1] as usize);
        if root_a == root_b {
            return edge.clone(); // the ends are already connected: this edge closes the cycle
        }
        if size[root_a] < size[root_b] {
            std::mem::swap(&mut root_a, &mut root_b);
        }
        parent[root_b] = root_a; // union by size: the smaller tree goes under the larger
        size[root_a] += size[root_b];
    }
    vec![]
}
