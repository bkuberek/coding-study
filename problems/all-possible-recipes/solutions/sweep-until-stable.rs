use std::collections::HashSet;

pub fn find_all_recipes(
    recipes: Vec<String>,
    ingredients: Vec<Vec<String>>,
    supplies: Vec<String>,
) -> Vec<String> {
    let mut available: HashSet<&str> = supplies.iter().map(String::as_str).collect();
    let mut prepared = Vec::new();
    let mut pending: Vec<usize> = (0..recipes.len()).collect();
    let mut changed = true;
    while changed {
        changed = false;
        let mut still_pending = Vec::new();
        for i in pending {
            if ingredients[i]
                .iter()
                .all(|item| available.contains(item.as_str()))
            {
                available.insert(&recipes[i]);
                prepared.push(recipes[i].clone());
                changed = true;
            } else {
                still_pending.push(i);
            }
        }
        pending = still_pending;
    }
    prepared
}
