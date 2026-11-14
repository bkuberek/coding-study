//! A small bank whose API grows one level at a time.

/// Accounts that hold a balance.
pub struct Bank {}

impl Bank {
    pub fn new() -> Self {
        Bank {}
    }

    pub fn create_account(&mut self, timestamp: i64, account_id: String) -> bool {
        todo!()
    }

    pub fn deposit(&mut self, timestamp: i64, account_id: String, amount: i64) -> i64 {
        todo!()
    }
}
