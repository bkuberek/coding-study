struct Node {
    leaf: bool,
    keys: Vec<Vec<i32>>,
    rows: Vec<i32>,
    children: Vec<usize>,
    next: Option<usize>,
}

impl Node {
    fn new(leaf: bool) -> Self {
        Node { leaf, keys: Vec::new(), rows: Vec::new(), children: Vec::new(), next: None }
    }
}

/// A B+ tree: every entry lives in a leaf, the leaves are linked left to right, and the inner
/// nodes hold separator keys that only steer the way down. Keys are `Vec<i32>`, whose derived
/// order compares field by field, exactly the order of a composite key.
///
/// The nodes live in an arena and refer to each other by index, so the leaf links and the path
/// kept on the way down are plain integers. A node that a merge empties stays in the arena,
/// unreachable.
pub struct BTreeIndex {
    d: usize,
    nodes: Vec<Node>,
    root: usize,
}

impl BTreeIndex {
    pub fn new(min_keys: i32) -> Self {
        BTreeIndex { d: min_keys as usize, nodes: vec![Node::new(true)], root: 0 }
    }

    // Level 1
    pub fn search(&mut self, key: Vec<i32>) -> i32 {
        let (leaf, _) = self.descend(&key);
        match self.nodes[leaf].keys.binary_search(&key) {
            Ok(at) => self.nodes[leaf].rows[at],
            Err(_) => -1,
        }
    }

    pub fn insert(&mut self, key: Vec<i32>, row_id: i32) -> bool {
        let (leaf, path) = self.descend(&key);
        let at = match self.nodes[leaf].keys.binary_search(&key) {
            Ok(_) => return false,
            Err(at) => at,
        };
        self.nodes[leaf].keys.insert(at, key);
        self.nodes[leaf].rows.insert(at, row_id);
        self.split_upward(leaf, path);
        true
    }

    pub fn levels(&mut self) -> Vec<String> {
        let mut lines = Vec::new();
        let mut level = vec![self.root];
        while !level.is_empty() {
            let shown: Vec<String> = level.iter().map(|&n| self.show(n)).collect();
            lines.push(shown.join(" "));
            level = level.iter().flat_map(|&n| self.nodes[n].children.clone()).collect();
        }
        lines
    }

    // Level 2
    pub fn range_scan(&mut self, low: Vec<i32>, high: Vec<i32>) -> Vec<i32> {
        self.scan(&low, &high).0
    }

    pub fn scan_visits(&mut self, low: Vec<i32>, high: Vec<i32>) -> i32 {
        self.scan(&low, &high).1
    }

    pub fn height(&mut self) -> i32 {
        let (mut count, mut node) = (1, self.root);
        while !self.nodes[node].leaf {
            node = self.nodes[node].children[0];
            count += 1;
        }
        count
    }

    // Level 3
    pub fn remove(&mut self, key: Vec<i32>) -> bool {
        let (leaf, mut path) = self.descend(&key);
        let at = match self.nodes[leaf].keys.binary_search(&key) {
            Ok(at) => at,
            Err(_) => return false,
        };
        self.nodes[leaf].keys.remove(at);
        self.nodes[leaf].rows.remove(at);
        let mut current = leaf;
        while self.nodes[current].keys.len() < self.d {
            let Some((parent, index)) = path.pop() else { break };
            if self.nodes[current].leaf {
                self.fix_leaf(parent, index);
            } else {
                self.fix_inner(parent, index);
            }
            current = parent;
        }
        let root = self.root;
        if !self.nodes[root].leaf && self.nodes[root].keys.is_empty() {
            self.root = self.nodes[root].children[0];
        }
        true
    }

    // Level 4
    pub fn bulk_load(&mut self, keys: Vec<Vec<i32>>, row_ids: Vec<i32>, fill_percent: i32) -> bool {
        if !self.nodes[self.root].leaf || !self.nodes[self.root].keys.is_empty() {
            return false;
        }
        if keys.windows(2).any(|pair| pair[0] >= pair[1]) {
            return false;
        }
        if keys.is_empty() {
            return true;
        }
        let d = self.d;
        let per = 2 * d * fill_percent as usize / 100;
        let mut level: Vec<usize> = Vec::new();
        let mut lowest: Vec<Vec<i32>> = Vec::new();
        let mut start = 0;
        for size in sizes(keys.len(), per, d, 2 * d) {
            let mut leaf = Node::new(true);
            leaf.keys = keys[start..start + size].to_vec();
            leaf.rows = row_ids[start..start + size].to_vec();
            lowest.push(leaf.keys[0].clone());
            let id = self.add(leaf);
            if let Some(&previous) = level.last() {
                self.nodes[previous].next = Some(id);
            }
            level.push(id);
            start += size;
        }
        while level.len() > 1 {
            let mut parents = Vec::new();
            let mut parent_lowest = Vec::new();
            start = 0;
            for size in sizes(level.len(), per + 1, d + 1, 2 * d + 1) {
                let mut parent = Node::new(false);
                parent.children = level[start..start + size].to_vec();
                parent.keys = lowest[start + 1..start + size].to_vec();
                parent_lowest.push(lowest[start].clone());
                parents.push(self.add(parent));
                start += size;
            }
            level = parents;
            lowest = parent_lowest;
        }
        self.root = level[0];
        true
    }

    pub fn prefix_scan(&mut self, prefix: Vec<i32>) -> Vec<i32> {
        let width = prefix.len();
        let mut node = self.root;
        while !self.nodes[node].leaf {
            let index = self.nodes[node].keys.iter().filter(|s| s[..width] < prefix[..]).count();
            node = self.nodes[node].children[index];
        }
        let mut rows = Vec::new();
        let mut leaf = Some(node);
        while let Some(id) = leaf {
            let current = &self.nodes[id];
            for (key, &row) in current.keys.iter().zip(&current.rows) {
                if key[..width] > prefix[..] {
                    return rows;
                }
                if key[..width] == prefix[..] {
                    rows.push(row);
                }
            }
            leaf = current.next;
        }
        rows
    }

    // Helpers
    fn add(&mut self, node: Node) -> usize {
        self.nodes.push(node);
        self.nodes.len() - 1
    }

    fn descend(&self, key: &[i32]) -> (usize, Vec<(usize, usize)>) {
        let mut path = Vec::new();
        let mut node = self.root;
        while !self.nodes[node].leaf {
            let index = self.nodes[node].keys.partition_point(|s| s.as_slice() <= key);
            path.push((node, index));
            node = self.nodes[node].children[index];
        }
        (node, path)
    }

    fn show(&self, node: usize) -> String {
        let keys: Vec<String> = self.nodes[node]
            .keys
            .iter()
            .map(|key| key.iter().map(|f| f.to_string()).collect::<Vec<_>>().join(","))
            .collect();
        format!("[{}]", keys.join(" "))
    }

    fn split_upward(&mut self, leaf: usize, mut path: Vec<(usize, usize)>) {
        let d = self.d;
        if self.nodes[leaf].keys.len() <= 2 * d {
            return;
        }
        let mut right = Node::new(true);
        right.keys = self.nodes[leaf].keys.split_off(d);
        right.rows = self.nodes[leaf].rows.split_off(d);
        right.next = self.nodes[leaf].next;
        let mut separator = right.keys[0].clone();
        let mut created = self.add(right);
        self.nodes[leaf].next = Some(created);
        let mut left = leaf;
        while let Some((parent, index)) = path.pop() {
            self.nodes[parent].keys.insert(index, separator);
            self.nodes[parent].children.insert(index + 1, created);
            if self.nodes[parent].keys.len() <= 2 * d {
                return;
            }
            let mut sibling = Node::new(false);
            sibling.keys = self.nodes[parent].keys.split_off(d + 1);
            sibling.children = self.nodes[parent].children.split_off(d + 1);
            separator = self.nodes[parent].keys.pop().expect("the middle key");
            created = self.add(sibling);
            left = parent;
        }
        let mut top = Node::new(false);
        top.keys.push(separator);
        top.children = vec![left, created];
        self.root = self.add(top);
    }

    fn scan(&self, low: &[i32], high: &[i32]) -> (Vec<i32>, i32) {
        let (mut leaf, path) = self.descend(low);
        let mut visits = path.len() as i32 + 1;
        let mut rows = Vec::new();
        let mut at = self.nodes[leaf].keys.partition_point(|k| k.as_slice() < low);
        loop {
            let current = &self.nodes[leaf];
            while at < current.keys.len() {
                if current.keys[at].as_slice() > high {
                    return (rows, visits);
                }
                rows.push(current.rows[at]);
                at += 1;
            }
            match current.next {
                None => return (rows, visits),
                Some(next) => {
                    leaf = next;
                    at = 0;
                    visits += 1;
                }
            }
        }
    }

    fn siblings(&self, parent: usize, index: usize) -> (Option<usize>, Option<usize>) {
        let children = &self.nodes[parent].children;
        let left = if index > 0 { Some(children[index - 1]) } else { None };
        (left, children.get(index + 1).copied())
    }

    fn fix_leaf(&mut self, parent: usize, index: usize) {
        let node = self.nodes[parent].children[index];
        let (left, right) = self.siblings(parent, index);
        let d = self.d;
        match (left, right) {
            (Some(l), _) if self.nodes[l].keys.len() > d => {
                let key = self.nodes[l].keys.pop().unwrap();
                let row = self.nodes[l].rows.pop().unwrap();
                self.nodes[node].keys.insert(0, key.clone());
                self.nodes[node].rows.insert(0, row);
                self.nodes[parent].keys[index - 1] = key;
            }
            (_, Some(r)) if self.nodes[r].keys.len() > d => {
                let key = self.nodes[r].keys.remove(0);
                let row = self.nodes[r].rows.remove(0);
                self.nodes[node].keys.push(key);
                self.nodes[node].rows.push(row);
                self.nodes[parent].keys[index] = self.nodes[r].keys[0].clone();
            }
            (Some(l), _) => self.merge_leaves(parent, index - 1, l, node),
            (None, Some(r)) => self.merge_leaves(parent, index, node, r),
            (None, None) => unreachable!("a node below the root has a sibling"),
        }
    }

    fn merge_leaves(&mut self, parent: usize, first: usize, left: usize, right: usize) {
        let keys = std::mem::take(&mut self.nodes[right].keys);
        let rows = std::mem::take(&mut self.nodes[right].rows);
        self.nodes[left].keys.extend(keys);
        self.nodes[left].rows.extend(rows);
        self.nodes[left].next = self.nodes[right].next;
        self.nodes[parent].keys.remove(first);
        self.nodes[parent].children.remove(first + 1);
    }

    fn fix_inner(&mut self, parent: usize, index: usize) {
        let node = self.nodes[parent].children[index];
        let (left, right) = self.siblings(parent, index);
        let d = self.d;
        match (left, right) {
            (Some(l), _) if self.nodes[l].keys.len() > d => {
                let lifted = self.nodes[l].keys.pop().unwrap();
                let child = self.nodes[l].children.pop().unwrap();
                let lowered = std::mem::replace(&mut self.nodes[parent].keys[index - 1], lifted);
                self.nodes[node].keys.insert(0, lowered);
                self.nodes[node].children.insert(0, child);
            }
            (_, Some(r)) if self.nodes[r].keys.len() > d => {
                let lifted = self.nodes[r].keys.remove(0);
                let child = self.nodes[r].children.remove(0);
                let lowered = std::mem::replace(&mut self.nodes[parent].keys[index], lifted);
                self.nodes[node].keys.push(lowered);
                self.nodes[node].children.push(child);
            }
            (Some(l), _) => self.merge_inner(parent, index - 1, l, node),
            (None, Some(r)) => self.merge_inner(parent, index, node, r),
            (None, None) => unreachable!("a node below the root has a sibling"),
        }
    }

    fn merge_inner(&mut self, parent: usize, first: usize, left: usize, right: usize) {
        let separator = self.nodes[parent].keys.remove(first);
        self.nodes[parent].children.remove(first + 1);
        let keys = std::mem::take(&mut self.nodes[right].keys);
        let children = std::mem::take(&mut self.nodes[right].children);
        self.nodes[left].keys.push(separator);
        self.nodes[left].keys.extend(keys);
        self.nodes[left].children.extend(children);
    }
}

fn sizes(total: usize, per: usize, minimum: usize, maximum: usize) -> Vec<usize> {
    let mut result = vec![per; total / per];
    if total % per != 0 {
        result.push(total % per);
    }
    if result.len() > 1 && result[result.len() - 1] < minimum {
        let pool = result.pop().unwrap() + result.pop().unwrap();
        if pool <= maximum {
            result.push(pool);
        } else {
            result.extend([(pool + 1) / 2, pool / 2]);
        }
    }
    result
}
