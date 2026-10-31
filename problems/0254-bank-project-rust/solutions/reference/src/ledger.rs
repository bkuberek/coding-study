//! Every account ever opened, by id, and where each merged account went.

use std::collections::hash_map::Entry;
use std::collections::HashMap;

use crate::account::Account;

/// An account's place in the ledger. It stays valid after a merge: the account is closed, never
/// removed.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub struct AccountKey(usize);

/// The accounts, open or merged away. Callers check a request first; the methods that change
/// money take keys of open accounts.
#[derive(Debug, Default)]
pub struct Ledger {
    accounts: Vec<Account>,
    keys: HashMap<String, AccountKey>,
    merged_into: HashMap<AccountKey, AccountKey>,
}

impl Ledger {
    /// Opens an account with balance 0; false when the id was ever taken, by an account merged
    /// away since included.
    pub fn open(&mut self, id: String, at: i64) -> bool {
        match self.keys.entry(id) {
            Entry::Occupied(_) => false,
            Entry::Vacant(entry) => {
                let key = AccountKey(self.accounts.len());
                self.accounts.push(Account::open(entry.key().clone(), at));
                entry.insert(key);
                true
            }
        }
    }

    /// The account opened with `id`, even one merged away since.
    pub fn find(&self, id: &str) -> Option<AccountKey> {
        self.keys.get(id).copied()
    }

    /// The account opened with `id`, unless it was merged away.
    pub fn find_open(&self, id: &str) -> Option<AccountKey> {
        self.find(id).filter(|&key| self.account(key).is_open())
    }

    pub fn account(&self, key: AccountKey) -> &Account {
        &self.accounts[key.0]
    }

    /// The accounts that were not merged away, in the order they were opened.
    pub fn open_accounts(&self) -> impl Iterator<Item = &Account> {
        self.accounts.iter().filter(|account| account.is_open())
    }

    /// The open account that holds `key` now, following merges.
    pub fn holder(&self, key: AccountKey) -> AccountKey {
        let mut holder = key;
        while let Some(&next) = self.merged_into.get(&holder) {
            holder = next;
        }
        holder
    }

    /// Adds `amount` to the account and returns its new balance.
    pub fn deposit(&mut self, key: AccountKey, amount: i64, at: i64) -> i64 {
        self.account_mut(key).credit(amount, at)
    }

    /// Moves `amount` and returns the source's new balance; `None`, changing nothing, when
    /// both are one account or the source holds less than `amount`.
    pub fn send(
        &mut self,
        source: AccountKey,
        target: AccountKey,
        amount: i64,
        at: i64,
    ) -> Option<i64> {
        if source == target || self.account(source).balance() < amount {
            return None;
        }
        self.account_mut(target).credit(amount, at);
        Some(self.account_mut(source).debit(amount, at))
    }

    /// Folds `absorbed` into `kept` at `at`; both must be open and distinct.
    pub fn merge(&mut self, kept: AccountKey, absorbed: AccountKey, at: i64) {
        let holdings = self.account_mut(absorbed).close(at);
        self.account_mut(kept).absorb(holdings, at);
        self.merged_into.insert(absorbed, kept);
    }

    fn account_mut(&mut self, key: AccountKey) -> &mut Account {
        &mut self.accounts[key.0]
    }
}

#[cfg(test)]
mod tests {
    use super::{AccountKey, Ledger};

    fn ledger_with(ids: &[&str]) -> (Ledger, Vec<AccountKey>) {
        let mut ledger = Ledger::default();
        for (at, id) in (1..).zip(ids) {
            ledger.open(id.to_string(), at);
        }
        let keys = ids.iter().map(|id| ledger.find(id).unwrap()).collect();
        (ledger, keys)
    }

    #[test]
    fn an_id_opens_one_account() {
        let (mut ledger, _) = ledger_with(&["ivy"]);
        assert!(!ledger.open("ivy".to_string(), 5));
    }

    #[test]
    fn a_second_open_keeps_the_balance() {
        let (mut ledger, keys) = ledger_with(&["ivy"]);
        ledger.deposit(keys[0], 40, 2);
        ledger.open("ivy".to_string(), 3);
        assert_eq!(ledger.account(keys[0]).balance(), 40);
    }

    #[test]
    fn a_merged_away_id_never_opens_again() {
        let (mut ledger, keys) = ledger_with(&["a", "b"]);
        ledger.merge(keys[0], keys[1], 5);
        assert!(!ledger.open("b".to_string(), 6));
    }

    #[test]
    fn a_merged_away_account_is_found_but_not_open() {
        let (mut ledger, keys) = ledger_with(&["a", "b"]);
        ledger.merge(keys[0], keys[1], 5);
        assert_eq!(
            (ledger.find("b"), ledger.find_open("b")),
            (Some(keys[1]), None)
        );
    }

    #[test]
    fn a_holder_follows_a_chain_of_merges() {
        let (mut ledger, keys) = ledger_with(&["a", "b", "c"]);
        ledger.merge(keys[1], keys[2], 5);
        ledger.merge(keys[0], keys[1], 6);
        assert_eq!(ledger.holder(keys[2]), keys[0]);
    }

    #[test]
    fn an_open_account_holds_itself() {
        let (ledger, keys) = ledger_with(&["a"]);
        assert_eq!(ledger.holder(keys[0]), keys[0]);
    }

    #[test]
    fn a_merge_adds_the_balance_and_the_money_sent() {
        let (mut ledger, keys) = ledger_with(&["a", "b", "c"]);
        ledger.deposit(keys[1], 50, 4);
        ledger.send(keys[1], keys[2], 20, 5);
        ledger.merge(keys[0], keys[1], 6);
        let kept = ledger.account(keys[0]);
        assert_eq!((kept.balance(), kept.sent()), (30, 20));
    }

    #[test]
    fn rankings_see_only_open_accounts() {
        let (mut ledger, keys) = ledger_with(&["a", "b", "c"]);
        ledger.merge(keys[2], keys[0], 5);
        let ids: Vec<&str> = ledger.open_accounts().map(|account| account.id()).collect();
        assert_eq!(ids, ["b", "c"]);
    }

    #[test]
    fn a_send_to_the_same_account_is_refused() {
        let (mut ledger, keys) = ledger_with(&["a"]);
        ledger.deposit(keys[0], 50, 2);
        assert_eq!(ledger.send(keys[0], keys[0], 10, 3), None);
    }

    #[test]
    fn a_send_beyond_the_balance_changes_nothing() {
        let (mut ledger, keys) = ledger_with(&["a", "b"]);
        ledger.deposit(keys[0], 50, 3);
        ledger.send(keys[0], keys[1], 51, 4);
        let balances = (
            ledger.account(keys[0]).balance(),
            ledger.account(keys[1]).balance(),
        );
        assert_eq!(balances, (50, 0));
    }

    #[test]
    fn a_merged_away_account_answers_for_the_time_before_the_merge() {
        let (mut ledger, keys) = ledger_with(&["a", "b"]);
        ledger.deposit(keys[1], 9, 4);
        ledger.merge(keys[0], keys[1], 10);
        let before_and_after = (
            ledger.account(keys[1]).balance_at(9),
            ledger.account(keys[1]).balance_at(10),
        );
        assert_eq!(before_and_after, (Some(9), None));
    }
}
