use std::collections::{HashMap, HashSet};

/// Rows are indexed once by id, then every question is a walk over the index. Nothing here
/// recurses: the outline and the subtree sizes use an explicit stack and a breadth-first order, so
/// a chain of 10^5 managers is as safe as a flat one.
pub struct OrgChart {
    ids: Vec<String>,
    parents: HashMap<String, String>,
    names: HashMap<String, String>,
    kids: HashMap<String, Vec<String>>,
    orphan_ids: Vec<String>,
    tops: Vec<String>,
    attached: HashSet<String>,
    sizes: HashMap<String, i32>,
    cycle_list: Vec<Vec<String>>,
}

impl OrgChart {
    pub fn new() -> Self {
        OrgChart {
            ids: Vec::new(),
            parents: HashMap::new(),
            names: HashMap::new(),
            kids: HashMap::new(),
            orphan_ids: Vec::new(),
            tops: Vec::new(),
            attached: HashSet::new(),
            sizes: HashMap::new(),
            cycle_list: Vec::new(),
        }
    }

    // Level 1
    pub fn load(&mut self, rows: Vec<Vec<String>>) {
        self.ids = rows.iter().map(|row| row[0].clone()).collect();
        self.parents = rows.iter().map(|row| (row[0].clone(), row[1].clone())).collect();
        self.names = rows.iter().map(|row| (row[0].clone(), row[2].clone())).collect();
        self.kids = HashMap::new();
        for id in &self.ids {
            self.kids.entry(self.parents[id].clone()).or_default().push(id.clone());
        }
        self.orphan_ids = self
            .ids
            .iter()
            .filter(|id| {
                let parent = &self.parents[*id];
                !parent.is_empty() && !self.names.contains_key(parent)
            })
            .cloned()
            .collect();
        let orphan_set: HashSet<&String> = self.orphan_ids.iter().collect();
        self.tops = self
            .ids
            .iter()
            .filter(|id| self.parents[*id].is_empty() || orphan_set.contains(*id))
            .cloned()
            .collect();
        let mut order: Vec<String> = self.tops.clone();
        let mut next = 0;
        while next < order.len() {
            if let Some(below) = self.kids.get(&order[next]) {
                order.extend(below.iter().cloned());
            }
            next += 1;
        }
        self.attached = order.iter().cloned().collect();
        self.sizes = order.iter().map(|id| (id.clone(), 1)).collect();
        for at in (0..order.len()).rev() {
            let parent = &self.parents[&order[at]];
            if let Some(parent_size) = self.sizes.get(parent).copied() {
                let own = self.sizes[&order[at]];
                self.sizes.insert(parent.clone(), parent_size + own);
            }
        }
        self.cycle_list = self.find_cycles();
    }

    pub fn roots(&mut self) -> Vec<String> {
        self.kids.get("").cloned().unwrap_or_default()
    }

    pub fn name_of(&mut self, employee: String) -> String {
        self.names.get(&employee).cloned().unwrap_or_default()
    }

    pub fn children(&mut self, employee: String) -> Vec<String> {
        if !self.names.contains_key(&employee) {
            return Vec::new();
        }
        self.kids.get(&employee).cloned().unwrap_or_default()
    }

    // Level 2
    pub fn orphans(&mut self) -> Vec<String> {
        self.orphan_ids.clone()
    }

    pub fn cycles(&mut self) -> Vec<Vec<String>> {
        self.cycle_list.clone()
    }

    // Level 3
    pub fn chain(&mut self, employee: String) -> Vec<String> {
        self.chain_of(&employee)
    }

    pub fn lowest_common_manager(&mut self, first: String, second: String) -> String {
        let above_second: HashSet<String> = self.chain_of(&second).into_iter().collect();
        self.chain_of(&first)
            .into_iter()
            .find(|manager| above_second.contains(manager))
            .unwrap_or_default()
    }

    // Level 4
    pub fn subtree_size(&mut self, employee: String) -> i32 {
        self.sizes.get(&employee).copied().unwrap_or(0)
    }

    pub fn outline(&mut self, order: String) -> Vec<String> {
        let mut lines = Vec::new();
        let mut stack: Vec<(String, usize)> = Vec::new();
        for top in self.sorted(&self.tops, &order).into_iter().rev() {
            stack.push((top, 0));
        }
        while let Some((current, depth)) = stack.pop() {
            lines.push(format!("{}{} ({})", "  ".repeat(depth), self.names[&current], current));
            if let Some(below) = self.kids.get(&current) {
                for kid in self.sorted(below, &order).into_iter().rev() {
                    stack.push((kid, depth + 1));
                }
            }
        }
        lines
    }

    fn chain_of(&self, employee: &str) -> Vec<String> {
        if !self.attached.contains(employee) {
            return Vec::new();
        }
        let mut path = vec![employee.to_string()];
        let mut parent = &self.parents[employee];
        while self.names.contains_key(parent) {
            path.push(parent.clone());
            parent = &self.parents[parent];
        }
        path
    }

    fn sorted(&self, members: &[String], order: &str) -> Vec<String> {
        let mut copy = members.to_vec();
        match order {
            "name" => copy.sort_by(|a, b| self.names[a].cmp(&self.names[b]).then_with(|| a.cmp(b))),
            "size" => copy.sort_by(|a, b| {
                self.sizes[b]
                    .cmp(&self.sizes[a])
                    .then_with(|| self.names[a].cmp(&self.names[b]))
                    .then_with(|| a.cmp(b))
            }),
            _ => {}
        }
        copy
    }

    fn find_cycles(&self) -> Vec<Vec<String>> {
        let position: HashMap<&String, usize> = self.ids.iter().enumerate().map(|(i, id)| (id, i)).collect();
        let mut seen: HashSet<&String> = self.attached.iter().collect();
        let mut found: Vec<Vec<String>> = Vec::new();
        for start in &self.ids {
            let mut walk: Vec<&String> = Vec::new();
            let mut current = start;
            while !seen.contains(current) {
                seen.insert(current);
                walk.push(current);
                current = &self.parents[current];
            }
            if let Some(at) = walk.iter().position(|member| *member == current) {
                let cycle = &walk[at..];
                let first = (0..cycle.len()).min_by_key(|k| position[cycle[*k]]).unwrap_or(0);
                let turned = cycle[first..].iter().chain(cycle[..first].iter());
                found.push(turned.map(|member| (*member).clone()).collect());
            }
        }
        found.sort_by_key(|cycle| position[&cycle[0]]);
        found
    }
}
