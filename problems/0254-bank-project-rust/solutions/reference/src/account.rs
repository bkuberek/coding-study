//! One bank account: its money, the money it has sent, its history and its lifetime.

use crate::history::History;

/// What an account hands over when it is merged into another.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Holdings {
    pub balance: i64,
    pub sent: i64,
}

/// One bank account. Every change of its balance is recorded at the moment it took effect.
#[derive(Debug)]
pub struct Account {
    id: String,
    balance: i64,
    sent: i64,
    history: History,
    closed_at: Option<i64>,
}

impl Account {
    /// A new account with balance 0 from `at` on.
    pub fn open(id: String, at: i64) -> Self {
        let mut history = History::default();
        history.record(at, 0);
        Account {
            id,
            balance: 0,
            sent: 0,
            history,
            closed_at: None,
        }
    }

    pub fn id(&self) -> &str {
        &self.id
    }

    pub fn balance(&self) -> i64 {
        self.balance
    }

    /// The total of the money that has left this account, the accounts it absorbed included.
    pub fn sent(&self) -> i64 {
        self.sent
    }

    /// False from the moment the account is merged into another.
    pub fn is_open(&self) -> bool {
        self.closed_at.is_none()
    }

    /// Money in, a deposit or a transfer received; returns the new balance.
    pub fn credit(&mut self, amount: i64, at: i64) -> i64 {
        self.change_balance(amount, at)
    }

    /// Money sent to another account; returns the new balance.
    pub fn debit(&mut self, amount: i64, at: i64) -> i64 {
        self.sent += amount;
        self.change_balance(-amount, at)
    }

    /// Closes the account at `at`, handing over its balance and its total sent. Its history
    /// still answers for the moments before `at`.
    pub fn close(&mut self, at: i64) -> Holdings {
        self.closed_at = Some(at);
        Holdings {
            balance: self.balance,
            sent: self.sent,
        }
    }

    /// Takes over what a merged account handed over, from `at` on.
    pub fn absorb(&mut self, holdings: Holdings, at: i64) {
        self.sent += holdings.sent;
        self.change_balance(holdings.balance, at);
    }

    /// The balance at `moment`; `None` before the account was opened and from its closing on.
    pub fn balance_at(&self, moment: i64) -> Option<i64> {
        if self.closed_at.is_some_and(|closed_at| moment >= closed_at) {
            return None;
        }
        self.history.at(moment)
    }

    fn change_balance(&mut self, delta: i64, at: i64) -> i64 {
        self.balance += delta;
        self.history.record(at, self.balance);
        self.balance
    }
}
