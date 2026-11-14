use std::collections::HashMap;

const LEGAL_FORMS: [&str; 7] = ["co", "company", "corp", "inc", "incorporated", "llc", "ltd"];
const TAX_ID_DIGITS: usize = 9;

pub fn duplicate_groups(names: Vec<String>, tax_ids: Vec<String>) -> Vec<Vec<i32>> {
    let mut parent: Vec<usize> = (0..names.len()).collect();
    let mut first_with_key: HashMap<(&str, String), usize> = HashMap::new();
    for (record, (name, tax_id)) in names.iter().zip(&tax_ids).enumerate() {
        for key in [
            ("name", normalize_name(name)),
            ("tax", normalize_tax_id(tax_id)),
        ] {
            if key.1.is_empty() {
                continue; // an empty key matches nothing
            }
            match first_with_key.get(&key) {
                Some(&first) => {
                    let (root, first_root) = (find(&mut parent, record), find(&mut parent, first));
                    parent[root] = first_root;
                }
                None => {
                    first_with_key.insert(key, record);
                }
            }
        }
    }

    // Groups are listed by their smallest member, so number the roots in the order they first appear.
    let mut group_of_root: HashMap<usize, usize> = HashMap::new();
    let mut groups: Vec<Vec<i32>> = Vec::new();
    for record in 0..names.len() {
        let root = find(&mut parent, record);
        let group = *group_of_root.entry(root).or_insert_with(|| {
            groups.push(Vec::new());
            groups.len() - 1
        });
        groups[group].push(record as i32);
    }
    groups.retain(|members| members.len() > 1);
    groups
}

/// The root of `record`'s set, halving the path on the way.
fn find(parent: &mut [usize], mut record: usize) -> usize {
    while parent[record] != record {
        parent[record] = parent[parent[record]];
        record = parent[record];
    }
    record
}

fn normalize_name(name: &str) -> String {
    let lowered = name.to_lowercase();
    let mut tokens: Vec<&str> = lowered
        .split(|character: char| !character.is_ascii_lowercase() && !character.is_ascii_digit())
        .filter(|token| !token.is_empty())
        .collect();
    while tokens
        .last()
        .is_some_and(|token| LEGAL_FORMS.contains(token))
    {
        tokens.pop();
    }
    tokens.join(" ")
}

fn normalize_tax_id(tax_id: &str) -> String {
    let digits: String = tax_id.chars().filter(char::is_ascii_digit).collect();
    if digits.len() == TAX_ID_DIGITS {
        digits
    } else {
        String::new()
    }
}
