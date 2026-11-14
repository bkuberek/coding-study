use std::cmp::Ordering;
use std::collections::{BTreeSet, HashMap, HashSet};

#[derive(Clone, Debug)]
struct Version {
    major: u32,
    minor: u32,
    patch: u32,
    pre: Vec<String>,
}

impl Version {
    fn text(&self) -> String {
        let core = format!("{}.{}.{}", self.major, self.minor, self.patch);
        if self.pre.is_empty() {
            core
        } else {
            format!("{}-{}", core, self.pre.join("."))
        }
    }
}

#[derive(Clone)]
struct Comparison {
    operator: &'static str,
    bound: Version,
}

type Sets = Vec<Vec<Comparison>>;

struct Dependency {
    name: String,
    text: String,
    sets: Sets,
    edge: usize,
}

struct Release {
    name: String,
    text: String,
    version: Version,
    dependencies: Vec<Dependency>,
}

struct Root {
    name: String,
    text: String,
    sets: Sets,
}

/// Versions are parsed once into numbers and identifiers; ranges are expanded into comparator
/// sets. Resolving is a depth-first search that picks the smallest open package name and tries its
/// versions from the highest down, undoing a choice when the rest cannot be resolved. Explaining a
/// failure reruns the search with constraints left out, one at a time.
pub struct SemverResolver {
    releases: HashMap<String, Vec<usize>>,
    published: Vec<Release>,
    edges: usize,
}

const OPERATORS: [&str; 7] = [">=", "<=", ">", "<", "=", "^", "~"];

fn is_number(text: &str) -> bool {
    !text.is_empty()
        && text.bytes().all(|b| b.is_ascii_digit())
        && (text == "0" || !text.starts_with('0'))
}

fn is_identifier(text: &str) -> bool {
    !text.is_empty() && text.bytes().all(|b| b.is_ascii_alphanumeric() || b == b'-')
}

fn is_digits(text: &str) -> bool {
    !text.is_empty() && text.bytes().all(|b| b.is_ascii_digit())
}

fn is_wildcard(text: &str) -> bool {
    text == "x" || text == "X" || text == "*"
}

fn parse(text: &str) -> Option<Version> {
    let (rest, build) = match text.split_once('+') {
        Some((rest, build)) => (rest, Some(build)),
        None => (text, None),
    };
    if let Some(build) = build {
        if !build.split('.').all(is_identifier) {
            return None;
        }
    }
    let (core, pre) = match rest.split_once('-') {
        Some((core, pre)) => (core, Some(pre)),
        None => (rest, None),
    };
    let numbers: Vec<&str> = core.split('.').collect();
    if numbers.len() != 3 || !numbers.iter().all(|n| is_number(n)) {
        return None;
    }
    let parts: Vec<String> = match pre {
        Some(pre) => pre.split('.').map(str::to_string).collect(),
        None => Vec::new(),
    };
    if parts
        .iter()
        .any(|p| !is_identifier(p) || (is_digits(p) && !is_number(p)))
    {
        return None;
    }
    Some(Version {
        major: numbers[0].parse().ok()?,
        minor: numbers[1].parse().ok()?,
        patch: numbers[2].parse().ok()?,
        pre: parts,
    })
}

fn compare_identifiers(a: &str, b: &str) -> Ordering {
    match (is_digits(a), is_digits(b)) {
        (true, true) => a.parse::<u32>().unwrap().cmp(&b.parse::<u32>().unwrap()),
        (true, false) => Ordering::Less,
        (false, true) => Ordering::Greater,
        (false, false) => a.cmp(b),
    }
}

fn order(a: &Version, b: &Version) -> Ordering {
    let core = (a.major, a.minor, a.patch).cmp(&(b.major, b.minor, b.patch));
    if core != Ordering::Equal {
        return core;
    }
    // A release (no pre-release) sorts after every pre-release of its core.
    if a.pre.is_empty() || b.pre.is_empty() {
        return b.pre.len().cmp(&a.pre.len());
    }
    for (x, y) in a.pre.iter().zip(b.pre.iter()) {
        let found = compare_identifiers(x, y);
        if found != Ordering::Equal {
            return found;
        }
    }
    a.pre.len().cmp(&b.pre.len())
}

fn sign(ordering: Ordering) -> i32 {
    match ordering {
        Ordering::Less => -1,
        Ordering::Equal => 0,
        Ordering::Greater => 1,
    }
}

fn below(major: u32, minor: u32, patch: u32) -> Comparison {
    Comparison {
        operator: "<",
        bound: Version {
            major,
            minor,
            patch,
            pre: vec!["0".to_string()],
        },
    }
}

fn floor_of(numbers: &[u32]) -> Version {
    let at = |i: usize| numbers.get(i).copied().unwrap_or(0);
    Version {
        major: at(0),
        minor: at(1),
        patch: at(2),
        pre: Vec::new(),
    }
}

/// The leading numbers of a pattern such as `1`, `1.x` or `1.2.*`.
fn partial(pattern: &str) -> Option<Vec<u32>> {
    let parts: Vec<&str> = pattern.split('.').collect();
    if parts.len() > 3 {
        return None;
    }
    let mut numbers = Vec::new();
    for (i, part) in parts.iter().enumerate() {
        if is_wildcard(part) {
            return if parts[i..].iter().all(|p| is_wildcard(p)) {
                Some(numbers)
            } else {
                None
            };
        }
        if !is_number(part) {
            return None;
        }
        numbers.push(part.parse().ok()?);
    }
    if numbers.len() < 3 {
        Some(numbers)
    } else {
        None
    }
}

fn wildcard_range(numbers: &[u32]) -> Vec<Comparison> {
    let low = Comparison {
        operator: ">=",
        bound: floor_of(numbers),
    };
    match numbers.len() {
        0 => vec![low],
        1 => vec![low, below(numbers[0] + 1, 0, 0)],
        _ => vec![low, below(numbers[0], numbers[1] + 1, 0)],
    }
}

fn caret_upper(numbers: &[u32]) -> Comparison {
    let floor = floor_of(numbers);
    if floor.major > 0 || numbers.len() == 1 {
        below(floor.major + 1, 0, 0)
    } else if floor.minor > 0 || numbers.len() == 2 {
        below(0, floor.minor + 1, 0)
    } else {
        below(0, 0, floor.patch + 1)
    }
}

fn expand_term(term: &str) -> Option<Vec<Comparison>> {
    let operator = OPERATORS
        .iter()
        .copied()
        .find(|op| term.starts_with(op))
        .unwrap_or("");
    let pattern = &term[operator.len()..];
    if let Some(full) = parse(pattern) {
        let low = Comparison {
            operator: ">=",
            bound: full.clone(),
        };
        return Some(match operator {
            "" | "=" => vec![Comparison {
                operator: "=",
                bound: full,
            }],
            "~" => vec![low, below(full.major, full.minor + 1, 0)],
            "^" => vec![low, caret_upper(&[full.major, full.minor, full.patch])],
            _ => vec![Comparison {
                operator,
                bound: full,
            }],
        });
    }
    let numbers = partial(pattern)?;
    if !["", "=", "^", "~"].contains(&operator) {
        return None;
    }
    if operator == "^" && !numbers.is_empty() {
        return Some(vec![
            Comparison {
                operator: ">=",
                bound: floor_of(&numbers),
            },
            caret_upper(&numbers),
        ]);
    }
    Some(wildcard_range(&numbers))
}

fn expand(text: &str) -> Option<Sets> {
    let mut sets = Vec::new();
    for piece in text.split("||") {
        let mut set = Vec::new();
        for term in piece.split(' ').filter(|t| !t.is_empty()) {
            set.extend(expand_term(term)?);
        }
        if set.is_empty() {
            return None;
        }
        sets.push(set);
    }
    Some(sets)
}

fn holds(version: &Version, comparison: &Comparison) -> bool {
    let found = order(version, &comparison.bound);
    match comparison.operator {
        "=" => found == Ordering::Equal,
        ">" => found == Ordering::Greater,
        ">=" => found != Ordering::Less,
        "<" => found == Ordering::Less,
        _ => found != Ordering::Greater,
    }
}

fn in_set(version: &Version, set: &[Comparison]) -> bool {
    if !set.iter().all(|c| holds(version, c)) {
        return false;
    }
    version.pre.is_empty()
        || set.iter().any(|c| {
            let b = &c.bound;
            !b.pre.is_empty()
                && (b.major, b.minor, b.patch) == (version.major, version.minor, version.patch)
        })
}

fn in_range(version: &Version, sets: &Sets) -> bool {
    sets.iter().any(|set| in_set(version, set))
}

/// What a search holds in force: the root ranges, the dependencies left out and the preferred
/// version of each package.
struct Search<'a> {
    resolver: &'a SemverResolver,
    roots: Vec<&'a Root>,
    dropped_edges: &'a HashSet<usize>,
    preferred: &'a HashMap<String, String>,
    chosen: HashMap<String, usize>,
}

impl<'a> Search<'a> {
    fn in_force(&self, release: usize) -> impl Iterator<Item = &'a Dependency> + '_ {
        self.resolver.published[release]
            .dependencies
            .iter()
            .filter(move |d| !self.dropped_edges.contains(&d.edge))
    }

    fn acceptable(&self, release: usize, ranges: &[&Sets]) -> bool {
        let version = &self.resolver.published[release].version;
        if !ranges.iter().all(|sets| in_range(version, sets)) {
            return false;
        }
        self.in_force(release)
            .all(|d| match self.chosen.get(&d.name) {
                Some(&other) => in_range(&self.resolver.published[other].version, &d.sets),
                None => true,
            })
    }

    fn solve(&mut self) -> bool {
        let mut needed: BTreeSet<String> = self.roots.iter().map(|r| r.name.clone()).collect();
        for &release in self.chosen.values() {
            needed.extend(self.in_force(release).map(|d| d.name.clone()));
        }
        let name = match needed.into_iter().find(|n| !self.chosen.contains_key(n)) {
            Some(name) => name,
            None => return true,
        };
        let mut ranges: Vec<&'a Sets> = self
            .roots
            .iter()
            .copied()
            .filter(|r| r.name == name)
            .map(|r| &r.sets)
            .collect();
        for &release in self.chosen.values() {
            ranges.extend(
                self.in_force(release)
                    .filter(|d| d.name == name)
                    .map(|d| &d.sets),
            );
        }
        let resolver = self.resolver;
        let preferred: &'a HashMap<String, String> = self.preferred;
        let all = resolver.releases.get(&name).cloned().unwrap_or_default();
        let wanted = preferred.get(&name);
        let mut tries: Vec<usize> = all
            .iter()
            .copied()
            .filter(|&r| Some(&resolver.published[r].text) == wanted)
            .collect();
        tries.extend(
            all.iter()
                .copied()
                .filter(|&r| Some(&resolver.published[r].text) != wanted),
        );
        for release in tries {
            if !self.acceptable(release, &ranges) {
                continue;
            }
            self.chosen.insert(name.clone(), release);
            if self.solve() {
                return true;
            }
            self.chosen.remove(&name);
        }
        false
    }
}

impl SemverResolver {
    pub fn new() -> Self {
        SemverResolver {
            releases: HashMap::new(),
            published: Vec::new(),
            edges: 0,
        }
    }

    // Level 1
    pub fn is_valid(&mut self, version: String) -> bool {
        parse(&version).is_some()
    }

    pub fn compare(&mut self, first: String, second: String) -> i32 {
        sign(order(&parse(&first).unwrap(), &parse(&second).unwrap()))
    }

    pub fn sort_versions(&mut self, versions: Vec<String>) -> Vec<String> {
        let mut valid: Vec<(Version, String)> = versions
            .into_iter()
            .filter_map(|text| parse(&text).map(|v| (v, text)))
            .collect();
        valid.sort_by(|(a, x), (b, y)| order(a, b).then_with(|| x.cmp(y)));
        valid.into_iter().map(|(_, text)| text).collect()
    }

    pub fn change_kind(&mut self, before: String, after: String) -> String {
        let (old, now) = match (parse(&before), parse(&after)) {
            (Some(old), Some(now)) => (old, now),
            _ => return "invalid".to_string(),
        };
        let kind = match order(&now, &old) {
            Ordering::Less => "downgrade",
            Ordering::Equal => "none",
            Ordering::Greater if now.major != old.major => "major",
            Ordering::Greater if now.minor != old.minor => "minor",
            Ordering::Greater if now.patch != old.patch => "patch",
            Ordering::Greater => "pre-release",
        };
        kind.to_string()
    }

    // Level 2
    pub fn expand_range(&mut self, version_range: String) -> Vec<String> {
        match expand(&version_range) {
            None => Vec::new(),
            Some(sets) => sets
                .iter()
                .map(|set| {
                    set.iter()
                        .map(|c| format!("{}{}", c.operator, c.bound.text()))
                        .collect::<Vec<_>>()
                        .join(" ")
                })
                .collect(),
        }
    }

    pub fn satisfies(&mut self, version: String, version_range: String) -> bool {
        match (parse(&version), expand(&version_range)) {
            (Some(parsed), Some(sets)) => in_range(&parsed, &sets),
            _ => false,
        }
    }

    pub fn max_satisfying(&mut self, versions: Vec<String>, version_range: String) -> String {
        let sets = match expand(&version_range) {
            Some(sets) => sets,
            None => return String::new(),
        };
        let mut best: Option<(Version, String)> = None;
        for text in versions {
            let parsed = match parse(&text) {
                Some(parsed) if in_range(&parsed, &sets) => parsed,
                _ => continue,
            };
            let better = match &best {
                None => true,
                Some((version, found)) => {
                    order(&parsed, version).then_with(|| text.cmp(found)) == Ordering::Greater
                }
            };
            if better {
                best = Some((parsed, text));
            }
        }
        best.map(|(_, text)| text).unwrap_or_default()
    }

    // Level 3
    pub fn publish(
        &mut self,
        name: String,
        version: String,
        dependencies: Vec<Vec<String>>,
    ) -> String {
        let parsed = match parse(&version) {
            Some(parsed) => parsed,
            None => return "invalid-version".to_string(),
        };
        let existing = self.releases.get(&name).cloned().unwrap_or_default();
        if existing
            .iter()
            .any(|&r| order(&self.published[r].version, &parsed) == Ordering::Equal)
        {
            return "duplicate".to_string();
        }
        let mut seen = HashSet::new();
        let mut expanded = Vec::new();
        for pair in &dependencies {
            match expand(&pair[1]) {
                Some(sets) if seen.insert(pair[0].clone()) && pair[0] != name => {
                    expanded.push(sets)
                }
                _ => return "invalid-dependency".to_string(),
            }
        }
        let mut own = Vec::new();
        for (pair, sets) in dependencies.into_iter().zip(expanded) {
            own.push(Dependency {
                name: pair[0].clone(),
                text: pair[1].clone(),
                sets,
                edge: self.edges,
            });
            self.edges += 1;
        }
        self.published.push(Release {
            name: name.clone(),
            text: version,
            version: parsed,
            dependencies: own,
        });
        let index = self.published.len() - 1;
        let published = &self.published;
        let list = self.releases.entry(name).or_default();
        list.push(index);
        list.sort_by(|&a, &b| order(&published[b].version, &published[a].version));
        "ok".to_string()
    }

    pub fn candidates(&mut self, name: String, version_range: String) -> Vec<String> {
        let sets = match expand(&version_range) {
            Some(sets) => sets,
            None => return Vec::new(),
        };
        self.releases
            .get(&name)
            .map(|list| {
                list.iter()
                    .filter(|&&r| in_range(&self.published[r].version, &sets))
                    .map(|&r| self.published[r].text.clone())
                    .collect()
            })
            .unwrap_or_default()
    }

    pub fn resolve(&mut self, requirements: Vec<Vec<String>>) -> Vec<String> {
        let roots = roots(&requirements);
        let chosen = self.search(&roots, &HashSet::new(), &HashSet::new(), &HashMap::new());
        self.result(chosen)
    }

    // Level 4
    pub fn explain(&mut self, requirements: Vec<Vec<String>>) -> Vec<String> {
        let roots = roots(&requirements);
        let none = HashMap::new();
        let mut dropped_roots = HashSet::new();
        let mut dropped_edges = HashSet::new();
        if self
            .search(&roots, &dropped_roots, &dropped_edges, &none)
            .is_some()
        {
            return Vec::new();
        }
        let mut kept = Vec::new();
        for (i, root) in roots.iter().enumerate() {
            dropped_roots.insert(i);
            if self
                .search(&roots, &dropped_roots, &dropped_edges, &none)
                .is_some()
            {
                dropped_roots.remove(&i);
                kept.push(format!("root requires {} {}", root.name, root.text));
            }
        }
        for release in &self.published {
            for dependency in &release.dependencies {
                dropped_edges.insert(dependency.edge);
                if self
                    .search(&roots, &dropped_roots, &dropped_edges, &none)
                    .is_some()
                {
                    dropped_edges.remove(&dependency.edge);
                    kept.push(format!(
                        "{}@{} requires {} {}",
                        release.name, release.text, dependency.name, dependency.text
                    ));
                }
            }
        }
        kept
    }

    pub fn locked_resolve(
        &mut self,
        requirements: Vec<Vec<String>>,
        lock: Vec<String>,
    ) -> Vec<String> {
        let roots = roots(&requirements);
        let chosen = self.search(&roots, &HashSet::new(), &HashSet::new(), &lock_of(&lock));
        self.result(chosen)
    }

    pub fn update(
        &mut self,
        requirements: Vec<Vec<String>>,
        lock: Vec<String>,
        unlock: Vec<String>,
    ) -> Vec<String> {
        let before = lock_of(&lock);
        let mut preferred = before.clone();
        preferred.retain(|name, _| !unlock.contains(name));
        let roots = roots(&requirements);
        let chosen = match self.search(&roots, &HashSet::new(), &HashSet::new(), &preferred) {
            Some(chosen) => chosen,
            None => return vec!["unsatisfiable".to_string()],
        };
        let names: BTreeSet<&String> = before.keys().chain(chosen.keys()).collect();
        let mut changes = Vec::new();
        for name in names {
            let now = chosen.get(name).map(|&r| self.published[r].text.clone());
            match (before.get(name), now) {
                (None, Some(now)) => changes.push(format!("{}: added {}", name, now)),
                (Some(old), None) => changes.push(format!("{}: removed {}", name, old)),
                (Some(old), Some(now)) if *old != now => {
                    let kind = self.change_kind(old.clone(), now.clone());
                    changes.push(format!("{}: {} -> {} ({})", name, old, now, kind));
                }
                _ => {}
            }
        }
        changes
    }

    // The search
    fn result(&self, chosen: Option<HashMap<String, usize>>) -> Vec<String> {
        let chosen = match chosen {
            Some(chosen) => chosen,
            None => return Vec::new(),
        };
        let mut names: Vec<&String> = chosen.keys().collect();
        names.sort();
        names
            .into_iter()
            .map(|name| format!("{}@{}", name, self.published[chosen[name]].text))
            .collect()
    }

    /// The chosen release of every needed package, or `None` when the constraints in force cannot
    /// all hold.
    fn search(
        &self,
        roots: &[Root],
        dropped_roots: &HashSet<usize>,
        dropped_edges: &HashSet<usize>,
        preferred: &HashMap<String, String>,
    ) -> Option<HashMap<String, usize>> {
        let mut search = Search {
            resolver: self,
            roots: roots
                .iter()
                .enumerate()
                .filter(|(i, _)| !dropped_roots.contains(i))
                .map(|(_, r)| r)
                .collect(),
            dropped_edges,
            preferred,
            chosen: HashMap::new(),
        };
        if search.solve() {
            Some(search.chosen)
        } else {
            None
        }
    }
}

fn roots(requirements: &[Vec<String>]) -> Vec<Root> {
    requirements
        .iter()
        .map(|pair| Root {
            name: pair[0].clone(),
            text: pair[1].clone(),
            sets: expand(&pair[1]).unwrap_or_default(),
        })
        .collect()
}

fn lock_of(lock: &[String]) -> HashMap<String, String> {
    lock.iter()
        .filter_map(|entry| entry.split_once('@'))
        .map(|(name, text)| (name.to_string(), text.to_string()))
        .collect()
}
