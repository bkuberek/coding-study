use std::collections::VecDeque;

pub fn has_path(n: i32, edges: Vec<Vec<i32>>, source: i32, target: i32) -> bool {
    let count = n as usize;
    let (source, target) = (source as usize, target as usize);
    // neighbors[node] lists every node joined to `node`; each connection works both ways.
    let mut neighbors: Vec<Vec<usize>> = vec![Vec::new(); count];
    for edge in &edges {
        let (a, b) = (edge[0] as usize, edge[1] as usize);
        neighbors[a].push(b);
        neighbors[b].push(a);
    }
    let mut seen = vec![false; count];
    seen[source] = true;
    let mut queue = VecDeque::from([source]);
    while let Some(node) = queue.pop_front() {
        if node == target {
            return true;
        }
        for &neighbor in &neighbors[node] {
            if !seen[neighbor] {
                seen[neighbor] = true;
                queue.push_back(neighbor);
            }
        }
    }
    false
}
