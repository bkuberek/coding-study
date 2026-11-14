use std::collections::{BTreeSet, HashMap, HashSet};

const ROW_CHECKS: [&str; 6] = ["not-null", "type", "allowed", "range", "unique", "references"];
const BATCH_CHECKS: [&str; 3] = ["row-count", "drift", "freshness"];
const ACTIONS: [&str; 3] = ["warn", "quarantine", "block"];
const EMPTY_SHARE: f64 = 0.0001;
const DAYS_IN_MONTH: [u32; 12] = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];

fn all_digits(text: &str) -> bool {
    text.bytes().all(|byte| byte.is_ascii_digit())
}

fn is_int(text: &str) -> bool {
    let digits = text.strip_prefix('-').unwrap_or(text);
    (1..=15).contains(&digits.len()) && all_digits(digits)
}

fn is_date(text: &str) -> bool {
    let bytes = text.as_bytes();
    if bytes.len() != 10 || bytes[4] != b'-' || bytes[7] != b'-' {
        return false;
    }
    let parts = [&text[0..4], &text[5..7], &text[8..10]];
    if !parts.iter().all(|part| all_digits(part)) {
        return false;
    }
    let [year, month, day] = parts.map(|part| part.parse::<u32>().unwrap_or(0));
    if year < 1 || !(1..=12).contains(&month) {
        return false;
    }
    let leap = year % 4 == 0 && (year % 100 != 0 || year % 400 == 0);
    let last = if month == 2 && leap { 29 } else { DAYS_IN_MONTH[month as usize - 1] };
    (1..=last).contains(&day)
}

/// A non-negative decimal with at most four places, in units of 0.0001.
fn ten_thousandths(decimal: &str) -> i64 {
    let (whole, fraction) = decimal.split_once('.').unwrap_or((decimal, ""));
    let padded = format!("{fraction}0000");
    whole.parse::<i64>().unwrap_or(0) * 10000 + padded[..4].parse::<i64>().unwrap_or(0)
}

fn is_row_check(check: &str) -> bool {
    ROW_CHECKS.contains(&check)
}

fn is_batch_check(check: &str) -> bool {
    BATCH_CHECKS.contains(&check)
}

struct Rule {
    rule_id: String,
    check: String,
    columns: Vec<String>,
    params: Vec<String>,
    action: String,
}

/// Rules are data: each one is a check name, its columns and its parameters, kept in the order they
/// were added. Validation runs every rule over the rows and reports what failed; the gate runs the
/// row rules first, sets aside the rows that quarantine rules reject, and runs the batch rules on
/// what is left.
pub struct QualityGate {
    index: HashMap<String, usize>,
    rules: Vec<Rule>,
    dimensions: HashMap<String, HashSet<String>>,
    previous: Option<Vec<Vec<String>>>,
    now: i64,
    aside: Vec<i32>,
}

impl QualityGate {
    pub fn new(columns: Vec<String>) -> Self {
        QualityGate {
            index: columns.into_iter().enumerate().map(|(at, name)| (name, at)).collect(),
            rules: Vec::new(),
            dimensions: HashMap::new(),
            previous: None,
            now: 0,
            aside: Vec::new(),
        }
    }

    // Level 1
    pub fn add_rule(&mut self, rule_id: String, check: String, columns: Vec<String>, params: Vec<String>) -> bool {
        let known = is_row_check(&check) || is_batch_check(&check);
        if self.rule(&rule_id).is_some() || !known || columns.iter().any(|c| !self.index.contains_key(c)) {
            return false;
        }
        if check == "references" && !self.dimensions.contains_key(&params[0]) {
            return false;
        }
        self.rules.push(Rule { rule_id, check, columns, params, action: "block".to_string() });
        true
    }

    pub fn validate(&mut self, rows: Vec<Vec<String>>) -> Vec<Vec<String>> {
        self.rules.iter().flat_map(|rule| self.findings(rule, &rows)).collect()
    }

    pub fn failing_rows(&mut self, rows: Vec<Vec<String>>, rule_id: String) -> Vec<i32> {
        match self.rule(&rule_id) {
            Some(rule) if !is_batch_check(&rule.check) => self.rows_failing(rule, &rows),
            _ => Vec::new(),
        }
    }

    // Level 2
    pub fn load_dimension(&mut self, name: String, keys: Vec<String>) -> i32 {
        let set: HashSet<String> = keys.into_iter().collect();
        let size = set.len() as i32;
        self.dimensions.insert(name, set);
        size
    }

    pub fn set_previous_batch(&mut self, rows: Vec<Vec<String>>) -> i32 {
        let size = rows.len() as i32;
        self.previous = Some(rows);
        size
    }

    // Level 3
    pub fn set_time(&mut self, now: i64) {
        self.now = now;
    }

    // Level 4
    pub fn set_action(&mut self, rule_id: String, action: String) -> bool {
        let Some(rule) = self.rules.iter_mut().find(|rule| rule.rule_id == rule_id) else {
            return false;
        };
        if !ACTIONS.contains(&action.as_str()) || (action == "quarantine" && is_batch_check(&rule.check)) {
            return false;
        }
        rule.action = action;
        true
    }

    pub fn decide(&mut self, rows: Vec<Vec<String>>) -> Vec<Vec<String>> {
        let mut set_aside: BTreeSet<i32> = BTreeSet::new();
        for rule in &self.rules {
            if is_row_check(&rule.check) && rule.action == "quarantine" {
                set_aside.extend(self.rows_failing(rule, &rows));
            }
        }
        let kept: Vec<Vec<String>> = rows
            .iter()
            .enumerate()
            .filter(|(at, _)| !set_aside.contains(&(*at as i32)))
            .map(|(_, row)| row.clone())
            .collect();
        let mut findings: Vec<Vec<String>> = Vec::new();
        for rule in &self.rules {
            let seen = if is_row_check(&rule.check) { &rows } else { &kept };
            for mut entry in self.findings(rule, seen) {
                entry.push(rule.action.clone());
                findings.push(entry);
            }
        }
        let head = if findings.iter().any(|entry| entry[3] == "block") {
            self.aside = Vec::new();
            vec!["block".to_string(), "0".to_string(), "0".to_string()]
        } else {
            self.aside = set_aside.iter().copied().collect();
            let head = vec!["publish".to_string(), kept.len().to_string(), set_aside.len().to_string()];
            self.previous = Some(kept);
            head
        };
        let mut answer = vec![head];
        answer.extend(findings);
        answer
    }

    pub fn quarantined(&mut self) -> Vec<i32> {
        self.aside.clone()
    }

    // Helpers
    fn rule(&self, rule_id: &str) -> Option<&Rule> {
        self.rules.iter().find(|rule| rule.rule_id == rule_id)
    }

    fn rows_failing(&self, rule: &Rule, rows: &[Vec<String>]) -> Vec<i32> {
        let failing: BTreeSet<i32> =
            self.row_failures(rule, rows).into_iter().flat_map(|(_, bad)| bad).collect();
        failing.into_iter().collect()
    }

    fn findings(&self, rule: &Rule, rows: &[Vec<String>]) -> Vec<Vec<String>> {
        if is_row_check(&rule.check) {
            return self
                .row_failures(rule, rows)
                .into_iter()
                .filter(|(_, bad)| !bad.is_empty())
                .map(|(column, bad)| vec![rule.rule_id.clone(), column, bad.len().to_string()])
                .collect();
        }
        match self.batch_failure(rule, rows) {
            Some(observed) => vec![vec![rule.rule_id.clone(), rule.columns.concat(), observed]],
            None => Vec::new(),
        }
    }

    /// For each column of a row rule (one joined key for unique), the rows that fail it.
    fn row_failures(&self, rule: &Rule, rows: &[Vec<String>]) -> Vec<(String, Vec<i32>)> {
        if rule.check == "unique" {
            let mut groups: HashMap<Vec<&str>, Vec<i32>> = HashMap::new();
            for (at, row) in rows.iter().enumerate() {
                let key: Vec<&str> = rule.columns.iter().map(|c| row[self.index[c]].as_str()).collect();
                if !key.contains(&"") {
                    groups.entry(key).or_default().push(at as i32);
                }
            }
            let mut bad: Vec<i32> = groups.into_values().filter(|group| group.len() > 1).flatten().collect();
            bad.sort_unstable();
            return vec![(rule.columns.join("+"), bad)];
        }
        rule.columns
            .iter()
            .map(|column| {
                let at = self.index[column];
                let bad = (0..rows.len()).filter(|&n| self.fails(rule, &rows[n][at])).map(|n| n as i32).collect();
                (column.clone(), bad)
            })
            .collect()
    }

    fn fails(&self, rule: &Rule, value: &str) -> bool {
        if rule.check == "not-null" {
            return value.is_empty();
        }
        if value.is_empty() {
            return false;
        }
        match rule.check.as_str() {
            "type" => !(if rule.params[0] == "int" { is_int(value) } else { is_date(value) }),
            "allowed" => !rule.params.iter().any(|allowed| allowed == value),
            "range" => {
                if !is_int(value) {
                    return false;
                }
                let number: i64 = value.parse().unwrap_or(0);
                let low: i64 = rule.params[0].parse().unwrap_or(0);
                let high: i64 = rule.params[1].parse().unwrap_or(0);
                number < low || number > high
            }
            _ => !self.dimensions[&rule.params[0]].contains(value),
        }
    }

    /// The observed value of a failing batch rule, or None when it passes.
    fn batch_failure(&self, rule: &Rule, rows: &[Vec<String>]) -> Option<String> {
        if rule.check == "row-count" {
            let before = self.previous.as_ref()?.len() as i64;
            let tolerance: i64 = rule.params[0].parse().unwrap_or(0);
            let low = before * (100 - tolerance) / 100;
            let high = (before * (100 + tolerance) + 99) / 100;
            let count = rows.len() as i64;
            return if (low..=high).contains(&count) { None } else { Some(count.to_string()) };
        }
        let column = self.index[&rule.columns[0]];
        let values = integers(rows, column);
        if rule.check == "freshness" {
            let Some(&newest) = values.iter().max() else {
                return Some("none".to_string());
            };
            let lag = self.now - newest;
            let limit: i64 = rule.params[0].parse().unwrap_or(0);
            return if lag > limit { Some(lag.to_string()) } else { None };
        }
        let baseline = integers(self.previous.as_ref()?, column);
        if values.is_empty() || baseline.is_empty() {
            return None;
        }
        let edges: Vec<i64> = rule.params[1..].iter().map(|edge| edge.parse().unwrap_or(0)).collect();
        let units = (psi(&values, &baseline, &edges) * 10000.0 + 0.5).floor() as i64;
        if units < ten_thousandths(&rule.params[0]) {
            return None;
        }
        Some(format!("{}.{:04}", units / 10000, units % 10000))
    }
}

fn integers(rows: &[Vec<String>], column: usize) -> Vec<i64> {
    rows.iter().filter(|row| is_int(&row[column])).map(|row| row[column].parse().unwrap_or(0)).collect()
}

fn psi(values: &[i64], baseline: &[i64], edges: &[i64]) -> f64 {
    let actual = shares(values, edges);
    let expected = shares(baseline, edges);
    let mut total = 0.0;
    for bin in 0..actual.len() {
        total += (actual[bin] - expected[bin]) * (actual[bin] / expected[bin]).ln();
    }
    total
}

fn shares(sample: &[i64], edges: &[i64]) -> Vec<f64> {
    let mut counts = vec![0usize; edges.len() + 1];
    for &value in sample {
        counts[edges.partition_point(|&edge| edge <= value)] += 1;
    }
    counts
        .into_iter()
        .map(|count| if count == 0 { EMPTY_SHARE } else { count as f64 / sample.len() as f64 })
        .collect()
}
