use std::collections::{BTreeMap, BTreeSet, HashMap, HashSet, VecDeque};

struct Contract {
    pairs: Vec<(String, String)>,
    direct: bool,
    ignores: HashSet<(String, String)>,
    exceptions: HashMap<(String, String), String>,
}

struct Walk {
    order: Vec<String>,
    parent: HashMap<String, Option<String>>,
}

/// Modules keep the imports as written. The first question after a change resolves every import
/// to the longest declared module that is the import or a dotted prefix of it, and keeps one
/// sorted list of targets per module, so every walk visits neighbours in name order.
///
/// A breadth-first walk from a sorted list of starts, over sorted neighbours, reaches each module
/// first along the shortest chain that is smallest in name order, so one walk per source name
/// answers every pair of a contract that starts there. Cycles are the strongly connected
/// components, found with two depth-first passes over the graph and its reverse.
pub struct ArchitectureChecker {
    imports: HashMap<String, Vec<String>>,
    graph: Option<HashMap<String, Vec<String>>>,
    contracts: HashMap<String, Contract>,
    version: Vec<u32>,
    baseline: BTreeSet<Vec<String>>,
}

impl ArchitectureChecker {
    pub fn new() -> Self {
        ArchitectureChecker {
            imports: HashMap::new(),
            graph: None,
            contracts: HashMap::new(),
            version: Vec::new(),
            baseline: BTreeSet::new(),
        }
    }

    // Level 1
    pub fn add_module(&mut self, name: String, imports: Vec<String>) -> bool {
        self.graph = None;
        self.imports.insert(name, imports).is_none()
    }

    pub fn unknown_imports(&mut self) -> Vec<Vec<String>> {
        let mut rows = BTreeSet::new();
        for (module, list) in &self.imports {
            for text in list {
                if self.resolve(text).is_none() {
                    rows.insert(vec![module.clone(), text.clone()]);
                }
            }
        }
        rows.into_iter().collect()
    }

    pub fn dependencies(&mut self, name: String) -> Vec<String> {
        self.ensure_graph();
        let graph = self.graph();
        let mut found = BTreeSet::new();
        for module in self.members(&name) {
            for target in &graph[&module] {
                if !inside(target, &name) {
                    found.insert(target.clone());
                }
            }
        }
        found.into_iter().collect()
    }

    pub fn transitive_dependencies(&mut self, name: String) -> Vec<String> {
        self.ensure_graph();
        let walk = self.walk(&self.members(&name), None);
        let mut depth: HashMap<&str, usize> = HashMap::new();
        for module in &walk.order {
            let steps = match &walk.parent[module] {
                Some(above) => depth[above.as_str()] + 1,
                None => 0,
            };
            depth.insert(module, steps);
        }
        let mut reached: Vec<String> = walk
            .order
            .iter()
            .filter(|module| !inside(module, &name))
            .cloned()
            .collect();
        reached.sort_by(|a, b| {
            depth[a.as_str()]
                .cmp(&depth[b.as_str()])
                .then_with(|| a.cmp(b))
        });
        reached
    }

    // Level 2
    pub fn cycles(&mut self, depth: i32) -> Vec<Vec<String>> {
        self.ensure_graph();
        let depth = depth as usize;
        let mut adjacency: BTreeMap<String, BTreeSet<String>> = BTreeMap::new();
        for (module, targets) in self.graph() {
            let group = group_of(module, depth);
            let out = adjacency.entry(group.clone()).or_default();
            for target in targets {
                let other = group_of(target, depth);
                if other != group {
                    out.insert(other);
                }
            }
        }
        let mut found: Vec<Vec<String>> = components(&adjacency)
            .into_iter()
            .filter(|part| part.len() > 1)
            .map(|mut part| {
                part.sort();
                part
            })
            .collect();
        found.sort();
        found
    }

    pub fn cycle_chain(&mut self, name: String) -> Vec<String> {
        if !self.imports.contains_key(&name) {
            return Vec::new();
        }
        self.ensure_graph();
        let graph = self.graph();
        let walk = self.walk(std::slice::from_ref(&name), None);
        for module in &walk.order {
            if graph[module].contains(&name) {
                let mut chain = chain_of(module, &walk.parent);
                chain.push(name);
                return chain;
            }
        }
        Vec::new()
    }

    // Level 3
    pub fn add_layers(&mut self, contract: String, layers: Vec<String>) -> bool {
        let mut pairs = Vec::new();
        for low in 0..layers.len() {
            for high in 0..low {
                pairs.push((layers[low].clone(), layers[high].clone()));
            }
        }
        self.add_contract(contract, pairs)
    }

    pub fn add_forbidden(&mut self, contract: String, source: String, target: String) -> bool {
        self.add_contract(contract, vec![(source, target)])
    }

    pub fn add_independence(&mut self, contract: String, names: Vec<String>) -> bool {
        let mut pairs = Vec::new();
        for first in &names {
            for second in &names {
                if first != second {
                    pairs.push((first.clone(), second.clone()));
                }
            }
        }
        self.add_contract(contract, pairs)
    }

    pub fn check(&mut self) -> Vec<Vec<String>> {
        self.ensure_graph();
        self.violations()
            .into_iter()
            .map(|(key, chain)| key.into_iter().chain(chain).collect())
            .collect()
    }

    // Level 4
    pub fn ignore(&mut self, contract: String, importer: String, imported: String) -> bool {
        match self.contracts.get_mut(&contract) {
            Some(rules) => rules.ignores.insert((importer, imported)),
            None => false,
        }
    }

    pub fn allow(
        &mut self,
        contract: String,
        importer: String,
        imported: String,
        until: String,
    ) -> bool {
        let Some(rules) = self.contracts.get_mut(&contract) else {
            return false;
        };
        let key = (importer, imported);
        if let Some(old) = rules.exceptions.get(&key) {
            if version_key(old) == version_key(&until) {
                return false;
            }
        }
        rules.exceptions.insert(key, until);
        true
    }

    pub fn set_version(&mut self, version: String) -> Vec<Vec<String>> {
        self.version = version_key(&version);
        let mut rows = Vec::new();
        for (name, rules) in &self.contracts {
            for ((importer, imported), until) in &rules.exceptions {
                if version_key(until) <= self.version {
                    rows.push(vec![
                        name.clone(),
                        importer.clone(),
                        imported.clone(),
                        until.clone(),
                    ]);
                }
            }
        }
        rows.sort();
        rows
    }

    pub fn set_mode(&mut self, contract: String, mode: String) -> bool {
        let direct = mode == "direct";
        match self.contracts.get_mut(&contract) {
            Some(rules) if rules.direct != direct => {
                rules.direct = direct;
                true
            }
            _ => false,
        }
    }

    pub fn set_baseline(&mut self, entries: Vec<Vec<String>>) -> i32 {
        self.baseline = entries
            .into_iter()
            .map(|mut entry| {
                entry.truncate(3);
                entry
            })
            .collect();
        self.baseline.len() as i32
    }

    pub fn ratchet(&mut self) -> Vec<Vec<String>> {
        self.ensure_graph();
        let current = self.violations();
        let broken: BTreeSet<&Vec<String>> = current.iter().map(|(key, _)| key).collect();
        let mut rows: Vec<Vec<String>> = Vec::new();
        for (key, chain) in &current {
            if !self.baseline.contains(key) {
                let mut row = vec!["new".to_string()];
                row.extend(key.iter().cloned());
                row.extend(chain.iter().cloned());
                rows.push(row);
            }
        }
        let fixed: Vec<Vec<String>> = self
            .baseline
            .iter()
            .filter(|entry| !broken.contains(entry))
            .cloned()
            .collect();
        for entry in fixed {
            self.baseline.remove(&entry);
            let mut row = vec!["fixed".to_string()];
            row.extend(entry);
            rows.push(row);
        }
        rows
    }

    // Helpers
    fn resolve(&self, text: &str) -> Option<String> {
        let mut name = text;
        loop {
            if self.imports.contains_key(name) {
                return Some(name.to_string());
            }
            let cut = name.rfind('.')?;
            name = &name[..cut];
        }
    }

    fn ensure_graph(&mut self) {
        if self.graph.is_some() {
            return;
        }
        let mut graph = HashMap::new();
        for (module, list) in &self.imports {
            let targets: BTreeSet<String> = list
                .iter()
                .filter_map(|text| self.resolve(text))
                .filter(|target| target != module)
                .collect();
            graph.insert(module.clone(), targets.into_iter().collect::<Vec<_>>());
        }
        self.graph = Some(graph);
    }

    fn graph(&self) -> &HashMap<String, Vec<String>> {
        self.graph
            .as_ref()
            .expect("the graph is built before it is read")
    }

    fn members(&self, name: &str) -> Vec<String> {
        let mut found: Vec<String> = self
            .imports
            .keys()
            .filter(|module| inside(module, name))
            .cloned()
            .collect();
        found.sort();
        found
    }

    /// Breadth-first from the sorted starts over sorted neighbours.
    fn walk(&self, starts: &[String], rules: Option<&Contract>) -> Walk {
        let graph = self.graph();
        let mut parent: HashMap<String, Option<String>> =
            starts.iter().map(|start| (start.clone(), None)).collect();
        let mut order = starts.to_vec();
        let mut queue: VecDeque<String> = starts.iter().cloned().collect();
        while let Some(module) = queue.pop_front() {
            for target in &graph[&module] {
                if !parent.contains_key(target) && !self.skipped(rules, &module, target) {
                    parent.insert(target.clone(), Some(module.clone()));
                    order.push(target.clone());
                    queue.push_back(target.clone());
                }
            }
        }
        Walk { order, parent }
    }

    fn add_contract(&mut self, contract: String, pairs: Vec<(String, String)>) -> bool {
        if self.contracts.contains_key(&contract) {
            return false;
        }
        let rules = Contract {
            pairs,
            direct: false,
            ignores: HashSet::new(),
            exceptions: HashMap::new(),
        };
        self.contracts.insert(contract, rules);
        true
    }

    fn skipped(&self, rules: Option<&Contract>, importer: &str, imported: &str) -> bool {
        let Some(rules) = rules else {
            return false;
        };
        let covers = |(first, second): &(String, String)| {
            inside(importer, first) && inside(imported, second)
        };
        rules.ignores.iter().any(covers)
            || rules
                .exceptions
                .iter()
                .any(|(rule, until)| self.version < version_key(until) && covers(rule))
    }

    fn violations(&self) -> Vec<(Vec<String>, Vec<String>)> {
        let mut found = Vec::new();
        let mut names: Vec<&String> = self.contracts.keys().collect();
        names.sort();
        for name in names {
            let rules = &self.contracts[name];
            let sources: BTreeSet<&String> = rules.pairs.iter().map(|(from, _)| from).collect();
            for source in sources {
                let targets: Vec<&String> = rules
                    .pairs
                    .iter()
                    .filter(|(from, _)| from == source)
                    .map(|(_, to)| to)
                    .collect();
                for (target, chain) in self.chains(rules, source, &targets) {
                    found.push((vec![name.clone(), source.clone(), target], chain));
                }
            }
        }
        found.sort();
        found
    }

    fn chains(
        &self,
        rules: &Contract,
        source: &str,
        targets: &[&String],
    ) -> Vec<(String, Vec<String>)> {
        let starts = self.members(source);
        if rules.direct {
            return targets
                .iter()
                .filter_map(|target| {
                    self.first_import(rules, &starts, target)
                        .map(|hit| (target.to_string(), hit))
                })
                .collect();
        }
        let walk = self.walk(&starts, Some(rules));
        targets
            .iter()
            .filter_map(|target| {
                let first = walk.order.iter().find(|module| inside(module, target))?;
                Some((target.to_string(), chain_of(first, &walk.parent)))
            })
            .collect()
    }

    /// The starts and their targets are sorted, so the first import found is the smallest.
    fn first_import(
        &self,
        rules: &Contract,
        starts: &[String],
        target: &str,
    ) -> Option<Vec<String>> {
        let graph = self.graph();
        for module in starts {
            for other in &graph[module] {
                if inside(other, target) && !self.skipped(Some(rules), module, other) {
                    return Some(vec![module.clone(), other.clone()]);
                }
            }
        }
        None
    }
}

fn inside(module: &str, name: &str) -> bool {
    module == name
        || (module.len() > name.len()
            && module.starts_with(name)
            && module.as_bytes()[name.len()] == b'.')
}

fn group_of(module: &str, depth: usize) -> String {
    if depth == 0 {
        return module.to_string();
    }
    module.split('.').take(depth).collect::<Vec<_>>().join(".")
}

fn chain_of(module: &str, parent: &HashMap<String, Option<String>>) -> Vec<String> {
    let mut chain = vec![module.to_string()];
    let mut step = module;
    while let Some(Some(above)) = parent.get(step) {
        chain.push(above.clone());
        step = above;
    }
    chain.reverse();
    chain
}

fn version_key(text: &str) -> Vec<u32> {
    let mut parts: Vec<u32> = text
        .split('.')
        .map(|part| part.parse().unwrap_or(0))
        .collect();
    while parts.last() == Some(&0) {
        parts.pop();
    }
    parts
}

/// Two depth-first passes: finishing order on the graph, then components on its reverse.
fn components(adjacency: &BTreeMap<String, BTreeSet<String>>) -> Vec<Vec<String>> {
    let forward: HashMap<&str, Vec<&str>> = adjacency
        .iter()
        .map(|(node, targets)| (node.as_str(), targets.iter().map(String::as_str).collect()))
        .collect();
    let mut reverse: HashMap<&str, Vec<&str>> = adjacency
        .keys()
        .map(|node| (node.as_str(), Vec::new()))
        .collect();
    for (node, targets) in adjacency {
        for target in targets {
            if let Some(sources) = reverse.get_mut(target.as_str()) {
                sources.push(node.as_str());
            }
        }
    }
    let mut finished: Vec<&str> = Vec::new();
    let mut seen: HashSet<&str> = HashSet::new();
    for root in adjacency.keys() {
        if !seen.insert(root.as_str()) {
            continue;
        }
        let mut stack: Vec<(&str, usize)> = vec![(root.as_str(), 0)];
        while let Some((node, index)) = stack.pop() {
            let targets = &forward[node];
            if index < targets.len() {
                stack.push((node, index + 1));
                let target = targets[index];
                if seen.insert(target) {
                    stack.push((target, 0));
                }
            } else {
                finished.push(node);
            }
        }
    }
    let mut assigned: HashSet<&str> = HashSet::new();
    let mut parts = Vec::new();
    for &root in finished.iter().rev() {
        if !assigned.insert(root) {
            continue;
        }
        let mut part = Vec::new();
        let mut stack = vec![root];
        while let Some(node) = stack.pop() {
            part.push(node.to_string());
            for &source in &reverse[node] {
                if assigned.insert(source) {
                    stack.push(source);
                }
            }
        }
        parts.push(part);
    }
    parts
}
