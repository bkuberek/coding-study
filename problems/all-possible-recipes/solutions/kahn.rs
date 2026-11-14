use std::collections::{HashMap, VecDeque};

pub fn find_all_recipes(
    recipes: Vec<String>,
    ingredients: Vec<Vec<String>>,
    supplies: Vec<String>,
) -> Vec<String> {
    let mut used_by: HashMap<&str, Vec<usize>> = HashMap::new();
    for (i, items) in ingredients.iter().enumerate() {
        for item in items {
            used_by.entry(item).or_default().push(i);
        }
    }
    // Ingredients each recipe still lacks.
    let mut missing: Vec<usize> = ingredients.iter().map(Vec::len).collect();
    let mut available: VecDeque<&str> = supplies.iter().map(String::as_str).collect();
    let mut prepared = Vec::new();
    while let Some(item) = available.pop_front() {
        let Some(users) = used_by.get(item) else {
            continue;
        };
        for &i in users {
            missing[i] -= 1;
            if missing[i] == 0 {
                prepared.push(recipes[i].clone());
                available.push_back(&recipes[i]);
            }
        }
    }
    prepared
}
