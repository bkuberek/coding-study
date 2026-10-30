use std::collections::{HashMap, HashSet};

#[derive(Clone, Copy)]
enum Verdict {
    OnPath, // the recipe is being explored right now
    Possible,
    Impossible,
}

struct Kitchen<'a> {
    needs: HashMap<&'a str, &'a [String]>,
    stocked: HashSet<&'a str>,
    // Memo per recipe: decided once, `OnPath` while it is being explored.
    verdict: HashMap<&'a str, Verdict>,
}

impl<'a> Kitchen<'a> {
    fn can_prepare(&mut self, item: &'a str) -> bool {
        if self.stocked.contains(item) {
            return true;
        }
        let Some(&ingredients) = self.needs.get(item) else {
            return false; // neither a supply nor a recipe
        };
        match self.verdict.get(item) {
            Some(Verdict::OnPath) => return false, // the ingredients loop back to this recipe
            Some(Verdict::Possible) => return true,
            Some(Verdict::Impossible) => return false,
            None => {}
        }
        self.verdict.insert(item, Verdict::OnPath);
        let result = ingredients
            .iter()
            .all(|ingredient| self.can_prepare(ingredient));
        let decided = if result {
            Verdict::Possible
        } else {
            Verdict::Impossible
        };
        self.verdict.insert(item, decided);
        result
    }
}

pub fn find_all_recipes(
    recipes: Vec<String>,
    ingredients: Vec<Vec<String>>,
    supplies: Vec<String>,
) -> Vec<String> {
    let mut kitchen = Kitchen {
        needs: recipes
            .iter()
            .map(String::as_str)
            .zip(ingredients.iter().map(Vec::as_slice))
            .collect(),
        stocked: supplies.iter().map(String::as_str).collect(),
        verdict: HashMap::new(),
    };
    recipes
        .iter()
        .filter(|recipe| kitchen.can_prepare(recipe))
        .cloned()
        .collect()
}
