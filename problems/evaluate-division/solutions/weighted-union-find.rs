use std::collections::HashMap;

/// A union-find over variable names. `weight[x]` is the value of `x / parent[x]`.
struct RatioSet<'a> {
    parent: HashMap<&'a str, &'a str>,
    weight: HashMap<&'a str, f64>,
}

impl<'a> RatioSet<'a> {
    /// Returns the root of `name` and the value of `name / root`, compressing the path on the way.
    fn find(&mut self, name: &'a str) -> (&'a str, f64) {
        let mut path = Vec::new();
        let mut current = name;
        while self.parent[current] != current {
            path.push(current);
            current = self.parent[current];
        }
        let root = current;
        // Walk back from the node nearest the root, so each weight already points at the root.
        for &node in path.iter().rev() {
            let parent = self.parent[node];
            if parent != root {
                let parent_weight = self.weight[parent];
                if let Some(weight) = self.weight.get_mut(node) {
                    *weight *= parent_weight;
                }
                self.parent.insert(node, root);
            }
        }
        match path.first() {
            Some(first) => (root, self.weight[first]),
            None => (root, 1.0),
        }
    }
}

pub fn calc_equation(
    equations: Vec<Vec<String>>,
    values: Vec<f64>,
    queries: Vec<Vec<String>>,
) -> Vec<f64> {
    let mut set = RatioSet {
        parent: HashMap::new(),
        weight: HashMap::new(),
    };
    for (equation, &value) in equations.iter().zip(&values) {
        let (a, b) = (equation[0].as_str(), equation[1].as_str());
        for name in [a, b] {
            set.parent.entry(name).or_insert(name);
            set.weight.entry(name).or_insert(1.0);
        }
        let (root_a, a_over_root_a) = set.find(a);
        let (root_b, b_over_root_b) = set.find(b);
        if root_a != root_b {
            // Hang root_a under root_b: root_a / root_b = (a / b) * (b / root_b) / (a / root_a).
            set.parent.insert(root_a, root_b);
            set.weight
                .insert(root_a, value * b_over_root_b / a_over_root_a);
        }
    }
    let mut answers = Vec::with_capacity(queries.len());
    for query in &queries {
        let (c, d) = (query[0].as_str(), query[1].as_str());
        if !set.parent.contains_key(c) || !set.parent.contains_key(d) {
            answers.push(-1.0);
            continue;
        }
        let (root_c, c_over_root) = set.find(c);
        let (root_d, d_over_root) = set.find(d);
        answers.push(if root_c == root_d {
            c_over_root / d_over_root
        } else {
            -1.0
        });
    }
    answers
}
