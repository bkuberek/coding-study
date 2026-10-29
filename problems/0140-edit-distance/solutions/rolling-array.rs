pub fn min_distance(word1: String, word2: String) -> i32 {
    // The distance is symmetric (insertions and deletions swap roles), so let the rows run
    // along the shorter word.
    let (longer, shorter) = if word1.len() >= word2.len() {
        (word1.as_bytes(), word2.as_bytes())
    } else {
        (word2.as_bytes(), word1.as_bytes())
    };
    // previous[j] is the distance between longer[..i - 1] and shorter[..j]; current is the row
    // being filled, and the two swap after every character of longer.
    let mut previous: Vec<i32> = (0..=shorter.len() as i32).collect();
    let mut current = vec![0; shorter.len() + 1];
    for (i, &character) in longer.iter().enumerate() {
        current[0] = i as i32 + 1;
        for (j, &other) in shorter.iter().enumerate() {
            current[j + 1] = if character == other {
                previous[j]
            } else {
                1 + previous[j + 1].min(current[j]).min(previous[j])
            };
        }
        std::mem::swap(&mut previous, &mut current);
    }
    previous[shorter.len()]
}
