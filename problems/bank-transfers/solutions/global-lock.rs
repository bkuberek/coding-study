use std::sync::Mutex;

/// One mutex guards every balance, so a transfer and an audit never overlap.
pub struct Bank {
    balances: Mutex<Vec<i64>>,
}

impl Bank {
    pub fn new(balances: Vec<i64>) -> Self {
        Bank {
            balances: Mutex::new(balances),
        }
    }

    pub fn transfer(&self, from_account: i32, to_account: i32, amount: i64) -> bool {
        let mut balances = self.balances.lock().unwrap();
        let (Some(from), Some(to)) = (index(&balances, from_account), index(&balances, to_account))
        else {
            return false;
        };
        if balances[from] < amount {
            return false;
        }
        balances[from] -= amount;
        balances[to] += amount;
        true
    }

    pub fn balance(&self, account: i32) -> i64 {
        let balances = self.balances.lock().unwrap();
        index(&balances, account).map_or(-1, |account| balances[account])
    }

    pub fn total(&self) -> i64 {
        self.balances.lock().unwrap().iter().sum()
    }
}

fn index(balances: &[i64], account: i32) -> Option<usize> {
    usize::try_from(account)
        .ok()
        .filter(|&account| account < balances.len())
}
