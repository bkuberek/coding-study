use std::collections::{BTreeMap, BTreeSet, HashMap};

fn find(parent: &[usize], mut x: usize) -> usize {
    while parent[x] != x {
        x = parent[x];
    }
    x
}

pub fn accounts_merge(accounts: Vec<Vec<String>>) -> Vec<Vec<String>> {
    let mut parent: Vec<usize> = (0..accounts.len()).collect(); // parent[x] == x marks a root

    let mut first_owner: HashMap<&str, usize> = HashMap::new(); // address -> first account that listed it
    for (i, account) in accounts.iter().enumerate() {
        for address in &account[1..] {
            let owner = *first_owner.entry(address).or_insert(i);
            let (root_owner, root_here) = (find(&parent, owner), find(&parent, i));
            if root_owner != root_here {
                parent[root_owner] = root_here; // no balancing: trees can grow into long chains
            }
        }
    }

    // A `BTreeSet` keeps each person's addresses in sorted order as they are added.
    let mut addresses_by_root: BTreeMap<usize, BTreeSet<&str>> = BTreeMap::new();
    for (i, account) in accounts.iter().enumerate() {
        addresses_by_root
            .entry(find(&parent, i))
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
