use std::collections::{BTreeSet, HashMap, HashSet};

const OPEN: i64 = (1 << 53) - 1;
const CURRENT: i64 = OPEN - 1;
const HUGE: i64 = 1_000_000_000_000_000;
const SEP: &str = "\u{0}";

struct Span {
    start: i64,
    end: i64,
    names: Vec<String>,
    times: Vec<i64>,
}

struct Found {
    row: Vec<String>,
    used: Vec<usize>,
}

struct Match {
    ends: Vec<String>,
    id: Option<usize>,
}

/// The numbers of the triples that can match, from the narrowest index that applies.
enum Candidates<'a> {
    All,
    List(&'a [usize]),
    One(usize),
}

type Index = HashMap<String, Vec<usize>>;

fn list<'a>(index: &'a Index, key: String) -> Candidates<'a> {
    Candidates::List(index.get(&key).map_or(&[][..], |ids| ids.as_slice()))
}

/// Every triple ever recorded gets a number and a list of spans, the periods during which it was
/// present. Six hash indexes list the numbers by subject, predicate, object and the three pairs,
/// and one more finds a whole triple, so any pattern with a bound position starts from a short
/// list instead of a scan. Removing a triple only closes its span, so the history stays.
///
/// A query joins its patterns one at a time, always taking the pattern whose candidate list is
/// shortest under the variables bound so far, and a path is a breadth-first walk with a visited
/// set, so a cycle ends the walk.
pub struct TripleStore {
    triples: Vec<[String; 3]>,
    spans: Vec<Vec<Span>>,
    exact: HashMap<String, usize>,
    by_s: Index,
    by_p: Index,
    by_o: Index,
    by_sp: Index,
    by_po: Index,
    by_so: Index,
    now: i64,
    live: i32,
}

impl TripleStore {
    pub fn new() -> Self {
        TripleStore {
            triples: Vec::new(),
            spans: Vec::new(),
            exact: HashMap::new(),
            by_s: HashMap::new(),
            by_p: HashMap::new(),
            by_o: HashMap::new(),
            by_sp: HashMap::new(),
            by_po: HashMap::new(),
            by_so: HashMap::new(),
            now: 0,
            live: 0,
        }
    }

    // Level 1
    pub fn add(&mut self, subject: String, predicate: String, obj: String) -> bool {
        let now = self.now;
        self.record(subject, predicate, obj, String::new(), now)
    }

    pub fn remove(&mut self, subject: String, predicate: String, obj: String) -> bool {
        let now = self.now;
        self.retract(subject, predicate, obj, now)
    }

    pub fn size(&mut self) -> i32 {
        self.live
    }

    pub fn r#match(&mut self, subject: String, predicate: String, obj: String) -> Vec<Vec<String>> {
        let candidates = self.candidates(term(&subject), term(&predicate), term(&obj));
        let mut hits: Vec<[String; 3]> = self
            .each(candidates)
            .into_iter()
            .filter(|id| self.present(*id, CURRENT))
            .map(|id| self.triples[id].clone())
            .collect();
        hits.sort();
        hits.into_iter().map(|triple| triple.to_vec()).collect()
    }

    // Level 2 and 3
    pub fn query(&mut self, patterns: Vec<Vec<String>>, columns: Vec<String>) -> Vec<Vec<String>> {
        self.rows(&patterns, &columns, CURRENT, false).0
    }

    // Level 4
    pub fn record(
        &mut self,
        subject: String,
        predicate: String,
        obj: String,
        source: String,
        time: i64,
    ) -> bool {
        self.now = time;
        let key = [subject.as_str(), predicate.as_str(), obj.as_str()].join(SEP);
        let id = match self.exact.get(&key) {
            Some(&id) => id,
            None => self.create(subject, predicate, obj, key),
        };
        let history = &mut self.spans[id];
        if history.last().is_some_and(|last| last.end == OPEN) {
            let last = history.last_mut().unwrap();
            if !source.is_empty() && !last.names.contains(&source) {
                last.names.push(source);
                last.times.push(time);
            }
            return false;
        }
        let mut span = Span { start: time, end: OPEN, names: Vec::new(), times: Vec::new() };
        if !source.is_empty() {
            span.names.push(source);
            span.times.push(time);
        }
        history.push(span);
        self.live += 1;
        true
    }

    pub fn retract(&mut self, subject: String, predicate: String, obj: String, time: i64) -> bool {
        self.now = time;
        let key = [subject.as_str(), predicate.as_str(), obj.as_str()].join(SEP);
        let Some(&id) = self.exact.get(&key) else {
            return false;
        };
        let last = self.spans[id].last_mut().unwrap();
        if last.end != OPEN {
            return false;
        }
        last.end = time;
        self.live -= 1;
        true
    }

    pub fn query_as_of(
        &mut self,
        patterns: Vec<Vec<String>>,
        columns: Vec<String>,
        time: i64,
    ) -> Vec<Vec<String>> {
        self.rows(&patterns, &columns, time, false).0
    }

    pub fn sources_as_of(
        &mut self,
        patterns: Vec<Vec<String>>,
        columns: Vec<String>,
        time: i64,
    ) -> Vec<Vec<String>> {
        self.rows(&patterns, &columns, time, true).1
    }

    // Storage
    fn create(&mut self, subject: String, predicate: String, obj: String, key: String) -> usize {
        let id = self.triples.len();
        self.by_s.entry(subject.clone()).or_default().push(id);
        self.by_p.entry(predicate.clone()).or_default().push(id);
        self.by_o.entry(obj.clone()).or_default().push(id);
        self.by_sp.entry(format!("{subject}{SEP}{predicate}")).or_default().push(id);
        self.by_po.entry(format!("{predicate}{SEP}{obj}")).or_default().push(id);
        self.by_so.entry(format!("{subject}{SEP}{obj}")).or_default().push(id);
        self.triples.push([subject, predicate, obj]);
        self.spans.push(Vec::new());
        self.exact.insert(key, id);
        id
    }

    fn span_at(&self, id: usize, when: i64) -> Option<&Span> {
        for span in self.spans[id].iter().rev() {
            if span.start <= when {
                return if when < span.end { Some(span) } else { None };
            }
        }
        None
    }

    fn present(&self, id: usize, when: i64) -> bool {
        self.span_at(id, when).is_some()
    }

    fn candidates(&self, s: Option<&str>, p: Option<&str>, o: Option<&str>) -> Candidates<'_> {
        match (s, p, o) {
            (Some(s), Some(p), Some(o)) => match self.exact.get(&[s, p, o].join(SEP)) {
                Some(&id) => Candidates::One(id),
                None => Candidates::List(&[]),
            },
            (Some(s), Some(p), None) => list(&self.by_sp, format!("{s}{SEP}{p}")),
            (None, Some(p), Some(o)) => list(&self.by_po, format!("{p}{SEP}{o}")),
            (Some(s), None, Some(o)) => list(&self.by_so, format!("{s}{SEP}{o}")),
            (Some(s), None, None) => list(&self.by_s, s.to_string()),
            (None, Some(p), None) => list(&self.by_p, p.to_string()),
            (None, None, Some(o)) => list(&self.by_o, o.to_string()),
            (None, None, None) => Candidates::All,
        }
    }

    fn count(&self, candidates: &Candidates) -> usize {
        match candidates {
            Candidates::All => self.triples.len(),
            Candidates::List(ids) => ids.len(),
            Candidates::One(_) => 1,
        }
    }

    fn each(&self, candidates: Candidates) -> Vec<usize> {
        match candidates {
            Candidates::All => (0..self.triples.len()).collect(),
            Candidates::List(ids) => ids.to_vec(),
            Candidates::One(id) => vec![id],
        }
    }

    // Queries
    fn rows(
        &self,
        patterns: &[Vec<String>],
        columns: &[String],
        when: i64,
        track: bool,
    ) -> (Vec<Vec<String>>, Vec<Vec<String>>) {
        let mut found: Vec<Found> = Vec::new();
        self.search(patterns, &mut HashMap::new(), &mut Vec::new(), columns, when, track, &mut found);
        let distinct: BTreeSet<Vec<String>> = found.iter().map(|one| one.row.clone()).collect();
        let rows: Vec<Vec<String>> = distinct.into_iter().collect();
        if !track {
            return (rows, Vec::new());
        }
        let mut by_row: HashMap<&Vec<String>, BTreeSet<&str>> = HashMap::new();
        for row in &rows {
            by_row.insert(row, BTreeSet::new());
        }
        for one in &found {
            let names = by_row.get_mut(&one.row).unwrap();
            for &id in &one.used {
                if let Some(span) = self.span_at(id, when) {
                    for (name, at) in span.names.iter().zip(&span.times) {
                        if *at <= when {
                            names.insert(name.as_str());
                        }
                    }
                }
            }
        }
        let sources: Vec<Vec<String>> = rows
            .iter()
            .map(|row| by_row[row].iter().map(|name| name.to_string()).collect())
            .collect();
        (rows, sources)
    }

    #[allow(clippy::too_many_arguments)]
    fn search(
        &self,
        remaining: &[Vec<String>],
        bindings: &mut HashMap<String, String>,
        used: &mut Vec<usize>,
        columns: &[String],
        when: i64,
        track: bool,
        found: &mut Vec<Found>,
    ) {
        if remaining.is_empty() {
            let row = columns.iter().map(|name| bindings[name].clone()).collect();
            found.push(Found { row, used: if track { used.clone() } else { Vec::new() } });
            return;
        }
        let mut best = 0;
        let mut best_cost = i64::MAX;
        for (at, pattern) in remaining.iter().enumerate() {
            let cost = self.cost(pattern, bindings);
            if cost < best_cost {
                best_cost = cost;
                best = at;
            }
        }
        let pattern = &remaining[best];
        let rest: Vec<Vec<String>> = remaining
            .iter()
            .enumerate()
            .filter(|(at, _)| *at != best)
            .map(|(_, other)| other.clone())
            .collect();
        for one in self.matches(pattern, bindings, when) {
            let mut undo: Vec<String> = Vec::new();
            if unify(pattern, &one.ends, bindings, &mut undo) {
                if let Some(id) = one.id {
                    used.push(id);
                }
                self.search(&rest, bindings, used, columns, when, track, found);
                if one.id.is_some() {
                    used.pop();
                }
            }
            for name in undo {
                bindings.remove(&name);
            }
        }
    }

    fn cost(&self, pattern: &[String], bindings: &HashMap<String, String>) -> i64 {
        let s = value(&pattern[0], bindings);
        let p = value(&pattern[1], bindings);
        let o = value(&pattern[2], bindings);
        if let Some(predicate) = pattern[1].strip_suffix('+') {
            if s.is_none() && o.is_none() {
                return HUGE;
            }
            return self.by_p.get(predicate).map_or(0, |ids| ids.len()) as i64;
        }
        self.count(&self.candidates(s.as_deref(), p.as_deref(), o.as_deref())) as i64
    }

    fn matches(
        &self,
        pattern: &[String],
        bindings: &HashMap<String, String>,
        when: i64,
    ) -> Vec<Match> {
        let s = value(&pattern[0], bindings);
        let p = value(&pattern[1], bindings);
        let o = value(&pattern[2], bindings);
        if let Some(predicate) = pattern[1].strip_suffix('+') {
            return self
                .path_pairs(s.as_deref(), predicate, o.as_deref(), when)
                .into_iter()
                .map(|pair| Match { ends: pair, id: None })
                .collect();
        }
        let candidates = self.candidates(s.as_deref(), p.as_deref(), o.as_deref());
        self.each(candidates)
            .into_iter()
            .filter(|id| self.present(*id, when))
            .map(|id| Match { ends: self.triples[id].to_vec(), id: Some(id) })
            .collect()
    }

    fn path_pairs(&self, s: Option<&str>, p: &str, o: Option<&str>, when: i64) -> Vec<Vec<String>> {
        if let Some(s) = s {
            let reached = self.reach(s, p, true, when);
            return match o {
                Some(o) if reached.contains(o) => vec![vec![s.to_string(), o.to_string()]],
                Some(_) => Vec::new(),
                None => reached.into_iter().map(|node| vec![s.to_string(), node]).collect(),
            };
        }
        if let Some(o) = o {
            return self
                .reach(o, p, false, when)
                .into_iter()
                .map(|node| vec![node, o.to_string()])
                .collect();
        }
        let mut starts: BTreeSet<&str> = BTreeSet::new();
        for &id in self.by_p.get(p).map_or(&[][..], |ids| ids.as_slice()) {
            if self.present(id, when) {
                starts.insert(self.triples[id][0].as_str());
            }
        }
        let mut pairs = Vec::new();
        for start in starts {
            for node in self.reach(start, p, true, when) {
                pairs.push(vec![start.to_string(), node]);
            }
        }
        pairs
    }

    /// The nodes at the end of one or more hops; the start is in it only through a cycle.
    fn reach(&self, start: &str, p: &str, forward: bool, when: i64) -> HashSet<String> {
        let mut seen: HashSet<String> = HashSet::new();
        let mut queue: Vec<String> = vec![start.to_string()];
        let mut next = 0;
        while next < queue.len() {
            let node = queue[next].clone();
            let key = if forward { format!("{node}{SEP}{p}") } else { format!("{p}{SEP}{node}") };
            let index = if forward { &self.by_sp } else { &self.by_po };
            for &id in index.get(&key).map_or(&[][..], |ids| ids.as_slice()) {
                if !self.present(id, when) {
                    continue;
                }
                let following = if forward { &self.triples[id][2] } else { &self.triples[id][0] };
                if seen.insert(following.clone()) {
                    queue.push(following.clone());
                }
            }
            next += 1;
        }
        seen
    }
}

fn term(token: &str) -> Option<&str> {
    if token == "?" {
        None
    } else {
        Some(token)
    }
}

fn value(token: &str, bindings: &HashMap<String, String>) -> Option<String> {
    if token == "?" {
        None
    } else if token.starts_with('?') {
        bindings.get(token).cloned()
    } else {
        Some(token.to_string())
    }
}

fn unify(
    pattern: &[String],
    ends: &[String],
    bindings: &mut HashMap<String, String>,
    undo: &mut Vec<String>,
) -> bool {
    let tokens: Vec<&String> =
        if ends.len() == 3 { pattern.iter().collect() } else { vec![&pattern[0], &pattern[2]] };
    for (at, token) in tokens.into_iter().enumerate() {
        if token.as_str() == "?" {
            continue;
        }
        if !token.starts_with('?') {
            if *token != ends[at] {
                return false;
            }
        } else if let Some(bound) = bindings.get(token) {
            if *bound != ends[at] {
                return false;
            }
        } else {
            bindings.insert(token.clone(), ends[at].clone());
            undo.push(token.clone());
        }
    }
    true
}
