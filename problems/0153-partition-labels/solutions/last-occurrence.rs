pub fn partition_labels(s: String) -> Vec<i32> {
    let bytes = s.as_bytes();
    let mut last = [0usize; 26];
    for (index, &letter) in bytes.iter().enumerate() {
        last[(letter - b'a') as usize] = index;
    }
    let mut sizes = Vec::new();
    let (mut start, mut end) = (0, 0);
    for (index, &letter) in bytes.iter().enumerate() {
        end = end.max(last[(letter - b'a') as usize]);
        if index == end {
            // Every letter seen since `start` has no copy after this point: cut here.
            sizes.push((end + 1 - start) as i32);
            start = index + 1;
        }
    }
    sizes
}
