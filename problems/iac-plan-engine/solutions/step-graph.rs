use std::cmp::Reverse;
use std::collections::{BTreeMap, BTreeSet, BinaryHeap, HashMap, HashSet};

const UNKNOWN: &str = "<unknown>";
const FORCES: &str = "forces-replacement";

#[derive(Clone, Copy, PartialEq)]
enum Mode {
    None,
    CreateFirst,
    DeleteFirst,
}

struct Step {
    verb: &'static str,
    address: String,
    tag: &'static str,
    rank: u8,
    mode: Mode,
    diff: Vec<Vec<String>>,
    before: Vec<usize>,
    after: Vec<usize>,
}

impl Step {
    fn new(verb: &'static str, address: &str, tag: &'static str, rank: u8) -> Self {
        Step {
            verb,
            address: address.to_string(),
            tag,
            rank,
            mode: Mode::None,
            diff: Vec::new(),
            before: Vec::new(),
            after: Vec::new(),
        }
    }
}

type Attributes = BTreeMap<String, String>;

/// The target address and key of a `${type.name.key}` value.
fn reference(value: &str) -> Option<(String, String)> {
    let inner = value.strip_prefix("${")?.strip_suffix('}')?;
    let parts: Vec<&str> = inner.split('.').collect();
    Some((format!("{}.{}", parts[0], parts[1]), parts[2].to_string()))
}

fn kind_of(address: &str) -> &str {
    address.split('.').next().unwrap_or("")
}

fn to_map(attributes: Vec<Vec<String>>) -> Attributes {
    attributes.into_iter().map(|pair| (pair[0].clone(), pair[1].clone())).collect()
}

fn row(parts: &[&str]) -> Vec<String> {
    parts.iter().map(|part| part.to_string()).collect()
}

fn removed(attributes: &Attributes) -> Vec<Vec<String>> {
    attributes.iter().map(|(key, value)| row(&["-", key, value])).collect()
}

/// Desired and actual resources are maps of attributes. A plan resolves the references of the
/// desired resources in dependency order, which tells for each resource whether it is created,
/// updated, replaced, left alone or deleted, then turns those actions into steps joined by
/// before-rules and lists the steps in the smallest order by (rank, address) that keeps every
/// rule. Apply walks the same steps, skips those behind a failure, and records the state after
/// each step that succeeds.
pub struct PlanEngine {
    desired: HashMap<String, Attributes>,
    current: HashMap<String, Attributes>,
    deps: HashMap<String, BTreeSet<String>>,
    old: HashMap<String, Attributes>,
    old_deps: HashMap<String, BTreeSet<String>>,
    forces: HashSet<(String, String)>,
    computed: HashMap<String, BTreeSet<String>>,
    marked: HashSet<String>,
}

impl PlanEngine {
    pub fn new() -> Self {
        PlanEngine {
            desired: HashMap::new(),
            current: HashMap::new(),
            deps: HashMap::new(),
            old: HashMap::new(),
            old_deps: HashMap::new(),
            forces: HashSet::new(),
            computed: HashMap::new(),
            marked: HashSet::new(),
        }
    }

    // Level 1
    pub fn desire(&mut self, address: String, attributes: Vec<Vec<String>>) -> bool {
        self.desired.insert(address, to_map(attributes)).is_none()
    }

    pub fn remove(&mut self, address: String) -> bool {
        self.desired.remove(&address).is_some()
    }

    pub fn observe(&mut self, address: String, attributes: Vec<Vec<String>>) -> bool {
        self.current.insert(address, to_map(attributes)).is_none()
    }

    pub fn plan(&mut self) -> Vec<Vec<String>> {
        let (steps, order) = match self.build() {
            Ok(built) => built,
            Err(errors) => return errors,
        };
        let mut rows = Vec::new();
        for index in order {
            let step = &steps[index];
            let mut head = row(&[step.verb, &step.address]);
            if !step.tag.is_empty() {
                head.push(step.tag.to_string());
            }
            rows.push(head);
            rows.extend(step.diff.iter().cloned());
        }
        rows
    }

    // Level 2
    pub fn observe_dependency(&mut self, address: String, depends_on: String) -> bool {
        if !self.current.contains_key(&address) || !self.current.contains_key(&depends_on) {
            return false;
        }
        self.deps.entry(address).or_default().insert(depends_on)
    }

    // Level 3
    pub fn force_replacement(&mut self, resource_type: String, key: String) -> bool {
        self.forces.insert((resource_type, key))
    }

    pub fn computed(&mut self, resource_type: String, key: String) -> bool {
        self.computed.entry(resource_type).or_default().insert(key)
    }

    pub fn create_before_destroy(&mut self, address: String) -> bool {
        self.marked.insert(address)
    }

    // Level 4
    pub fn apply(&mut self, failures: Vec<Vec<String>>, values: Vec<Vec<String>>) -> Vec<Vec<String>> {
        let (steps, order) = match self.build() {
            Ok(built) => built,
            Err(errors) => return errors,
        };
        let failing: HashSet<(String, String)> =
            failures.into_iter().map(|pair| (pair[0].clone(), pair[1].clone())).collect();
        let assigned: HashMap<(String, String), String> = values
            .into_iter()
            .map(|row| ((row[0].clone(), row[1].clone()), row[2].clone()))
            .collect();
        let mut ok = vec![false; steps.len()];
        let mut rows = Vec::new();
        for index in order {
            let step = &steps[index];
            let outcome = if step.before.iter().any(|&prior| !ok[prior]) {
                "skipped"
            } else if step.verb != "no-op"
                && failing.contains(&(step.verb.to_string(), step.address.clone()))
            {
                "failed"
            } else {
                self.perform(step, &assigned);
                ok[index] = true;
                "ok"
            };
            rows.push(row(&[step.verb, &step.address, outcome]));
        }
        rows
    }

    pub fn state(&mut self) -> Vec<Vec<String>> {
        let addresses: BTreeSet<&String> = self.current.keys().chain(self.old.keys()).collect();
        let mut rows = Vec::new();
        for address in addresses {
            for (role, objects) in [("current", &self.current), ("old", &self.old)] {
                if let Some(attributes) = objects.get(address) {
                    let mut line = row(&[address, role]);
                    for (key, value) in attributes {
                        line.push(key.clone());
                        line.push(value.clone());
                    }
                    rows.push(line);
                }
            }
        }
        rows
    }

    // Planning
    fn is_computed(&self, address: &str, key: &str) -> bool {
        self.computed.get(kind_of(address)).map_or(false, |keys| keys.contains(key))
    }

    fn computed_of(&self, address: &str) -> Vec<String> {
        self.computed.get(kind_of(address)).map_or(Vec::new(), |keys| keys.iter().cloned().collect())
    }

    fn cycles(needs: &BTreeMap<String, BTreeSet<String>>) -> Vec<Vec<String>> {
        let mut reach: HashMap<&String, HashSet<&String>> = HashMap::new();
        for (start, targets) in needs {
            let mut seen = HashSet::new();
            let mut stack: Vec<&String> = targets.iter().collect();
            while let Some(node) = stack.pop() {
                if seen.insert(node) {
                    stack.extend(needs[node].iter());
                }
            }
            reach.insert(start, seen);
        }
        let mut groups: BTreeMap<String, Vec<String>> = BTreeMap::new();
        for node in needs.keys() {
            if reach[node].contains(node) {
                let group: BTreeSet<&String> =
                    reach[node].iter().copied().filter(|other| reach[*other].contains(node)).collect();
                let group: Vec<String> = group.into_iter().cloned().collect();
                groups.insert(group[0].clone(), group);
            }
        }
        groups
            .into_values()
            .map(|group| {
                let mut line = row(&["error", "cycle"]);
                line.extend(group);
                line
            })
            .collect()
    }

    fn dependency_order(needs: &BTreeMap<String, BTreeSet<String>>) -> Vec<String> {
        let mut waiting: HashMap<&String, usize> = needs.iter().map(|(a, t)| (a, t.len())).collect();
        let mut users: HashMap<&String, Vec<&String>> = HashMap::new();
        for (address, targets) in needs {
            for target in targets {
                users.entry(target).or_default().push(address);
            }
        }
        let mut ready: BinaryHeap<Reverse<&String>> =
            needs.iter().filter(|(_, targets)| targets.is_empty()).map(|(a, _)| Reverse(a)).collect();
        let mut order = Vec::new();
        while let Some(Reverse(address)) = ready.pop() {
            order.push(address.clone());
            if let Some(list) = users.get(address) {
                for &user in list {
                    let count = waiting.get_mut(user).unwrap();
                    *count -= 1;
                    if *count == 0 {
                        ready.push(Reverse(user));
                    }
                }
            }
        }
        order
    }

    fn create_first(&self, needs: &BTreeMap<String, BTreeSet<String>>) -> HashSet<String> {
        let mut found = HashSet::new();
        let mut stack: Vec<String> =
            self.marked.iter().filter(|a| self.desired.contains_key(*a)).cloned().collect();
        while let Some(address) = stack.pop() {
            if found.insert(address.clone()) {
                stack.extend(needs[&address].iter().cloned());
            }
        }
        found
    }

    fn build(&self) -> Result<(Vec<Step>, Vec<usize>), Vec<Vec<String>>> {
        let mut errors = Vec::new();
        let mut needs: BTreeMap<String, BTreeSet<String>> =
            self.desired.keys().map(|a| (a.clone(), BTreeSet::new())).collect();
        let addresses: Vec<String> = needs.keys().cloned().collect();
        for address in &addresses {
            for (key, value) in &self.desired[address] {
                let Some((other, wanted)) = reference(value) else { continue };
                let exists = self.desired.get(&other).map_or(false, |declared| {
                    declared.contains_key(&wanted) || self.is_computed(&other, &wanted)
                });
                if exists {
                    needs.get_mut(address).unwrap().insert(other);
                } else {
                    errors.push(row(&["error", "unknown-reference", address, key, &format!("{other}.{wanted}")]));
                }
            }
        }
        errors.extend(Self::cycles(&needs));
        if !errors.is_empty() {
            return Err(errors);
        }

        let early = self.create_first(&needs);
        let mut steps: Vec<Step> = Vec::new();
        let mut action: HashMap<String, &'static str> = HashMap::new();
        let mut resolved: HashMap<String, Attributes> = HashMap::new();
        let mut applies: HashMap<String, usize> = HashMap::new();
        let mut deletes: BTreeMap<String, usize> = BTreeMap::new();
        for address in Self::dependency_order(&needs) {
            let mut values = Attributes::new();
            for (key, value) in &self.desired[&address] {
                let resolved_value = match reference(value) {
                    None => value.clone(),
                    Some((other, wanted)) if self.is_computed(&other, &wanted) => {
                        if matches!(action[&other], "create" | "replace") {
                            UNKNOWN.to_string()
                        } else {
                            self.current[&other][&wanted].clone()
                        }
                    }
                    Some((other, wanted)) => resolved[&other][&wanted].clone(),
                };
                values.insert(key.clone(), resolved_value);
            }
            let step = self.classify(&address, &values);
            let kind = if step.verb == "create" && step.tag == "replace" { "replace" } else { step.verb };
            resolved.insert(address.clone(), values);
            action.insert(address.clone(), kind);
            applies.insert(address.clone(), steps.len());
            steps.push(step);
            if kind == "replace" {
                let mut half = Step::new("delete", &address, "replace", 1);
                half.mode = if early.contains(&address) { Mode::CreateFirst } else { Mode::DeleteFirst };
                deletes.insert(address.clone(), steps.len());
                steps.push(half);
            }
        }
        for (address, attributes) in &self.current {
            if !self.desired.contains_key(address) {
                let mut step = Step::new("delete", address, "", 1);
                step.diff = removed(attributes);
                deletes.insert(address.clone(), steps.len());
                steps.push(step);
            }
        }
        let mut olds: BTreeMap<String, usize> = BTreeMap::new();
        for (address, attributes) in &self.old {
            let mut step = Step::new("delete", address, "old", 1);
            step.diff = removed(attributes);
            olds.insert(address.clone(), steps.len());
            steps.push(step);
        }
        let deletes_of = |address: &String| -> Vec<usize> {
            olds.get(address).into_iter().chain(deletes.get(address)).copied().collect()
        };

        let mut edges: Vec<(usize, usize)> = Vec::new();
        for (address, targets) in &needs {
            for target in targets {
                edges.push((applies[target], applies[address]));
            }
        }
        for (address, &index) in deletes.iter().chain(olds.iter()) {
            let held = if steps[index].tag == "old" { &self.old_deps } else { &self.deps };
            for target in held.get(address).into_iter().flatten() {
                for gone in deletes_of(target) {
                    edges.push((index, gone));
                }
            }
        }
        for (address, &index) in &applies {
            if !self.current.contains_key(address) {
                continue;
            }
            for target in self.deps.get(address).into_iter().flatten() {
                let replaced_again = deletes.get(target).map_or(false, |&later| steps[later].tag == "replace");
                for gone in deletes_of(target) {
                    let held_back = steps[gone].mode != Mode::DeleteFirst
                        && !(steps[gone].tag == "old" && replaced_again);
                    if held_back {
                        edges.push((index, gone));
                    }
                }
            }
        }
        for (address, &index) in &deletes {
            match steps[index].mode {
                Mode::DeleteFirst => edges.push((index, applies[address])),
                Mode::CreateFirst => edges.push((applies[address], index)),
                Mode::None => {}
            }
        }
        for (address, &stale) in &olds {
            if let Some(&later) = deletes.get(address) {
                edges.push((stale, later));
                if steps[later].tag == "replace" {
                    edges.push((stale, applies[address]));
                }
            }
        }
        for (first, second) in edges {
            steps[first].after.push(second);
            steps[second].before.push(first);
        }
        let order = Self::order(&steps);
        Ok((steps, order))
    }

    fn classify(&self, address: &str, values: &Attributes) -> Step {
        let computed = self.computed_of(address);
        let Some(existing) = self.current.get(address) else {
            let mut step = Step::new("create", address, "", 0);
            step.diff = values.iter().map(|(k, v)| row(&["+", k, v])).collect();
            step.diff.extend(computed.iter().map(|name| row(&["+", name, UNKNOWN])));
            step.diff.sort_by(|a, b| a[1].cmp(&b[1]));
            return step;
        };
        let actual: Attributes = existing
            .iter()
            .filter(|(key, _)| !self.is_computed(address, key))
            .map(|(k, v)| (k.clone(), v.clone()))
            .collect();
        let keys: BTreeSet<&String> = values.keys().chain(actual.keys()).collect();
        let mut rows = Vec::new();
        let mut forced = false;
        for key in keys {
            let before = actual.get(key);
            let after = values.get(key);
            if before == after {
                continue;
            }
            let mut line = match (before, after) {
                (None, Some(new)) => row(&["+", key, new]),
                (Some(old), None) => row(&["-", key, old]),
                (Some(old), Some(new)) => row(&["~", key, old, new]),
                (None, None) => continue,
            };
            if self.forces.contains(&(kind_of(address).to_string(), key.clone())) {
                line.push(FORCES.to_string());
                forced = true;
            }
            rows.push(line);
        }
        if rows.is_empty() {
            return Step::new("no-op", address, "", 0);
        }
        if !forced {
            let mut step = Step::new("update", address, "", 0);
            step.diff = rows;
            return step;
        }
        for name in &computed {
            rows.push(match existing.get(name) {
                Some(was) => row(&["~", name, was, UNKNOWN]),
                None => row(&["+", name, UNKNOWN]),
            });
        }
        rows.sort_by(|a, b| a[1].cmp(&b[1]));
        let mut step = Step::new("create", address, "replace", 0);
        step.diff = rows;
        step
    }

    /// Kahn's algorithm, always taking the smallest ready step by rank, then address.
    fn order(steps: &[Step]) -> Vec<usize> {
        let mut waiting: Vec<usize> = steps.iter().map(|step| step.before.len()).collect();
        let mut ready: BinaryHeap<Reverse<(u8, &str, usize)>> = steps
            .iter()
            .enumerate()
            .filter(|(index, _)| waiting[*index] == 0)
            .map(|(index, step)| Reverse((step.rank, step.address.as_str(), index)))
            .collect();
        let mut order = Vec::new();
        while let Some(Reverse((_, _, index))) = ready.pop() {
            order.push(index);
            for &later in &steps[index].after {
                waiting[later] -= 1;
                if waiting[later] == 0 {
                    ready.push(Reverse((steps[later].rank, steps[later].address.as_str(), later)));
                }
            }
        }
        order
    }

    // Applying
    fn live(&self, address: &str, key: &str) -> String {
        let value = &self.desired[address][key];
        match reference(value) {
            None => value.clone(),
            Some((other, wanted)) if self.is_computed(&other, &wanted) => self.current[&other][&wanted].clone(),
            Some((other, wanted)) => self.live(&other, &wanted),
        }
    }

    fn resolved_now(&self, address: &str) -> Attributes {
        self.desired[address].keys().map(|key| (key.clone(), self.live(address, key))).collect()
    }

    fn perform(&mut self, step: &Step, assigned: &HashMap<(String, String), String>) {
        let address = step.address.clone();
        let needs: BTreeSet<String> = self
            .desired
            .get(&address)
            .map(|attributes| attributes.values().filter_map(|v| reference(v).map(|r| r.0)).collect())
            .unwrap_or_default();
        match step.verb {
            "create" => {
                if step.tag == "replace" {
                    if let Some(existing) = self.current.remove(&address) {
                        self.old.insert(address.clone(), existing);
                        let links = self.deps.remove(&address).unwrap_or_default();
                        self.old_deps.insert(address.clone(), links);
                    }
                }
                let mut made = self.resolved_now(&address);
                for name in self.computed_of(&address) {
                    let value = assigned.get(&(address.clone(), name.clone())).cloned().unwrap_or_default();
                    made.insert(name, value);
                }
                self.current.insert(address.clone(), made);
                self.deps.insert(address, needs);
            }
            "update" => {
                let mut made = self.resolved_now(&address);
                for (key, value) in &self.current[&address] {
                    if self.is_computed(&address, key) {
                        made.insert(key.clone(), value.clone());
                    }
                }
                self.current.insert(address.clone(), made);
                self.deps.insert(address, needs);
            }
            "delete" => {
                if step.tag == "old" || step.mode == Mode::CreateFirst {
                    self.old.remove(&address);
                    self.old_deps.remove(&address);
                } else {
                    self.current.remove(&address);
                    self.deps.remove(&address);
                }
            }
            _ => {}
        }
    }
}
