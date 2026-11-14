use std::collections::{BTreeMap, BTreeSet, HashMap};

struct DisjointSet {
    parent: Vec<usize>,
    size: Vec<usize>, // size[r]: number of accounts in the tree rooted at r
}

impl DisjointSet {
    fn new(count: usize) -> Self {
        DisjointSet {
            parent: (0..count).collect(),
            size: vec![1; count],
        }
    }

    fn find(&mut self, mut x: usize) -> usize {
        let mut root = x;
        while self.parent[root] != root {
            root = self.parent[root];
        }
        while self.parent[x] != root {
            // path compression: point the whole path at the root
            let next = self.parent[x];
            self.parent[x] = root;
            x = next;
        }
        root
    }

    fn union(&mut self, a: usize, b: usize) {
        let (mut root_a, mut root_b) = (self.find(a), self.find(b));
        if root_a == root_b {
            return;
        }
        if self.size[root_a] < self.size[root_b] {
            std::mem::swap(&mut root_a, &mut root_b);
        }
        self.parent[root_b] = root_a; // union by size: the smaller tree goes under the larger
        self.size[root_a] += self.size[root_b];
    }
}

pub fn accounts_merge(accounts: Vec<Vec<String>>) -> Vec<Vec<String>> {
    let mut set = DisjointSet::new(accounts.len());
    let mut first_owner: HashMap<&str, usize> = HashMap::new(); // address -> first account that listed it
    for (i, account) in accounts.iter().enumerate() {
        for address in &account[1..] {
            let owner = *first_owner.entry(address).or_insert(i);
            set.union(owner, i);
        }
    }

    // A `BTreeSet` keeps each person's addresses in sorted order as they are added.
    let mut addresses_by_root: BTreeMap<usize, BTreeSet<&str>> = BTreeMap::new();
    for (i, account) in accounts.iter().enumerate() {
        addresses_by_root
            .entry(set.find(i))
            .or_default()
            .extend(account[1..].iter().map(String::as_str));
    }
    addresses_by_root
        .into_iter()
        .map(|(root, addresses)| {
            let mut person = vec![accounts[root][0].clone()];
            person.extend(addresses.into_iter().map(String::from));
            person
        })
        .collect()
}
