const ALPHABET_SIZE: usize = 26;
const USED: char = '#';
const STEPS: [(isize, isize); 4] = [(1, 0), (-1, 0), (0, 1), (0, -1)];

#[derive(Default)]
struct Node {
    children: [Option<Box<Node>>; ALPHABET_SIZE],
    /// The complete word that ends at this node, until it has been reported.
    word: Option<String>,
}

pub fn find_words(mut board: Vec<Vec<char>>, words: Vec<String>) -> Vec<String> {
    let mut root = Node::default();
    for word in words {
        let mut node = &mut root;
        for letter in word.chars() {
            node = node.children[slot(letter)].get_or_insert_with(Box::default);
        }
        node.word = Some(word);
    }
    let mut found = Vec::new();
    for row in 0..board.len() {
        for col in 0..board[0].len() {
            explore(&mut board, (row, col), &mut root, &mut found);
        }
    }
    found
}

fn explore(
    board: &mut [Vec<char>],
    cell: (usize, usize),
    parent: &mut Node,
    found: &mut Vec<String>,
) {
    let (row, col) = cell;
    let letter = board[row][col];
    if letter == USED {
        return;
    }
    let Some(node) = parent.children[slot(letter)].as_deref_mut() else {
        return;
    };
    if let Some(word) = node.word.take() {
        found.push(word);
    }
    board[row][col] = USED;
    for step in STEPS {
        if let Some(next) = neighbor(board, cell, step) {
            explore(board, next, node, found);
        }
    }
    board[row][col] = letter;
}

/// The cell one `step` away, or `None` when it falls off the board.
fn neighbor(
    board: &[Vec<char>],
    cell: (usize, usize),
    step: (isize, isize),
) -> Option<(usize, usize)> {
    let row = cell.0.checked_add_signed(step.0)?;
    let col = cell.1.checked_add_signed(step.1)?;
    (row < board.len() && col < board[0].len()).then_some((row, col))
}

fn slot(letter: char) -> usize {
    usize::from(letter as u8 - b'a')
}
