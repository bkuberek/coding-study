const SHOWN: usize = 3;

pub fn suggested_products(products: Vec<String>, search_word: String) -> Vec<Vec<String>> {
    (1..=search_word.len())
        .map(|typed| {
            let prefix = &search_word[..typed];
            let mut matches: Vec<&String> = products
                .iter()
                .filter(|product| product.starts_with(prefix))
                .collect();
            matches.sort();
            matches.into_iter().take(SHOWN).cloned().collect()
        })
        .collect()
}
