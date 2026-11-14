use std::collections::{HashMap, HashSet};

type Sets = HashMap<String, HashSet<String>>;

/// Every concept keeps the set of its parents and the set of its children. Questions about
/// ancestors, descendants, cycles and expansion are breadth-first walks over those sets, so
/// nothing recurses and a chain of 10^5 concepts is as safe as a flat list. Retired concepts keep
/// their id and their labels; a table of replacements sends them to a live concept, and every
/// method that takes an id first follows that table.
pub struct Taxonomy {
    label: HashMap<String, String>,
    up: Sets,
    down: Sets,
    alts: HashMap<String, Vec<String>>,
    index: Sets,
    gone: HashMap<String, String>,
    same: Sets,
}

impl Taxonomy {
    pub fn new() -> Self {
        Taxonomy {
            label: HashMap::new(),
            up: HashMap::new(),
            down: HashMap::new(),
            alts: HashMap::new(),
            index: HashMap::new(),
            gone: HashMap::new(),
            same: HashMap::new(),
        }
    }

    // Level 1
    pub fn add_concept(&mut self, concept: String, label: String, parents: Vec<String>) -> String {
        if self.label.contains_key(&concept) {
            return "duplicate".to_string();
        }
        if parents.contains(&concept) {
            return "cycle".to_string();
        }
        if parents.iter().any(|parent| !self.label.contains_key(parent)) {
            return "unknown-broader".to_string();
        }
        let resolved: HashSet<String> = parents.iter().map(|parent| self.follow(parent)).collect();
        if resolved.iter().any(|parent| scheme_of(parent) != scheme_of(&concept)) {
            return "cross-scheme".to_string();
        }
        for parent in &resolved {
            self.down.get_mut(parent).unwrap().insert(concept.clone());
        }
        self.label.insert(concept.clone(), label.clone());
        self.up.insert(concept.clone(), resolved);
        self.down.insert(concept.clone(), HashSet::new());
        self.alts.insert(concept.clone(), Vec::new());
        self.same.insert(concept.clone(), HashSet::new());
        self.index_label(&concept, &label);
        "ok".to_string()
    }

    pub fn add_broader(&mut self, narrower: String, broader: String) -> String {
        let child = self.follow(&narrower);
        let parent = self.follow(&broader);
        if !self.label.contains_key(&child) || !self.label.contains_key(&parent) {
            return "unknown-concept".to_string();
        }
        if scheme_of(&child) != scheme_of(&parent) {
            return "cross-scheme".to_string();
        }
        if child == parent || reach(&parent, &self.up).contains(&child) {
            return "cycle".to_string();
        }
        self.up.get_mut(&child).unwrap().insert(parent.clone());
        self.down.get_mut(&parent).unwrap().insert(child);
        "ok".to_string()
    }

    pub fn pref_label(&mut self, concept: String) -> String {
        let id = self.follow(&concept);
        self.label.get(&id).cloned().unwrap_or_default()
    }

    pub fn broader(&mut self, concept: String) -> Vec<String> {
        let id = self.follow(&concept);
        self.up.get(&id).map(sorted).unwrap_or_default()
    }

    pub fn narrower(&mut self, concept: String) -> Vec<String> {
        let id = self.follow(&concept);
        self.down.get(&id).map(sorted).unwrap_or_default()
    }

    pub fn ancestors(&mut self, concept: String) -> Vec<String> {
        let id = self.follow(&concept);
        nearest_first(&id, &self.up)
    }

    pub fn descendants(&mut self, concept: String) -> Vec<String> {
        let id = self.follow(&concept);
        nearest_first(&id, &self.down)
    }

    pub fn roots(&mut self) -> Vec<String> {
        let mut found: Vec<String> = self
            .up
            .iter()
            .filter(|(concept, parents)| !self.gone.contains_key(*concept) && parents.is_empty())
            .map(|(concept, _)| concept.clone())
            .collect();
        found.sort();
        found
    }

    // Level 2
    pub fn lowest_common_ancestors(&mut self, first: String, second: String) -> Vec<String> {
        let a = self.follow(&first);
        let b = self.follow(&second);
        if !self.label.contains_key(&a) || !self.label.contains_key(&b) {
            return Vec::new();
        }
        let above_b = reach(&b, &self.up);
        let common: HashSet<String> =
            reach(&a, &self.up).into_iter().filter(|concept| above_b.contains(concept)).collect();
        let mut lowest: Vec<String> = common
            .iter()
            .filter(|concept| !self.down[*concept].iter().any(|kid| common.contains(kid)))
            .cloned()
            .collect();
        lowest.sort();
        lowest
    }

    // Level 3
    pub fn add_alt_label(&mut self, concept: String, label: String) -> String {
        let id = self.follow(&concept);
        if !self.label.contains_key(&id) {
            return "unknown-concept".to_string();
        }
        let key = normalize(&label);
        if key.is_empty() {
            return "empty-label".to_string();
        }
        let own = std::iter::once(&self.label[&id]).chain(self.alts[&id].iter());
        if own.into_iter().any(|text| normalize(text) == key) {
            return "duplicate".to_string();
        }
        self.index_label(&id, &label);
        self.alts.get_mut(&id).unwrap().push(label);
        "ok".to_string()
    }

    pub fn alt_labels(&mut self, concept: String) -> Vec<String> {
        let id = self.follow(&concept);
        self.alts.get(&id).cloned().unwrap_or_default()
    }

    pub fn find_by_label(&mut self, label: String) -> Vec<String> {
        sorted(&self.matching(&label))
    }

    pub fn expand(&mut self, labels: Vec<String>) -> Vec<String> {
        let mut seen: HashSet<String> = HashSet::new();
        let mut queue: Vec<String> = Vec::new();
        for label in &labels {
            for concept in self.matching(label) {
                if seen.insert(concept.clone()) {
                    queue.push(concept);
                }
            }
        }
        let mut next = 0;
        while next < queue.len() {
            let current = queue[next].clone();
            for kid in &self.down[&current] {
                if seen.insert(kid.clone()) {
                    queue.push(kid.clone());
                }
            }
            next += 1;
        }
        sorted(&seen)
    }

    // Level 4
    pub fn rename(&mut self, concept: String, label: String) -> String {
        let id = self.follow(&concept);
        if !self.label.contains_key(&id) {
            return "unknown-concept".to_string();
        }
        let old = self.label[&id].clone();
        let key = normalize(&label);
        let mut kept: Vec<String> =
            self.alts[&id].iter().filter(|text| normalize(text) != key).cloned().collect();
        let old_key = normalize(&old);
        if !old_key.is_empty() && old_key != key {
            kept.push(old);
        }
        self.alts.insert(id.clone(), kept);
        self.index_label(&id, &label);
        self.label.insert(id, label);
        "ok".to_string()
    }

    pub fn remove_broader(&mut self, narrower: String, broader: String) -> String {
        let child = self.follow(&narrower);
        let parent = self.follow(&broader);
        if !self.label.contains_key(&child) || !self.label.contains_key(&parent) {
            return "unknown-concept".to_string();
        }
        if !self.up[&child].contains(&parent) {
            return "no-link".to_string();
        }
        self.up.get_mut(&child).unwrap().remove(&parent);
        self.down.get_mut(&parent).unwrap().remove(&child);
        "ok".to_string()
    }

    pub fn deprecate(&mut self, concept: String, replacement: String) -> String {
        if !self.label.contains_key(&concept) || !self.label.contains_key(&replacement) {
            return "unknown-concept".to_string();
        }
        if self.gone.contains_key(&concept) {
            return "deprecated".to_string();
        }
        let target = self.follow(&replacement);
        if target == concept {
            return "same-concept".to_string();
        }
        if scheme_of(&target) != scheme_of(&concept) {
            return "cross-scheme".to_string();
        }
        if !self.down[&concept].is_empty() {
            return "has-narrower".to_string();
        }
        let parents = std::mem::take(self.up.get_mut(&concept).unwrap());
        for parent in parents {
            self.down.get_mut(&parent).unwrap().remove(&concept);
        }
        let partners = std::mem::take(self.same.get_mut(&concept).unwrap());
        for partner in partners {
            self.same.get_mut(&partner).unwrap().remove(&concept);
            self.same.get_mut(&partner).unwrap().insert(target.clone());
            self.same.get_mut(&target).unwrap().insert(partner);
        }
        self.gone.insert(concept, target);
        "ok".to_string()
    }

    pub fn resolve(&mut self, concept: String) -> String {
        let id = self.follow(&concept);
        if self.label.contains_key(&id) {
            id
        } else {
            String::new()
        }
    }

    pub fn add_exact_match(&mut self, first: String, second: String) -> String {
        let a = self.follow(&first);
        let b = self.follow(&second);
        if !self.label.contains_key(&a) || !self.label.contains_key(&b) {
            return "unknown-concept".to_string();
        }
        if scheme_of(&a) == scheme_of(&b) {
            return "same-scheme".to_string();
        }
        self.same.get_mut(&a).unwrap().insert(b.clone());
        self.same.get_mut(&b).unwrap().insert(a);
        "ok".to_string()
    }

    pub fn translate(&mut self, concepts: Vec<String>, scheme: String) -> Vec<String> {
        let mut found: HashSet<String> = HashSet::new();
        for concept in self.known(&concepts) {
            found.extend(self.targets(&concept, &scheme));
        }
        sorted(&found)
    }

    pub fn unmapped(&mut self, concepts: Vec<String>, scheme: String) -> Vec<String> {
        let known = self.known(&concepts);
        known.into_iter().filter(|concept| self.targets(concept, &scheme).is_empty()).collect()
    }

    // Helpers
    fn follow(&mut self, concept: &str) -> String {
        let mut current = concept.to_string();
        while let Some(next) = self.gone.get(&current) {
            current = next.clone();
        }
        if current != concept {
            self.gone.insert(concept.to_string(), current.clone());
        }
        current
    }

    fn known(&mut self, concepts: &[String]) -> Vec<String> {
        let mut resolved: HashSet<String> = HashSet::new();
        for concept in concepts {
            let id = self.follow(concept);
            if self.label.contains_key(&id) {
                resolved.insert(id);
            }
        }
        sorted(&resolved)
    }

    fn targets(&self, concept: &str, scheme: &str) -> Vec<String> {
        if scheme_of(concept) == scheme {
            return vec![concept.to_string()];
        }
        self.same[concept].iter().filter(|partner| scheme_of(partner) == scheme).cloned().collect()
    }

    fn index_label(&mut self, concept: &str, label: &str) {
        let key = normalize(label);
        if !key.is_empty() {
            self.index.entry(key).or_default().insert(concept.to_string());
        }
    }

    fn matching(&mut self, label: &str) -> HashSet<String> {
        let key = normalize(label);
        let holders: Vec<String> = match self.index.get(&key) {
            Some(holders) if !key.is_empty() => holders.iter().cloned().collect(),
            _ => Vec::new(),
        };
        holders.iter().map(|concept| self.follow(concept)).collect()
    }
}

fn scheme_of(concept: &str) -> &str {
    concept.find(':').map_or("", |colon| &concept[..colon])
}

/// Trim the spaces at both ends, turn each run of spaces into one, lower-case A to Z.
fn normalize(label: &str) -> String {
    let parts: Vec<&str> = label.split(' ').filter(|part| !part.is_empty()).collect();
    parts.join(" ").to_ascii_lowercase()
}

fn sorted(items: &HashSet<String>) -> Vec<String> {
    let mut list: Vec<String> = items.iter().cloned().collect();
    list.sort();
    list
}

/// The concept itself and everything above (or below) it.
fn reach(start: &str, edges: &Sets) -> HashSet<String> {
    let mut seen: HashSet<String> = HashSet::new();
    seen.insert(start.to_string());
    let mut queue = vec![start.to_string()];
    let mut next = 0;
    while next < queue.len() {
        let current = queue[next].clone();
        for neighbour in &edges[&current] {
            if seen.insert(neighbour.clone()) {
                queue.push(neighbour.clone());
            }
        }
        next += 1;
    }
    seen
}

fn nearest_first(start: &str, edges: &Sets) -> Vec<String> {
    let mut found: Vec<String> = Vec::new();
    if !edges.contains_key(start) {
        return found;
    }
    let mut seen: HashSet<String> = HashSet::new();
    seen.insert(start.to_string());
    let mut level = vec![start.to_string()];
    while !level.is_empty() {
        let mut following: HashSet<String> = HashSet::new();
        for current in &level {
            for neighbour in &edges[current] {
                if !seen.contains(neighbour) {
                    following.insert(neighbour.clone());
                }
            }
        }
        seen.extend(following.iter().cloned());
        level = sorted(&following);
        found.extend(level.iter().cloned());
    }
    found
}
