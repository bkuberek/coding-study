pub fn longest_palindrome(s: String) -> String {
    let bytes = s.as_bytes();
    // Interleave a separator so every palindrome has odd length: "ab" becomes "|a|b|".
    let mut t = vec![b'|'; 2 * bytes.len() + 1];
    for (i, &byte) in bytes.iter().enumerate() {
        t[2 * i + 1] = byte;
    }
    // radius[i] is how far the palindrome centered at t[i] extends to each side.
    let mut radius = vec![0usize; t.len()];
    // The palindrome reaching furthest right is t[2 * center - right ..= right].
    let (mut center, mut right) = (0, 0);
    for i in 0..t.len() {
        if i < right {
            // Mirror of i around center; its radius is valid up to the right boundary.
            radius[i] = (right - i).min(radius[2 * center - i]);
        }
        // `radius[i] < i` is the unsigned form of `i - radius[i] - 1 >= 0`.
        while radius[i] < i
            && i + radius[i] + 1 < t.len()
            && t[i - radius[i] - 1] == t[i + radius[i] + 1]
        {
            radius[i] += 1;
        }
        if i + radius[i] > right {
            center = i;
            right = i + radius[i];
        }
    }
    let mut best = 0;
    for (i, &r) in radius.iter().enumerate() {
        if r > radius[best] {
            best = i;
        }
    }
    // A radius r around position i of t covers r characters of s starting at (i - r) / 2.
    let start = (best - radius[best]) / 2;
    s[start..start + radius[best]].to_string()
}
