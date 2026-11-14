use std::cmp::Reverse;
use std::collections::{BinaryHeap, HashMap};

struct Account {
    id: String,
    created_at: i64,
    balance: i64,
    outgoing: i64,
    closed_at: Option<i64>,
    /// `(time, balance after the change)` in time order: the account's balance history.
    history: Vec<(i64, i64)>,
}

impl Account {
    fn new(id: String, created_at: i64) -> Self {
        Account {
            id,
            created_at,
            balance: 0,
            outgoing: 0,
            closed_at: None,
            history: vec![(created_at, 0)],
        }
    }

    fn change_balance(&mut self, timestamp: i64, delta: i64) -> i64 {
        self.balance += delta;
        self.history.push((timestamp, self.balance));
        self.balance
    }

    fn balance_at(&self, moment: i64) -> i64 {
        let closed = self.closed_at.is_some_and(|closed_at| moment >= closed_at);
        if moment < self.created_at || closed {
            return -1;
        }
        let position = self.history.partition_point(|&(time, _)| time <= moment);
        self.history[position - 1].1
    }
}

struct ScheduledTransfer {
    source_id: String,
    target_id: String,
    amount: i64,
    pending: bool,
}

pub struct Bank {
    accounts: HashMap<String, Account>,
    merged_into: HashMap<String, String>,
    /// Transfers in the order they were scheduled, and the position of each by transfer id.
    transfers: Vec<ScheduledTransfer>,
    transfer_positions: HashMap<String, usize>,
    /// `(due, position)` of the transfers not yet run. `BinaryHeap` is a max-heap, so `Reverse`
    /// puts the earliest due first, ties in scheduling order. A cancelled transfer stays here
    /// until it reaches the top.
    due: BinaryHeap<Reverse<(i64, usize)>>,
}

impl Bank {
    pub fn new() -> Self {
        Bank {
            accounts: HashMap::new(),
            merged_into: HashMap::new(),
            transfers: Vec::new(),
            transfer_positions: HashMap::new(),
            due: BinaryHeap::new(),
        }
    }

    // Level 1
    pub fn create_account(&mut self, timestamp: i64, account_id: String) -> bool {
        self.settle(timestamp);
        if self.accounts.contains_key(&account_id) {
            return false;
        }
        let account = Account::new(account_id.clone(), timestamp);
        self.accounts.insert(account_id, account);
        true
    }

    // Level 1
    pub fn deposit(&mut self, timestamp: i64, account_id: String, amount: i64) -> i64 {
        self.settle(timestamp);
        match self.open_mut(&account_id) {
            Some(account) => account.change_balance(timestamp, amount),
            None => -1,
        }
    }

    // Level 1
    pub fn transfer(
        &mut self,
        timestamp: i64,
        source_id: String,
        target_id: String,
        amount: i64,
    ) -> i64 {
        self.settle(timestamp);
        self.send(&source_id, &target_id, amount, timestamp)
            .unwrap_or(-1)
    }

    // Level 2
    pub fn top_spenders(&mut self, timestamp: i64, n: i32) -> Vec<String> {
        self.settle(timestamp);
        let mut ranked: Vec<&Account> = self
            .accounts
            .values()
            .filter(|account| account.closed_at.is_none())
            .collect();
        ranked.sort_by(|a, b| b.outgoing.cmp(&a.outgoing).then_with(|| a.id.cmp(&b.id)));
        ranked
            .into_iter()
            .take(usize::try_from(n).unwrap_or(0))
            .map(|account| format!("{}({})", account.id, account.outgoing))
            .collect()
    }

    // Level 3
    pub fn schedule_transfer(
        &mut self,
        timestamp: i64,
        source_id: String,
        target_id: String,
        amount: i64,
        delay: i64,
    ) -> String {
        self.settle(timestamp);
        if source_id == target_id || !self.is_open(&source_id) || !self.is_open(&target_id) {
            return String::new();
        }
        let position = self.transfers.len();
        let transfer_id = format!("transfer{}", position + 1);
        let due = timestamp + delay;
        self.transfer_positions
            .insert(transfer_id.clone(), position);
        self.due.push(Reverse((due, position)));
        self.transfers.push(ScheduledTransfer {
            source_id,
            target_id,
            amount,
            pending: true,
        });
        transfer_id
    }

    // Level 3
    pub fn cancel_transfer(
        &mut self,
        timestamp: i64,
        account_id: String,
        transfer_id: String,
    ) -> bool {
        self.settle(timestamp);
        let Some(&position) = self.transfer_positions.get(&transfer_id) else {
            return false;
        };
        let scheduled = &self.transfers[position];
        if !self.is_open(&account_id)
            || !scheduled.pending
            || self.owner(&scheduled.source_id) != account_id
        {
            return false;
        }
        self.transfers[position].pending = false;
        true
    }

    // Level 4
    pub fn merge_accounts(&mut self, timestamp: i64, account_id: String, other_id: String) -> bool {
        self.settle(timestamp);
        if account_id == other_id || self.open_mut(&account_id).is_none() {
            return false;
        }
        let (other_balance, other_outgoing) = match self.open_mut(&other_id) {
            Some(other) => {
                other.closed_at = Some(timestamp);
                (other.balance, other.outgoing)
            }
            None => return false,
        };
        if let Some(account) = self.open_mut(&account_id) {
            account.change_balance(timestamp, other_balance);
            account.outgoing += other_outgoing;
        }
        self.merged_into.insert(other_id, account_id);
        true
    }

    // Level 4
    pub fn get_balance(&mut self, timestamp: i64, account_id: String, time_at: i64) -> i64 {
        self.settle(timestamp);
        self.accounts
            .get(&account_id)
            .map_or(-1, |account| account.balance_at(time_at))
    }

    fn is_open(&self, account_id: &str) -> bool {
        self.accounts
            .get(account_id)
            .is_some_and(|account| account.closed_at.is_none())
    }

    /// The account when it exists and has not been merged away.
    fn open_mut(&mut self, account_id: &str) -> Option<&mut Account> {
        self.accounts
            .get_mut(account_id)
            .filter(|account| account.closed_at.is_none())
    }

    /// The open account that now holds `account_id`, following merges.
    fn owner<'a>(&'a self, mut account_id: &'a str) -> &'a str {
        while let Some(next) = self.merged_into.get(account_id) {
            account_id = next;
        }
        account_id
    }

    /// Moves `amount` between two distinct open accounts at `moment` and returns the source's new
    /// balance, or `None`, changing nothing, when either account is missing, they are the same
    /// account or the source holds less than `amount`. Two accounts of one map cannot be borrowed
    /// mutably at once, so it validates first and then touches them one at a time.
    fn send(&mut self, source_id: &str, target_id: &str, amount: i64, moment: i64) -> Option<i64> {
        let source_balance = self.open_mut(source_id)?.balance;
        if source_id == target_id || source_balance < amount {
            return None;
        }
        self.open_mut(target_id)?.change_balance(moment, amount);
        let source = self.open_mut(source_id)?;
        source.outgoing += amount;
        Some(source.change_balance(moment, -amount))
    }

    /// Runs every scheduled transfer due at or before `timestamp`, each at its own due time.
    fn settle(&mut self, timestamp: i64) {
        while let Some(&Reverse((due, position))) = self.due.peek() {
            if due > timestamp {
                break;
            }
            self.due.pop();
            if !self.transfers[position].pending {
                continue;
            }
            self.transfers[position].pending = false;
            let scheduled = &self.transfers[position];
            let source = self.owner(&scheduled.source_id).to_string();
            let target = self.owner(&scheduled.target_id).to_string();
            let amount = scheduled.amount;
            // A skipped transfer (same account after a merge, or too little money) changes nothing.
            let _ = self.send(&source, &target, amount, due);
        }
    }
}
