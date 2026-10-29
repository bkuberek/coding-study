pub fn is_valid(s: String) -> bool {
    let mut current = s;
    loop {
        let shorter = current
            .replace("()", "")
            .replace("[]", "")
            .replace("{}", "");
        if shorter.len() == current.len() {
            // Nothing left to delete: balanced exactly when nothing is left at all.
            return current.is_empty();
        }
        current = shorter;
    }
}
