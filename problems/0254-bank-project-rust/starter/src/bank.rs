//! `Bank`, the type that `cstudy submit` and the tests drive.

use std::collections::HashMap;

use crate::account::Account;

/// A set of bank accounts that hold whole amounts of money and send money to one another.
#[derive(Default)]
pub struct Bank {
    accounts: HashMap<String, Account>,
}

impl Bank {
    /// A bank with no accounts.
    pub fn new() -> Self {
        Self::default()
    }

    /// Opens an account with balance 0; false when the id is taken.
    pub fn create_account(&mut self, timestamp: i64, account_id: String) -> bool {
        todo!()
    }

    /// Adds `amount` to the account and returns its new balance; -1 when there is no such
    /// account.
    pub fn deposit(&mut self, timestamp: i64, account_id: String, amount: i64) -> i64 {
        todo!()
    }

    /// Moves `amount` from the source account to the target account and returns the source's
    /// new balance; -1, changing nothing, when it cannot.
    pub fn transfer(
        &mut self,
        timestamp: i64,
        source_id: String,
        target_id: String,
        amount: i64,
    ) -> i64 {
        todo!()
    }
}
