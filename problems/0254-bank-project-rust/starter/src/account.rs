//! One bank account. Grow it as the levels add rules, or replace it.

/// One bank account and the money it holds.
#[derive(Debug)]
pub struct Account {
    pub id: String,
    pub balance: i64,
}
