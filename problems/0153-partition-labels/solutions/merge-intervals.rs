pub fn partition_labels(s: String) -> Vec<i32> {
    // Each letter occupies the span from its first to its last copy. Spans listed by first
    // occurrence are already sorted by start, so merging overlapping spans gives the pieces.
    const UNSEEN: usize = usize::MAX;
    let mut first = [UNSEEN; 26];
    let mut last = [0usize; 26];
    let mut letters = Vec::new(); // slots of the letters, by first occurrence
    for (index, &letter) in s.as_bytes().iter().enumerate() {
        let slot = (letter - b'a') as usize;
        if first[slot] == UNSEEN {
            first[slot] = index;
            letters.push(slot);
        }
        last[slot] = index;
    }
    let mut sizes = Vec::new();
    // The current piece is piece_start..piece_end, with an exclusive end; it is empty before
    // the first letter.
    let (mut piece_start, mut piece_end) = (0, 0);
    for slot in letters {
        if first[slot] >= piece_end {
            if piece_end > piece_start {
                sizes.push((piece_end - piece_start) as i32);
            }
            piece_start = first[slot];
        }
        piece_end = piece_end.max(last[slot] + 1);
    }
    sizes.push((piece_end - piece_start) as i32);
    sizes
}
