pub fn min_cost_connect_points(points: Vec<Vec<i32>>) -> i32 {
    let n = points.len();
    // Tuples compare by cost first, so sorting them orders the pairs from cheapest to dearest.
    let mut pairs = Vec::with_capacity(n * n.saturating_sub(1) / 2);
    for i in 0..n {
        for j in i + 1..n {
            let cost = (points[i][0] - points[j][0]).abs() + (points[i][1] - points[j][1]).abs();
            pairs.push((cost, i, j));
        }
    }
    pairs.sort_unstable();
    let mut parent: Vec<usize> = (0..n).collect();
    let mut total = 0;
    let mut cables = 0;
    // Take pairs from cheapest to most expensive, keeping each one that joins two groups.
    for (cost, i, j) in pairs {
        if cables == n - 1 {
            break;
        }
        let (root_i, root_j) = (find(&mut parent, i), find(&mut parent, j));
        if root_i != root_j {
            parent[root_i] = root_j;
            total += cost;
            cables += 1;
        }
    }
    total
}

// The root of the group that holds `node`, with every node on the way pointed at the root.
fn find(parent: &mut [usize], mut node: usize) -> usize {
    let mut root = node;
    while parent[root] != root {
        root = parent[root];
    }
    while parent[node] != root {
        let next = parent[node];
        parent[node] = root;
        node = next;
    }
    root
}
