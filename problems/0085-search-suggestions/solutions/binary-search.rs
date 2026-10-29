const SHOWN: usize = 3;

pub fn suggested_products(products: Vec<String>, search_word: String) -> Vec<Vec<String>> {
    let mut ordered = products;
    ordered.sort();
    let mut suggestions = Vec::with_capacity(search_word.len());
    let mut start = 0;
    for typed in 1..=search_word.len() {
        let prefix = &search_word[..typed];
        // Products starting with `prefix` form one block; it begins at the first product >= prefix.
        // A longer prefix never begins its block earlier, so the search can start at `start`.
        start += ordered[start..].partition_point(|product| product.as_str() < prefix);
        suggestions.push(
            ordered[start..]
                .iter()
                .take(SHOWN)
                .filter(|product| product.starts_with(prefix))
                .cloned()
                .collect(),
        );
    }
    suggestions
}
