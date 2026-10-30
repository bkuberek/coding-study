pub fn check_inclusion(pattern: String, text: String) -> bool {
    let mut target = pattern.into_bytes();
    target.sort_unstable();
    text.as_bytes().windows(target.len()).any(|window| {
        let mut sorted = window.to_vec();
        sorted.sort_unstable();
        sorted == target
    })
}
