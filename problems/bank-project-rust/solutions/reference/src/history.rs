//! The balances an account had over time.

/// One balance, from the moment `at` on.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
struct Change {
    at: i64,
    balance: i64,
}

/// Balances in time order, each recorded at the moment its change took effect.
#[derive(Debug, Default)]
pub struct History {
    changes: Vec<Change>,
}

impl History {
    /// Records `balance` from `at` on. Moments never go back, so the record stays sorted.
    pub fn record(&mut self, at: i64, balance: i64) {
        self.changes.push(Change { at, balance });
    }

    /// The balance after every change at or before `moment`; `None` before the first change.
    pub fn at(&self, moment: i64) -> Option<i64> {
        let changes_so_far = self.changes.partition_point(|change| change.at <= moment);
        let last = changes_so_far.checked_sub(1)?;
        Some(self.changes[last].balance)
    }
}

#[cfg(test)]
mod tests {
    use super::History;

    fn history(changes: &[(i64, i64)]) -> History {
        let mut history = History::default();
        for &(at, balance) in changes {
            history.record(at, balance);
        }
        history
    }

    #[test]
    fn nothing_is_known_before_the_first_change() {
        assert_eq!(history(&[(10, 0)]).at(9), None);
    }

    #[test]
    fn a_change_holds_from_its_own_moment() {
        assert_eq!(history(&[(10, 0), (20, 5)]).at(20), Some(5));
    }

    #[test]
    fn a_change_holds_until_the_next_one() {
        assert_eq!(history(&[(10, 0), (20, 5), (30, 9)]).at(29), Some(5));
    }

    #[test]
    fn the_last_of_several_changes_at_one_moment_answers() {
        assert_eq!(
            history(&[(10, 0), (20, 5), (20, 7), (20, 3)]).at(20),
            Some(3)
        );
    }

    #[test]
    fn the_latest_change_holds_for_every_later_moment() {
        assert_eq!(history(&[(10, 0), (20, 5)]).at(i64::MAX), Some(5));
    }
}
