//! How items are named and labelled.

/// The name an item is counted under: its name without surrounding spaces.
pub fn item_key(name: &str) -> String {
    name.trim().to_string()
}

/// `<name>: <count>`.
pub fn label(name: &str, count: i32) -> String {
    format!("{name}: {count}")
}
