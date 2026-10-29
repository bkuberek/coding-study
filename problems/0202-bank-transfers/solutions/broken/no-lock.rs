use std::sync::atomic::{AtomicI64, Ordering};

pub struct Bank {
    balances: Vec<AtomicI64>,
}

impl Bank {
    pub fn new(balances: Vec<i64>) -> Self {
        Bank {
            balances: balances.into_iter().map(AtomicI64::new).collect(),
        }
    }

    pub fn transfer(&self, from_account: i32, to_account: i32, amount: i64) -> bool {
        let (Some(from), Some(to)) = (self.index(from_account), self.index(to_account)) else {
            return false;
        };
        let source = self.balances[from].load(Ordering::SeqCst);
        if source < amount {
            return false;
        }
        self.balances[from].store(source - amount, Ordering::SeqCst);
        let target = self.balances[to].load(Ordering::SeqCst);
        self.balances[to].store(target + amount, Ordering::SeqCst);
        true
    }

    pub fn balance(&self, account: i32) -> i64 {
        self.index(account)
            .map_or(-1, |account| self.balances[account].load(Ordering::SeqCst))
    }

    pub fn total(&self) -> i64 {
        self.balances
            .iter()
            .map(|balance| balance.load(Ordering::SeqCst))
            .sum()
    }

    fn index(&self, account: i32) -> Option<usize> {
        usize::try_from(account)
            .ok()
            .filter(|&account| account < self.balances.len())
    }
}
