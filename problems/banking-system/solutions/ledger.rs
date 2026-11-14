use std::collections::{HashMap, VecDeque};

const CASHBACK_DELAY: i64 = 86_400_000;
const CASHBACK_PERCENT: i64 = 2;

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

struct Payment {
    account_id: String,
    cashback: i64,
    due: i64,
    received: bool,
}

pub struct BankingSystem {
    accounts: HashMap<String, Account>,
    merged_into: HashMap<String, String>,
    /// Payments in the order they were made, and the position of each by payment id.
    payments: Vec<Payment>,
    payment_positions: HashMap<String, usize>,
    /// Indexes of the unsettled payments. The delay is constant and timestamps increase, so
    /// cashbacks fall due in payment order.
    pending: VecDeque<usize>,
}

impl BankingSystem {
    pub fn new() -> Self {
        BankingSystem {
            accounts: HashMap::new(),
            merged_into: HashMap::new(),
            payments: Vec::new(),
            payment_positions: HashMap::new(),
            pending: VecDeque::new(),
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
        // Two accounts of one map cannot both be borrowed mutably, so validate first and then
        // touch them one at a time.
        let source_balance = match self.open_mut(&source_id) {
            Some(source) => source.balance,
            None => return -1,
        };
        if source_id == target_id || self.open_mut(&target_id).is_none() || source_balance < amount
        {
            return -1;
        }
        if let Some(target) = self.open_mut(&target_id) {
            target.change_balance(timestamp, amount);
        }
        match self.open_mut(&source_id) {
            Some(source) => {
                source.outgoing += amount;
                source.change_balance(timestamp, -amount)
            }
            None => -1,
        }
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
    pub fn pay(&mut self, timestamp: i64, account_id: String, amount: i64) -> String {
        self.settle(timestamp);
        match self.open_mut(&account_id) {
            Some(account) if account.balance >= amount => {
                account.change_balance(timestamp, -amount);
                account.outgoing += amount;
            }
            _ => return String::new(),
        }
        let payment_id = format!("payment{}", self.payments.len() + 1);
        self.payment_positions
            .insert(payment_id.clone(), self.payments.len());
        self.pending.push_back(self.payments.len());
        self.payments.push(Payment {
            account_id,
            cashback: amount * CASHBACK_PERCENT / 100,
            due: timestamp + CASHBACK_DELAY,
            received: false,
        });
        payment_id
    }

    // Level 3
    pub fn payment_status(
        &mut self,
        timestamp: i64,
        account_id: String,
        payment_id: String,
    ) -> String {
        self.settle(timestamp);
        let Some(&position) = self.payment_positions.get(&payment_id) else {
            return String::new();
        };
        let payment = &self.payments[position];
        if !self.is_open(&account_id) || self.owner(&payment.account_id) != account_id {
            return String::new();
        }
        let status = if payment.received {
            "CASHBACK_RECEIVED"
        } else {
            "IN_PROGRESS"
        };
        status.to_string()
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

    /// Credits every cashback due at or before `timestamp`, at its own due time.
    fn settle(&mut self, timestamp: i64) {
        while let Some(&index) = self.pending.front() {
            if self.payments[index].due > timestamp {
                break;
            }
            self.pending.pop_front();
            let (due, cashback) = (self.payments[index].due, self.payments[index].cashback);
            let owner = self.owner(&self.payments[index].account_id).to_string();
            if let Some(account) = self.accounts.get_mut(&owner) {
                account.change_balance(due, cashback);
            }
            self.payments[index].received = true;
        }
    }
}
