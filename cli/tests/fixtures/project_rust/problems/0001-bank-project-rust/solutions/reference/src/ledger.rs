//! The balances of the accounts, by account id.

use std::collections::HashMap;

#[derive(Default)]
pub struct Ledger {
    balances: HashMap<String, i64>,
}

impl Ledger {
    /// Opens an account with balance 0; false when the id is taken.
    pub fn open(&mut self, account_id: String) -> bool {
        if self.balances.contains_key(&account_id) {
            return false;
        }
        self.balances.insert(account_id, 0);
        true
    }

    /// The new balance, or None for an unknown account.
    pub fn add(&mut self, account_id: &str, amount: i64) -> Option<i64> {
        let balance = self.balances.get_mut(account_id)?;
        *balance += amount;
        Some(*balance)
    }

    /// The source's new balance, or None when the move is refused.
    pub fn move_between(&mut self, source_id: &str, target_id: &str, amount: i64) -> Option<i64> {
        let known = self.balances.contains_key(target_id);
        let source = *self.balances.get(source_id)?;
        if !known || source_id == target_id || source < amount {
            return None;
        }
        self.add(target_id, amount);
        self.add(source_id, -amount)
    }
}
