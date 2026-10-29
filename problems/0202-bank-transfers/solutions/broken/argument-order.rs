use std::sync::{Mutex, MutexGuard};

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
        if from == to {
            return *self.lock(from) >= amount;
        }
        let mut source = self.lock(from);
        let mut target = self.lock(to);
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
