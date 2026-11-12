use chrono::NaiveDate;
use std::collections::{BTreeMap, HashMap, HashSet};

// Manifests are kept as trees by id, rules as data in the order they were added. A check expands
// each rule's pointer pattern over each manifest and tests the concrete pointers; a service's port
// rule looks up the workloads its selector picks. Exceptions, severities, modes and fixes are
// applied on top of the same list of violations.

const SEVERITIES: [&str; 4] = ["critical", "high", "medium", "low"];

struct Node {
    kind: String,
    text: String,
    members: HashMap<String, Node>,
    items: Vec<Node>,
}

impl Node {
    fn new(kind: &str, text: &str) -> Self {
        Node { kind: kind.to_string(), text: text.to_string(), members: HashMap::new(), items: Vec::new() }
    }
}

struct Rule {
    check: &'static str,
    kind: String,
    pointer: String,
    tags: Vec<String>,
    severity: String,
    mode: String,
    fix: String,
}

#[derive(PartialEq, Eq, Hash, Clone, PartialOrd, Ord)]
struct Key {
    manifest_id: String,
    rule_id: String,
}

struct Allowance {
    reason: String,
    expires: NaiveDate,
}

struct Violation {
    manifest_id: String,
    rule_id: String,
    pointer: String,
}

pub struct PolicyChecker {
    manifests: BTreeMap<String, Node>,
    rule_ids: Vec<String>,
    rules: HashMap<String, Rule>,
    allowances: HashMap<Key, Allowance>,
}

impl PolicyChecker {
    pub fn new() -> Self {
        PolicyChecker {
            manifests: BTreeMap::new(),
            rule_ids: Vec::new(),
            rules: HashMap::new(),
            allowances: HashMap::new(),
        }
    }

    // Level 1
    pub fn add_manifest(&mut self, rows: Vec<Vec<String>>) -> bool {
        let root = decode(&rows);
        let id = format!("{}/{}", text_of(&root, "/kind").unwrap_or(""), text_of(&root, "/name").unwrap_or(""));
        self.manifests.insert(id, root).is_none()
    }

    pub fn require_field(&mut self, rule_id: String, kind: String, pointer: String) -> bool {
        self.define(rule_id, "field", kind, pointer, Vec::new())
    }

    pub fn forbid_tags(&mut self, rule_id: String, kind: String, pointer: String, tags: Vec<String>) -> bool {
        self.define(rule_id, "tags", kind, pointer, tags)
    }

    pub fn check(&mut self) -> Vec<Vec<String>> {
        self.violations().into_iter().map(|v| vec![v.manifest_id, v.rule_id, v.pointer]).collect()
    }

    // Level 2
    pub fn require_port_targets(&mut self, rule_id: String) -> bool {
        self.define(rule_id, "ports", "service".to_string(), String::new(), Vec::new())
    }

    // Level 3
    pub fn allow(&mut self, rule_id: String, manifest_id: String, reason: String, expires: NaiveDate) -> bool {
        self.allowances.insert(Key { manifest_id, rule_id }, Allowance { reason, expires }).is_none()
    }

    pub fn check_on(&mut self, today: NaiveDate) -> Vec<Vec<String>> {
        let mut rows = Vec::new();
        for v in self.violations() {
            let (outcome, note) = match self.active(&v.rule_id, &v.manifest_id, today) {
                Some(allowance) => ("excepted", allowance.reason.clone()),
                None => ("violation", String::new()),
            };
            rows.push(vec![v.manifest_id, v.rule_id, v.pointer, outcome.to_string(), note]);
        }
        let mut expired: Vec<(&Key, &Allowance)> =
            self.allowances.iter().filter(|(_, allowance)| today > allowance.expires).collect();
        expired.sort_by(|a, b| a.0.cmp(b.0));
        for (key, allowance) in expired {
            rows.push(vec![
                key.manifest_id.clone(),
                key.rule_id.clone(),
                String::new(),
                "expired".to_string(),
                allowance.expires.format("%Y-%m-%d").to_string(),
            ]);
        }
        rows
    }

    // Level 4
    pub fn configure(&mut self, rule_id: String, severity: String, mode: String, fix: String) -> bool {
        match self.rules.get_mut(&rule_id) {
            Some(rule) => {
                rule.severity = severity;
                rule.mode = mode;
                rule.fix = fix;
                true
            }
            None => false,
        }
    }

    pub fn findings(&mut self, today: NaiveDate) -> Vec<Vec<String>> {
        let mut rows = Vec::new();
        for v in self.violations() {
            if self.active(&v.rule_id, &v.manifest_id, today).is_some() {
                continue;
            }
            let rule = &self.rules[&v.rule_id];
            let (op, value) = fix_for(rule, &self.manifests[&v.manifest_id], &v.pointer);
            rows.push(vec![v.manifest_id, v.rule_id, v.pointer, rule.severity.clone(), rule.mode.clone(), op, value]);
        }
        rows.sort_by_key(|row| SEVERITIES.iter().position(|s| *s == row[3]));
        rows
    }

    pub fn decide(&mut self, today: NaiveDate) -> Vec<Vec<String>> {
        let found = self.findings(today);
        self.manifests
            .keys()
            .map(|id| {
                let deny = found.iter().filter(|row| &row[0] == id && row[4] == "deny").count();
                let warn = found.iter().filter(|row| &row[0] == id && row[4] == "warn").count();
                let decision = if deny > 0 { "reject" } else { "admit" };
                vec![id.clone(), decision.to_string(), deny.to_string(), warn.to_string()]
            })
            .collect()
    }

    // Rules
    fn define(&mut self, rule_id: String, check: &'static str, kind: String, pointer: String, tags: Vec<String>) -> bool {
        if let Some(rule) = self.rules.get_mut(&rule_id) {
            rule.check = check;
            rule.kind = kind;
            rule.pointer = pointer;
            rule.tags = tags;
            return false;
        }
        self.rule_ids.push(rule_id.clone());
        let rule = Rule {
            check,
            kind,
            pointer,
            tags,
            severity: "medium".to_string(),
            mode: "deny".to_string(),
            fix: String::new(),
        };
        self.rules.insert(rule_id, rule);
        true
    }

    fn violations(&self) -> Vec<Violation> {
        let mut found = Vec::new();
        for (manifest_id, root) in &self.manifests {
            let kind = text_of(root, "/kind").unwrap_or("");
            for rule_id in &self.rule_ids {
                let rule = &self.rules[rule_id];
                if rule.kind != "*" && rule.kind != kind {
                    continue;
                }
                for pointer in self.broken(rule, root) {
                    found.push(Violation { manifest_id: manifest_id.clone(), rule_id: rule_id.clone(), pointer });
                }
            }
        }
        found
    }

    fn broken(&self, rule: &Rule, root: &Node) -> Vec<String> {
        if rule.check == "ports" {
            return self.unserved_ports(root);
        }
        expand(root, &rule.pointer)
            .into_iter()
            .filter(|pointer| match resolve(root, pointer) {
                None => rule.check == "field",
                Some(node) if rule.check == "field" => node.kind == "null" || (node.kind == "string" && node.text.is_empty()),
                Some(node) if node.kind == "string" && !node.text.contains('@') => match tag_split(&node.text).1 {
                    None => true,
                    Some(tag) => rule.tags.iter().any(|t| t == tag),
                },
                Some(_) => false,
            })
            .collect()
    }

    fn unserved_ports(&self, service: &Node) -> Vec<String> {
        let selector = match resolve(service, "/selector") {
            Some(selector) if selector.kind == "object" && !selector.members.is_empty() => selector,
            _ => return vec!["/selector".to_string()],
        };
        let served: Vec<HashSet<&str>> = self
            .manifests
            .values()
            .filter(|root| text_of(root, "/kind") == Some("workload") && selects(selector, root))
            .map(|root| {
                expand(root, "/containers/*/ports/*/name").iter().filter_map(|pointer| text_of(root, pointer)).collect()
            })
            .collect();
        if served.is_empty() {
            return vec!["/selector".to_string()];
        }
        expand(service, "/ports/*")
            .into_iter()
            .filter(|pointer| match text_of(service, &format!("{}/target", pointer)) {
                Some(target) => served.iter().any(|names| !names.contains(target)),
                None => false,
            })
            .map(|pointer| format!("{}/target", pointer))
            .collect()
    }

    fn active(&self, rule_id: &str, manifest_id: &str, today: NaiveDate) -> Option<&Allowance> {
        let key = Key { manifest_id: manifest_id.to_string(), rule_id: rule_id.to_string() };
        self.allowances.get(&key).filter(|allowance| today <= allowance.expires)
    }
}

fn selects(selector: &Node, workload: &Node) -> bool {
    selector.members.iter().all(|(key, value)| {
        value.kind == "string" && text_of(workload, &format!("/labels/{}", key)) == Some(value.text.as_str())
    })
}

fn fix_for(rule: &Rule, root: &Node, pointer: &str) -> (String, String) {
    let none = (String::new(), String::new());
    if rule.fix.is_empty() || rule.check == "ports" {
        return none;
    }
    let node = resolve(root, pointer);
    if rule.check == "tags" {
        let image = &node.unwrap().text;
        return ("replace".to_string(), format!("{}:{}", tag_split(image).0, rule.fix));
    }
    if node.is_some() {
        return ("replace".to_string(), rule.fix.clone());
    }
    match resolve(root, &pointer[..pointer.rfind('/').unwrap()]) {
        Some(parent) if parent.kind == "object" => ("add".to_string(), rule.fix.clone()),
        _ => none,
    }
}

// Documents

fn decode(rows: &[Vec<String>]) -> Node {
    let mut root = Node::new("object", "");
    for row in rows {
        let segments: Vec<&str> = row[0].split('/').skip(1).collect();
        let (last, parents) = segments.split_last().unwrap();
        let mut parent = &mut root;
        for segment in parents {
            parent = if parent.kind == "object" {
                parent.members.get_mut(*segment).unwrap()
            } else {
                let index: usize = segment.parse().unwrap();
                &mut parent.items[index]
            };
        }
        let node = Node::new(&row[1], &row[2]);
        if parent.kind == "object" {
            parent.members.insert(last.to_string(), node);
        } else {
            parent.items.push(node);
        }
    }
    root
}

fn resolve<'a>(root: &'a Node, pointer: &str) -> Option<&'a Node> {
    let mut node = root;
    if pointer.is_empty() {
        return Some(node);
    }
    for segment in pointer.split('/').skip(1) {
        node = match node.kind.as_str() {
            "object" => node.members.get(segment)?,
            "array" if !segment.is_empty() && segment.bytes().all(|b| b.is_ascii_digit()) => {
                node.items.get(segment.parse::<usize>().ok()?)?
            }
            _ => return None,
        };
    }
    Some(node)
}

fn expand(root: &Node, pattern: &str) -> Vec<String> {
    let mut pointers = vec![String::new()];
    for segment in pattern.split('/').skip(1) {
        let mut next = Vec::new();
        for pointer in &pointers {
            if segment != "*" {
                next.push(format!("{}/{}", pointer, segment));
                continue;
            }
            if let Some(node) = resolve(root, pointer) {
                if node.kind == "array" {
                    next.extend((0..node.items.len()).map(|index| format!("{}/{}", pointer, index)));
                }
            }
        }
        pointers = next;
    }
    pointers
}

/// The repository and the tag of an image reference; the tag is None when there is none.
fn tag_split(image: &str) -> (&str, Option<&str>) {
    match (image.rfind(':'), image.rfind('/')) {
        (Some(colon), slash) if slash.map_or(true, |s| colon > s) => (&image[..colon], Some(&image[colon + 1..])),
        _ => (image, None),
    }
}

fn text_of<'a>(root: &'a Node, pointer: &str) -> Option<&'a str> {
    resolve(root, pointer).filter(|node| node.kind == "string").map(|node| node.text.as_str())
}
