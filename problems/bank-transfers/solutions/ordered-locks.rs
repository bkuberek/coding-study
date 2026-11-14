use std::sync::{Mutex, MutexGuard};

/// One mutex per account. A transfer locks its two accounts in index order and an audit locks
/// every account in index order, so no two of them can wait for each other in a cycle.
pub struct Bank {
    balances: Vec<Mutex<i64>>,
}

impl Bank {
    pub fn new(balances: Vec<i64>) -> Self {
        Bank {
            balances: balances.into_iter().map(Mutex::new).collect(),
        }
    }

    pub fn transfer(&self, from_account: i32, to_account: i32, amount: i64) -> bool {
        let (Some(from), Some(to)) = (self.index(from_account), self.index(to_account)) else {
            return false;
        };
        // A `Mutex` is not reentrant: locking it twice on one thread never returns.
        if from == to {
            return *self.lock(from) >= amount;
        }
        let mut first = self.lock(from.min(to));
        let mut second = self.lock(from.max(to));
        let (source, target) = if from < to {
            (&mut *first, &mut *second)
        } else {
            (&mut *second, &mut *first)
        };
        if *source < amount {
            return false;
        }
        *source -= amount;
        *target += amount;
        true
    }

    pub fn balance(&self, account: i32) -> i64 {
        self.index(account)
            .map_or(-1, |account| *self.lock(account))
    }

    pub fn total(&self) -> i64 {
        let guards: Vec<MutexGuard<i64>> = (0..self.balances.len())
            .map(|account| self.lock(account))
            .collect();
        guards.iter().map(|balance| **balance).sum()
    }

    fn lock(&self, account: usize) -> MutexGuard<i64> {
        self.balances[account].lock().unwrap()
    }

    fn index(&self, account: i32) -> Option<usize> {
        usize::try_from(account)
            .ok()
            .filter(|&account| account < self.balances.len())
    }
}
