use chrono::NaiveDate;

pub fn coverage_gaps(
    periods: Vec<Vec<NaiveDate>>,
    window_start: NaiveDate,
    window_end: NaiveDate,
) -> Vec<Vec<NaiveDate>> {
    // The vector is owned, so it is the copy to sort.
    let mut sorted = periods;
    sorted.sort_by_key(|period| period[0]);
    let mut gaps = Vec::new();
    // Every day of the window before `cursor` is covered or already reported.
    let mut cursor = window_start;
    for period in &sorted {
        if cursor >= window_end {
            break;
        }
        if period[0] > cursor {
            gaps.push(vec![cursor, period[0].min(window_end)]);
        }
        if period[1] > cursor {
            cursor = period[1];
        }
    }
    if cursor < window_end {
        gaps.push(vec![cursor, window_end]);
    }
    gaps
}
