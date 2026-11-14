use std::collections::{BTreeSet, HashMap, HashSet, VecDeque};

const USAGES: [&str; 4] = ["identity", "transform", "aggregate", "filter"];
const MASKABLE: [&str; 2] = ["transform", "aggregate"];

struct Edge {
    source: String,
    target: String,
    usage: String,
    masking: bool,
}

impl Edge {
    fn carries_value(&self) -> bool {
        self.usage != "filter" && !self.masking
    }
}

/// A dataset or column name: 1 to 20 characters from a-z, 0-9 and _.
fn is_name(text: &str) -> bool {
    (1..=20).contains(&text.len())
        && text.bytes().all(|byte| byte.is_ascii_lowercase() || byte.is_ascii_digit() || byte == b'_')
}

fn is_column_ref(text: &str) -> bool {
    text.split_once('.').is_some_and(|(dataset, column)| is_name(dataset) && is_name(column))
}

fn dataset_of(column: &str) -> &str {
    column.split_once('.').map_or(column, |(dataset, _)| dataset)
}

fn every_edge(_: &Edge) -> bool {
    true
}

fn identity_only(edge: &Edge) -> bool {
    edge.usage == "identity"
}

/// Columns are nodes named `dataset.column`, and each lineage edge points from an input column to
/// the column computed from it. Edges live in one vector, and two adjacency maps of edge indexes,
/// forward and backward, answer every walk: a breadth-first search gives distances for the ordered
/// queries, a filter on the edge's usage restricts a walk to the edges a change or a label travels
/// along, and Kosaraju's two passes group the columns that sit on a cycle.
pub struct LineageGraph {
    columns: HashMap<String, Vec<String>>,
    edges: Vec<Edge>,
    forward: HashMap<String, Vec<usize>>,
    backward: HashMap<String, Vec<usize>>,
    labels: HashMap<String, HashSet<String>>,
    published: HashSet<String>,
}

impl LineageGraph {
    pub fn new() -> Self {
        LineageGraph {
            columns: HashMap::new(),
            edges: Vec::new(),
            forward: HashMap::new(),
            backward: HashMap::new(),
            labels: HashMap::new(),
            published: HashSet::new(),
        }
    }

    // Level 1
    pub fn add_dataset(&mut self, name: String, columns: Vec<String>, edges: Vec<Vec<String>>) -> bool {
        let distinct: HashSet<&String> = columns.iter().collect();
        let all_names = is_name(&name) && columns.iter().all(|column| is_name(column));
        if self.columns.contains_key(&name) || !all_names || distinct.len() != columns.len() {
            return false;
        }
        let mut pairs: HashSet<(&str, &str)> = HashSet::new();
        let mut parsed = Vec::new();
        for spec in &edges {
            if !(3..=4).contains(&spec.len()) || !distinct.contains(&spec[0]) || !is_column_ref(&spec[1]) {
                return false;
            }
            let usage = spec[2].as_str();
            let masking = spec.len() == 4;
            if !USAGES.contains(&usage) || (masking && (spec[3] != "masking" || !MASKABLE.contains(&usage))) {
                return false;
            }
            if !pairs.insert((spec[0].as_str(), spec[1].as_str())) {
                return false;
            }
            parsed.push(Edge {
                source: spec[1].clone(),
                target: format!("{}.{}", name, spec[0]),
                usage: usage.to_string(),
                masking,
            });
        }
        for edge in parsed {
            let at = self.edges.len();
            self.forward.entry(edge.source.clone()).or_default().push(at);
            self.backward.entry(edge.target.clone()).or_default().push(at);
            self.edges.push(edge);
        }
        self.columns.insert(name, columns);
        true
    }

    pub fn validate(&mut self) -> Vec<Vec<String>> {
        let mut issues: Vec<Vec<String>> = Vec::new();
        for edge in &self.edges {
            let (dataset, column) = edge.source.split_once('.').unwrap_or((edge.source.as_str(), ""));
            match self.columns.get(dataset) {
                None => issues.push(vec!["unknown-dataset".into(), edge.target.clone(), edge.source.clone()]),
                Some(declared) if !declared.iter().any(|c| c == column) => {
                    issues.push(vec!["unknown-column".into(), edge.target.clone(), edge.source.clone()])
                }
                _ => {}
            }
        }
        for group in self.cycles() {
            let mut issue = vec!["cycle".to_string()];
            issue.extend(group);
            issues.push(issue);
        }
        issues.sort();
        issues
    }

    pub fn inputs_of(&mut self, column: String) -> Vec<String> {
        let mut inputs: Vec<String> =
            self.edges_into(&column).iter().map(|&at| self.edges[at].source.clone()).collect();
        inputs.sort();
        inputs
    }

    // Level 2
    pub fn upstream(&mut self, column: String) -> Vec<String> {
        by_distance(&self.walk(&column, false, every_edge))
    }

    pub fn downstream(&mut self, column: String) -> Vec<String> {
        by_distance(&self.walk(&column, true, every_edge))
    }

    // Level 3
    pub fn impact(&mut self, column: String, change: String) -> Vec<Vec<String>> {
        let reached = self.affected(&column, &change);
        by_distance(&reached)
            .into_iter()
            .map(|name| {
                let using = if reached[&name] == 1 { "direct" } else { "derived" };
                vec![name, using.to_string()]
            })
            .collect()
    }

    pub fn is_breaking(&mut self, column: String, change: String) -> bool {
        if change != "retype" {
            return !self.affected(&column, &change).is_empty();
        }
        self.typed(&column)
            .keys()
            .any(|name| self.edges_from(name).iter().any(|&at| self.edges[at].usage != "identity"))
    }

    pub fn impacted_datasets(&mut self, column: String, change: String) -> Vec<String> {
        let datasets: BTreeSet<String> =
            self.affected(&column, &change).keys().map(|name| dataset_of(name).to_string()).collect();
        datasets.into_iter().collect()
    }

    // Level 4
    pub fn tag(&mut self, column: String, label: String) -> bool {
        if !self.declared(&column) {
            return false;
        }
        self.labels.entry(column).or_default().insert(label)
    }

    pub fn tags_of(&mut self, column: String) -> Vec<String> {
        let mut sources = self.walk(&column, false, Edge::carries_value);
        sources.insert(column, 0);
        let found: BTreeSet<String> =
            sources.keys().filter_map(|name| self.labels.get(name)).flatten().cloned().collect();
        found.into_iter().collect()
    }

    pub fn publish(&mut self, dataset: String) -> bool {
        self.columns.contains_key(&dataset) && self.published.insert(dataset)
    }

    pub fn exposures(&mut self, label: String) -> Vec<Vec<String>> {
        let mut found: Vec<Vec<String>> = Vec::new();
        for (source, given) in &self.labels {
            if !given.contains(&label) {
                continue;
            }
            let mut reached = self.walk(source, true, Edge::carries_value);
            reached.insert(source.clone(), 0);
            for name in reached.into_keys() {
                if self.published.contains(dataset_of(&name)) {
                    found.push(vec![name, source.clone()]);
                }
            }
        }
        found.sort();
        found
    }

    // Helpers
    fn edges_from(&self, column: &str) -> &[usize] {
        self.forward.get(column).map_or(&[], |list| list.as_slice())
    }

    fn edges_into(&self, column: &str) -> &[usize] {
        self.backward.get(column).map_or(&[], |list| list.as_slice())
    }

    fn declared(&self, column: &str) -> bool {
        match column.split_once('.') {
            Some((dataset, name)) if is_column_ref(column) => {
                self.columns.get(dataset).is_some_and(|declared| declared.iter().any(|c| c == name))
            }
            _ => false,
        }
    }

    /// Breadth-first distances from `start` along the kept edges; `start` is in the answer only on
    /// a cycle.
    fn walk(&self, start: &str, ahead: bool, keep: fn(&Edge) -> bool) -> HashMap<String, i32> {
        let mut distance: HashMap<String, i32> = HashMap::new();
        let mut queue: VecDeque<(String, i32)> = VecDeque::new();
        queue.push_back((start.to_string(), 0));
        while let Some((node, steps)) = queue.pop_front() {
            let list = if ahead { self.edges_from(&node) } else { self.edges_into(&node) };
            for &at in list {
                let edge = &self.edges[at];
                let next = if ahead { &edge.target } else { &edge.source };
                if keep(edge) && !distance.contains_key(next) {
                    distance.insert(next.clone(), steps + 1);
                    queue.push_back((next.clone(), steps + 1));
                }
            }
        }
        distance
    }

    fn typed(&self, column: &str) -> HashMap<String, i32> {
        let mut typed = self.walk(column, true, identity_only);
        typed.insert(column.to_string(), 0);
        typed
    }

    fn affected(&self, column: &str, change: &str) -> HashMap<String, i32> {
        match change {
            "drop" => self.walk(column, true, every_edge),
            "rename" => self.edges_from(column).iter().map(|&at| (self.edges[at].target.clone(), 1)).collect(),
            _ => {
                let mut affected: HashMap<String, i32> = HashMap::new();
                for (name, steps) in self.typed(column) {
                    for &at in self.edges_from(&name) {
                        let entry = affected.entry(self.edges[at].target.clone()).or_insert(steps + 1);
                        *entry = (*entry).min(steps + 1);
                    }
                }
                affected
            }
        }
    }

    /// Strongly connected groups that hold a cycle, by Kosaraju's two passes.
    fn cycles(&self) -> Vec<Vec<String>> {
        let nodes: BTreeSet<&str> =
            self.edges.iter().flat_map(|edge| [edge.source.as_str(), edge.target.as_str()]).collect();
        let self_loops: HashSet<&str> =
            self.edges.iter().filter(|edge| edge.source == edge.target).map(|edge| edge.source.as_str()).collect();
        let mut finished: Vec<&str> = Vec::new();
        let mut seen: HashSet<&str> = HashSet::new();
        for &root in &nodes {
            if !seen.insert(root) {
                continue;
            }
            let mut stack: Vec<(&str, usize)> = vec![(root, 0)];
            while let Some((node, at)) = stack.pop() {
                let out = self.edges_from(node);
                if at == out.len() {
                    finished.push(node);
                    continue;
                }
                stack.push((node, at + 1));
                let next = self.edges[out[at]].target.as_str();
                if seen.insert(next) {
                    stack.push((next, 0));
                }
            }
        }
        let mut grouped: HashSet<&str> = HashSet::new();
        let mut groups: Vec<Vec<String>> = Vec::new();
        for &root in finished.iter().rev() {
            if !grouped.insert(root) {
                continue;
            }
            let mut members = vec![root.to_string()];
            let mut pending = vec![root];
            while let Some(node) = pending.pop() {
                for &at in self.edges_into(node) {
                    let source = self.edges[at].source.as_str();
                    if grouped.insert(source) {
                        members.push(source.to_string());
                        pending.push(source);
                    }
                }
            }
            if members.len() > 1 || self_loops.contains(root) {
                members.sort();
                groups.push(members);
            }
        }
        groups
    }
}

fn by_distance(distance: &HashMap<String, i32>) -> Vec<String> {
    let mut names: Vec<String> = distance.keys().cloned().collect();
    names.sort_by(|a, b| distance[a].cmp(&distance[b]).then_with(|| a.cmp(b)));
    names
}
