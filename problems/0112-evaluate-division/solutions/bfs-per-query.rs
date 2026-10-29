use std::collections::{HashMap, VecDeque};

type Graph<'a> = HashMap<&'a str, Vec<(&'a str, f64)>>;

/// Returns `source / target`, or -1 when no chain of equations links them.
fn ratio(graph: &Graph, source: &str, target: &str) -> f64 {
    if !graph.contains_key(source) || !graph.contains_key(target) {
        return -1.0;
    }
    // product[x] is the value of source / x along the path that reached x.
    let mut product = HashMap::from([(source, 1.0)]);
    let mut queue = VecDeque::from([source]);
    while let Some(node) = queue.pop_front() {
        if node == target {
            return product[node];
        }
        for &(next, value) in &graph[node] {
            if !product.contains_key(next) {
                let reached = product[node] * value;
                product.insert(next, reached);
                queue.push_back(next);
            }
        }
    }
    -1.0
}

pub fn calc_equation(
    equations: Vec<Vec<String>>,
    values: Vec<f64>,
    queries: Vec<Vec<String>>,
) -> Vec<f64> {
    // graph[a] lists every (b, a / b), and graph[b] the reverse edge (a, b / a).
    let mut graph: Graph = HashMap::new();
    for (equation, &value) in equations.iter().zip(&values) {
        let (a, b) = (equation[0].as_str(), equation[1].as_str());
        graph.entry(a).or_default().push((b, value));
        graph.entry(b).or_default().push((a, 1.0 / value));
    }
    queries
        .iter()
        .map(|query| ratio(&graph, &query[0], &query[1]))
        .collect()
}
