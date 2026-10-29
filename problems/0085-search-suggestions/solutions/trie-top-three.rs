const ALPHABET_SIZE: usize = 26;
const SHOWN: usize = 3;

#[derive(Default)]
struct Node {
    children: [Option<Box<Node>>; ALPHABET_SIZE],
    smallest: Vec<String>,
}

pub fn suggested_products(products: Vec<String>, search_word: String) -> Vec<Vec<String>> {
    let mut ordered = products;
    ordered.sort();
    let mut root = Node::default();
    // Inserting in sorted order means each node's first three products are its smallest.
    for product in &ordered {
        let mut node = &mut root;
        for letter in product.bytes() {
            node = node.children[slot(letter)].get_or_insert_with(Box::default);
            if node.smallest.len() < SHOWN {
                node.smallest.push(product.clone());
            }
        }
    }
    let mut suggestions = Vec::with_capacity(search_word.len());
    let mut cursor = Some(&root);
    for letter in search_word.bytes() {
        cursor = cursor.and_then(|node| node.children[slot(letter)].as_deref());
        suggestions.push(cursor.map_or_else(Vec::new, |node| node.smallest.clone()));
    }
    suggestions
}

fn slot(letter: u8) -> usize {
    usize::from(letter - b'a')
}
