//! `Bank`, the type that `cstudy submit` and the tests drive.

use std::cmp::Reverse;

use crate::account::Account;
use crate::ledger::{AccountKey, Ledger};
use crate::schedule::{Scheduler, Ticket};

/// What a failed call returns where a balance is expected.
const FAILED: i64 = -1;
const TRANSFER_ID_PREFIX: &str = "transfer";

/// A transfer waiting to run, between the accounts it was booked with.
#[derive(Clone, Copy, Debug)]
struct BookedTransfer {
    source: AccountKey,
    target: AccountKey,
    amount: i64,
}

/// A set of bank accounts that hold whole amounts of money and send money to one another.
///
/// Every method first runs the scheduled transfers that fell due by its timestamp, so it sees
/// the bank as it is at that time.
#[derive(Default)]
pub struct Bank {
    ledger: Ledger,
    scheduler: Scheduler<BookedTransfer>,
}

impl Bank {
    /// A bank with no accounts.
    pub fn new() -> Self {
        Self::default()
    }

    /// Opens an account with balance 0; false when the id is taken or was ever merged away.
    pub fn create_account(&mut self, timestamp: i64, account_id: String) -> bool {
        self.settle(timestamp);
        self.ledger.open(account_id, timestamp)
    }

    /// Adds `amount` to the account and returns its new balance; -1 when there is no such
    /// account.
    pub fn deposit(&mut self, timestamp: i64, account_id: String, amount: i64) -> i64 {
        self.settle(timestamp);
        let Some(account) = self.ledger.find_open(&account_id) else {
            return FAILED;
        };
        self.ledger.deposit(account, amount, timestamp)
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
        self.settle(timestamp);
        let Some((source, target)) = self.open_pair(&source_id, &target_id) else {
            return FAILED;
        };
        self.ledger
            .send(source, target, amount, timestamp)
            .unwrap_or(FAILED)
    }

    /// The first `n` open accounts by money sent, largest first, then by id, as
    /// `"<id>(<total>)"`.
    pub fn top_spenders(&mut self, timestamp: i64, n: i32) -> Vec<String> {
        self.settle(timestamp);
        let mut ranked: Vec<&Account> = self.ledger.open_accounts().collect();
        // Ids are unique, so the key orders every pair and an unstable sort is enough.
        ranked.sort_unstable_by_key(|&account| (Reverse(account.sent()), account.id()));
        ranked
            .into_iter()
            .take(usize::try_from(n).unwrap_or(0))
            .map(|account| format!("{}({})", account.id(), account.sent()))
            .collect()
    }

    /// Books a transfer due at `timestamp + delay` and returns its id; `""` when either account
    /// is missing or both are the same. The source's balance is checked only when it runs.
    pub fn schedule_transfer(
        &mut self,
        timestamp: i64,
        source_id: String,
        target_id: String,
        amount: i64,
        delay: i64,
    ) -> String {
        self.settle(timestamp);
        let Some((source, target)) = self.open_pair(&source_id, &target_id) else {
            return String::new();
        };
        let booked = BookedTransfer {
            source,
            target,
            amount,
        };
        transfer_id(self.scheduler.book(timestamp + delay, booked))
    }

    /// Cancels a pending transfer; only the account that holds its source now may.
    pub fn cancel_transfer(
        &mut self,
        timestamp: i64,
        account_id: String,
        transfer_id: String,
    ) -> bool {
        self.settle(timestamp);
        let Some(ticket) = parse_transfer_id(&transfer_id) else {
            return false;
        };
        let Some(booked) = self.scheduler.pending(ticket) else {
            return false;
        };
        let sender = self.ledger.holder(booked.source);
        self.ledger.find_open(&account_id) == Some(sender) && self.scheduler.cancel(ticket)
    }

    /// Folds `other_id` into `account_id`; false, changing nothing, when the ids are equal or
    /// either account is missing.
    pub fn merge_accounts(&mut self, timestamp: i64, account_id: String, other_id: String) -> bool {
        self.settle(timestamp);
        let Some((kept, absorbed)) = self.open_pair(&account_id, &other_id) else {
            return false;
        };
        self.ledger.merge(kept, absorbed, timestamp);
        true
    }

    /// The account's balance at `time_at`; -1 when it did not exist then.
    pub fn get_balance(&mut self, timestamp: i64, account_id: String, time_at: i64) -> i64 {
        self.settle(timestamp);
        let Some(account) = self.ledger.find(&account_id) else {
            return FAILED;
        };
        self.ledger
            .account(account)
            .balance_at(time_at)
            .unwrap_or(FAILED)
    }

    /// Runs every scheduled transfer due at or before `now`, each at its own due time. One the
    /// source cannot pay, or whose ends a merge has joined, is skipped: `send` refuses it.
    fn settle(&mut self, now: i64) {
        while let Some((due, booked)) = self.scheduler.pop_due(now) {
            let source = self.ledger.holder(booked.source);
            let target = self.ledger.holder(booked.target);
            self.ledger.send(source, target, booked.amount, due);
        }
    }

    /// Both accounts, when both are open and distinct.
    fn open_pair(&self, first_id: &str, second_id: &str) -> Option<(AccountKey, AccountKey)> {
        let first = self.ledger.find_open(first_id)?;
        let second = self.ledger.find_open(second_id)?;
        (first != second).then_some((first, second))
    }
}

fn transfer_id(ticket: Ticket) -> String {
    format!("{TRANSFER_ID_PREFIX}{}", ticket.0)
}

/// The ticket of an id that `transfer_id` wrote. `parse` also takes `+7` and `007`, which name
/// no transfer, so the number must read back as the same text.
fn parse_transfer_id(id: &str) -> Option<Ticket> {
    let digits = id.strip_prefix(TRANSFER_ID_PREFIX)?;
    let number: u64 = digits.parse().ok()?;
    (number.to_string() == digits).then_some(Ticket(number))
}

#[cfg(test)]
mod tests {
    use super::{parse_transfer_id, transfer_id};
    use crate::schedule::Ticket;

    #[test]
    fn a_transfer_id_reads_back_as_its_ticket() {
        assert_eq!(
            parse_transfer_id(&transfer_id(Ticket(12))),
            Some(Ticket(12))
        );
    }

    #[test]
    fn an_id_with_a_leading_zero_names_no_transfer() {
        assert_eq!(parse_transfer_id("transfer012"), None);
    }

    #[test]
    fn an_id_with_a_plus_sign_names_no_transfer() {
        assert_eq!(parse_transfer_id("transfer+3"), None);
    }

    #[test]
    fn an_id_without_the_prefix_names_no_transfer() {
        assert_eq!(parse_transfer_id("12"), None);
    }
}
