const BAD: i32 = 1;
const SKIP: i32 = 2;

pub fn first_bad_commit(statuses: Vec<i32>) -> Vec<i32> {
    let first_bad = find_first_bad(&statuses);
    let last_good = find_last_good_before(&statuses, first_bad);
    vec![last_good + 1, first_bad]
}

// Some commit is bad, so the first bad commit is somewhere in [low, high].
fn find_first_bad(statuses: &[i32]) -> i32 {
    let (mut low, mut high) = (0_i32, statuses.len() as i32 - 1);
    while low < high {
        let middle = low + (high - low) / 2;
        let mut probe = middle;
        while probe >= low && statuses[probe as usize] == SKIP {
            probe -= 1;
        }
        if probe >= low && statuses[probe as usize] == BAD {
            high = probe;
        } else {
            low = middle + 1;
        }
    }
    low
}

// Before the first bad commit every commit that was tested is good. The last good one is somewhere
// in [low, high], where -1 stands for "none", so positions are signed.
fn find_last_good_before(statuses: &[i32], first_bad: i32) -> i32 {
    let (mut low, mut high) = (-1_i32, first_bad - 1);
    while low < high {
        let middle = (low + high + 1) / 2;
        let mut probe = middle;
        while probe <= high && statuses[probe as usize] == SKIP {
            probe += 1;
        }
        if probe <= high {
            low = probe;
        } else {
            high = middle - 1;
        }
    }
    low
}
