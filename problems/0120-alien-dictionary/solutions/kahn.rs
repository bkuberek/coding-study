use std::collections::VecDeque;

const LETTERS: usize = 26;

pub fn alien_order(words: Vec<String>) -> String {
    let mut present = [false; LETTERS];
    for word in &words {
        for letter in word.bytes() {
            present[(letter - b'a') as usize] = true;
        }
    }
    // before[x][y]: letter x must come before letter y. A matrix dedupes repeated rules.
    let mut before = [[false; LETTERS]; LETTERS];
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
    let mut waiting = [0; LETTERS];
    for row in &before {
        for (y, &rule) in row.iter().enumerate() {
            if rule {
                waiting[y] += 1;
            }
        }
    }
    let mut ready = VecDeque::new();
    let mut letter_count = 0;
    for x in 0..LETTERS {
        if present[x] {
            letter_count += 1;
            if waiting[x] == 0 {
                ready.push_back(x);
            }
        }
    }
    let mut order = String::with_capacity(letter_count);
    while let Some(x) = ready.pop_front() {
        order.push((b'a' + x as u8) as char);
        for y in 0..LETTERS {
            if before[x][y] {
                waiting[y] -= 1;
                if waiting[y] == 0 {
                    ready.push_back(y);
                }
            }
        }
    }
    if order.len() == letter_count {
        order
    } else {
        String::new()
    }
}
