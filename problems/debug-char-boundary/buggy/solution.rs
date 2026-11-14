// Debug: Char Boundary. Some tests fail: find the bug and fix it.
pub fn truncate_label(label: String, width: i32) -> String {
    let width = width as usize;
    if label.len() <= width {
        return label;
    }
    format!("{}…", &label[..width - 1])
}
