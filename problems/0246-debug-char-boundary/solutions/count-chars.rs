pub fn truncate_label(label: String, width: i32) -> String {
    let width = width as usize;
    // len() counts UTF-8 bytes; the width is in characters.
    if label.chars().count() <= width {
        return label;
    }
    // chars() steps one whole character at a time, so the cut can never fall inside one, which is
    // what slicing at a byte index would risk.
    let mut short: String = label.chars().take(width - 1).collect();
    short.push('…');
    short
}
