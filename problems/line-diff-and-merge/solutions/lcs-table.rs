use std::collections::HashMap;

const KEEP: char = ' ';
const REMOVE: char = '-';
const ADD: char = '+';
const OURS: &str = "<<<<<<< ours";
const BASE: &str = "||||||| base";
const SEPARATOR: &str = "=======";
const THEIRS: &str = ">>>>>>> theirs";

struct Step {
    kind: char,
    line: String,
}

struct Hunk {
    start: usize,
    old: Vec<String>,
    fresh: Vec<String>,
}

pub struct LineDiff {
    last: Vec<String>,
}

impl LineDiff {
    pub fn new() -> Self {
        LineDiff { last: Vec::new() }
    }

    // Level 1
    pub fn lcs(&mut self, before: Vec<String>, after: Vec<String>) -> Vec<String> {
        script(&before, &after)
            .into_iter()
            .filter(|step| step.kind == KEEP)
            .map(|step| step.line)
            .collect()
    }

    pub fn diff(&mut self, before: Vec<String>, after: Vec<String>) -> Vec<String> {
        script(&before, &after)
            .into_iter()
            .map(|step| format!("{}{}", step.kind, step.line))
            .collect()
    }

    // Level 2
    pub fn unified(&mut self, before: Vec<String>, after: Vec<String>, context: i32) -> Vec<String> {
        let context = context.max(0) as usize;
        let steps = script(&before, &after);
        let changed: Vec<usize> = (0..steps.len()).filter(|&index| steps[index].kind != KEEP).collect();
        let mut lines = Vec::new();
        let Some(&first_change) = changed.first() else {
            return lines;
        };
        let mut groups = Vec::new();
        let (mut first, mut previous) = (first_change, first_change);
        for &index in &changed[1..] {
            if index - previous - 1 > 2 * context {
                groups.push((first, previous));
                first = index;
            }
            previous = index;
        }
        groups.push((first, previous));
        for (group_first, group_last) in groups {
            let start = group_first.saturating_sub(context);
            let end = steps.len().min(group_last + context + 1);
            let (prior, hunk) = (&steps[..start], &steps[start..end]);
            let old_range = range(count(prior, ADD), count(hunk, ADD));
            let new_range = range(count(prior, REMOVE), count(hunk, REMOVE));
            lines.push(format!("@@ -{} +{} @@", old_range, new_range));
            lines.extend(hunk.iter().map(|step| format!("{}{}", step.kind, step.line)));
        }
        lines
    }

    // Level 3
    pub fn apply_patch(&mut self, lines: Vec<String>, patch: Vec<String>, max_offset: i32) -> Vec<String> {
        let mut result = lines;
        let mut statuses = Vec::new();
        let (mut added, mut shift, mut floor) = (0_i64, 0_i64, 0_i64);
        for hunk in parse_hunks(&patch) {
            let base = hunk.start as i64 + added;
            let Some(found) = find_hunk(&result, &hunk.old, base + shift, floor, max_offset as i64) else {
                statuses.push("rejected".to_string());
                continue;
            };
            let at = found as usize;
            result.splice(at..at + hunk.old.len(), hunk.fresh.iter().cloned());
            shift = found - base;
            added += hunk.fresh.len() as i64 - hunk.old.len() as i64;
            floor = found + hunk.fresh.len() as i64;
            statuses.push(format!("applied {}", shift));
        }
        self.last = result;
        statuses
    }

    pub fn patched(&mut self) -> Vec<String> {
        self.last.clone()
    }

    // Level 4
    pub fn merge(&mut self, base: Vec<String>, ours: Vec<String>, theirs: Vec<String>) -> Vec<String> {
        let to_ours = kept_at(&base, &ours);
        let to_theirs = kept_at(&base, &theirs);
        let mut merged = Vec::new();
        let (mut o, mut a, mut b) = (0, 0, 0);
        for (index, line) in base.iter().enumerate() {
            if let (Some(&j), Some(&k)) = (to_ours.get(&index), to_theirs.get(&index)) {
                merged.extend(resolve(&base[o..index], &ours[a..j], &theirs[b..k]));
                merged.push(line.clone());
                (o, a, b) = (index + 1, j + 1, k + 1);
            }
        }
        merged.extend(resolve(&base[o..], &ours[a..], &theirs[b..]));
        merged
    }
}

/// The diff with the most kept lines that, read from the top, keeps rather than removes and
/// removes rather than adds wherever both stay optimal.
fn script(before: &[String], after: &[String]) -> Vec<Step> {
    let (n, m) = (before.len(), after.len());
    // longest[i][j]: the length of a longest common subsequence of before[i..] and after[j..].
    let mut longest = vec![vec![0_u32; m + 1]; n + 1];
    for i in (0..n).rev() {
        for j in (0..m).rev() {
            longest[i][j] = if before[i] == after[j] {
                longest[i + 1][j + 1] + 1
            } else {
                longest[i + 1][j].max(longest[i][j + 1])
            };
        }
    }
    let mut steps = Vec::new();
    let (mut i, mut j) = (0, 0);
    while i < n || j < m {
        if i < n && j < m && before[i] == after[j] {
            steps.push(Step { kind: KEEP, line: before[i].clone() });
            i += 1;
            j += 1;
        } else if i < n && (j == m || longest[i + 1][j] >= longest[i][j + 1]) {
            steps.push(Step { kind: REMOVE, line: before[i].clone() });
            i += 1;
        } else {
            steps.push(Step { kind: ADD, line: after[j].clone() });
            j += 1;
        }
    }
    steps
}

/// The number of steps that are not of the skipped kind.
fn count(steps: &[Step], skipped: char) -> usize {
    steps.iter().filter(|step| step.kind != skipped).count()
}

fn range(lines_before: usize, size: usize) -> String {
    match size {
        0 => format!("{},0", lines_before),
        1 => format!("{}", lines_before + 1),
        _ => format!("{},{}", lines_before + 1, size),
    }
}

/// Reads a header's old range: its start and its count.
fn old_range(line: &str) -> Option<(usize, usize)> {
    let rest = line.strip_prefix("@@ -")?.strip_suffix(" @@")?;
    let (old, new) = rest.split_once(" +")?;
    let digits = |text: &str| !text.is_empty() && text.bytes().all(|byte| byte.is_ascii_digit());
    let (new_start, new_count) = new.split_once(',').unwrap_or((new, "1"));
    if !digits(new_start) || !digits(new_count) {
        return None;
    }
    let (start, count) = old.split_once(',').unwrap_or((old, "1"));
    if !digits(start) || !digits(count) {
        return None;
    }
    Some((start.parse().ok()?, count.parse().ok()?))
}

/// Each hunk with the index where its old lines start, its old lines and its new lines.
fn parse_hunks(patch: &[String]) -> Vec<Hunk> {
    let mut hunks: Vec<Hunk> = Vec::new();
    for line in patch {
        if let Some((start, count)) = old_range(line) {
            let start = if count > 0 { start - 1 } else { start };
            hunks.push(Hunk { start, old: Vec::new(), fresh: Vec::new() });
            continue;
        }
        let (Some(kind), Some(hunk)) = (line.chars().next(), hunks.last_mut()) else {
            continue;
        };
        let text = line[kind.len_utf8()..].to_string();
        if kind != ADD {
            hunk.old.push(text.clone());
        }
        if kind != REMOVE {
            hunk.fresh.push(text);
        }
    }
    hunks
}

/// The nearest position to `expected` where `old` matches, the earlier one first.
fn find_hunk(result: &[String], old: &[String], expected: i64, floor: i64, max_offset: i64) -> Option<i64> {
    for distance in 0..=max_offset {
        for position in [expected - distance, expected + distance] {
            let fits = floor <= position && position + old.len() as i64 <= result.len() as i64;
            if fits && result[position as usize..position as usize + old.len()] == *old {
                return Some(position);
            }
        }
    }
    None
}

/// For each line of `base` that the diff to `other` keeps, the index it keeps it at.
fn kept_at(base: &[String], other: &[String]) -> HashMap<usize, usize> {
    let mut kept = HashMap::new();
    let (mut i, mut j) = (0, 0);
    for step in script(base, other) {
        if step.kind == KEEP {
            kept.insert(i, j);
        }
        if step.kind != ADD {
            i += 1;
        }
        if step.kind != REMOVE {
            j += 1;
        }
    }
    kept
}

fn resolve(base: &[String], ours: &[String], theirs: &[String]) -> Vec<String> {
    if ours == theirs {
        return ours.to_vec();
    }
    if ours == base {
        return theirs.to_vec();
    }
    if theirs == base {
        return ours.to_vec();
    }
    let mut conflict = vec![OURS.to_string()];
    conflict.extend_from_slice(ours);
    conflict.push(BASE.to_string());
    conflict.extend_from_slice(base);
    conflict.push(SEPARATOR.to_string());
    conflict.extend_from_slice(theirs);
    conflict.push(THEIRS.to_string());
    conflict
}
