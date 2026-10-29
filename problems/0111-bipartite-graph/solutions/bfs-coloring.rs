use std::collections::VecDeque;

pub fn is_bipartite(graph: Vec<Vec<i32>>) -> bool {
    // `None` means not colored yet; the two colors are `false` and `true`.
    let mut color: Vec<Option<bool>> = vec![None; graph.len()];
    // Every piece of the graph needs its own start node.
    for start in 0..graph.len() {
        if color[start].is_some() {
            continue;
        }
        color[start] = Some(false);
        let mut queue = VecDeque::from([start]);
        while let Some(node) = queue.pop_front() {
            let node_color = color[node];
            for &neighbor in &graph[node] {
                let neighbor = neighbor as usize;
                match color[neighbor] {
                    None => {
                        color[neighbor] = node_color.map(|shade| !shade);
                        queue.push_back(neighbor);
                    }
                    shade if shade == node_color => return false,
                    Some(_) => {}
                }
            }
        }
    }
    true
}
