//! A small bank whose API grows one level at a time.

mod ledger;

use ledger::Ledger;

/// Accounts that hold a balance, keyed by account id.
pub struct Bank {
    ledger: Ledger,
}

impl Bank {
    pub fn new() -> Self {
        Bank {
            ledger: Ledger::default(),
        }
    }

    pub fn create_account(&mut self, _timestamp: i64, account_id: String) -> bool {
        self.ledger.open(account_id)
    }

    pub fn deposit(&mut self, _timestamp: i64, account_id: String, amount: i64) -> i64 {
        self.ledger.add(&account_id, amount).unwrap_or(-1)
    }

    pub fn transfer(
        &mut self,
        _timestamp: i64,
        source_id: String,
        target_id: String,
        amount: i64,
    ) -> i64 {
        self.ledger
            .move_between(&source_id, &target_id, amount)
            .unwrap_or(-1)
    }
}
