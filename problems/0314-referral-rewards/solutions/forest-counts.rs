use std::collections::HashMap;

const COUNTED: usize = 0;
const DUPLICATE: usize = 1;
const RIVAL: usize = 2;
const LOOP: usize = 3;
const NONE: i32 = -1;

/// Counted referrals form a forest: a person has at most one referrer.
///
/// People are numbered in the order they first appear in a counted referral. The forest is kept
/// in vectors (a referrer, a first and a last child, and a next sibling per person), a union-find
/// answers "would this referral close a loop?" without walking up, and the totals are recounted
/// in one breadth-first pass when a question needs them after a change. Nothing recurses, so a
/// chain of 10^6 referrals is as safe as a flat one.
pub struct ReferralProgram {
    bonus: i32,
    index: HashMap<String, usize>,
    names: Vec<String>,
    referrer: Vec<i32>,
    first: Vec<i32>,
    last: Vec<i32>,
    next: Vec<i32>,
    direct: Vec<i32>,
    parent_set: Vec<usize>,
    set_size: Vec<usize>,
    totals: Vec<i32>,
    totals_fresh: bool,
}

impl ReferralProgram {
    pub fn new(bonus: i32) -> Self {
        ReferralProgram {
            bonus,
            index: HashMap::new(),
            names: Vec::new(),
            referrer: Vec::new(),
            first: Vec::new(),
            last: Vec::new(),
            next: Vec::new(),
            direct: Vec::new(),
            parent_set: Vec::new(),
            set_size: Vec::new(),
            totals: Vec::new(),
            totals_fresh: true,
        }
    }

    // Level 1
    pub fn refer(&mut self, referrer: String, referred: String) -> i32 {
        if self.apply(&referrer, &referred) == COUNTED {
            self.bonus
        } else {
            0
        }
    }

    pub fn points(&mut self, person: String) -> i32 {
        self.index.get(&person).map_or(0, |&at| self.direct[at] * self.bonus)
    }

    pub fn referrals_of(&mut self, person: String) -> Vec<String> {
        let mut found = Vec::new();
        let mut child = self.index.get(&person).map_or(NONE, |&at| self.first[at]);
        while child != NONE {
            found.push(self.names[child as usize].clone());
            child = self.next[child as usize];
        }
        found
    }

    // Level 2
    pub fn total_referrals(&mut self, person: String) -> i32 {
        match self.index.get(&person).copied() {
            Some(at) => self.recount()[at],
            None => 0,
        }
    }

    pub fn top_referrer(&mut self) -> String {
        self.leaderboard(1).into_iter().next().unwrap_or_default()
    }

    // Level 3
    pub fn refer_all(&mut self, rows: Vec<Vec<String>>) -> Vec<i32> {
        let mut tally = vec![0; 4];
        for row in &rows {
            tally[self.apply(&row[0], &row[1])] += 1;
        }
        tally
    }

    // Level 4
    pub fn leaderboard(&mut self, k: i32) -> Vec<String> {
        let totals = self.recount().clone();
        let mut ranked: Vec<usize> = (0..totals.len()).filter(|&at| totals[at] > 0).collect();
        ranked.sort_by(|&a, &b| {
            totals[b]
                .cmp(&totals[a])
                .then_with(|| self.direct[b].cmp(&self.direct[a]))
                .then_with(|| self.names[a].cmp(&self.names[b]))
        });
        ranked.into_iter().take(k.max(0) as usize).map(|at| self.names[at].clone()).collect()
    }

    fn person(&mut self, name: &str) -> usize {
        if let Some(&at) = self.index.get(name) {
            return at;
        }
        let at = self.names.len();
        self.index.insert(name.to_string(), at);
        self.names.push(name.to_string());
        self.referrer.push(NONE);
        self.first.push(NONE);
        self.last.push(NONE);
        self.next.push(NONE);
        self.direct.push(0);
        self.parent_set.push(at);
        self.set_size.push(1);
        self.totals_fresh = false;
        at
    }

    fn root_of(&mut self, start: usize) -> usize {
        let mut at = start;
        while self.parent_set[at] != at {
            self.parent_set[at] = self.parent_set[self.parent_set[at]];
            at = self.parent_set[at];
        }
        at
    }

    fn apply(&mut self, referrer_name: &str, referred_name: &str) -> usize {
        if referrer_name == referred_name {
            return LOOP;
        }
        if let Some(&known) = self.index.get(referred_name) {
            if self.referrer[known] != NONE {
                let same = self.names[self.referrer[known] as usize] == referrer_name;
                return if same { DUPLICATE } else { RIVAL };
            }
        }
        let above = self.person(referrer_name);
        let below = self.person(referred_name);
        let mut top = self.root_of(above);
        let mut bottom = self.root_of(below);
        if top == bottom {
            return LOOP;
        }
        if self.set_size[top] < self.set_size[bottom] {
            std::mem::swap(&mut top, &mut bottom);
        }
        self.parent_set[bottom] = top;
        self.set_size[top] += self.set_size[bottom];
        self.referrer[below] = above as i32;
        if self.first[above] == NONE {
            self.first[above] = below as i32;
        } else {
            let tail = self.last[above] as usize;
            self.next[tail] = below as i32;
        }
        self.last[above] = below as i32;
        self.direct[above] += 1;
        self.totals_fresh = false;
        COUNTED
    }

    fn recount(&mut self) -> &Vec<i32> {
        if !self.totals_fresh {
            let count = self.names.len();
            let mut order: Vec<usize> = (0..count).filter(|&at| self.referrer[at] == NONE).collect();
            let mut seen = 0;
            while seen < order.len() {
                let mut child = self.first[order[seen]];
                while child != NONE {
                    order.push(child as usize);
                    child = self.next[child as usize];
                }
                seen += 1;
            }
            let mut totals = vec![0; count];
            for &at in order.iter().rev() {
                let above = self.referrer[at];
                if above != NONE {
                    totals[above as usize] += totals[at] + 1;
                }
            }
            self.totals = totals;
            self.totals_fresh = true;
        }
        &self.totals
    }
}
