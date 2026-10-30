const ALPHABET_SIZE: usize = 26;

/// Per-letter surplus of the window over the pattern, and how many letters have none.
struct Balance {
    surplus: [i32; ALPHABET_SIZE],
    balanced: usize,
}

impl Balance {
    fn against(pattern: &[u8]) -> Self {
        let mut surplus = [0i32; ALPHABET_SIZE];
        for &byte in pattern {
            surplus[usize::from(byte - b'a')] -= 1;
        }
        let balanced = surplus.iter().filter(|&&value| value == 0).count();
        Balance { surplus, balanced }
    }

    fn shift(&mut self, byte: u8, delta: i32) {
        let letter = usize::from(byte - b'a');
        if self.surplus[letter] == 0 {
            self.balanced -= 1;
        }
        self.surplus[letter] += delta;
        if self.surplus[letter] == 0 {
            self.balanced += 1;
        }
    }
}

pub fn check_inclusion(pattern: String, text: String) -> bool {
    let (pattern, text) = (pattern.as_bytes(), text.as_bytes());
    let width = pattern.len();
    if width > text.len() {
        return false;
    }
    let mut window = Balance::against(pattern);
    for (right, &byte) in text.iter().enumerate() {
        window.shift(byte, 1);
        if right >= width {
            window.shift(text[right - width], -1);
        }
        if window.balanced == ALPHABET_SIZE {
            return true;
        }
    }
    false
}
