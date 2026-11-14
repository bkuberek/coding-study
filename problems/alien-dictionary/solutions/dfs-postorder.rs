const LETTERS: usize = 26;
const UNVISITED: u8 = 0;
const ON_PATH: u8 = 1;
const DONE: u8 = 2;

type Rules = [[bool; LETTERS]; LETTERS];

/// Emits everything after `x`, then `x`; false if a rule loops back.
fn visit(x: usize, before: &Rules, state: &mut [u8; LETTERS], finished: &mut String) -> bool {
    state[x] = ON_PATH;
    for y in 0..LETTERS {
        if !before[x][y] {
            continue;
        }
        if state[y] == ON_PATH || (state[y] == UNVISITED && !visit(y, before, state, finished)) {
            return false;
        }
    }
    state[x] = DONE;
    finished.push((b'a' + x as u8) as char);
    true
}

pub fn alien_order(words: Vec<String>) -> String {
    let mut present = [false; LETTERS];
    for word in &words {
        for letter in word.bytes() {
            present[(letter - b'a') as usize] = true;
        }
    }
    // before[x][y]: letter x must come before letter y.
    let mut before: Rules = [[false; LETTERS]; LETTERS];
    for pair in words.windows(2) {
        let (first, second) = (pair[0].as_bytes(), pair[1].as_bytes());
        let shorter = first.len().min(second.len());
        let mut k = 0;
        while k < shorter && first[k] == second[k] {
            k += 1;
        }
        if k < shorter {
            before[(first[k] - b'a') as usize][(second[k] - b'a') as usize] = true;
        } else if first.len() > second.len() {
            return String::new(); // a word placed before its own proper prefix
        }
    }
    let mut state = [UNVISITED; LETTERS];
    // Each letter lands in `finished` after every letter that must follow it.
    let mut finished = String::with_capacity(LETTERS);
    for x in 0..LETTERS {
        if present[x] && state[x] == UNVISITED && !visit(x, &before, &mut state, &mut finished) {
            return String::new();
        }
    }
    finished.chars().rev().collect()
}
